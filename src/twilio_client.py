from dataclasses import dataclass

import requests

from config import Settings
from models import DownloadedMedia
from validation import validate_media_size, validate_media_type


class TwilioClientError(RuntimeError):
    """Raised when Twilio media retrieval fails."""


@dataclass
class TwilioClient:
    settings: Settings
    session: requests.Session | None = None

    def _session(self) -> requests.Session:
        if self.session is None:
            self.session = requests.Session()
        return self.session

    def download_media(self, media_url: str) -> DownloadedMedia:
        response = self._session().get(
            media_url,
            auth=self.settings.twilio_auth(),
            timeout=self.settings.request_timeout,
        )
        try:
            response.raise_for_status()
        except requests.RequestException as error:
            raise TwilioClientError("Twilio media download failed") from error
        content = response.content
        mime_type = validate_media_type(response.headers.get("Content-Type", ""))
        validate_media_size(content)
        return DownloadedMedia(content=content, mime_type=mime_type)
