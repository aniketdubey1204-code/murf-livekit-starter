import asyncio
import json
import logging
import os

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    RunContext,
    cli,
    function_tool,
    tokenize,
    room_io,
    UserInputTranscribedEvent,
)
from livekit.agents.inference import TurnDetector
from livekit.plugins import murf, silero, openai, deepgram, noise_cancellation

logger = logging.getLogger("agent")

load_dotenv(".env.local")

try:
    from prompt import SYSTEM_PROMPT
except ImportError:
    from src.prompt import SYSTEM_PROMPT

try:
    from db import init_db, lookup_caller, save_caller
except ImportError:
    from src.db import init_db, lookup_caller, save_caller

try:
    from prices import check_price, check_availability
except ImportError:
    from src.prices import check_price, check_availability

# Default greeting for new callers (Hinglish - safe ASCII)
DEFAULT_GREETING = (
    "Namaste! Main Dukaan Sathi hoon, aapki local dukaan ki digital sahayika. "
    "Bataiye, aaj aapko kya saman chahiye ya store ke baare mein kya jaankari chahiye?"
)


class Assistant(Agent):
    def __init__(self, caller_context: str = "") -> None:
        # Inject caller context into the system prompt so the agent knows
        # whether this is a new or returning caller right from the start.
        full_prompt = SYSTEM_PROMPT
        if caller_context:
            full_prompt += f"\n\nCALLER CONTEXT:\n{caller_context}"
        super().__init__(instructions=full_prompt)

    @function_tool
    async def lookup_caller_tool(self, context: RunContext, user_id: str):
        """Look up a caller in the database to check if they are a returning customer.

        Args:
            user_id: The unique identifier of the caller (participant identity or phone number).
        """
        logger.info(f"Tool call: looking up caller {user_id}")
        result = await lookup_caller(user_id)
        if result is None:
            return "No record found. This is a new caller."
        return json.dumps(result, ensure_ascii=False)

    @function_tool
    async def save_caller_info(
        self,
        context: RunContext,
        user_id: str,
        name: str,
        language_preference: str,
        facts: str,
    ):
        """Save caller information to the database. IMPORTANT: Only call this
        AFTER the caller has given explicit verbal consent to save their data.

        Args:
            user_id: The unique identifier of the caller.
            name: The caller's name.
            language_preference: Preferred language - hi, en, or hinglish.
            facts: A JSON string of facts to remember, e.g. {"past_orders": "5 kg aata, 2 kg cheeni", "area": "Sector 4", "preferred_delivery_slot": "morning"}.
        """
        logger.info(f"Tool call: saving caller info for {name} ({user_id})")
        try:
            facts_dict = json.loads(facts) if isinstance(facts, str) else facts
        except json.JSONDecodeError:
            facts_dict = {"notes": facts}

        result = await save_caller(
            user_id=user_id,
            name=name,
            language_pref=language_preference,
            facts=facts_dict,
        )
        return f"Caller profile saved successfully for {name}."

    @function_tool
    async def check_item_price(self, context: RunContext, item_name: str):
        """Check the retail price of an item in the store."""
        logger.info(f"Tool call: checking price for '{item_name}'")
        result = await check_price(item_name)
        return result

    @function_tool
    async def check_item_availability(self, context: RunContext, item_name: str):
        """Check if an item is available in the store."""
        logger.info(f"Tool call: checking availability for '{item_name}'")
        result = await check_availability(item_name)
        return result


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()
    # Initialize the caller database at startup.
    # Use asyncio.run() because prewarm runs in a background thread
    # (no current event loop), so get_event_loop() would fail here.
    asyncio.run(init_db())
    logger.info("Caller database initialised during prewarm")


server.setup_fnc = prewarm


