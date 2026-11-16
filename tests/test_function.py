import json
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lambda"))
import function


class WebhookTests(unittest.TestCase):
    def test_verification_returns_challenge(self):
        with patch.dict(os.environ, {"WHATSAPP_VERIFY_TOKEN": "secret"}):
            result = function.verify_webhook(
                {"queryStringParameters": {
                    "hub.mode": "subscribe",
                    "hub.verify_token": "secret",
                    "hub.challenge": "12345",
                }}
            )
        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(result["body"], "12345")

    def test_gemini_markdown_is_parsed(self):
        result = function._parse_gemini_json(
            '```json\n{"amount": 42.5, "currency": "BRL"}\n```'
        )
        self.assertEqual(result["amount"], 42.5)

    def test_post_accepts_base64_body(self):
        payload = {"entry": [{"changes": [{"value": {"messages": []}}]}]}
        body = __import__("base64").b64encode(json.dumps(payload).encode()).decode()
        result = function.lambda_handler(
            {"requestContext": {"http": {"method": "POST"}}, "body": body, "isBase64Encoded": True},
            None,
        )
        self.assertEqual(result["statusCode"], 200)


if __name__ == "__main__":
    unittest.main()
