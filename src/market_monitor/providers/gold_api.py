"""Fallback for the world gold ounce only. Verified 2026-08-12, no key required.

The three rial instruments have no independent second source (docs/PROVIDERS.md);
they are cross-checked arithmetically instead.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from typing import Any

import httpx

from ..domain.enums import Instrument, Unit
from ..domain.errors import ProviderParseError
from ..domain.models import Quote
from ..timeutil import from_iso, now_utc
from .base import DEFAULT_TIMEOUT, http_get

URL = "https://api.gold-api.com/price/XAU"


class GoldApiProvider:
    name = "gold-api"

    def __init__(self, client: httpx.Client | None = None, url: str = URL) -> None:
        self.url = url
        self._client = client or httpx.Client(timeout=DEFAULT_TIMEOUT, follow_redirects=True)

    def fetch_quotes(self, instruments: Iterable[Instrument]) -> dict[Instrument, Quote]:
        if Instrument.XAU_USD not in set(instruments):
            return {}
        response = http_get(self._client, self.url)
        try:
            data: dict[str, Any] = response.json()
            price = float(data["price"])
        except (ValueError, KeyError, TypeError) as exc:
            raise ProviderParseError(f"gold-api response unusable: {exc}") from exc

        updated = data.get("updatedAt")
        return {
            Instrument.XAU_USD: Quote(
                instrument=Instrument.XAU_USD,
                provider=self.name,
                provider_symbol="XAU",
                raw_value=str(data["price"]),
                normalized_value=price,
                unit=Unit.USD_PER_TROY_OUNCE,
                currency="USD",
                retrieved_at=now_utc(),
                source_timestamp=from_iso(updated.replace("Z", "+00:00")) if updated else None,
                raw_payload_hash=hashlib.sha256(response.content).hexdigest()[:16],
            )
        }

    def health_check(self) -> bool:
        try:
            return bool(self.fetch_quotes([Instrument.XAU_USD]))
        except Exception:
            return False
