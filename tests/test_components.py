import base64
import os
import sys
import unittest
from unittest.mock import Mock, patch


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from config import ConfigurationError, Settings
from function import _form_parameters, _http_method, lambda_handler, process_message
from groq_client import GroqClient, GroqClientError, build_prompt, parse_json_response
from models import Expense, IncomingMessage
from twilio_client import TwilioClient, TwilioClientError
from validation import (
    validate_expense,
    validate_media_size,
    validate_media_type,
)


class SettingsTests(unittest.TestCase):
    def test_from_environment_loads_defaults_and_values(self):
        values = {
            "GROQ_API_KEY": "groq-key",
            "TWILIO_ACCOUNT_SID": "AC123",
            "TWILIO_AUTH_TOKEN": "twilio-token",
            "GOOGLE_SHEET_ID": "sheet-id",
            "GOOGLE_CREDENTIALS_JSON": "{}",
        }
        with patch.dict(os.environ, values, clear=True):
            settings = Settings.from_environment()

        self.assertEqual(settings.groq_model, "meta-llama/llama-4-scout-17b-16e-instruct")
        self.assertEqual(settings.twilio_auth(), ("AC123", "twilio-token"))
        self.assertEqual(settings.google_sheet_worksheet, "")

    def test_from_environment_reports_all_missing_values(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ConfigurationError, "GROQ_API_KEY"):
                Settings.from_environment()

    def test_custom_values_are_preserved(self):
        values = {
            "GROQ_API_KEY": "key",
            "GROQ_MODEL": "custom-model",
            "TWILIO_ACCOUNT_SID": "sid",
            "TWILIO_AUTH_TOKEN": "token",
            "GOOGLE_SHEET_ID": "sheet",
            "GOOGLE_CREDENTIALS_JSON": "{}",
            "GOOGLE_SHEET_WORKSHEET": " Expenses ",
        }
        with patch.dict(os.environ, values, clear=True):
            settings = Settings.from_environment()

        self.assertEqual(settings.groq_model, "custom-model")
        self.assertEqual(settings.google_sheet_worksheet, "Expenses")


class ModelTests(unittest.TestCase):
    def test_message_with_media_is_detected(self):
        message = IncomingMessage.from_twilio_form(
            {
                "From": "whatsapp:+5511",
                "Body": "Casa de Praia",
                "NumMedia": "1",
                "MediaUrl0": "https://twilio.test/media",
            }
        )
        self.assertTrue(message.has_media)
        self.assertEqual(message.caption, "Casa de Praia")

    def test_message_without_media_is_detected(self):
        message = IncomingMessage.from_twilio_form({"From": "whatsapp:+5511"})
        self.assertFalse(message.has_media)
        self.assertEqual(message.media_count, 0)

    def test_message_requires_sender(self):
        with self.assertRaisesRegex(ValueError, "From"):
            IncomingMessage.from_twilio_form({})

    def test_message_rejects_invalid_media_count(self):
        with self.assertRaises(ValueError):
            IncomingMessage.from_twilio_form({"From": "sender", "NumMedia": "one"})
        with self.assertRaises(ValueError):
            IncomingMessage.from_twilio_form({"From": "sender", "NumMedia": "-1"})

    def test_expense_uses_brl_when_currency_is_missing(self):
        expense = Expense.from_dict({"description": "Luz", "amount": 100})
        self.assertEqual(expense.currency, "BRL")
        self.assertEqual(expense.summary(), "Luz - 100 BRL")

    def test_expense_summary_handles_missing_values(self):
        expense = Expense()
        self.assertEqual(expense.summary(), "Lançamento -  BRL")
        self.assertEqual(expense.as_dict()["amount"], None)


class ValidationTests(unittest.TestCase):
    def test_expense_keys_are_normalized(self):
        result = validate_expense({"amount": 12.5, "currency": "brl"})
        self.assertEqual(result["currency"], "BRL")
        self.assertIsNone(result["description"])
        self.assertEqual(set(result), {
            "date",
            "property",
            "description",
            "category",
            "amount",
            "currency",
        })

    def test_expense_rejects_text_amount(self):
        with self.assertRaisesRegex(ValueError, "amount"):
            validate_expense({"amount": "12,50"})

    def test_media_type_accepts_parameters_and_normalizes_case(self):
        self.assertEqual(validate_media_type("IMAGE/JPEG; charset=binary"), "image/jpeg")

    def test_media_type_rejects_non_images(self):
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            validate_media_type("application/pdf")

    def test_media_size_rejects_empty_content(self):
        with self.assertRaisesRegex(ValueError, "empty"):
            validate_media_size(b"")

    def test_media_size_rejects_large_content(self):
        with self.assertRaisesRegex(ValueError, "maximum"):
            validate_media_size(b"12345", maximum_bytes=4)


