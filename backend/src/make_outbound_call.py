import asyncio
import os
import uuid
import sys
from dotenv import load_dotenv

from livekit.api import LiveKitAPI
from livekit.api.sip_service import CreateSIPParticipantRequest

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env.local"))

async def main():
    sip_trunk_id = os.getenv("LIVEKIT_SIP_OUTBOUND_TRUNK_ID") or os.getenv("SIP_TRUNK_ID")
    call_to_number = os.getenv("CALL_TO_NUMBER")

    if len(sys.argv) > 1:
        call_to_number = sys.argv[1]

    if not sip_trunk_id or not call_to_number:
        print("ERROR: SIP_TRUNK_ID (or LIVEKIT_SIP_OUTBOUND_TRUNK_ID) or CALL_TO_NUMBER is missing.")
        print("Usage: python src/make_outbound_call.py [phone_number_or_linphone_username]")
        sys.exit(1)

    # Format destination for Linphone if username passed
    if not call_to_number.startswith("+") and not call_to_number.startswith("sip:"):
        call_to_target = f"sip:{call_to_number}@sip.linphone.org"
    else:
        call_to_target = call_to_number

    # Generate a unique room name for this outbound call
    room_name = f"outbound-call-{uuid.uuid4().hex[:8]}"
    participant_identity = f"outbound-caller-{uuid.uuid4().hex[:8]}"
    
    print(f"Initiating outbound call to {call_to_target} via trunk {sip_trunk_id}...")
    print(f"Room name: {room_name}")

    api = LiveKitAPI()
    try:
        req = CreateSIPParticipantRequest(
            sip_trunk_id=sip_trunk_id,
            sip_call_to=call_to_number,
            sip_number=call_to_number,
            room_name=room_name,
            participant_identity=participant_identity,
        )
        participant = await api.sip.create_sip_participant(req)
        print("Outbound call triggered successfully!")
        print(f"SIP Participant ID: {participant.participant_id}")
        print(f"SIP Call ID: {participant.sip_call_id}")
        print("Monitoring call status for 15 seconds...")

        from livekit.api import ListParticipantsRequest
        for i in range(15):
            await asyncio.sleep(1)
            try:
                res = await api.room.list_participants(ListParticipantsRequest(room=room_name))
                found = False
                for p in res.participants:
                    if p.identity == participant_identity:
                        found = True
                        print(f"[{i+1}s] Participant status: {p.state} (Name: {p.name}, SIP: {p.attributes})")
                        break
                if not found:
                    print(f"[{i+1}s] Participant left or disconnected.")
                    break
            except Exception as ex:
                print(f"Error checking status: {ex}")

    except Exception as e:
        print(f"Failed to initiate outbound call: {e}")
    finally:
        await api.aclose()

if __name__ == "__main__":
    asyncio.run(main())
