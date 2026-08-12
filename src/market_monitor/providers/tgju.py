"""TGJU adapter. Verified 2026-08-12 — see docs/PROVIDERS.md.

Two things here are load-bearing:

* The three Iranian instruments are quoted in **rial**. Reading them as toman
  publishes every number 10x too high, so the unit is declared per symbol and
  converted through normalization, never assumed.
* A `ts` whose time component is 00:00:00 is the previous close, not a live
  tick. It is passed through as the source timestamp so staleness is decided by
  the validator instead of being hidden here.
"""

from __future__ import annotations

import hashlib
import json
import logging
import secrets
from collections.abc import Iterable
from datetime import datetime
from typing import Any

import httpx

from ..domain.enums import Instrument, Unit
from ..domain.errors import ProviderParseError
from ..domain.models import Quote
from ..normalization.units import parse_number, to_canonical
from ..timeutil import TEHRAN, now_utc
from .base import DEFAULT_TIMEOUT, http_get

log = logging.getLogger(__name__)

BASE_URL = "https://call1.tgju.org/ajax.json"
FALLBACK_URL = "https://call3.tgju.org/ajax.json"

# instrument -> (provider symbol, unit the provider reports it in)
SYMBOLS: dict[Instrument, tuple[str, Unit]] = {
    Instrument.USD_IRR_FREE: ("price_dollar_rl", Unit.RIAL_PER_USD),
    Instrument.GOLD_18K: ("geram18", Unit.RIAL_PER_GRAM),
    Instrument.XAU_USD: ("ons", Unit.USD_PER_TROY_OUNCE),
    Instrument.EMAMI_COIN: ("sekee", Unit.RIAL_PER_COIN),
}


def _parse_ts(text: str | None) -> datetime | None:
    """TGJU reports Tehran local time with no offset."""
    if not text:
        return None
    try:
        return datetime.strptime(text.strip(), "%Y-%m-%d %H:%M:%S").replace(tzinfo=TEHRAN)
    except ValueError:
        return None


class TgjuProvider:
    name = "tgju"

    def __init__(self, client: httpx.Client | None = None, url: str = BASE_URL) -> None:
        self.url = url
        self._client = client or httpx.Client(timeout=DEFAULT_TIMEOUT, follow_redirects=True)

    def _payload(self) -> dict[str, Any]:
        # Cloudflare caches this path; without a buster a HIT can be ~20 minutes old.
        response = http_get(self._client, f"{self.url}?cb={secrets.token_hex(4)}")
        try:
            data: dict[str, Any] = response.json()
        except ValueError as exc:
            raise ProviderParseError("TGJU response was not JSON") from exc
        if "current" not in data:
            raise ProviderParseError("TGJU response has no 'current' block — layout changed")
        return data

    def fetch_quotes(self, instruments: Iterable[Instrument]) -> dict[Instrument, Quote]:
        data = self._payload()
        current = data["current"]
        retrieved_at = now_utc()
        quotes: dict[Instrument, Quote] = {}
        for instrument in instruments:
            mapping = SYMBOLS.get(instrument)
            if mapping is None:
                continue
            symbol, source_unit = mapping
            entry = current.get(symbol)
            if not isinstance(entry, dict) or "p" not in entry:
                # One absent symbol must not discard the others. The instrument
                # is simply missing from the result; validate_snapshot refuses
                # to publish if it was a mandatory one.
                log.warning(
                    "symbol_missing", extra={"provider": self.name, "provider_symbol": symbol}
                )
                continue
            raw = str(entry["p"])
            value, unit = to_canonical(instrument, parse_number(raw), source_unit)
            quotes[instrument] = Quote(
                instrument=instrument,
                provider=self.name,
                provider_symbol=symbol,
                raw_value=raw,
                normalized_value=value,
                unit=unit,
                currency="USD" if instrument is Instrument.XAU_USD else "IRT",
                retrieved_at=retrieved_at,
                source_timestamp=_parse_ts(entry.get("ts")),
                raw_payload_hash=hashlib.sha256(
                    json.dumps(entry, sort_keys=True, ensure_ascii=False).encode()
                ).hexdigest()[:16],
                metadata={"source_unit": source_unit.value},
            )
        return quotes

    def health_check(self) -> bool:
        try:
            return bool(self._payload())
        except Exception:
            return False
