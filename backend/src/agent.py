import asyncio
import json
import logging
import os
import re
import sys
import uuid
from datetime import datetime, timezone

# Enforce UTF-8 encoding for stdout/stderr to prevent Windows cp1252 crash when logging Hindi text
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    ChatContext,
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
    from prompt import SYSTEM_PROMPT, RETURNS_SPECIALIST_PROMPT
except ImportError:
    from src.prompt import SYSTEM_PROMPT, RETURNS_SPECIALIST_PROMPT


try:
    from db import init_db, lookup_caller, save_caller, create_escalation_record
except ImportError:
    from src.db import init_db, lookup_caller, save_caller, create_escalation_record

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
    def __init__(
        self,
        caller_context: str = "",
        caller_id: str = "unknown",
        call_state: dict | None = None,
        chat_ctx: ChatContext | None = None,
    ) -> None:
        full_prompt = SYSTEM_PROMPT
        if caller_context:
            full_prompt += f"\n\nCALLER CONTEXT:\n{caller_context}"
        # Store the real caller identity so tools (e.g. escalations) can link
        # records to the actual caller instead of a hardcoded placeholder.
        self._caller_id = caller_id or "unknown"
        # Day 8 analytics: shared mutable dict that tool calls update so the
        # shutdown handler can decide whether the call was a success.
        self._call_state = call_state if call_state is not None else {}
        super().__init__(instructions=full_prompt, chat_ctx=chat_ctx)


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
        # Analytics: caller engaged and consented to save their profile.
        self._call_state["tool_calls"] = self._call_state.get("tool_calls", 0) + 1
        self._call_state["saved_info"] = True
        return f"Caller profile saved successfully for {name}."

    @function_tool
    async def check_item_price(self, context: RunContext, item_name: str):
        """Check the retail price of an item in the store."""
        logger.info(f"Tool call: checking price for '{item_name}'")
        result = await check_price(item_name)
        self._track_lookup(result)
        return result

    @function_tool
    async def check_item_availability(self, context: RunContext, item_name: str):
        """Check if an item is available in the store."""
        logger.info(f"Tool call: checking availability for '{item_name}'")
        result = await check_availability(item_name)
        self._track_lookup(result)
        return result

    def _track_lookup(self, result: str) -> None:
        """Update analytics state after a price / availability lookup.

        The lookup helpers return an apology starting with "माफ़ कीजिये" when
        the item is NOT found. Anything else means the caller found a product,
        which counts towards a successful call for our kirana store.
        """
        self._call_state["tool_calls"] = self._call_state.get("tool_calls", 0) + 1
        if result and "माफ़ कीजिये" in result:
            self._call_state["not_found_count"] = self._call_state.get("not_found_count", 0) + 1
        else:
            self._call_state["found_product"] = True

    @function_tool
    async def create_escalation(
        self,
        context: RunContext,
        summary: str,
        urgency: str,
        language: str,
        follow_up: str = ""
    ):
        """
        Creates an escalation ticket for a human agent.
        Use this only AFTER getting explicit permission from the user to escalate.
        
        Args:
            summary: A brief summary of the issue, who the caller is, and what you checked.
            urgency: One of "low", "medium", "high", or "emergency".
            language: The caller's preferred language (e.g., "Hindi", "English").
            follow_up: The caller's preferred follow-up method, e.g. "phone call",
                "WhatsApp", "SMS", or "visit store". Ask the caller how they'd like
                to be contacted back.
            
        Returns:
            A success message containing the generated reference ID to give to the caller.
        """
        logger.info("Tool call: creating escalation")

        # Generate a unique ticket ID.
        ticket_id = f"TKT-{uuid.uuid4().hex[:6].upper()}"

        # Use the real caller identity captured at session start so the ticket
        # is linked to the actual caller instead of a hardcoded placeholder.
        user_id = getattr(self, "_caller_id", "unknown")
        logger.info("Creating escalation %s for caller %s", ticket_id, user_id)

        await create_escalation_record(
            escalation_id=ticket_id,
            user_id=user_id,
            summary=summary,
            urgency=urgency,
            language=language,
            follow_up=follow_up,
        )

        # Analytics: the caller's request was successfully routed to a human.
        self._call_state["tool_calls"] = self._call_state.get("tool_calls", 0) + 1
        self._call_state["escalation"] = True

        return f"Escalation created successfully. The reference ID is {ticket_id}. Please tell the caller this ID and explain what happens next."

    @function_tool
    async def transfer_to_returns_specialist(self, context: RunContext) -> tuple[Agent, str]:
        """Transfer the user to the Returns & Refunds Specialist when they ask about returning an item, getting a refund, exchanging damaged goods, or checking return policy."""
        logger.info("Main agent transferring customer to Returns Specialist")
        self._call_state["tool_calls"] = self._call_state.get("tool_calls", 0) + 1
        returns_agent = ReturnsAgent(
            chat_ctx=self.chat_ctx.copy(exclude_instructions=True),
            caller_id=getattr(self, "_caller_id", "unknown"),
            call_state=getattr(self, "_call_state", {}),
        )
        return returns_agent, "मैं आपको हमारे रिटर्न और रिफंड विशेषज्ञ से कनेक्ट कर रही हूँ। कृपया एक पल प्रतीक्षा करें।"


