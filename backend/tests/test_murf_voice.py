import asyncio
import os
from dotenv import load_dotenv
from livekit.plugins import murf
from livekit.agents import tokenize

load_dotenv("backend/.env.local")
if not os.getenv("MURF_API_KEY"):
    load_dotenv(".env.local")

async def test_voice(voice_id: str):
    print(f"Testing Murf Falcon voice: '{voice_id}'...")
    try:
        tts = murf.TTS(
            voice=voice_id,
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
            text_pacing=True,
        )
        # Try creating a audio stream
        stream = tts.synthesize("नमस्ते! यह एक टेस्ट संदेश है।")
        async for frame in stream:
            pass
        print(f"✅ Voice '{voice_id}' works perfectly!")
        return True
    except Exception as e:
        print(f"❌ Voice '{voice_id}' failed: {e}")
        return False

async def main():
    candidate_voices = [
        "hi-IN-anisha",
        "hi-IN-shaurya",
        "hi-IN-karan",
        "hi-IN-rahul",
        "hi-IN-neerja",
        "hi-IN-kabir",
        "hi-IN-aarav",
    ]
    working = []
    for v in candidate_voices:
        ok = await test_voice(v)
        if ok:
            working.append(v)
    print("\nWorking Murf Falcon Hindi voices:", working)

if __name__ == "__main__":
    asyncio.run(main())
