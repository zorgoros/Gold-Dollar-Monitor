"""collect -> analyse -> render, with a provider that never touches the network."""

import json
from datetime import timedelta
from pathlib import Path

import httpx
import pytest

from market_monitor.analysis.engine import analyze
from market_monitor.domain.enums import (
    AnalysisBasis,
    GateCode,
    Instrument,
    ReportType,
    SnapshotStatus,
)
from market_monitor.domain.errors import ProviderUnavailable
from market_monitor.jobs.collect import collect
from market_monitor.jobs.report import (
    SCHEDULE_KEY,
    base_analysis,
    due_report_types,
    prepare,
    scheduled_slot,
    slot_window,
    store_analytics,
)
from market_monitor.providers.tgju import TgjuProvider
from market_monitor.settings import Settings
from market_monitor.timeutil import TEHRAN, to_tehran

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "default.toml"


def settings_from(config, db_path):
    return Settings(
        config=config,
        db_path=db_path,
        telegram_token=None,
        telegram_channel=None,
        log_level="INFO",
    )


@pytest.fixture
def settings(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    loaded = Settings.load(CONFIG_PATH)
    # Freshness limits are minutes; the fixture is a captured previous close, so
    # widen them here to test the happy path rather than the staleness path.
    config = json.loads(json.dumps(loaded.config))
    config["freshness"] = {
        k: (v if k.endswith("_minutes") else 60 * 24 * 365) for k, v in config["freshness"].items()
    }
    return settings_from(config, tmp_path / "pipeline.db")


def fixture_provider(payload=None) -> TgjuProvider:
    data = payload or json.loads((FIXTURES / "tgju_call1_ajax.json").read_text(encoding="utf-8"))
    handler = lambda request: httpx.Response(200, json=data)  # noqa: E731
    return TgjuProvider(httpx.Client(transport=httpx.MockTransport(handler)))


def emit(repo, settings, snapshot, verdict, report_type):
    observation = base_analysis(repo, settings, snapshot, verdict)
    store_analytics(repo, snapshot, observation)
    return prepare(repo, settings, snapshot, verdict, report_type, observation)


def test_full_pipeline_produces_a_persian_snapshot(repo, settings):
    snapshot, verdict, snapshot_id = collect(repo, settings, [fixture_provider()])
    assert verdict.publishable
    # PARTIAL, not COMPLETE: the captured response really does pair a live ounce
    # with a previous-day rial close, so the quotes span ~34 hours. The board
    # still publishes (§15) — it is the analysis that refuses that pairing.
    assert snapshot.status is SnapshotStatus.PARTIAL
    assert GateCode.SNAPSHOT_WINDOW_EXCEEDED in verdict.codes
    assert snapshot_id > 0

    stored = repo.latest_snapshot()
    assert stored is not None
    assert stored.require(Instrument.USD_IRR_FREE) == 187_800.0

    prepared = emit(repo, settings, stored, verdict, ReportType.MARKET_SNAPSHOT)
    assert not prepared.gated
    assert "📊 عیار مارکت" in prepared.report.content
    assert "دلار: 187,800 تومان" in prepared.report.content
    assert prepared.report.report_key.startswith("market_snapshot|")
    assert prepared.analysis.metrics["usd_gap_pct"] is not None

    counts = repo.counts()
    assert counts["metrics"] >= 7 and counts["signals"] >= 2


def test_the_new_fx_instruments_are_collected_and_stored(repo, settings):
    """Live symbols verified 2026-08-12; the fixture carries all four."""
    snapshot, _, _ = collect(repo, settings, [fixture_provider()])
    for instrument in (
        Instrument.AED_IRT,
        Instrument.EUR_IRT,
        Instrument.TRY_IRT,
        Instrument.JPY_IRT,
    ):
        assert instrument in snapshot.quotes, instrument

    stored = repo.latest_snapshot()
    assert stored.require(Instrument.AED_IRT) == pytest.approx(51_161.0)
    # per 100 yen in the feed, per one yen in storage
    assert stored.require(Instrument.JPY_IRT) == pytest.approx(1_176.0)


def test_collect_attaches_the_snapshot_id_so_the_time_series_gets_written(repo, settings):
    snapshot, verdict, snapshot_id = collect(repo, settings, [fixture_provider()])
    assert snapshot.id == snapshot_id

    emit(repo, settings, snapshot, verdict, ReportType.MARKET_SNAPSHOT)
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


def test_an_unpublishable_snapshot_yields_a_status_message_not_numbers(repo, settings):
    payload = json.loads((FIXTURES / "tgju_call1_ajax.json").read_text(encoding="utf-8"))
    del payload["current"]["ons"]
    snapshot, verdict, _ = collect(repo, settings, [fixture_provider(payload)])

    assert not verdict.publishable
    prepared = emit(repo, settings, snapshot, verdict, ReportType.AYAR_ANALYSIS)
    assert prepared.gated
    assert "187,800" not in prepared.report.content


def test_raw_quotes_are_preserved_even_when_the_snapshot_is_degraded(repo, settings):
    """A failed run is still data — the observations are kept for later analysis."""
    payload = json.loads((FIXTURES / "tgju_call1_ajax.json").read_text(encoding="utf-8"))
    del payload["current"]["sekee"]  # optional instrument only
    snapshot, verdict, _ = collect(repo, settings, [fixture_provider(payload)])
    assert verdict.publishable
    assert Instrument.EMAMI_COIN not in snapshot.quotes
    assert repo.counts()["quotes"] == 8


# ------------------------------------------------------- the publication gate


def test_stale_board_still_publishes_but_says_it_is_a_previous_close(repo, tmp_path):
    """§15: the price board is the tolerant surface."""
    strict = Settings.load(CONFIG_PATH)
    settings = settings_from(strict.config, tmp_path / "strict.db")
    snapshot, verdict, _ = collect(repo, settings, [fixture_provider()])
    assert verdict.status is SnapshotStatus.PARTIAL
    assert verdict.publishable

    prepared = emit(repo, settings, snapshot, verdict, ReportType.MARKET_SNAPSHOT)
    assert not prepared.gated
    assert prepared.analysis.basis is AnalysisBasis.LAST_CLOSE
    assert "🕐 بر مبنای آخرین پایان معاملات" in prepared.report.content


def test_analysis_is_withheld_when_no_aligned_ounce_exists(repo, tmp_path):
    """§16 and the resolution of 2026-08-12: yesterday's Tehran close may not be
    paired with a live ounce, and on a fresh database no aligned ounce exists."""
    strict = Settings.load(CONFIG_PATH)
    settings = settings_from(strict.config, tmp_path / "strict.db")
    snapshot, verdict, _ = collect(repo, settings, [fixture_provider()])

    prepared = emit(repo, settings, snapshot, verdict, ReportType.AYAR_ANALYSIS)
    assert prepared.gated
    assert "تحلیل این نوبت منتشر نشد" in prepared.report.content
    assert "187,800" not in prepared.report.content
    assert any("no stored xau_usd" in d for d in prepared.diagnostics)


def test_analysis_publishes_on_last_close_once_an_aligned_ounce_is_stored(repo, tmp_path):
    """With history at the Tehran session instant, the closed-session read is
    publishable — and it uses the historical ounce, not the live one."""
    from market_monitor.analysis.session import session_anchor
    from market_monitor.domain.models import Metric

    strict = Settings.load(CONFIG_PATH)
    settings = settings_from(strict.config, tmp_path / "strict.db")
    snapshot, verdict, _ = collect(repo, settings, [fixture_provider()])

    # The ounce has to sit near the session's *close*, not near TGJU's zeroed
    # midnight marker — that is what session_anchor exists to correct.
    session_at = session_anchor(snapshot.quotes[Instrument.USD_IRR_FREE].observed_at)
    sid = repo.save_snapshot(snapshot)
    repo.save_metrics(sid, [Metric("xau_usd", 4_000.0, "usd/troy_oz", "1.1")], session_at)

    prepared = emit(repo, settings, snapshot, verdict, ReportType.AYAR_ANALYSIS)
    assert not prepared.gated
    assert prepared.analysis.basis is AnalysisBasis.LAST_CLOSE
    assert prepared.analysis.metrics["xau_usd"] == 4_000.0
    assert "🕐 بر مبنای آخرین پایان معاملات" in prepared.report.content


def test_stored_series_keeps_the_observed_ounce_not_the_aligned_one(repo, settings):
    """Alignment reads xau_usd history; writing an aligned value back into it
    would make the lookup consume its own output."""
    snapshot, verdict, _ = collect(repo, settings, [fixture_provider()])
    observation = base_analysis(repo, settings, snapshot, verdict)
    store_analytics(repo, snapshot, observation)
    stored = repo.metric_before("xau_usd", snapshot.snapshot_at + timedelta(seconds=1))
    assert stored[0] == snapshot.require(Instrument.XAU_USD)


def test_session_incoherence_blocks_the_analysis(repo, settings, snapshot):
    """A dollar from today and a gold price from last week is not a market state."""
    from tests.conftest import AT, make_quote

    quotes = snapshot().quotes
    quotes[Instrument.GOLD_18K] = make_quote(
        Instrument.GOLD_18K, 19_150_000.0, AT - timedelta(days=7)
    )
    incoherent = snapshot()
    incoherent.quotes.update(quotes)

    prepared = emit(repo, settings, incoherent, None, ReportType.AYAR_ANALYSIS)
    assert prepared.gated
    assert any("span" in d for d in prepared.diagnostics)


# ------------------------------------------------------------ slot scheduling


def test_the_shipped_config_builds_a_working_provider_chain():
    """Regression guard: a config section silently dropped leaves the chain
    empty, and every instrument then reads as 'missing mandatory data'."""
    from market_monitor.jobs.collect import build_chain

    settings = Settings.load(CONFIG_PATH)
    assert [p.name for p in build_chain(settings)] == ["tgju", "gold-api"]


def test_every_collected_instrument_has_a_provider_and_a_symbol():
    from market_monitor.providers.tgju import SYMBOLS

    settings = Settings.load(CONFIG_PATH)
    providers = settings.section("providers")
    for key in ("mandatory", "optional"):
        for instrument in settings.instrument_list("instruments", key):
            assert instrument.value in providers, instrument
            assert instrument in SYMBOLS, instrument


def test_every_displayed_instrument_is_actually_collected():
    """§26/§27: display is a subset of collection, or the board shows blanks."""
    settings = Settings.load(CONFIG_PATH)
    collected = set(settings.instrument_list("instruments", "mandatory")) | set(
        settings.instrument_list("instruments", "optional")
    )
    shown = set(settings.instrument_list("display", "fx")) | set(
        settings.instrument_list("display", "metals")
    )
    analysed = set(settings.instrument_list("instruments", "analysis_required")) | set(
        settings.instrument_list("instruments", "analysis_optional")
    )
    assert shown <= collected
    assert analysed <= collected


def test_both_report_types_are_published_on_the_same_hourly_slots():
    """TASK-008: a price board and an analysis always arrive together.

    The owner's requirement is a property of the two lists, not of code, so it
    is asserted against the shipped config rather than against the scheduler.
    """
    config = Settings.load(CONFIG_PATH).config["schedule"]
    assert config["snapshot"] == config["analysis"]
    assert config["snapshot"] == [f"{hour:02d}:00" for hour in range(9, 22)]


def test_ten_minute_collection_does_not_raise_the_post_rate():
    """84 collection runs a day, still 13 boards and 13 analyses.

    Walks the exact cron in .github/workflows/collect.yml — every ten minutes
    from 05:02 to 18:52 UTC — through the shipped config. The five runs after the
    first inside each slot must claim the same slot key, because that is what
    routes them to an edit instead of a second post; runs past the last slot's
    window must go adhoc and publish nothing.
    """
    from datetime import UTC, datetime

    shipped = Settings.load(CONFIG_PATH)
    runs = [datetime(2026, 8, 12, 5, 2, tzinfo=UTC) + timedelta(minutes=10 * i) for i in range(84)]
    assert to_tehran(runs[0]).strftime("%H:%M") == "08:32"
    assert to_tehran(runs[-1]).strftime("%H:%M") == "22:22"

    window = slot_window(shipped)
    keys = {
        report_type: {
            scheduled_slot(at, shipped.slots(key), window)
            for at in runs
            if report_type in due_report_types(at, shipped)
        }
        for report_type, key in SCHEDULE_KEY.items()
    }
    # One distinct key per slot per type: 13 messages each, 26 in the channel.
    assert len(keys[ReportType.MARKET_SNAPSHOT]) == 13
    assert len(keys[ReportType.AYAR_ANALYSIS]) == 13
    assert sum(len(k) for k in keys.values()) == 26

    due_runs = [at for at in runs if due_report_types(at, shipped)]
    assert to_tehran(due_runs[0]).strftime("%H:%M") == "09:02"
    assert to_tehran(due_runs[-1]).strftime("%H:%M") == "21:52"
    # Six runs land in every slot; before 09:00 and after 21:59 none do.
    assert len(due_runs) == 13 * 6


def test_a_run_belongs_to_the_slot_it_has_passed_never_one_still_ahead():
    """The 2026-08-16 defect: a symmetric window is wrong in both directions.

    That day the 17:00 slot published nothing. GitHub started the two nearest
    runs 22.7 minutes early and 20.4 minutes late against a window of 20 either
    side, so neither claimed the slot and the report was lost outright. A
    scheduler is late, never early, so the window only ever looks backward — and
    a late run now refreshes the slot it passed rather than losing it.
    """
    from datetime import UTC, datetime

    shipped = Settings.load(CONFIG_PATH)
    slots = shipped.slots("snapshot")
    window = slot_window(shipped)

    early = datetime(2026, 8, 16, 13, 7, 19, tzinfo=UTC)  # 16:37 Tehran
    late = datetime(2026, 8, 16, 13, 50, 22, tzinfo=UTC)  # 17:20 Tehran
    assert scheduled_slot(early, slots, window) == "2026-08-16 16:00"
    assert scheduled_slot(late, slots, window) == "2026-08-16 17:00"


def test_the_slot_window_stays_under_the_gap_between_slots():
    """Above the gap, one slot's window swallows the next and that slot is lost.

    The window replaced a symmetric tolerance that had to stay under the
    *collection* interval. What bounds it now is the spacing of the slots
    themselves, so the invariant is asserted rather than left in a comment.
    """
    from datetime import datetime

    config = Settings.load(CONFIG_PATH).config["schedule"]
    slots = sorted({*config["snapshot"], *config["analysis"]})
    marks = [datetime.strptime(slot, "%H:%M") for slot in slots]
    gap = min((b - a).total_seconds() / 60 for a, b in zip(marks, marks[1:], strict=False))
    assert config["slot_window_minutes"] < gap


def test_due_report_types_follow_config_not_code(settings, tmp_path):
    from datetime import datetime

    config = json.loads(json.dumps(settings.config))
    config["schedule"] = {"snapshot": ["10:00"], "analysis": ["18:00"], "slot_window_minutes": 5}
    tuned = settings_from(config, tmp_path / "sched.db")

    at_ten = datetime(2026, 8, 12, 10, 0, tzinfo=TEHRAN)
    at_six = datetime(2026, 8, 12, 18, 0, tzinfo=TEHRAN)
    at_noon = datetime(2026, 8, 12, 12, 0, tzinfo=TEHRAN)

    assert due_report_types(at_ten, tuned) == [ReportType.MARKET_SNAPSHOT]
    assert due_report_types(at_six, tuned) == [ReportType.AYAR_ANALYSIS]
    assert due_report_types(at_noon, tuned) == []


def test_the_two_report_types_do_not_share_a_delivery_key(repo, settings, snapshot):
    observation = base_analysis(repo, settings, snapshot(aed=True), None)
    keys = {
        report_type: prepare(
            repo, settings, snapshot(aed=True), None, report_type, observation
        ).report.report_key
        for report_type in (ReportType.MARKET_SNAPSHOT, ReportType.AYAR_ANALYSIS)
    }
    assert len(set(keys.values())) == 2
    assert all("|1.2" in k for k in keys.values())


def test_model_version_bump_does_not_rewrite_history(repo, settings, snapshot):
    """A v1.0 key and a v1.1 key are different keys; stored rows keep their own."""
    from market_monitor.jobs.report import report_key

    old = report_key(ReportType.MARKET_SNAPSHOT, "2026-08-12 09:00", "1.0")
    new = report_key(ReportType.MARKET_SNAPSHOT, "2026-08-12 09:00", "1.1")
    assert old != new


def test_duplicate_publication_is_prevented_per_report_type(repo, settings, snapshot):
    from market_monitor.domain.enums import DeliveryStatus
    from market_monitor.jobs.report import publish

    class Fake:
        channel = "telegram"
        sent = 0

        def publish(self, report):
            Fake.sent += 1
            return 42

        def edit(self, report, message_id):
            return True

        def health_check(self):
            return True

    snap = snapshot()
    snap_id = repo.save_snapshot(snap)
    observation = base_analysis(repo, settings, snap, None)
    prepared = prepare(repo, settings, snap, None, ReportType.MARKET_SNAPSHOT, observation)
    report = prepared.report.__class__(**{**prepared.report.__dict__, "snapshot_id": snap_id})

    first = publish(repo, report, Fake(), observation)
    second = publish(repo, report, Fake(), observation)
    assert first.published and first.report.delivery_status is DeliveryStatus.SENT
    # One message per key still holds. The second run rewrites it (TASK-008)
    # rather than adding a second post, which is what `Fake.sent` proves.
    assert second.published and second.edited and not second.skipped_duplicate
    assert Fake.sent == 1


def test_analysis_and_snapshot_render_from_the_same_analytical_output(repo, settings, snapshot):
    """§47: no business logic hidden in a template — both surfaces read metrics."""
    from market_monitor.reporting.formatter_fa import ReportConfig, render_analysis, render_snapshot

    analysis = analyze(snapshot(aed=True, coin=True), repo, settings.config)
    config = ReportConfig(
        fx=[Instrument.USD_IRR_FREE, Instrument.AED_IRT],
        metals=[Instrument.GOLD_18K],
    )
    board = render_snapshot(analysis, config)
    read = render_analysis(analysis, config)
    usd = f"{round(analysis.metrics['usd_market']):,}"
    assert usd in board and usd in read
