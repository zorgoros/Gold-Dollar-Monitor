"""UTC everywhere internally; Tehran only at the edges."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

TEHRAN = ZoneInfo("Asia/Tehran")


def now_utc() -> datetime:
    return datetime.now(UTC)


def to_iso(moment: datetime) -> str:
    """Timezone-aware datetime -> UTC ISO-8601 string, the only storage format."""
    if moment.tzinfo is None:
        raise ValueError("refusing to store a naive datetime")
    return moment.astimezone(UTC).isoformat(timespec="seconds")


def from_iso(text: str) -> datetime:
    moment = datetime.fromisoformat(text)
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def to_tehran(moment: datetime) -> datetime:
    return moment.astimezone(TEHRAN)
