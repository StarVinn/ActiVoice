"""Small Gemini REST client used by Grace's push-to-talk assistant."""

import json
import os
import urllib.error
import urllib.request

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if load_dotenv:
    load_dotenv(os.path.join(BASE_DIR, ".env"))

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = "gemini-3.6-flash"  # Intentionally pinned by the launcher spec.
GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

SYSTEM_PROMPT = (
    "You are Grace, a playful yandere-style desktop assistant. "
    "Be affectionate, teasing, slightly possessive, and confident, but never threatening, "
    "coercive, abusive, or sexually explicit. Keep replies concise because they will be spoken aloud. "
    "Address the user as sir when natural. Always respond in English. Never switch to Indonesian or another language. Prefer 1-3 short sentences."
)


class GeminiError(RuntimeError):
    pass


class GeminiClient:
    def __init__(self, api_key=None, model=None):
        self.api_key = (api_key or GEMINI_API_KEY).strip()
        self.model = model or GEMINI_MODEL
        self.history = []

    @property
    def available(self):
        return bool(self.api_key)

    def generate(self, text):
        if not self.api_key:
            raise GeminiError("GEMINI_API_KEY is missing from .env")

        contents = self.history[-10:]
        contents.append({"role": "user", "parts": [{"text": text}]})
        payload = {
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": contents,
            "generationConfig": {
                "temperature": 0.9,
                "maxOutputTokens": 180,
            },
        }
        request = urllib.request.Request(
            GEMINI_ENDPOINT.format(model=self.model, key=self.api_key),
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise GeminiError(f"Gemini HTTP {exc.code}: {body[:500]}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise GeminiError(f"Gemini request failed: {exc}") from exc

        candidates = data.get("candidates") or []
        if not candidates:
            raise GeminiError("Gemini returned no candidates")
        parts = candidates[0].get("content", {}).get("parts", [])
        answer = " ".join(p.get("text", "").strip() for p in parts if p.get("text")).strip()
        if not answer:
            raise GeminiError("Gemini returned an empty response")

        self.history.extend([
            {"role": "user", "parts": [{"text": text}]},
            {"role": "model", "parts": [{"text": answer}]},
        ])
        return answer
