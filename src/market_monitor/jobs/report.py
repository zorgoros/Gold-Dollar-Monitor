"""Analyse a snapshot, render it, and publish it at most once."""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from ..analysis.engine import Analysis, analyze
from ..domain.enums import DeliveryStatus, ReportType
from ..domain.errors import InsufficientSnapshot, TelegramDeliveryError
from ..domain.models import Report, Snapshot
from ..normalization.validators import SnapshotVerdict
from ..publishers.base import Publisher
from ..reporting.formatter_fa import render
from ..settings import Settings
from ..storage.repositories import Repository
from ..timeutil import now_utc, to_tehran

log = logging.getLogger(__name__)

SLOT_TOLERANCE = timedelta(minutes=90)


def scheduled_slot(moment: datetime, slots: list[str]) -> str:
    """Name the configured slot this run belongs to, in Tehran local time.

    Runs that do not line up with a configured slot get their own key, so a
    manual run can never consume the scheduled slot's single delivery.
    """
    local = to_tehran(moment)
    for slot in slots:
        hour, _, minute = slot.partition(":")
        target = local.replace(hour=int(hour), minute=int(minute or 0), second=0, microsecond=0)
        if abs(local - target) <= SLOT_TOLERANCE:
            return f"{local:%Y-%m-%d} {slot}"
    return f"{local:%Y-%m-%d %H:%M} adhoc"


def report_key(report_type: ReportType, slot: str, model_version: str) -> str:
    return f"{report_type.value}|{slot}|{model_version}"


def channel_note(settings: Settings) -> str:
    """Operator footer line: the configured note, or the channel handle itself.

    A numeric private-channel id is not shown — it is meaningless to readers.
    """
    note = str(settings.section("reporting").get("channel_note", "")).strip()
    if note:
        return note
    handle = (settings.telegram_channel or "").strip()
    return handle if handle.startswith("@") else ""


@dataclass(frozen=True)
class ReportOutcome:
    report: Report
    analysis: Analysis
    published: bool
    skipped_duplicate: bool


def build_report(
    repo: Repository,
    settings: Settings,
    snapshot: Snapshot,
    verdict: SnapshotVerdict | None = None,
    report_type: ReportType = ReportType.SCHEDULED_SUMMARY,
) -> tuple[Report, Analysis]:
    if verdict is not None and not verdict.publishable:
        raise InsufficientSnapshot("; ".join(verdict.warnings) or "snapshot is not publishable")

    analysis = analyze(snapshot, repo, settings.config, verdict.warnings if verdict else [])
    if snapshot.id:
        repo.save_metrics(snapshot.id, analysis.metric_rows(), snapshot.snapshot_at)
        repo.save_signals(snapshot.id, analysis.signals)

    slot = scheduled_slot(
        snapshot.snapshot_at, list(settings.section("schedule").get("reports", []))
    )
    report = Report(
        report_type=report_type,
        report_key=report_key(report_type, slot, analysis.model_version),
        content=render(analysis, channel_note(settings)),
        channel="telegram",
        generated_at=now_utc(),
        model_version=analysis.model_version,
        snapshot_id=snapshot.id,
    )
    return report, analysis


def publish(
    repo: Repository, report: Report, publisher: Publisher, analysis: Analysis
) -> ReportOutcome:
    """Store the report, then deliver it unless this key already went out."""
    if repo.already_delivered(report.report_key):
        log.info("duplicate_suppressed", extra={"report_key": report.report_key})
        return ReportOutcome(
            replace(report, delivery_status=DeliveryStatus.SKIPPED_DUPLICATE),
            analysis,
            published=False,
            skipped_duplicate=True,
        )

    report_id = repo.save_report(report)
    try:
        message_id = publisher.publish(report)
    except TelegramDeliveryError:
        repo.mark_report_failed(report_id, DeliveryStatus.FAILED)
        raise
    repo.mark_report_sent(report_id, message_id)
    return ReportOutcome(
        replace(report, delivery_status=DeliveryStatus.SENT, telegram_message_id=message_id),
        analysis,
        published=True,
        skipped_duplicate=False,
    )
