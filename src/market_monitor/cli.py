"""Operator entry point. Every pipeline stage can be run on its own."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime

from .domain.enums import ReportType
from .domain.errors import MarketMonitorError
from .domain.models import Snapshot
from .jobs.backfill import backfill
from .jobs.collect import build_chain, collect
from .jobs.report import base_analysis, due_report_types, prepare, publish, store_analytics
from .normalization.validators import SnapshotVerdict
from .observability.logging import configure
from .publishers.telegram import TelegramPublisher
from .settings import Settings
from .storage.database import open_migrated
from .storage.repositories import Repository
from .timeutil import to_tehran

log = logging.getLogger("market_monitor")


def _repo(settings: Settings) -> Repository:
    return Repository(open_migrated(settings.db_path))


def _publisher(settings: Settings) -> TelegramPublisher:
    telegram = settings.section("telegram")
    return TelegramPublisher(
        token=settings.telegram_token or "",
        chat_id=settings.telegram_channel or "",
        parse_mode=str(telegram.get("parse_mode", "HTML")),
        disable_preview=bool(telegram.get("disable_web_page_preview", True)),
        max_retries=int(telegram.get("max_retries", 3)),
    )


def cmd_fetch(settings: Settings, _: argparse.Namespace) -> int:
    repo = _repo(settings)
    job = repo.start_job("fetch")
    snapshot, verdict, snapshot_id = collect(repo, settings)
    repo.finish_job(
        job,
        "OK" if verdict.publishable else "DEGRADED",
        metadata={"snapshot_id": snapshot_id, "warnings": verdict.warnings},
    )
    print(f"snapshot {snapshot_id} — {verdict.status.value}")
    for instrument, quote in sorted(snapshot.quotes.items()):
        print(
            f"  {instrument.value:<14} {quote.normalized_value:>16,.2f} {quote.unit.value:<12}"
            f" {quote.quality_status.value}"
        )
    for warning in verdict.warnings:
        print(f"  ⚠ {warning}")
    return 0 if verdict.publishable else 1


TYPES = {"snapshot": ReportType.MARKET_SNAPSHOT, "analysis": ReportType.AYAR_ANALYSIS}


def _wanted(settings: Settings, args: argparse.Namespace, at: datetime) -> list[ReportType]:
    """Which report types to produce: the ones forced, else the ones due now.

    Off-slot runs publish nothing by default — that is the noise control in §37.
    A dry run with nothing due still renders both, so an operator can look.
    """
    if args.type:
        return [TYPES[args.type]]
    due = due_report_types(at, settings)
    if not due and args.dry_run:
        return list(TYPES.values())
    return due


def _emit(
    repo: Repository,
    settings: Settings,
    args: argparse.Namespace,
    snapshot: Snapshot,
    verdict: SnapshotVerdict | None,
) -> list[str]:
    observation = base_analysis(repo, settings, snapshot, verdict)
    store_analytics(repo, snapshot, observation)
    results: list[str] = []
    for report_type in _wanted(settings, args, snapshot.snapshot_at):
        prepared = prepare(repo, settings, snapshot, verdict, report_type, observation)
        if args.dry_run:
            print(f"───── {report_type.value} " + ("(GATED)" if prepared.gated else ""))
            print(prepared.report.content)
            print()
            for line in prepared.diagnostics:
                print(f"  diag: {line}", file=sys.stderr)
            results.append(f"{report_type.value}:rendered")
            continue
        outcome = publish(repo, prepared.report, _publisher(settings), prepared.analysis)
        state = "duplicate" if outcome.skipped_duplicate else "edited" if outcome.edited else "sent"
        print(f"{report_type.value}: {state}{' (gated)' if prepared.gated else ''}")
        results.append(f"{report_type.value}:{state}")
    if not results:
        print("no report slot due — use --type to force one")
    return results


def cmd_report(settings: Settings, args: argparse.Namespace) -> int:
    """Re-render the stored latest snapshot. --dry-run never reaches Telegram."""
    repo = _repo(settings)
    snapshot = repo.latest_snapshot()
    if snapshot is None:
        print("no snapshot stored yet — run: market-monitor fetch", file=sys.stderr)
        return 1
    _emit(repo, settings, args, snapshot, None)
    return 0


def cmd_run_once(settings: Settings, args: argparse.Namespace) -> int:
    repo = _repo(settings)
    job = repo.start_job("run-once")
    try:
        snapshot, verdict, snapshot_id = collect(repo, settings)
        if not verdict.publishable:
            # Raw quotes are stored regardless; what is refused is publication.
            repo.finish_job(job, "FAILED", "InsufficientSnapshot", "; ".join(verdict.warnings))
            print("not publishable: " + "; ".join(verdict.warnings), file=sys.stderr)
            return 1
        results = _emit(repo, settings, args, snapshot, verdict)
        repo.finish_job(
            job,
            "OK",
            metadata={"snapshot_id": snapshot_id, "dry_run": args.dry_run, "reports": results},
        )
        return 0
    except MarketMonitorError as exc:
        repo.finish_job(job, "FAILED", type(exc).__name__, str(exc))
        log.error("run_once_failed", exc_info=True)
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


def cmd_config(settings: Settings, _: argparse.Namespace) -> int:
    """Show the effective administrative settings (§35)."""
    schedule = settings.section("schedule")
    print(f"model version   {settings.model_version}")
    print(f"timezone        {settings.timezone}")
    print(f"snapshot slots  {', '.join(schedule.get('snapshot', [])) or '(none)'}")
    print(f"analysis slots  {', '.join(schedule.get('analysis', [])) or '(none)'}")
    for section, key in (
        ("instruments", "mandatory"),
        ("instruments", "optional"),
        ("instruments", "analysis_required"),
        ("instruments", "analysis_optional"),
        ("display", "fx"),
        ("display", "metals"),
    ):
        names = [i.value for i in settings.instrument_list(section, key)]
        print(f"{section}.{key:<18} {', '.join(names) or '(none)'}")
    print(f"usd/aed peg     {settings.section('peg').get('usd_aed')}")
    footer = settings.section("reporting").get("footer", {})
    for field_name in ("brand_name", "bot_username", "channel_username"):
        print(f"footer.{field_name:<16} {footer.get(field_name, '') or '(unset)'}")
    return 0


def cmd_health(settings: Settings, _: argparse.Namespace) -> int:
    repo = _repo(settings)
    ok = True
    for provider in build_chain(settings):
        healthy = provider.health_check()
        ok = ok and healthy
        print(f"provider {provider.name:<10} {'ok' if healthy else 'FAILED'}")
    telegram = "configured" if settings.telegram_token and settings.telegram_channel else "missing"
    print(f"telegram credentials {telegram}")
    last = repo.last_job("run-once")
    if last:
        print(f"last run-once {last['status']} at {last['started_at']}")
    snapshot = repo.latest_snapshot()
    if snapshot:
        print(f"latest snapshot {to_tehran(snapshot.snapshot_at):%Y-%m-%d %H:%M} Tehran")
    return 0 if ok else 1


def cmd_backfill(settings: Settings, args: argparse.Namespace) -> int:
    """Import TGJU's daily closes so trends and calibration have history to read."""
    repo = _repo(settings)
    job = repo.start_job("backfill")
    try:
        result = backfill(repo, settings, days=args.days, dry_run=args.dry_run)
    except MarketMonitorError as exc:
        repo.finish_job(job, "FAILED", type(exc).__name__, str(exc))
        log.error("backfill_failed", exc_info=True)
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    repo.finish_job(
        job,
        "OK",
        metadata={
            "sessions": result.sessions,
            "skipped_existing": result.skipped_existing,
            "dry_run": args.dry_run,
        },
    )
    span = f"{result.first} → {result.last}" if result.first else "nothing new"
    print(f"{'would import' if args.dry_run else 'imported'} {result.sessions} sessions — {span}")
    print(f"  already stored  {result.skipped_existing}")
    print(f"  no aligned ounce {result.skipped_no_ounce}")
    return 0


