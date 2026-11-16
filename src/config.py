from dataclasses import dataclass
import os


class ConfigurationError(RuntimeError):
    """Raised when a required runtime setting is missing."""


@dataclass(frozen=True)
class Settings:
    groq_api_key: str
    groq_model: str
    twilio_account_sid: str
    twilio_auth_token: str
    google_sheet_id: str
    google_credentials_json: str
    google_sheet_worksheet: str
    request_timeout: int = 30
    groq_timeout: int = 60

    @classmethod
    def from_environment(cls) -> "Settings":
        required = (
            "GROQ_API_KEY",
            "TWILIO_ACCOUNT_SID",
            "TWILIO_AUTH_TOKEN",
            "GOOGLE_SHEET_ID",
            "GOOGLE_CREDENTIALS_JSON",
        )
        missing = [name for name in required if not os.getenv(name)]
        if missing:
            raise ConfigurationError(
                "Missing required environment variables: " + ", ".join(missing)
            )
        return cls(
            groq_api_key=os.environ["GROQ_API_KEY"],
            groq_model=os.getenv(
                "GROQ_MODEL",
                "meta-llama/llama-4-scout-17b-16e-instruct",
            ),
            twilio_account_sid=os.environ["TWILIO_ACCOUNT_SID"],
            twilio_auth_token=os.environ["TWILIO_AUTH_TOKEN"],
            google_sheet_id=os.environ["GOOGLE_SHEET_ID"],
            google_credentials_json=os.environ["GOOGLE_CREDENTIALS_JSON"],
            google_sheet_worksheet=os.getenv("GOOGLE_SHEET_WORKSHEET", "").strip(),
        )

    def twilio_auth(self) -> tuple[str, str]:
        return self.twilio_account_sid, self.twilio_auth_token


def load_settings() -> Settings:
    return Settings.from_environment()
