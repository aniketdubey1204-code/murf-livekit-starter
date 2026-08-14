import asyncio
import os
import sys
from dotenv import load_dotenv

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv(".env.local")
load_dotenv("backend/.env.local")

from livekit.plugins import murf
from livekit.agents import tokenize, utils

async def test_synth(voice_id: str):
    print(f"Testing synthesis for voice: '{voice_id}'...")
    try:
        async with utils.http_context.open():
            tts = murf.TTS(
                voice=voice_id,
                style="Conversation",
                tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
                text_pacing=True,
            )
            stream = tts.synthesize("नमस्ते! मैं रिटर्न और रिफंड विशेषज्ञ हूँ।")
            count = 0
            async for event in stream:
                count += 1
                if count >= 2:
                    break
            print(f"[OK] Voice '{voice_id}' generated audio frames successfully!")
            return True
    except Exception as e:
        print(f"[FAIL] Voice '{voice_id}' failed: {e}")
        return False

async def main():
    for v in ["hi-IN-karan", "hi-IN-aman"]:
        await test_synth(v)

if __name__ == "__main__":
    asyncio.run(main())