def cmd_db_info(settings: Settings, _: argparse.Namespace) -> int:
    repo = _repo(settings)
    print(f"database {settings.db_path}")
    for table, count in repo.counts().items():
        print(f"  {table:<12} {count:>8}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="market-monitor", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("fetch", help="fetch, validate, and store one snapshot")

    for name, help_text in (
        ("report", "render the latest stored snapshot"),
        ("run-once", "fetch, analyse, render, publish"),
    ):
        cmd = sub.add_parser(name, help=help_text)
        cmd.add_argument("--dry-run", action="store_true", help="print instead of publishing")
        cmd.add_argument(
            "--type",
            choices=sorted(TYPES),
            help="force one report type instead of the slots due now",
        )

    history = sub.add_parser("backfill", help="import TGJU daily closes into the history")
    history.add_argument(
        "--days",
        type=int,
        default=365,
        help="how far back to import (default 365; 0 imports everything TGJU has,"
        " which is a decade and a much larger database)",
    )
    history.add_argument(
        "--dry-run", action="store_true", help="count what would be imported, write nothing"
    )

    sub.add_parser("health", help="provider, credential, and database status")
    sub.add_parser("db-info", help="row counts and latest snapshot")
    sub.add_parser("config", help="show the effective schedule, instruments, and footer")
    return parser


COMMANDS = {
    "fetch": cmd_fetch,
    "report": cmd_report,
    "run-once": cmd_run_once,
    "backfill": cmd_backfill,
    "health": cmd_health,
    "db-info": cmd_db_info,
    "config": cmd_config,
}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = Settings.load()
    configure(settings.log_level)
    return COMMANDS[args.command](settings, args)


if __name__ == "__main__":
    raise SystemExit(main())
