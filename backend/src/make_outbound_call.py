import asyncio
import os
import uuid
import sys
from dotenv import load_dotenv

from livekit.api import LiveKitAPI
from livekit.api.sip_service import CreateSIPParticipantRequest

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env.local"))

async def main():
    sip_trunk_id = os.getenv("SIP_TRUNK_ID")
    call_to_number = os.getenv("CALL_TO_NUMBER")

    if not sip_trunk_id or not call_to_number:
        print("ERROR: SIP_TRUNK_ID or CALL_TO_NUMBER is missing from .env.local")
        print("Please configure them and try again.")
        sys.exit(1)

    # Generate a unique room name for this outbound call
    room_name = f"outbound-call-{uuid.uuid4().hex[:8]}"
    participant_identity = f"outbound-caller-{uuid.uuid4().hex[:8]}"
    
    print(f"Initiating outbound call to {call_to_number} via trunk {sip_trunk_id}...")
    print(f"Room name: {room_name}")

    api = LiveKitAPI()
    try:
        req = CreateSIPParticipantRequest(
            sip_trunk_id=sip_trunk_id,
            sip_call_to=call_to_number,
            room_name=room_name,
            participant_identity=participant_identity,
        )
        participant = await api.sip.create_sip_participant(req)
        print("Outbound call triggered successfully!")
        print(f"SIP Participant ID: {participant.participant_id}")
        print("The LiveKit Agent should now join the room and greet the caller.")
    except Exception as e:
        print(f"Failed to initiate outbound call: {e}")
    finally:
        await api.aclose()

if __name__ == "__main__":
    asyncio.run(main())
