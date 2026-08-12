"""Analyse a snapshot, render its report types, and publish each at most once.

Two things are separated here that v1.0 ran together:

* **The stored time series** is always computed from the inputs exactly as
  collected. It is the observation record, and `session.align` reads it back to
  find the ounce that matches a closed Tehran session — so it must never be
  written from an aligned analysis, or alignment would start consuming its own
  output.
* **The published analysis** uses the aligned ounce and is withheld entirely
  when no aligned ounce exists. Its exact text is preserved in `reports.content`,
  so a published report stays reproducible even though the series behind it
  records the raw observation (docs/FORMULAS.md).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from ..analysis.engine import Analysis, analyze
from ..analysis.session import align, parse_close
from ..domain.enums import AnalysisBasis, DeliveryStatus, GateCode, QualityStatus, ReportType
from ..domain.errors import TelegramDeliveryError
from ..domain.models import Report, Snapshot
from ..normalization.validators import SnapshotVerdict
from ..publishers.base import Publisher
from ..reporting.formatter_fa import (
    ReportConfig,
    render_analysis,
    render_snapshot,
    render_unavailable,
)
from ..settings import Settings
from ..storage.repositories import Repository
from ..timeutil import now_utc, to_tehran

log = logging.getLogger(__name__)

SCHEDULE_KEY = {
    ReportType.MARKET_SNAPSHOT: "snapshot",
    ReportType.AYAR_ANALYSIS: "analysis",
}


DEFAULT_SLOT_TOLERANCE = timedelta(minutes=90)


def scheduled_slot(
    moment: datetime, slots: list[str], tolerance: timedelta = DEFAULT_SLOT_TOLERANCE
) -> str:
    """Name the configured slot this run belongs to, in Tehran local time.

    Runs that do not line up with a configured slot get their own key, so a
    manual run can never consume the scheduled slot's single delivery.
    """
    local = to_tehran(moment)
    for slot in slots:
        hour, _, minute = slot.partition(":")
        target = local.replace(hour=int(hour), minute=int(minute or 0), second=0, microsecond=0)
        if abs(local - target) <= tolerance:
            return f"{local:%Y-%m-%d} {slot}"
    return f"{local:%Y-%m-%d %H:%M} adhoc"


def slot_tolerance(settings: Settings) -> timedelta:
    configured = settings.section("schedule").get("slot_tolerance_minutes")
    return DEFAULT_SLOT_TOLERANCE if configured is None else timedelta(minutes=float(configured))


def due_report_types(moment: datetime, settings: Settings) -> list[ReportType]:
    """Which report types this moment is a scheduled slot for.

    Counts and times live entirely in `[schedule]` (§4). A deployment that wants
    six snapshots and one analysis changes config and nothing else.
    """
    tolerance = slot_tolerance(settings)
    due = []
    for report_type, key in SCHEDULE_KEY.items():
        slot = scheduled_slot(moment, settings.slots(key), tolerance)
        if not slot.endswith("adhoc"):
            due.append(report_type)
    return due


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


def report_config(settings: Settings) -> ReportConfig:
    return replace(ReportConfig.from_settings(settings), channel_note=channel_note(settings))


@dataclass(frozen=True)
class ReportOutcome:
    report: Report
    analysis: Analysis | None
    published: bool
    skipped_duplicate: bool


@dataclass(frozen=True)
class Prepared:
    report: Report
    # None when the report was withheld: there was nothing computable to render,
    # which is precisely why the reader gets a status line instead of numbers.
    analysis: Analysis | None
    gated: bool
    # Engineer-facing detail. Goes to job_runs and the log, never to Telegram.
    diagnostics: list[str]


def base_analysis(
    repo: Repository, settings: Settings, snapshot: Snapshot, verdict: SnapshotVerdict | None
) -> Analysis | None:
    """The observation analysis: inputs exactly as collected, nothing aligned.

    This is what gets written to `metrics` and `signals`, and what the price
    board renders. Its basis reflects whether the quotes themselves are current.
    Returns None when the snapshot cannot support the core relationship at all —
    a run that collected nothing usable still stored its raw quotes, but there
    is no analysis to derive from them.
    """
    if verdict is not None and not verdict.publishable:
        return None
    analysis = analyze(snapshot, repo, settings.config, verdict.warnings if verdict else [])
    stale = any(q.quality_status is not QualityStatus.OK for q in snapshot.quotes.values())
    return replace(analysis, basis=AnalysisBasis.LAST_CLOSE if stale else AnalysisBasis.LIVE)


def store_analytics(repo: Repository, snapshot: Snapshot, analysis: Analysis | None) -> None:
    """Write the time series once per snapshot, whatever reports go out."""
    if analysis and snapshot.id:
        repo.save_metrics(snapshot.id, analysis.metric_rows(), snapshot.snapshot_at)
        repo.save_signals(snapshot.id, analysis.signals)


def prepare(
    repo: Repository,
    settings: Settings,
    snapshot: Snapshot,
    verdict: SnapshotVerdict | None,
    report_type: ReportType,
    observation: Analysis | None,
) -> Prepared:
    """Render one report type, applying the gate that report type demands."""
    config = report_config(settings)
    slot = scheduled_slot(
        snapshot.snapshot_at, settings.slots(SCHEDULE_KEY[report_type]), slot_tolerance(settings)
    )
    publishable = (verdict.publishable if verdict else True) and observation is not None
    codes = list(verdict.codes) if verdict else []
    diagnostics = list(verdict.warnings) if verdict else []
    analysis = observation
    gated = not publishable
    model_version = observation.model_version if observation else str(settings.model_version)

    if publishable and report_type is ReportType.AYAR_ANALYSIS:
        alignment = align(
            snapshot.quotes,
            settings.instrument_list("instruments", "analysis_required"),
            repo,
            snapshot.snapshot_at,
            settings.section("freshness"),
            timedelta(
                minutes=float(settings.section("freshness").get("session_window_minutes", 20))
            ),
            timedelta(
                hours=float(settings.section("analysis").get("xau_alignment_tolerance_hours", 12))
            ),
            parse_close(settings.section("analysis").get("tehran_session_close", "17:00")),
        )
        diagnostics += alignment.diagnostics
        codes += alignment.codes
        if not alignment.ok:
            gated = True
        else:
            analysis = analyze(
                snapshot,
                repo,
                settings.config,
                verdict.warnings if verdict else [],
                alignment=alignment,
            )

    if gated or analysis is None:
        gated = True
        content = render_unavailable(
            codes, config, analysis_report=report_type is ReportType.AYAR_ANALYSIS
        )
    elif report_type is ReportType.AYAR_ANALYSIS:
        content = render_analysis(analysis, config)
        model_version = analysis.model_version
    else:
        content = render_snapshot(analysis, config)
        model_version = analysis.model_version

    report = Report(
        report_type=report_type,
        report_key=report_key(report_type, slot, model_version),
        content=content,
        channel="telegram",
        generated_at=now_utc(),
        model_version=model_version,
        snapshot_id=snapshot.id,
    )
    if gated:
        log.warning(
            "report_gated",
            extra={
                "report_type": report_type.value,
                "codes": [c.value for c in codes if c is not GateCode.OK],
                "diagnostics": diagnostics,
            },
        )
    return Prepared(report, analysis, gated, diagnostics)


def publish(
    repo: Repository, report: Report, publisher: Publisher, analysis: Analysis | None = None
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
