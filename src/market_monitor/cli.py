"""Operator entry point. Every pipeline stage can be run on its own."""

from __future__ import annotations

import argparse
import logging
import sys

from .domain.errors import MarketMonitorError
from .jobs.collect import build_chain, collect
from .jobs.report import build_report, publish
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


def cmd_report(settings: Settings, args: argparse.Namespace) -> int:
    """Re-render the stored latest snapshot. --dry-run never reaches Telegram."""
    repo = _repo(settings)
    snapshot = repo.latest_snapshot()
    if snapshot is None:
        print("no snapshot stored yet — run: market-monitor fetch", file=sys.stderr)
        return 1
    report, analysis = build_report(repo, settings, snapshot)
    if args.dry_run:
        print(report.content)
        return 0
    outcome = publish(repo, report, _publisher(settings), analysis)
    print("skipped (already delivered)" if outcome.skipped_duplicate else "sent")
    return 0


def cmd_run_once(settings: Settings, args: argparse.Namespace) -> int:
    repo = _repo(settings)
    job = repo.start_job("run-once")
    try:
        snapshot, verdict, snapshot_id = collect(repo, settings)
        if not verdict.publishable:
            repo.finish_job(job, "FAILED", "InsufficientSnapshot", "; ".join(verdict.warnings))
            print("not publishable: " + "; ".join(verdict.warnings), file=sys.stderr)
            return 1
        report, analysis = build_report(repo, settings, snapshot, verdict)
        if args.dry_run:
            repo.finish_job(job, "OK", metadata={"snapshot_id": snapshot_id, "dry_run": True})
            print(report.content)
            return 0
        outcome = publish(repo, report, _publisher(settings), analysis)
        repo.finish_job(
            job,
            "OK",
            metadata={
                "snapshot_id": snapshot_id,
                "published": outcome.published,
                "message_id": outcome.report.telegram_message_id,
            },
        )
        print("skipped (already delivered)" if outcome.skipped_duplicate else "sent")
        return 0
    except MarketMonitorError as exc:
        repo.finish_job(job, "FAILED", type(exc).__name__, str(exc))
        log.error("run_once_failed", exc_info=True)
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


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

    report = sub.add_parser("report", help="render the latest stored snapshot")
    report.add_argument("--dry-run", action="store_true", help="print instead of publishing")

    run_once = sub.add_parser("run-once", help="fetch, analyse, render, publish")
    run_once.add_argument("--dry-run", action="store_true", help="print instead of publishing")

    sub.add_parser("health", help="provider, credential, and database status")
    sub.add_parser("db-info", help="row counts and latest snapshot")
    return parser


COMMANDS = {
    "fetch": cmd_fetch,
    "report": cmd_report,
    "run-once": cmd_run_once,
    "health": cmd_health,
    "db-info": cmd_db_info,
}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = Settings.load()
    configure(settings.log_level)
    return COMMANDS[args.command](settings, args)


if __name__ == "__main__":
    raise SystemExit(main())
