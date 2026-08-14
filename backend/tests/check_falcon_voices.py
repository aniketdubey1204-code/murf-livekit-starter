import os
import requests
from dotenv import load_dotenv

load_dotenv(".env.local")
load_dotenv("backend/.env.local")

api_key = os.getenv("MURF_API_KEY")

headers = {}
if api_key:
    headers["api-key"] = api_key

try:
    resp = requests.get("https://api.murf.ai/v1/speech/voices", headers=headers)
    print(f"Status Code: {resp.status_code}")
    if resp.status_code == 200:
        voices = resp.json()
        print(f"Total Voices Received: {len(voices)}")
        hindi_and_indian = [
            v for v in voices 
            if "hi" in str(v.get("locale", "")).lower() or "in" in str(v.get("locale", "")).lower() or "hindi" in str(v.get("language", "")).lower()
        ]
        print("\nHindi / Indian Voices:")
        for v in hindi_and_indian:
            print(v)
    else:
        print("Response:", resp.text[:500])
except Exception as e:
    print("Error:", e)
