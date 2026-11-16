import base64
import json
import re
from dataclasses import dataclass
from typing import Any

import requests

from config import Settings
from validation import validate_expense


class GroqClientError(RuntimeError):
    """Raised when Groq cannot extract a receipt."""


def parse_json_response(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end < start:
        raise GroqClientError("Groq did not return a JSON object")
    try:
        parsed = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as error:
        raise GroqClientError("Groq returned invalid JSON") from error
    if not isinstance(parsed, dict):
        raise GroqClientError("Groq response is not an object")
    return validate_expense(parsed)


def build_prompt(caption: str) -> str:
    return (
        "Extraia os dados deste recibo e retorne somente um objeto JSON válido, "
        "sem markdown. Use as chaves date, property, description, category, "
        'amount e currency. A legenda pode indicar a propriedade e o contexto: "'
        + caption
        + '". Use amount como número, date no formato YYYY-MM-DD e null quando '
        "o dado não existir."
    )


@dataclass
class GroqClient:
    settings: Settings
    session: requests.Session | None = None

    def _session(self) -> requests.Session:
        if self.session is None:
            self.session = requests.Session()
        return self.session

    def extract_expense(
        self,
        image: bytes,
        mime_type: str,
        caption: str,
    ) -> dict[str, Any]:
        encoded = base64.b64encode(image).decode("ascii")
        payload = {
            "model": self.settings.groq_model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": build_prompt(caption)},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{encoded}"
                            },
                        },
                    ],
                }
            ],
        }
        response = self._session().post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": "Bearer " + self.settings.groq_api_key,
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self.settings.groq_timeout,
        )
        try:
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
        except (requests.RequestException, KeyError, IndexError, TypeError) as error:
            raise GroqClientError("Groq request failed") from error
        return parse_json_response(content)
