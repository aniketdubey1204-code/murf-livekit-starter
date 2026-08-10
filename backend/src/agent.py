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

# Default greeting for new callers (Devanagari Hindi for native TTS)
DEFAULT_GREETING = (
    "नमस्ते! मैं दुकान साथी हूँ, आपकी लोकल दुकान की डिजिटल सहायिका। "
    "बताइए, आज आपको क्या सामान चाहिए या स्टोर के बारे में क्या जानकारी चाहिए?"
)


class CleanGroqLLM(openai.LLM):
    def chat(self, *args, **kwargs):
        stream = super().chat(*args, **kwargs)
        orig_anext = stream.__anext__

        async def _clean_anext():
            chunk = await orig_anext()
            if chunk and chunk.choices:
                for c in chunk.choices:
                    if c.delta and c.delta.content:
                        content = c.delta.content
                        if "<function=" in content or "{" in content:
                            content = re.sub(r'<function=.*?>', '', content, flags=re.DOTALL)
                            content = re.sub(r'\{"(name|user_id|item_name|language_preference|facts)":.*', '', content, flags=re.DOTALL)
                            content = re.sub(r'<function=.*', '', content, flags=re.DOTALL)
                            c.delta.content = content
            return chunk

        stream.__anext__ = _clean_anext
        return stream


class Assistant(Agent):
    def __init__(self, caller_context: str = "") -> None:
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
            facts: A JSON string of facts to remember, e.g. {"past_orders": "5 kg aata, 2 kg cheeni", "area": "Sector 4"}.
        """
        logger.info(f"Tool call: saving caller info for {name} ({user_id})")
        if isinstance(facts, dict):
            facts_dict = facts
        elif isinstance(facts, str):
            try:
                facts_dict = json.loads(facts)
            except json.JSONDecodeError:
                facts_dict = {"notes": facts}
        else:
            facts_dict = {}

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
    asyncio.run(init_db())
    logger.info("Caller database initialised during prewarm")


server.setup_fnc = prewarm


@server.rtc_session(agent_name="my-agent")
async def my_agent(ctx: JobContext):
    # Logging setup
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Set up a voice AI pipeline with pure Hindi TTS (hi-IN-anisha)
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
        llm=CleanGroqLLM(
            model="llama-3.3-70b-versatile",
            base_url="https://api.groq.com/openai/v1",
            api_key=os.getenv("GROQ_API_KEY"),
        ),
        tts=murf.TTS(
            voice="hi-IN-anisha",
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
            text_pacing=True,
        ),
        turn_detection=TurnDetector(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
    )
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
    )

    # Connect to the room first
    await ctx.connect()

    # --- Caller Memory: Auto-lookup & Outbound Detection ---
    is_outbound = ctx.room.name.startswith("outbound")
    outbound_greeting = (
        "नमस्ते, मैं दुकान साथी से बात कर रही हूँ। मैं आपको याद दिलाने के लिए कॉल कर रही हूँ कि आपका पिछला ऑर्डर खत्म होने वाला है। अगर आप ऐसी कॉल्स नहीं चाहते, तो कृपया 'स्टॉप' बोलें।"
    )
    
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
                        f" पिछली बार आपने {facts['past_orders']} लिया था।"
                    )
                greeting = f"नमस्ते {name} जी!{facts_summary} आज आपको क्या सामान चाहिए?"

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
