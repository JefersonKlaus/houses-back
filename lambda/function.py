import base64
import json
import logging
import os
import re
from typing import Any

import requests


logger = logging.getLogger()
logger.setLevel(logging.INFO)
GRAPH_API_VERSION = "v20.0"


def _response(status_code: int, body: Any) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, ensure_ascii=False),
    }


def _query_parameters(event: dict[str, Any]) -> dict[str, str]:
    return {str(k): str(v) for k, v in (event.get("queryStringParameters") or {}).items()}


def verify_webhook(event: dict[str, Any]) -> dict[str, Any]:
    params = _query_parameters(event)
    if (
        params.get("hub.mode") == "subscribe"
        and params.get("hub.verify_token") == os.environ.get("WHATSAPP_VERIFY_TOKEN")
        and params.get("hub.challenge")
    ):
        return {"statusCode": 200, "headers": {"Content-Type": "text/plain"}, "body": params["hub.challenge"]}
    return _response(403, {"error": "verification failed"})


def _message_from_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], str] | None:
    try:
        value = payload["entry"][0]["changes"][0]["value"]
        message = value["messages"][0]
        return message, message["from"]
    except (KeyError, IndexError, TypeError):
        return None


def _download_media(media_id: str) -> tuple[bytes, str]:
    headers = {"Authorization": "Bearer " + os.environ["WHATSAPP_TOKEN"]}
    metadata = requests.get(
        f"https://graph.facebook.com/{GRAPH_API_VERSION}/{media_id}",
        headers=headers,
        timeout=15,
    )
    metadata.raise_for_status()
    media = metadata.json()
    download = requests.get(media["url"], headers=headers, timeout=30)
    download.raise_for_status()
    return download.content, media.get("mime_type", "image/jpeg")


def _parse_gemini_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end < start:
        raise ValueError("Gemini did not return a JSON object")
    result = json.loads(cleaned[start : end + 1])
    if not isinstance(result, dict):
        raise ValueError("Gemini response is not an object")
    return result


def extract_expense(image: bytes, mime_type: str, caption: str) -> dict[str, Any]:
    from google import genai
    from google.genai import types

    prompt = (
        "Extraia os dados deste recibo e retorne somente um objeto JSON válido, sem markdown. "
        'Use as chaves "date", "property", "description", "category", "amount", "currency". '
        'A legenda do usuário pode indicar a propriedade e contexto: "' + caption + '". '
        "Use amount como número, date no formato YYYY-MM-DD e null quando o dado não existir."
    )
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    result = client.models.generate_content(
        model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
        contents=[prompt, types.Part.from_bytes(data=image, mime_type=mime_type)],
    )
    return _parse_gemini_json(result.text or "")


def send_whatsapp_message(recipient: str, text: str) -> None:
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{os.environ['WHATSAPP_PHONE_NUMBER_ID']}/messages"
    response = requests.post(
        url,
        headers={
            "Authorization": "Bearer " + os.environ["WHATSAPP_TOKEN"],
            "Content-Type": "application/json",
        },
        json={
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        },
        timeout=15,
    )
    response.raise_for_status()


def process_message(message: dict[str, Any], sender: str) -> None:
    if message.get("type") == "image":
        image = message["image"]
        image_bytes, mime_type = _download_media(image["id"])
        expense = extract_expense(
            image_bytes,
            mime_type,
            image.get("caption", ""),
        )
        from sheets_helper import SheetsHelper

        SheetsHelper().append_expense(expense, sender)
        summary = f"{expense.get('description', 'Lançamento')} - {expense.get('amount', '')} {expense.get('currency', 'BRL')}"
        send_whatsapp_message(sender, f"✅ Lançamento salvo: {summary}")
    elif message.get("type") == "text":
        send_whatsapp_message(sender, "Envie uma foto do recibo com a legenda da casa.")


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    method = (
        event.get("requestContext", {}).get("http", {}).get("method")
        or event.get("httpMethod", "")
    ).upper()
    if method == "GET":
        return verify_webhook(event)
    if method != "POST":
        return _response(405, {"error": "method not allowed"})

    body = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")
    try:
        message_data = _message_from_payload(json.loads(body))
        if message_data:
            process_message(*message_data)
    except Exception:
        logger.exception("Could not process WhatsApp webhook")
        return _response(500, {"error": "message processing failed"})
    return _response(200, {"ok": True})