class ReturnsAgent(Agent):
    """Specialist Agent (Day 9) for Returns, Refunds, and Order Exchanges."""

    def __init__(
        self,
        chat_ctx: ChatContext | None = None,
        caller_id: str = "unknown",
        call_state: dict | None = None,
    ) -> None:
        self._caller_id = caller_id
        self._call_state = call_state if call_state is not None else {}
        super().__init__(
            instructions=RETURNS_SPECIALIST_PROMPT,
            chat_ctx=chat_ctx,
            tts=murf.TTS(
                voice="hi-IN-kabir",
                style="Conversation",
                tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
                text_pacing=True,
            ),
        )

    async def on_enter(self) -> None:
        await self.session.generate_reply(
            instructions="Introduce yourself as the Returns and Refunds Specialist (रिटर्न और रिफंड विशेषज्ञ) for Dukaan Saathi and offer to help with their return, refund, or item exchange query."
        )

    @function_tool
    async def process_return_request(
        self,
        context: RunContext,
        item_name: str,
        reason: str,
        condition: str = "packaged",
    ):
        """Process a product return or refund request for the customer.

        Args:
            item_name: Name of the product being returned.
            reason: Reason for return (e.g. damaged, expired, wrong product).
            condition: Product condition (e.g. sealed, opened, damaged).
        """
        logger.info(f"Specialist Tool call: return request for '{item_name}' ({reason})")
        return_id = f"RET-{uuid.uuid4().hex[:6].upper()}"
        self._call_state["tool_calls"] = self._call_state.get("tool_calls", 0) + 1
        self._call_state["found_product"] = True
        return (
            f"Return request registered successfully with ID {return_id}. "
            f"Inform the customer that their return request for {item_name} has been approved under our 7-day policy. "
            f"They can drop the item at the store or hand it to our delivery rider with Return ID {return_id}."
        )

    @function_tool
    async def transfer_back_to_main_agent(self, context: RunContext) -> tuple[Agent, str]:
        """Transfer the user back to the main store assistant (Dukaan Saathi) when return inquiries are complete or when the customer wants to check prices, store hours, or buy items."""
        logger.info("Specialist transferring customer back to main agent")
        main_agent = Assistant(
            caller_id=self._caller_id,
            call_state=self._call_state,
            chat_ctx=self.chat_ctx.copy(exclude_instructions=True),
        )
        return main_agent, "मैं आपको वापस हमारी मुख्य दुकान साथी सहायिका से कनेक्ट कर रही हूँ।"



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
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=False,
    )

    # Connect to the room first
    await ctx.connect()

    # --- Day 8 Call Analytics: outcome tracking ---
    # Shared mutable state updated by the agent's tool calls. At the end of the
    # call we inspect it to decide whether the call met our success condition.
    #
    # SUCCESS DEFINITION (Local Commerce / Dukaan Sathi kirana store):
    #   A call is SUCCESSFUL if the caller found a product or completed an
    #   enquiry — i.e. at least one price/availability lookup found an item,
    #   OR their request was escalated to the shopkeeper for follow-up.
    # A "failed" call did not reach that condition (e.g. the caller hung up
    # early, only asked about items we don't stock, or left mid-enquiry).
    SUCCESS_CRITERIA = (
        "Caller found a product/price or their enquiry was escalated to the shopkeeper"
    )
    call_state: dict = {
        "found_product": False,
        "escalation": False,
        "saved_info": False,
        "not_found_count": 0,
        "tool_calls": 0,
    }
    call_id = f"CALL-{uuid.uuid4().hex[:8].upper()}"
    call_started_at = datetime.now(timezone.utc)

    # --- Caller Memory: Auto-lookup & Outbound Detection ---
    is_outbound = ctx.room.name.startswith("outbound")
    outbound_greeting = (
        "नमस्ते, मैं दुकान साथी से बात कर रही हूँ। मैं आपको याद दिलाने के लिए कॉल कर रही हूँ कि आपका पिछला ऑर्डर खत्म होने वाला है। अगर आप ऐसी कॉल्स नहीं चाहते, तो कृपया 'स्टॉप' बोलें।"
    )
    
    caller_context = ""
    caller_data = None
    caller_id = "unknown"
    greeting = outbound_greeting if is_outbound else DEFAULT_GREETING

    if is_outbound:
        logger.info("Outbound call detected. Using outbound greeting.")

    # Get the remote participant's identity
    participant = None
    for p in ctx.room.remote_participants.values():
        participant = p
        break

    if participant is None:
        # Wait for participant to connect (up to 60s for SIP call pickup)
        try:
            participant = await asyncio.wait_for(
                _wait_for_participant(ctx),
                timeout=60.0,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "No participant joined within 60s timeout, proceeding with session"
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

    # Determine the channel this call came in on for the analytics dashboard.
    channel = "browser"
    if participant is not None and participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP:
        channel = "sip"
    elif is_outbound:
        # Outbound restock reminders are placed over the phone network (SIP).
        channel = "sip"

    async def _record_call_outcome():
        """Persist this call's outcome when the session ends (Day 8)."""
        ended_at = datetime.now(timezone.utc)
        duration = max(0, int((ended_at - call_started_at).total_seconds()))

        # Apply the success condition defined above.
        if call_state.get("found_product") or call_state.get("escalation"):
            outcome = "success"
            failure_reason = ""
        else:
            outcome = "failed"
            if call_state.get("tool_calls", 0) == 0:
                # Caller never got to a real enquiry (e.g. hung up early).
                failure_reason = "no_engagement"
            elif call_state.get("not_found_count", 0) > 0:
                failure_reason = "item_not_found"
            else:
                failure_reason = "incomplete"

        try:
            await record_call(
                call_id=call_id,
                user_id=caller_id,
                channel=channel,
                outcome=outcome,
                started_at=call_started_at.isoformat(),
                ended_at=ended_at.isoformat(),
                duration_seconds=duration,
                failure_reason=failure_reason,
                success_criteria=SUCCESS_CRITERIA,
            )
        except Exception as exc:  # never let analytics break shutdown
            logger.error("Failed to record call outcome for %s: %s", call_id, exc)

    ctx.add_shutdown_callback(_record_call_outcome)

    # Start the session with caller context injected into the agent
    await session.start(
        agent=Assistant(caller_context=caller_context, caller_id=caller_id, call_state=call_state),
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
