"""Publisher contract. Telegram is the first surface, not the only one."""

from __future__ import annotations

from typing import Protocol

from ..domain.models import Report


class Publisher(Protocol):
    channel: str

    def publish(self, report: Report) -> int | None:
        """Deliver the report. Returns a provider message id when there is one."""
        ...