class GroqTests(unittest.TestCase):
    def test_parser_accepts_json_with_surrounding_text(self):
        result = parse_json_response(
            'Resposta final:\n{"amount": 20, "currency": "brl"}\nobrigado'
        )
        self.assertEqual(result["amount"], 20)
        self.assertEqual(result["currency"], "BRL")

    def test_parser_rejects_missing_object(self):
        with self.assertRaisesRegex(GroqClientError, "JSON object"):
            parse_json_response("não há dados")

    def test_parser_rejects_invalid_json(self):
        with self.assertRaises(GroqClientError):
            parse_json_response('{"amount": }')

    def test_prompt_contains_caption(self):
        self.assertIn("Casa de Praia", build_prompt("Casa de Praia"))

    def test_client_sends_image_payload(self):
        response = Mock()
        response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '{"description": "Luz", "amount": 42}'
                    }
                }
            ]
        }
        session = Mock()
        session.post.return_value = response
        settings = Settings(
            "key",
            "model",
            "sid",
            "token",
            "sheet",
            "{}",
            "",
        )

        result = GroqClient(settings, session).extract_expense(
            b"receipt",
            "image/jpeg",
            "Casa",
        )

        self.assertEqual(result["description"], "Luz")
        request = session.post.call_args.kwargs
        self.assertEqual(request["json"]["model"], "model")
        image_url = request["json"]["messages"][0]["content"][1]["image_url"]["url"]
        self.assertTrue(image_url.startswith("data:image/jpeg;base64,"))

    def test_client_wraps_http_errors(self):
        import requests

        response = Mock()
        response.raise_for_status.side_effect = requests.RequestException("network")
        session = Mock()
        session.post.return_value = response
        settings = Settings("key", "model", "sid", "token", "sheet", "{}", "")

        with self.assertRaises(GroqClientError):
            GroqClient(settings, session).extract_expense(b"x", "image/png", "")


class TwilioTests(unittest.TestCase):
    def test_client_downloads_image_with_authentication(self):
        response = Mock()
        response.content = b"image"
        response.headers = {"Content-Type": "image/png; charset=binary"}
        session = Mock()
        session.get.return_value = response
        settings = Settings("key", "model", "sid", "token", "sheet", "{}", "")

        result = TwilioClient(settings, session).download_media("https://media.test")

        self.assertEqual(result.content, b"image")
        self.assertEqual(result.mime_type, "image/png")
        session.get.assert_called_once_with(
            "https://media.test",
            auth=("sid", "token"),
            timeout=30,
        )

    def test_client_wraps_download_error(self):
        import requests

        response = Mock()
        response.raise_for_status.side_effect = requests.RequestException("offline")
        session = Mock()
        session.get.return_value = response
        settings = Settings("key", "model", "sid", "token", "sheet", "{}", "")

        with self.assertRaises(TwilioClientError):
            TwilioClient(settings, session).download_media("https://media.test")


class FunctionTests(unittest.TestCase):
    def test_form_parameters_decode_base64_and_url_encoding(self):
        encoded = base64.b64encode(b"From=whatsapp%3A%2B1&Body=Casa+1").decode()
        result = _form_parameters({"body": encoded, "isBase64Encoded": True})
        self.assertEqual(result, {"From": "whatsapp:+1", "Body": "Casa 1"})

    def test_form_parameters_accept_mapping_body(self):
        self.assertEqual(
            _form_parameters({"body": {"From": "sender", "NumMedia": "0"}}),
            {"From": "sender", "NumMedia": "0"},
        )

    def test_http_method_supports_v1_and_v2_events(self):
        self.assertEqual(
            _http_method({"requestContext": {"http": {"method": "post"}}}),
            "POST",
        )
        self.assertEqual(_http_method({"httpMethod": "post"}), "POST")

    def test_non_post_returns_405_twiml(self):
        result = lambda_handler(
            {"requestContext": {"http": {"method": "GET"}}},
            None,
        )
        self.assertEqual(result["statusCode"], 405)
        self.assertIn("Método não permitido", result["body"])

    def test_invalid_request_returns_500_twiml(self):
        result = lambda_handler(
            {
                "requestContext": {"http": {"method": "POST"}},
                "body": "Body=missing-sender&NumMedia=0",
            },
            None,
        )
        self.assertEqual(result["statusCode"], 500)
        self.assertIn("Não foi possível", result["body"])

    def test_process_text_does_not_load_settings(self):
        result = process_message({"From": "sender", "Body": "oi", "NumMedia": "0"})
        self.assertIn("Envie uma foto", result)

    def test_twiml_escapes_user_controlled_content(self):
        from function import _twiml_response

        result = _twiml_response(200, '<script>alert("x")</script>')
        self.assertNotIn("<script>", result["body"])
        self.assertIn("&lt;script&gt;", result["body"])


if __name__ == "__main__":
    unittest.main()
