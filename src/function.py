import base64
import json
import logging
from typing import Any
from urllib.parse import parse_qs

from config import load_settings
from groq_client import parse_json_response
from models import Expense, IncomingMessage
from twilio_client import TwilioClient


logger = logging.getLogger()
logger.setLevel(logging.INFO)
_parse_groq_json = parse_json_response


def _twiml_response(status_code: int, message: str) -> dict[str, Any]:
    escaped = (
        message.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/xml"},
        "body": (
            '<?xml version="1.0" encoding="UTF-8"?>'
            f"<Response><Message>{escaped}</Message></Response>"
        ),
    }


def _form_parameters(event: dict[str, Any]) -> dict[str, str]:
    body = event.get("body") or ""
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")
    if isinstance(body, dict):
        return {str(key): str(value) for key, value in body.items()}
    return {
        key: values[0]
        for key, values in parse_qs(body, keep_blank_values=True).items()
    }


def _http_method(event: dict[str, Any]) -> str:
    request_context = event.get("requestContext") or {}
    http = request_context.get("http") or {}
    return str(http.get("method") or event.get("httpMethod") or "").upper()


def _load_message(event: dict[str, Any]) -> IncomingMessage:
    return IncomingMessage.from_twilio_form(_form_parameters(event))


def _process_image(message: IncomingMessage) -> Expense:
    settings = load_settings()
    media = TwilioClient(settings).download_media(message.media_url or "")
    data = GroqClient(settings).extract_expense(
        media.content,
        media.mime_type,
        message.caption,
    )
    expense = Expense.from_dict(data)
    from sheets_helper import SheetsHelper

    SheetsHelper(
        credentials_json=settings.google_credentials_json,
        sheet_id=settings.google_sheet_id,
        worksheet_name=settings.google_sheet_worksheet,
    ).append_expense(expense.as_dict(), message.sender)
    return expense


def process_message(params: dict[str, str]) -> str:
    message = IncomingMessage.from_twilio_form(params)
    if not message.has_media:
        return "Envie uma foto do recibo com a legenda da casa."
    expense = _process_image(message)
    return f"✅ Lançamento salvo: {expense.summary()}"


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    if _http_method(event) != "POST":
        return _twiml_response(405, "Método não permitido.")
    try:
        return _twiml_response(200, process_message(_form_parameters(event)))
    except Exception:
        logger.exception("Could not process Twilio WhatsApp webhook")
        return _twiml_response(
            500,
            "Não foi possível processar sua mensagem. Tente novamente.",
        )
