"""Provider contract. Adapters return normalized Quotes; nothing else escapes."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable
from typing import Protocol

import httpx

from ..domain.enums import Instrument
from ..domain.errors import ProviderUnavailable, RateLimitError, TransientError
from ..domain.models import Quote

DEFAULT_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


class MarketDataProvider(Protocol):
    name: str

    def fetch_quotes(self, instruments: Iterable[Instrument]) -> dict[Instrument, Quote]: ...

    def health_check(self) -> bool: ...


def with_retry[T](call: Callable[[], T], attempts: int = 3, base_delay: float = 1.0) -> T:
    """Bounded exponential retry for transient failures only.

    Invalid data is never retried — a malformed price will be just as malformed
    the second time, and retrying it only delays the failure report.
    """
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            return call()
        except TransientError as exc:
            last = exc
            if attempt == attempts - 1:
                break
            time.sleep(base_delay * (2**attempt))
    raise last if last else ProviderUnavailable("retry loop ended without an error")


def http_get(client: httpx.Client, url: str) -> httpx.Response:
    """GET with provider errors mapped onto the taxonomy in §24."""
    try:
        response = client.get(url)
    except httpx.TimeoutException as exc:
        raise ProviderUnavailable(f"timeout for {url}") from exc
    except httpx.HTTPError as exc:
        raise ProviderUnavailable(f"transport error for {url}: {exc}") from exc
    if response.status_code == 429:
        raise RateLimitError(f"rate limited by {url}")
    if response.status_code >= 500:
        raise ProviderUnavailable(f"{response.status_code} from {url}")
    if response.status_code >= 400:
        raise ProviderUnavailable(f"{response.status_code} from {url}")
    return response
