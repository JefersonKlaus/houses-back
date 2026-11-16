from typing import Any


SUPPORTED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}


def validate_expense(data: dict[str, Any]) -> dict[str, Any]:
    required_keys = {
        "date",
        "property",
        "description",
        "category",
        "amount",
        "currency",
    }
    normalized = {key: data.get(key) for key in required_keys}
    amount = normalized["amount"]
    if amount is not None and not isinstance(amount, (int, float)):
        raise ValueError("Expense amount must be a number or null")
    if normalized["currency"] is not None:
        normalized["currency"] = str(normalized["currency"]).upper()
    return normalized


def validate_media_type(mime_type: str) -> str:
    normalized = mime_type.split(";", 1)[0].strip().lower()
    if normalized not in SUPPORTED_IMAGE_TYPES:
        raise ValueError(f"Unsupported media type: {normalized}")
    return normalized


def validate_media_size(content: bytes, maximum_bytes: int = 10_000_000) -> None:
    if not content:
        raise ValueError("Downloaded media is empty")
    if len(content) > maximum_bytes:
        raise ValueError("Downloaded media exceeds the maximum size")