@server.rtc_session(agent_name="my-agent")
async def my_agent(ctx: JobContext):
    # Logging setup
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Set up a voice AI pipeline
    session = AgentSession(
        stt=deepgram.STT(
            model="nova-3",
            language="multi",
            smart_format=True,
            keyterm=[
                "dukaan", "bhaiya", "kirana", "aata", "chawal", "cheeni",
                "dal", "tel", "saman", "order", "price", "rate", "delivery",
                "udhaar", "batao", "bataiye", "kitna", "kab", "namaste",
                "shukriya", "rupee", "kilo",
            ],
        ),
        llm=openai.LLM(
            model="llama-3.1-8b-instant",
            base_url="https://api.groq.com/openai/v1",
            api_key=os.getenv("GROQ_API_KEY"),
        ),
        tts=murf.TTS(
            voice="en-IN-anisha",
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
            text_pacing=True,
        ),
        turn_detection=TurnDetector(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
    )

    @session.on("user_input_transcribed")
    def on_user_input_transcribed(ev: UserInputTranscribedEvent):
        transcript = ev.transcript.strip().lower()
        if not transcript:
            return

        has_devanagari = any(
            0x0900 <= ord(c) <= 0x097F for c in transcript
        )

        hindi_keywords = {
            "kya", "hai", "aur", "main", "haan", "nahin", "aap",
            "namaste", "shukriya", "dukaan", "bhaiya", "kirana", "aata",
            "chawal", "cheeni", "dal", "saman", "order", "rate",
            "delivery", "udhaar", "batao", "bataiye", "samjhao", "mein",
            "ke", "ki", "se", "ko", "ka", "jo", "toh", "bhi", "ho",
            "kar", "raha", "rahi", "rha", "rhi", "mujhe", "mera",
            "meri", "hum", "tum", "apna", "apni", "karke", "karo",
            "karna", "tha", "thi", "the", "ab", "kab", "tab", "sab",
            "kitna",
        }
        words = set(transcript.split())
        has_hindi_words = not words.isdisjoint(hindi_keywords)

        current_voice = getattr(session.tts, "_current_voice", "en-IN-anisha")

        if has_devanagari:
            if current_voice != "hi-IN-anisha":
                logger.info(
                    "Detected Devanagari: '%s'. Switching to hi-IN-anisha",
                    ev.transcript,
                )
                session.tts.update_options(voice="hi-IN-anisha")
                session.tts._current_voice = "hi-IN-anisha"
        else:
            if current_voice != "en-IN-anisha":
                logger.info(
                    "Detected English/Hinglish: '%s'. Switching to en-IN-anisha",
                    ev.transcript,
                )
                session.tts.update_options(voice="en-IN-anisha")
                session.tts._current_voice = "en-IN-anisha"

    # Connect to the room first
    await ctx.connect()

    # --- Caller Memory: Auto-lookup & Outbound Detection ---
    is_outbound = ctx.room.name.startswith("outbound")
    outbound_greeting = "Namaste, main Dukaan Sathi se baat kar rahi hoon. Main aapko yaad dilane ke liye call kar rahi hoon ki aapka pichla order khatam hone wala hai. Agar aap aisi calls nahi chahte, toh kripya 'stop' bole."
    
    caller_context = ""
    caller_data = None
    greeting = outbound_greeting if is_outbound else DEFAULT_GREETING

    if is_outbound:
        logger.info("Outbound call detected. Using outbound greeting.")

    # Get the remote participant's identity
    participant = None
    for p in ctx.room.remote_participants.values():
        participant = p
        break

    if participant is None:
        # Wait for a participant to connect
        try:
            participant = await asyncio.wait_for(
                _wait_for_participant(ctx),
                timeout=10.0,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "No participant joined within timeout, using default greeting"
            )

    if participant:
        caller_id = participant.identity
        logger.info("Caller connected with identity: %s", caller_id)

        # Look up the caller in the database
        caller_data = await lookup_caller(caller_id)

        if caller_data:
            # Returning caller - build personalised context
            name = caller_data.get("name", "")
            facts = caller_data.get("facts", {})
            last_seen = caller_data.get("last_interaction", "")

            caller_context = (
                f"This is a RETURNING caller. Their user_id is '{caller_id}'.\n"
                f"Name: {name}\n"
                f"Language preference: {caller_data.get('language_pref', 'hi')}\n"
                f"Known facts: {json.dumps(facts, ensure_ascii=False)}\n"
                f"Last interaction: {last_seen}\n"
                f"Greet them warmly by name and reference what you know."
            )

            # Build a personalised greeting if it's an inbound call
            if not is_outbound:
                facts_summary = ""
                if facts.get("past_orders"):
                    facts_summary = (
                        f" Pichli baar aapne {facts['past_orders']} manga tha."
                    )
                greeting = f"Namaste {name}!{facts_summary} Aaj kya chahiye?"

            logger.info("Returning caller: %s, facts: %s", name, facts)
        else:
            caller_context = (
                f"This is a NEW caller. Their user_id is '{caller_id}'.\n"
                "Use the standard greeting. Try to learn their name "
                "during the conversation.\n"
                "When you learn useful info, ask for their consent "
                "before saving it."
            )
            
    if is_outbound:
        caller_context += "\nNOTE: YOU INITIATED THIS CALL. It is an outbound restock reminder. Act proactively as the caller."

    # Start the session with caller context injected into the agent
    await session.start(
        agent=Assistant(caller_context=caller_context),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: (
                    noise_cancellation.BVCTelephony()
                    if params.participant.kind
                    == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                    else noise_cancellation.BVC()
                ),
            ),
        ),
    )

    # Send the appropriate greeting
    await session.say(greeting, allow_interruptions=True)


async def _wait_for_participant(ctx: JobContext):
    """Wait for a remote participant to join the room."""
    future = asyncio.get_event_loop().create_future()

    def on_participant_connected(participant):
        if not future.done():
            future.set_result(participant)

    ctx.room.on("participant_connected", on_participant_connected)

    # Check if someone already connected while we were setting up
    for p in ctx.room.remote_participants.values():
        if not future.done():
            future.set_result(p)
            break

    return await future


if __name__ == "__main__":
    cli.run_app(server)
