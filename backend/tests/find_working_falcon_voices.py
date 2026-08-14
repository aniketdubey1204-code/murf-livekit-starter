import os
import requests
from dotenv import load_dotenv

load_dotenv(".env.local")
load_dotenv("backend/.env.local")

api_key = os.getenv("MURF_API_KEY")
print(f"MURF_API_KEY found: {bool(api_key)}")

headers = {"api-key": api_key} if api_key else {}

# Test URL with model=FALCON parameter
url = "https://api.murf.ai/v1/speech/voices?model=FALCON"
try:
    resp = requests.get(url, headers=headers)
    print(f"GET {url} -> Status {resp.status_code}")
    if resp.status_code == 200:
        voices = resp.json()
        print(f"Total FALCON model voices count: {len(voices)}")
        print("\nAll Available Falcon Voices:")
        for v in voices:
            v_id = v.get("voiceId") or v.get("voice_id") or v.get("id")
            name = v.get("displayName") or v.get("name")
            lang = v.get("displayLanguage") or v.get("locale")
            gender = v.get("gender")
            print(f"ID: '{v_id}' | Name: {name} | Gender: {gender} | Lang: {lang}")
    else:
        print("Response:", resp.text[:500])
except Exception as e:
    print("Error:", e)
