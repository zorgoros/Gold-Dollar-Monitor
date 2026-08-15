"""Public dashboard data must remain separate from storage and Telegram text."""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest

from market_monitor.analysis.engine import analyze
from market_monitor.domain.enums import Instrument, QualityStatus
from market_monitor.jobs.report import store_analytics
from market_monitor.settings import Settings
from market_monitor.web.projection import DashboardProjection
from tests.conftest import AT, make_quote

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "default.toml"


@pytest.fixture
def settings(tmp_path):
    loaded = Settings.load(CONFIG_PATH)
    return replace(loaded, db_path=tmp_path / "dashboard.db")


def test_latest_keeps_usd_reference_routes_separate(repo, snapshot, settings):
    repo.save_snapshot(snapshot(aed=True, coin=True))

    payload = DashboardProjection(repo, settings).latest()

    usd = next(card for card in payload["cards"] if card["instrument"] == "USD_IRT")
    assert [item["name"] for item in usd["references"]] == ["gold", "aed"]
    assert "composite" not in payload
    assert "coin_premium_world_pct" not in str(payload)


def test_latest_marks_recent_live_observation_as_current(repo, snapshot, settings):
    repo.save_snapshot(snapshot())

    payload = DashboardProjection(
        repo,
        settings,
        clock=lambda: AT + timedelta(minutes=5),
    ).latest()

    assert payload["data_status"] == {
        "code": "LIVE",
        "as_of": "2026-08-12T09:30:00+00:00",
        "age_seconds": 300,
        "freshness_limit_seconds": 1200,
    }


def test_latest_marks_old_snapshot_as_stale(repo, snapshot, settings):
    repo.save_snapshot(snapshot())

    payload = DashboardProjection(
        repo,
        settings,
        clock=lambda: AT + timedelta(hours=1),
    ).latest()

    assert payload["data_status"]["code"] == "STALE"


def test_latest_reports_last_close_without_claiming_market_hours(repo, snapshot, settings):
    closed = snapshot()
    closed.quotes[Instrument.GOLD_18K] = make_quote(
        Instrument.GOLD_18K,
        19_150_000.0,
        AT,
        quality_status=QualityStatus.STALE,
    )
    repo.save_snapshot(closed)

    payload = DashboardProjection(
        repo,
        settings,
        clock=lambda: AT + timedelta(minutes=5),
    ).latest()

    assert payload["data_status"]["code"] == "LAST_CLOSE"


def test_latest_hides_detail_when_analysis_alignment_fails(repo, snapshot, settings):
    closed_at = AT - timedelta(hours=30)
    closed = snapshot(at=AT)
    closed.quotes[Instrument.USD_IRR_FREE] = make_quote(
        Instrument.USD_IRR_FREE, 185_400.0, closed_at
    )
    closed.quotes[Instrument.GOLD_18K] = make_quote(Instrument.GOLD_18K, 19_150_000.0, closed_at)
    closed.quotes[Instrument.XAU_USD] = make_quote(Instrument.XAU_USD, 4_382.0, AT)
    repo.save_snapshot(closed)

    payload = DashboardProjection(repo, settings).latest()

    assert payload["state"] == "READY"
    assert payload["analysis"] == {"state": "UNAVAILABLE"}


def test_latest_returns_no_data_without_a_snapshot(repo, settings):
    assert DashboardProjection(repo, settings).latest() == {
        "state": "NO_DATA",
        "cards": [],
        "analysis": {"state": "UNAVAILABLE"},
    }


def test_history_reports_incomplete_coverage(repo, snapshot, settings):
    old_at = AT - timedelta(hours=2)
    for at, usd in ((old_at, 180_000.0), (AT, 185_400.0)):
        stored = snapshot(at=at, usd=usd)
        snapshot_id = repo.save_snapshot(stored)
        stored = replace(stored, id=snapshot_id)
        store_analytics(repo, stored, analyze(stored, repo, settings.config))

    payload = DashboardProjection(repo, settings).history(("usd_market",), "1d")

    assert payload["range"] == "1d"
    assert payload["start"] == "2026-08-11T09:30:00+00:00"
    assert payload["end"] == "2026-08-12T09:30:00+00:00"
    assert payload["coverage_complete"] is False
    assert [point["value"] for point in payload["series"]["usd_market"]] == [
        180_000.0,
        185_400.0,
    ]


def test_latest_publishes_short_analysis_conclusions(repo, snapshot, settings):
    repo.save_snapshot(snapshot(aed=True, coin=True))

    payload = DashboardProjection(repo, settings, clock=lambda: AT).latest()

    assert payload["analysis"]["summary_fa"]
    assert len(payload["analysis"]["summary_fa"]) <= 2
    assert payload["analysis"]["summary_fa"][0] == payload["analysis"]["signals"][0]["summary_fa"]


@pytest.mark.parametrize("metric", ["coin_premium_world_pct", "secret", ""])
def test_history_rejects_non_public_metrics(repo, settings, metric):
    with pytest.raises(ValueError, match="unsupported metric"):
        DashboardProjection(repo, settings).history((metric,), "1d")


def test_history_rejects_an_unknown_range(repo, settings):
    with pytest.raises(ValueError, match="unsupported range"):
        DashboardProjection(repo, settings).history(("usd_market",), "90d")
