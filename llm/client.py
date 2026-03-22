import os
import json
import logging
import time
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = "gemini-2.5-flash"
GEMINI_ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"


class LLMClient:
    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not found in environment (.env).")

    def generate_json(self, system_prompt: str, user_prompt: str,
                      max_attempts: int = 4, base_delay: float = 5.0) -> dict:
        """
        Call Gemini and return parsed JSON.
        Retries with exponential backoff on 429 rate-limit responses.
        """
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
                "responseMimeType": "application/json"
            }
        }

        delay = base_delay
        for attempt in range(1, max_attempts + 1):
            resp = requests.post(
                f"{GEMINI_ENDPOINT}?key={GEMINI_API_KEY}",
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=60,
            )

            # Rate limited — back off and retry
            if resp.status_code == 429:
                if attempt == max_attempts:
                    raise RuntimeError(f"Gemini rate limit exceeded after {max_attempts} attempts.")
                logger.warning("Rate limit hit (attempt %d/%d). Retrying in %.0fs…", attempt, max_attempts, delay)
                time.sleep(delay)
                delay *= 2
                continue

            if not resp.ok:
                raise RuntimeError(f"Gemini API error {resp.status_code}: {resp.text}")

            data = resp.json()
            text_output = data["candidates"][0]["content"]["parts"][0]["text"]

            try:
                return json.loads(text_output)
            except json.JSONDecodeError:
                raise ValueError(f"LLM did not return valid JSON. Raw output:\n{text_output}")