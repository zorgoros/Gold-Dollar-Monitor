from datetime import timedelta

import pytest

from market_monitor.domain.enums import DeliveryStatus, Instrument, ReportType
from market_monitor.domain.errors import DatabaseError
from market_monitor.domain.models import Metric, Report
from market_monitor.storage.database import connect, migrate
from market_monitor.timeutil import now_utc
from tests.conftest import AT


def test_migrations_are_idempotent(tmp_path):
    conn = connect(tmp_path / "m.db")
    assert migrate(conn) == ["001_initial", "002_fx_instruments", "003_gold_24k"]
    assert migrate(conn) == []
    conn.close()


def test_snapshot_round_trips_with_provenance(repo, snapshot):
    snapshot_id = repo.save_snapshot(snapshot())
    loaded = repo.latest_snapshot()
    assert loaded is not None and loaded.id == snapshot_id
    assert loaded.require(Instrument.USD_IRR_FREE) == 185_400.0
    quote = loaded.quotes[Instrument.GOLD_18K]
    assert (quote.provider, quote.unit.value) == ("test", "toman/gram")
    assert quote.source_timestamp == AT


def test_last_value_returns_the_most_recent_observation(repo, snapshot):
    repo.save_snapshot(snapshot(at=AT, usd=185_400.0))
    repo.save_snapshot(snapshot(at=AT + timedelta(hours=4), usd=186_000.0))
    assert repo.last_value(Instrument.USD_IRR_FREE) == 186_000.0


def test_metric_near_picks_the_closest_observation_in_window(repo, snapshot):
    sid = repo.save_snapshot(snapshot())
    repo.save_metrics(sid, [Metric("usd_market", 185_400.0, "toman/usd", "1.0")], AT)
    repo.save_metrics(
        sid, [Metric("usd_market", 180_000.0, "toman/usd", "1.0")], AT - timedelta(days=1)
    )

    found = repo.metric_near("usd_market", AT - timedelta(days=1), timedelta(hours=12))
    assert found is not None and found[0] == 180_000.0


def test_metric_near_returns_nothing_outside_tolerance(repo, snapshot):
    sid = repo.save_snapshot(snapshot())
    repo.save_metrics(sid, [Metric("usd_market", 185_400.0, "toman/usd", "1.0")], AT)
    assert repo.metric_near("usd_market", AT - timedelta(days=7), timedelta(hours=12)) is None


def test_metric_history_returns_requested_points_in_time_order(repo, snapshot):
    old_at = AT - timedelta(hours=2)
    old_id = repo.save_snapshot(snapshot(at=old_at))
    new_id = repo.save_snapshot(snapshot(at=AT))
    repo.save_metrics(old_id, [Metric("usd_market", 180_000.0, "toman/usd", "1.2")], old_at)
    repo.save_metrics(new_id, [Metric("usd_market", 185_400.0, "toman/usd", "1.2")], AT)

    points = repo.metric_history(("usd_market",), AT - timedelta(days=1), AT)

    assert [(point.name, point.value, point.at) for point in points] == [
        ("usd_market", 180_000.0, old_at),
        ("usd_market", 185_400.0, AT),
    ]


def _report(key: str) -> Report:
    return Report(
        report_type=ReportType.SCHEDULED_SUMMARY,
        report_key=key,
        content="x",
        channel="telegram",
        generated_at=now_utc(),
        model_version="1.0",
    )


def test_duplicate_delivery_is_refused_by_the_database(repo):
    first = repo.save_report(_report("scheduled_summary|2026-08-12T13:00|1.0"))
    repo.mark_report_sent(first, 42)
    assert repo.already_delivered("scheduled_summary|2026-08-12T13:00|1.0")

    second = repo.save_report(_report("scheduled_summary|2026-08-12T13:00|1.0"))
    with pytest.raises(DatabaseError):
        repo.mark_report_sent(second, 43)


def test_a_failed_report_does_not_block_a_later_delivery(repo):
    failed = repo.save_report(_report("k"))
    repo.mark_report_failed(failed, DeliveryStatus.FAILED)
    retry = repo.save_report(_report("k"))
    repo.mark_report_sent(retry, 7)
    assert repo.already_delivered("k")


def test_job_run_records_outcome(repo):
    job_id = repo.start_job("run-once")
    repo.finish_job(job_id, "FAILED", "ProviderUnavailable", "timeout")
    row = repo.last_job("run-once")
    assert row is not None and (row["status"], row["error_type"]) == (
        "FAILED",
        "ProviderUnavailable",
    )


def test_absolute_database_urls_stay_absolute(tmp_path):
    """Four slashes means absolute. Stripping them all put the database inside
    the repository instead of where the operator pointed it."""
    from market_monitor.settings import ROOT, _db_path

    absolute = tmp_path / "elsewhere.db"
    assert _db_path(f"sqlite:///{absolute}") == absolute
    assert _db_path("sqlite:///data/market.db") == ROOT / "data" / "market.db"
