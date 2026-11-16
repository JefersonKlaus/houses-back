import json
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import function


class WebhookTests(unittest.TestCase):
    def test_text_message_returns_twiml(self):
        result = function.lambda_handler(
            {
                "requestContext": {"http": {"method": "POST"}},
                "body": "From=whatsapp%3A%2B5511999999999&Body=teste&NumMedia=0",
            },
            None,
        )
        self.assertEqual(result["statusCode"], 200)
        self.assertIn("Envie uma foto", result["body"])

    def test_groq_markdown_is_parsed(self):
        result = function._parse_groq_json(
            '```json\n{"amount": 42.5, "currency": "BRL"}\n```'
        )
        self.assertEqual(result["amount"], 42.5)

    def test_base64_form_body_is_accepted(self):
        body = __import__("base64").b64encode(
            b"From=whatsapp%3A%2B5511999999999&Body=teste&NumMedia=0"
        ).decode()
        result = function.lambda_handler(
            {"requestContext": {"http": {"method": "POST"}}, "body": body, "isBase64Encoded": True},
            None,
        )
        self.assertEqual(result["statusCode"], 200)


if __name__ == "__main__":
    unittest.main()
