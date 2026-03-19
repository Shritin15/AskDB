import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = "gemini-2.5-flash"
GEMINI_ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"


class LLMClient:
    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not found in environment (.env).")

    def generate_json(self, system_prompt: str, user_prompt: str) -> dict:
        payload = {
            "system_instruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                # IMPORTANT: Gemini uses camelCase
                "responseMimeType": "application/json"
            }
        }

        resp = requests.post(
            f"{GEMINI_ENDPOINT}?key={GEMINI_API_KEY}",
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )

        # Helpful error detail instead of just "400"
        if not resp.ok:
            raise RuntimeError(f"Gemini API error {resp.status_code}: {resp.text}")

        data = resp.json()
        text_output = data["candidates"][0]["content"]["parts"][0]["text"]

        try:
            return json.loads(text_output)
        except json.JSONDecodeError:
            raise ValueError(f"LLM did not return valid JSON. Raw output:\n{text_output}")