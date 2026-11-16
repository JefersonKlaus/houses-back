from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class IncomingMessage:
    sender: str
    caption: str
    media_url: str | None
    media_count: int

    @property
    def has_media(self) -> bool:
        return self.media_count > 0 and bool(self.media_url)

    @classmethod
    def from_twilio_form(cls, params: dict[str, str]) -> "IncomingMessage":
        sender = params.get("From", "").strip()
        if not sender:
            raise ValueError("Twilio request does not contain From")
        try:
            media_count = int(params.get("NumMedia", "0") or "0")
        except ValueError as error:
            raise ValueError("Twilio NumMedia must be an integer") from error
        if media_count < 0:
            raise ValueError("Twilio NumMedia cannot be negative")
        return cls(
            sender=sender,
            caption=params.get("Body", "").strip(),
            media_url=params.get("MediaUrl0") or None,
            media_count=media_count,
        )


@dataclass(frozen=True)
class Expense:
    date: Any = None
    property: Any = None
    description: Any = None
    category: Any = None
    amount: Any = None
    currency: Any = "BRL"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Expense":
        return cls(
            date=data.get("date"),
            property=data.get("property"),
            description=data.get("description"),
            category=data.get("category"),
            amount=data.get("amount"),
            currency=data.get("currency") or "BRL",
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "property": self.property,
            "description": self.description,
            "category": self.category,
            "amount": self.amount,
            "currency": self.currency,
        }

    def summary(self) -> str:
        description = self.description or "Lançamento"
        amount = "" if self.amount is None else str(self.amount)
        return f"{description} - {amount} {self.currency}"


@dataclass(frozen=True)
class DownloadedMedia:
    content: bytes
    mime_type: str
