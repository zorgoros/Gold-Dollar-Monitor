"""collect -> analyse -> render, with a provider that never touches the network."""

import json
from pathlib import Path

import httpx
import pytest

from market_monitor.domain.enums import Instrument, SnapshotStatus
from market_monitor.domain.errors import InsufficientSnapshot, ProviderUnavailable
from market_monitor.jobs.collect import collect
from market_monitor.jobs.report import build_report
from market_monitor.providers.tgju import TgjuProvider
from market_monitor.settings import Settings

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "default.toml"


@pytest.fixture
def settings(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    loaded = Settings.load(CONFIG_PATH)
    # Freshness limits are minutes; the fixture is a captured previous close, so
    # widen them here to test the happy path rather than the staleness path.
    config = json.loads(json.dumps(loaded.config))
    config["freshness"] = {k: 60 * 24 * 365 for k in config["freshness"]}
    return Settings(
        config=config,
        db_path=tmp_path / "pipeline.db",
        telegram_token=None,
        telegram_channel=None,
        log_level="INFO",
    )


def fixture_provider(payload=None) -> TgjuProvider:
    data = payload or json.loads((FIXTURES / "tgju_call1_ajax.json").read_text(encoding="utf-8"))
    handler = lambda request: httpx.Response(200, json=data)  # noqa: E731
    return TgjuProvider(httpx.Client(transport=httpx.MockTransport(handler)))


def test_full_pipeline_produces_a_persian_report(repo, settings):
    snapshot, verdict, snapshot_id = collect(repo, settings, [fixture_provider()])
    assert verdict.publishable
    assert snapshot.status is SnapshotStatus.COMPLETE
    assert snapshot_id > 0

    stored = repo.latest_snapshot()
    assert stored is not None
    assert stored.require(Instrument.USD_IRR_FREE) == 187_800.0

    report, analysis = build_report(repo, settings, stored, verdict)
    assert "📊 گزارش بازار" in report.content
    assert "بازار: 187,800 تومان" in report.content
    assert report.report_key.startswith("scheduled_summary|")
    assert analysis.metrics["usd_gap_pct"] is not None

    # metrics and signals were persisted for the next run's trend lookup
    counts = repo.counts()
    assert counts["metrics"] >= 7 and counts["signals"] >= 2


def test_collect_attaches_the_snapshot_id_so_the_time_series_gets_written(repo, settings):
    """Without the id, build_report writes no metrics and trends stay empty forever."""
    snapshot, verdict, snapshot_id = collect(repo, settings, [fixture_provider()])
    assert snapshot.id == snapshot_id

    build_report(repo, settings, snapshot, verdict)
    counts = repo.counts()
    assert counts["metrics"] >= 7 and counts["signals"] >= 2


def test_all_providers_failing_yields_an_unpublishable_snapshot(repo, settings):
    class Dead:
        name = "dead"

        def fetch_quotes(self, instruments):
            raise ProviderUnavailable("down")

        def health_check(self):
            return False

    snapshot, verdict, snapshot_id = collect(repo, settings, [Dead()])
    assert not verdict.publishable
    assert snapshot.quotes == {} and snapshot_id == 0
    assert "missing mandatory data" in verdict.warnings[0]


def test_an_unpublishable_snapshot_never_becomes_a_report(repo, settings):
    payload = json.loads((FIXTURES / "tgju_call1_ajax.json").read_text(encoding="utf-8"))
    del payload["current"]["ons"]
    snapshot, verdict, _ = collect(repo, settings, [fixture_provider(payload)])

    assert not verdict.publishable
    with pytest.raises(InsufficientSnapshot):
        build_report(repo, settings, snapshot, verdict)


def test_raw_quotes_are_preserved_even_when_the_snapshot_is_degraded(repo, settings):
    """A failed run is still data — the observations are kept for later analysis."""
    payload = json.loads((FIXTURES / "tgju_call1_ajax.json").read_text(encoding="utf-8"))
    del payload["current"]["sekee"]  # optional instrument only
    snapshot, verdict, snapshot_id = collect(repo, settings, [fixture_provider(payload)])
    assert verdict.publishable
    assert Instrument.EMAMI_COIN not in snapshot.quotes
    assert repo.counts()["quotes"] == 3


def test_stale_previous_close_is_flagged_but_still_reported(repo, tmp_path):
    """Real freshness limits: the fixture's rial quotes are yesterday's close."""
    strict = Settings.load(CONFIG_PATH)
    settings = Settings(
        config=strict.config,
        db_path=tmp_path / "strict.db",
        telegram_token=None,
        telegram_channel=None,
        log_level="INFO",
    )
    snapshot, verdict, _ = collect(repo, settings, [fixture_provider()])
    assert verdict.status is SnapshotStatus.PARTIAL
    assert verdict.publishable
    assert any("stale" in w for w in verdict.warnings)

    report, analysis = build_report(repo, settings, snapshot, verdict)
    assert analysis.degraded
    assert "⚠️ هشدار داده:" in report.content
