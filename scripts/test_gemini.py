from llm.client import LLMClient

client = LLMClient()

system = "You must output valid JSON only."
user = 'Return JSON: {"ok": true, "message": "Gemini connected"}'

print(client.generate_json(system, user))