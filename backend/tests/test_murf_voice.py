import asyncio
import os
from dotenv import load_dotenv
from livekit.plugins import murf
from livekit.agents import tokenize

load_dotenv(".env.local")
load_dotenv("backend/.env.local")

async def test_voice(voice_id: str):
    print(f"Testing Murf Falcon voice: '{voice_id}'...")
    try:
        tts = murf.TTS(
            voice=voice_id,
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
            text_pacing=True,
        )
        print(f"✅ Voice '{voice_id}' initialized successfully!")
        return True
    except Exception as e:
        print(f"❌ Voice '{voice_id}' failed: {e}")
        return False

async def main():
    candidate_voices = [
        "hi-IN-shaan",
        "hi-IN-amit",
        "hi-IN-ayushi",
        "hi-IN-anisha",
    ]
    working = []
    for v in candidate_voices:
        ok = await test_voice(v)
        if ok:
            working.append(v)
    print("\nSupported Murf Falcon Hindi voices:", working)

if __name__ == "__main__":
    asyncio.run(main())
