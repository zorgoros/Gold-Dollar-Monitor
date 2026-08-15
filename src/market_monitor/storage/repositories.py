"""All SQL lives here. Nothing above this layer knows the database exists."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Any

from ..domain.enums import (
    DeliveryStatus,
    Instrument,
    QualityStatus,
    ReportType,
    SnapshotStatus,
    Unit,
)
from ..domain.errors import DatabaseError
from ..domain.models import Metric, Quote, Report, Signal, Snapshot
from ..timeutil import from_iso, now_utc, to_iso


class Repository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self._instrument_ids: dict[str, int] = {}

    # ---------------------------------------------------------------- lookups
    def instrument_id(self, instrument: Instrument) -> int:
        cached = self._instrument_ids.get(instrument.value)
        if cached is not None:
            return cached
        row = self.conn.execute(
            "SELECT id FROM instruments WHERE symbol = ?", (instrument.value,)
        ).fetchone()
        if row is None:
            raise DatabaseError(f"unknown instrument {instrument.value!r} — migration missing?")
        self._instrument_ids[instrument.value] = int(row["id"])
        return int(row["id"])

    def last_value(self, instrument: Instrument) -> float | None:
        """Most recent stored value, used to catch a parser producing a 10x jump.

        Ordered by when the price was *observed*, not when the row was written.
        A backfill inserts thousands of rows retrieved just now but observed
        years ago (jobs/backfill.py); ordering on `retrieved_at` would hand the
        jump check an arbitrary one of them and reject every honest live quote
        afterwards.
        """
        row = self.conn.execute(
            "SELECT normalized_value FROM quotes WHERE instrument_id = ?"
            " ORDER BY COALESCE(source_timestamp, retrieved_at) DESC LIMIT 1",
            (self.instrument_id(instrument),),
        ).fetchone()
        return float(row["normalized_value"]) if row else None

    def snapshot_at_exists(self, at: datetime) -> bool:
        """Whether a snapshot is already stored at exactly this instant.

        Backfill computes each session's instant deterministically, so this is
        what makes re-running it a no-op instead of a second copy of history.
        """
        row = self.conn.execute(
            "SELECT 1 FROM snapshots WHERE snapshot_at = ? LIMIT 1", (to_iso(at),)
        ).fetchone()
        return row is not None

    # ---------------------------------------------------------------- writes
    def save_snapshot(self, snapshot: Snapshot) -> int:
        """Persist the raw quotes and the snapshot that groups them, atomically."""
        try:
            self.conn.execute("BEGIN")
            cur = self.conn.execute(
                "INSERT INTO snapshots (snapshot_at, status, created_at) VALUES (?, ?, ?)",
                (to_iso(snapshot.snapshot_at), snapshot.status.value, to_iso(now_utc())),
            )
            snapshot_id = int(cur.lastrowid or 0)
            for quote in snapshot.quotes.values():
                quote_cur = self.conn.execute(
                    "INSERT INTO quotes (instrument_id, provider, provider_symbol, raw_value,"
                    " normalized_value, currency, unit, source_timestamp, retrieved_at,"
                    " quality_status, raw_payload_hash, metadata_json)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        self.instrument_id(quote.instrument),
                        quote.provider,
                        quote.provider_symbol,
                        quote.raw_value,
                        quote.normalized_value,
                        quote.currency,
                        quote.unit.value,
                        to_iso(quote.source_timestamp) if quote.source_timestamp else None,
                        to_iso(quote.retrieved_at),
                        quote.quality_status.value,
                        quote.raw_payload_hash,
                        json.dumps(quote.metadata, ensure_ascii=False),
                    ),
                )
                self.conn.execute(
                    "INSERT INTO snapshot_quotes (snapshot_id, quote_id) VALUES (?, ?)",
                    (snapshot_id, quote_cur.lastrowid),
                )
            self.conn.execute("COMMIT")
        except sqlite3.Error as exc:
            self.conn.execute("ROLLBACK")
            raise DatabaseError(f"could not store snapshot: {exc}") from exc
        return snapshot_id

    def save_metrics(self, snapshot_id: int, metrics: list[Metric], at: datetime) -> None:
        self.conn.executemany(
            "INSERT INTO metrics (snapshot_id, metric_name, metric_value, unit, model_version,"
            " created_at) VALUES (?, ?, ?, ?, ?, ?)",
            [(snapshot_id, m.name, m.value, m.unit, m.model_version, to_iso(at)) for m in metrics],
        )

    def save_signals(self, snapshot_id: int, signals: list[Signal]) -> None:
        self.conn.executemany(
            "INSERT INTO signals (snapshot_id, instrument, classification, severity, confidence,"
            " summary_fa, reason_codes_json, model_version, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    snapshot_id,
                    s.instrument.value,
                    s.classification.value,
                    s.severity,
                    s.confidence,
                    s.summary_fa,
                    json.dumps([c.value for c in s.reason_codes]),
                    s.model_version,
                    to_iso(s.generated_at),
                )
                for s in signals
            ],
        )

    # ---------------------------------------------------------------- history
    def metric_near(
        self, name: str, target: datetime, tolerance: timedelta
    ) -> tuple[float, datetime] | None:
        """Closest metric value to a target time, not 'the row N rows back'.

        History is irregular — runs are missed, markets close. A lookback asks
        for a moment in time and accepts the nearest observation within
        tolerance, or nothing.
        """
        low, high = to_iso(target - tolerance), to_iso(target + tolerance)
        row = self.conn.execute(
            "SELECT metric_value, created_at FROM metrics"
            " WHERE metric_name = ? AND created_at BETWEEN ? AND ?"
            " ORDER BY ABS(julianday(created_at) - julianday(?)) LIMIT 1",
            (name, low, high, to_iso(target)),
        ).fetchone()
        if row is None:
            return None
        return float(row["metric_value"]), from_iso(row["created_at"])

    def metric_before(self, name: str, before: datetime) -> tuple[float, datetime] | None:
        """The most recent value of a metric strictly before an instant.

        Not the baseline for "change since the last report" — that is
        `published_baseline`, and wiring it back to this would silently make the
        published percentage mean "since the last collection" (BUG-007). This
        answers the plain question about the stored series, which is what
        inspection and tests want.
        """
        row = self.conn.execute(
            "SELECT metric_value, created_at FROM metrics"
            " WHERE metric_name = ? AND created_at < ?"
            " ORDER BY created_at DESC LIMIT 1",
            (name, to_iso(before)),
        ).fetchone()
        if row is None:
            return None
        return float(row["metric_value"]), from_iso(row["created_at"])

    def published_baseline(
        self, report_type: ReportType, exclude_snapshot_id: int | None = None
    ) -> dict[str, float]:
        """Every metric behind the last report of this type that readers actually saw.

        This is the baseline for "change since the last report" (§18), and it is
        deliberately not `metric_before`: once collection runs more often than
        publication, the previous row is a reading from thirty minutes ago while
        the previous *report* is hours old. Anchoring on the delivered report is
        what keeps the published percentage meaning what its label says.

        A gated delivery writes no metrics, so it is skipped rather than
        producing an empty baseline — the reader compares against the last board
        that showed numbers. Returns `{}` when nothing has been published yet,
        which drops the change section instead of inventing a zero.
        """
        row = self.conn.execute(
            "SELECT r.snapshot_id FROM reports r"
            " WHERE r.report_type = ? AND r.delivery_status = ? AND r.snapshot_id IS NOT NULL"
            "   AND r.snapshot_id IS NOT ?"
            "   AND EXISTS (SELECT 1 FROM metrics m WHERE m.snapshot_id = r.snapshot_id)"
            " ORDER BY r.sent_at DESC LIMIT 1",
            (report_type.value, DeliveryStatus.SENT.value, exclude_snapshot_id),
        ).fetchone()
        if row is None:
            return {}
        return {
            r["metric_name"]: float(r["metric_value"])
            for r in self.conn.execute(
                "SELECT metric_name, metric_value FROM metrics WHERE snapshot_id = ?",
                (row["snapshot_id"],),
            )
        }

    def latest_snapshot(self) -> Snapshot | None:
        row = self.conn.execute(
            "SELECT id, snapshot_at, status FROM snapshots ORDER BY snapshot_at DESC LIMIT 1"
        ).fetchone()
        return self._load_snapshot(row) if row else None

    def _load_snapshot(self, row: sqlite3.Row) -> Snapshot:
        quote_rows = self.conn.execute(
            "SELECT q.*, i.symbol FROM quotes q"
            " JOIN snapshot_quotes sq ON sq.quote_id = q.id"
            " JOIN instruments i ON i.id = q.instrument_id"
            " WHERE sq.snapshot_id = ?",
            (row["id"],),
        ).fetchall()
        quotes = {}
        for q in quote_rows:
            instrument = Instrument(q["symbol"])
            quotes[instrument] = Quote(
                instrument=instrument,
                provider=q["provider"],
                provider_symbol=q["provider_symbol"],
                raw_value=q["raw_value"],
                normalized_value=float(q["normalized_value"]),
                unit=Unit(q["unit"]),
                currency=q["currency"],
                retrieved_at=from_iso(q["retrieved_at"]),
                source_timestamp=from_iso(q["source_timestamp"]) if q["source_timestamp"] else None,
                quality_status=QualityStatus(q["quality_status"]),
                raw_payload_hash=q["raw_payload_hash"],
                metadata=json.loads(q["metadata_json"]),
                id=int(q["id"]),
            )
        return Snapshot(
            snapshot_at=from_iso(row["snapshot_at"]),
            quotes=quotes,
            status=SnapshotStatus(row["status"]),
            id=int(row["id"]),
        )

    # ---------------------------------------------------------------- reports
    def already_delivered(self, report_key: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM reports WHERE report_key = ? AND delivery_status = ? LIMIT 1",
            (report_key, DeliveryStatus.SENT.value),
        ).fetchone()
        return row is not None

    def save_report(self, report: Report) -> int:
        cur = self.conn.execute(
            "INSERT INTO reports (snapshot_id, report_type, report_key, content, channel,"
            " generated_at, delivery_status, model_version) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                report.snapshot_id,
                report.report_type.value,
                report.report_key,
                report.content,
                report.channel,
                to_iso(report.generated_at),
                report.delivery_status.value,
                report.model_version,
            ),
        )
        return int(cur.lastrowid or 0)

    def mark_report_sent(self, report_id: int, message_id: int | None) -> None:
        try:
            self.conn.execute(
                "UPDATE reports SET delivery_status = ?, sent_at = ?, telegram_message_id = ?"
                " WHERE id = ?",
                (DeliveryStatus.SENT.value, to_iso(now_utc()), message_id, report_id),
            )
        except sqlite3.IntegrityError as exc:
            # The partial unique index fired: another run delivered this key first.
            raise DatabaseError(f"report key already delivered: {exc}") from exc

    def mark_report_failed(self, report_id: int, status: DeliveryStatus) -> None:
        self.conn.execute(
            "UPDATE reports SET delivery_status = ? WHERE id = ?", (status.value, report_id)
        )

    # ---------------------------------------------------------------- job runs
    def start_job(self, job_name: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO job_runs (job_name, started_at, status) VALUES (?, ?, 'RUNNING')",
            (job_name, to_iso(now_utc())),
        )
        return int(cur.lastrowid or 0)

    def finish_job(
        self,
        job_id: int,
        status: str,
        error_type: str | None = None,
        error_message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.conn.execute(
            "UPDATE job_runs SET finished_at = ?, status = ?, error_type = ?, error_message = ?,"
            " metadata_json = ? WHERE id = ?",
            (
                to_iso(now_utc()),
                status,
                error_type,
                error_message,
                json.dumps(metadata or {}, ensure_ascii=False),
                job_id,
            ),
        )

    def last_job(self, job_name: str) -> sqlite3.Row | None:
        row: sqlite3.Row | None = self.conn.execute(
            "SELECT * FROM job_runs WHERE job_name = ? ORDER BY started_at DESC LIMIT 1",
            (job_name,),
        ).fetchone()
        return row

    def counts(self) -> dict[str, int]:
        tables = ("quotes", "snapshots", "metrics", "signals", "reports", "job_runs")
        return {
            table: int(self.conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"])
            for table in tables
        }
