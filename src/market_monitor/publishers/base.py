"""Publisher contract. Telegram is the first surface, not the only one."""

from __future__ import annotations

from typing import Protocol

from ..domain.models import Report


class Publisher(Protocol):
    channel: str

    def publish(self, report: Report) -> int | None:
        """Deliver the report. Returns a provider message id when there is one."""
        ...

    def edit(self, report: Report, message_id: int) -> bool:
        """Rewrite a message already delivered. False when it is no longer there.

        A surface with no notion of editing answers False and gets a fresh post,
        which is the feed behaviour this project shipped with.
        """
        ...
