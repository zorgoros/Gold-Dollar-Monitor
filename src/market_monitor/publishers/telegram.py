"""Telegram delivery.

The bot token never appears in a log line, an exception message, or a retry
trace — errors here are constructed from the status code and body only.
"""

from __future__ import annotations

import time

import httpx

from ..domain.errors import AuthenticationError, TelegramDeliveryError
from ..domain.models import Report

API = "https://api.telegram.org"


class TelegramPublisher:
    channel = "telegram"

    def __init__(
        self,
        token: str,
        chat_id: str,
        parse_mode: str = "HTML",
        disable_preview: bool = True,
        max_retries: int = 3,
        client: httpx.Client | None = None,
        base_url: str = API,
    ) -> None:
        if not token or not chat_id:
            raise AuthenticationError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID are required")
        self._token = token
        self.chat_id = chat_id
        self.parse_mode = parse_mode
        self.disable_preview = disable_preview
        self.max_retries = max_retries
        self.base_url = base_url
        self._client = client or httpx.Client(timeout=httpx.Timeout(15.0, connect=5.0))

    def _url(self, method: str) -> str:
        return f"{self.base_url}/bot{self._token}/{method}"

    def publish(self, report: Report) -> int | None:
        payload = {
            "chat_id": self.chat_id,
            "text": report.content,
            "parse_mode": self.parse_mode,
            "disable_web_page_preview": self.disable_preview,
        }
        last_error = "no attempt made"
        for attempt in range(self.max_retries):
            try:
                response = self._client.post(self._url("sendMessage"), json=payload)
            except httpx.HTTPError as exc:
                last_error = f"transport error: {type(exc).__name__}"
            else:
                if response.status_code == 200:
                    result = response.json().get("result", {})
                    message_id = result.get("message_id")
                    return int(message_id) if message_id is not None else None
                if response.status_code in (401, 403):
                    # Wrong token or the bot is not an admin of the channel. No retry.
                    raise AuthenticationError(
                        f"Telegram rejected the bot ({response.status_code}) — "
                        "check the token and that it can post to the channel"
                    )
                if response.status_code == 429:
                    retry_after = int(response.json().get("parameters", {}).get("retry_after", 5))
                    last_error = f"rate limited, retry_after={retry_after}"
                    time.sleep(min(retry_after, 30))
                    continue
                if response.status_code < 500:
                    # 400: malformed text or bad chat id — retrying cannot fix it.
                    raise TelegramDeliveryError(
                        f"Telegram refused the message ({response.status_code}): "
                        f"{response.text[:200]}"
                    )
                last_error = f"{response.status_code} from Telegram"
            if attempt < self.max_retries - 1:
                time.sleep(2**attempt)
        raise TelegramDeliveryError(
            f"delivery failed after {self.max_retries} attempts: {last_error}"
        )

    def health_check(self) -> bool:
        try:
            response = self._client.get(self._url("getMe"))
        except httpx.HTTPError:
            return False
        return response.status_code == 200
