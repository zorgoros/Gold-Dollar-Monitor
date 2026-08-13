from datetime import timedelta

import pytest

from market_monitor.analysis import engine
from market_monitor.analysis.engine import analyze
from market_monitor.domain.enums import Classification, Instrument
from market_monitor.domain.models import Metric
from market_monitor.reporting.formatter_fa import ReportConfig, render_analysis
from market_monitor.reporting.models import widget_payload
from tests.conftest import AT

CONFIG = {
    "model_version": "1.1",
    "analysis": {
        "gap_neutral_band_pct": 1.0,
        "gap_slight_band_pct": 3.0,
        "gap_stretched_pct": 7.0,
        "gap_expansion_tolerance_pct": 0.25,
        "trend_tolerance_hours": 12,
    },
    "peg": {"usd_aed": 3.6725},
}


def test_analysis_reproduces_the_spec_example(repo, snapshot):
    result = analyze(snapshot(), repo, CONFIG)
    assert result.metrics[engine.USD_IMPLIED] == pytest.approx(181_236.0, abs=50.0)
    assert result.metrics[engine.USD_GAP] == pytest.approx(2.30, abs=0.05)
    assert result.metrics[engine.GOLD_THEORETICAL] == pytest.approx(19_590_000.0, rel=1e-4)
    assert result.metrics[engine.GOLD_GAP] == pytest.approx(-2.25, abs=0.05)


def test_first_ever_run_produces_signals_without_history(repo, snapshot):
    result = analyze(snapshot(), repo, CONFIG)
    assert [s.instrument for s in result.signals] == [Instrument.USD_IRR_FREE, Instrument.GOLD_18K]
    assert all(t is None for t in result.trends[engine.USD_MARKET].values())
    assert result.signals[0].classification is Classification.SLIGHTLY_EXPENSIVE


def test_trends_appear_once_history_exists(repo, snapshot):
    sid = repo.save_snapshot(snapshot())
    repo.save_metrics(
        sid,
        [
            Metric(engine.USD_MARKET, 180_000.0, "toman/usd", "1.0"),
            Metric(engine.USD_IMPLIED, 178_000.0, "toman/usd", "1.0"),
            Metric(engine.USD_GAP, 1.1, "pct", "1.0"),
        ],
        AT - timedelta(days=1),
    )
    result = analyze(snapshot(), repo, CONFIG)
    assert result.trends[engine.USD_MARKET]["1d"] == pytest.approx(3.0)
    assert result.trends[engine.USD_IMPLIED]["1d"] is not None
    # gap went 1.1 -> ~2.3, so it widened
    assert any(c.value == "GAP_EXPANDING" for c in result.signals[0].reason_codes)


def test_coin_metrics_only_appear_when_the_coin_is_quoted(repo, snapshot):
    without = analyze(snapshot(), repo, CONFIG)
    assert engine.COIN_PREMIUM_DOMESTIC not in without.metrics

    with_coin = analyze(snapshot(coin=189_485_000.0), repo, CONFIG)
    assert with_coin.metrics[engine.COIN_PREMIUM_DOMESTIC] == pytest.approx(
        (189_485_000.0 / with_coin.metrics[engine.COIN_INTRINSIC_DOMESTIC] - 1) * 100
    )
    assert len(with_coin.signals) == 3


def test_the_world_route_coin_series_is_computed_but_never_published(repo, snapshot):
    """Stored for the lead/lag research, kept out of every reader-facing surface."""
    result = analyze(snapshot(coin=189_485_000.0), repo, CONFIG)
    assert engine.COIN_PREMIUM_WORLD in result.metrics
    assert result.metrics[engine.COIN_PREMIUM_WORLD] != result.metrics[engine.COIN_PREMIUM_DOMESTIC]

    report = render_analysis(
        result, ReportConfig(fx=[Instrument.USD_IRR_FREE], metals=[Instrument.EMAMI_COIN])
    )
    assert "حباب" in report
    for value in (
        result.metrics[engine.COIN_PREMIUM_WORLD],
        result.metrics[engine.COIN_INTRINSIC_WORLD],
    ):
        assert f"{value:,.0f}" not in report
    assert all(
        engine.COIN_PREMIUM_WORLD not in str(ref)
        for card in widget_payload(result)
        for ref in card.get("references", [])
    )


def test_metric_rows_carry_units_and_model_version(repo, snapshot):
    rows = analyze(snapshot(), repo, CONFIG).metric_rows()
    by_name = {m.name: m for m in rows}
    assert by_name[engine.USD_MARKET].unit == "toman/usd"
    assert by_name[engine.USD_GAP].unit == "pct"
    assert all(m.model_version == "1.1" for m in rows)


# ------------------------------------------------------------- v1.1 additions


def test_aed_implied_usd_and_its_gap_are_computed(repo, snapshot):
    """Live 2026-08-12 figures: 51,161 toman/AED at the peg implies ~187,889."""
    result = analyze(snapshot(usd=187_800.0, aed=51_161.0), repo, CONFIG)
    assert result.metrics[engine.USD_AED_IMPLIED] == pytest.approx(187_889.0, abs=1.0)
    assert result.metrics[engine.AED_GAP] == pytest.approx(-0.047, abs=0.01)


def test_the_configured_peg_is_used_not_a_hard_coded_one(repo, snapshot):
    config = {**CONFIG, "peg": {"usd_aed": 4.0}}
    result = analyze(snapshot(aed=50_000.0), repo, config)
    assert result.metrics[engine.USD_AED_IMPLIED] == pytest.approx(200_000.0)


def test_aed_metrics_are_absent_without_a_dirham_quote(repo, snapshot):
    """Section-level input: no dirham means no dirham section, not no analysis."""
    result = analyze(snapshot(), repo, CONFIG)
    assert engine.USD_AED_IMPLIED not in result.metrics
    assert engine.AED_GAP not in result.metrics
    assert result.metrics[engine.USD_GAP] is not None


def test_gold_and_aed_gaps_stay_separate_numbers(repo, snapshot):
    """§11: no composite, no average, no weighting anywhere in the metrics."""
    result = analyze(snapshot(usd=187_800.0, aed=51_161.0), repo, CONFIG)
    blended = (result.metrics[engine.USD_IMPLIED] + result.metrics[engine.USD_AED_IMPLIED]) / 2
    assert blended not in result.metrics.values()
    assert result.metrics[engine.USD_GAP] != result.metrics[engine.AED_GAP]


def test_display_only_currencies_are_still_stored_as_metrics(repo, snapshot):
    """§27: collected and kept even though no calculation reads them yet."""
    result = analyze(snapshot(eur=True, try_=True, jpy=True), repo, CONFIG)
    for name in ("eur_irt", "try_irt", "jpy_irt"):
        assert name in result.metrics
    names = {m.name: m.unit for m in result.metric_rows()}
    assert names["jpy_irt"] == "toman/jpy"


def test_change_since_previous_report_is_computed(repo, snapshot):
    from datetime import timedelta

    from market_monitor.domain.models import Metric
    from tests.conftest import AT

    sid = repo.save_snapshot(snapshot())
    repo.save_metrics(
        sid, [Metric(engine.USD_MARKET, 180_000.0, "toman/usd", "1.1")], AT - timedelta(hours=4)
    )
    result = analyze(snapshot(), repo, CONFIG)
    assert result.changes[engine.USD_MARKET] == pytest.approx(3.0)
    assert result.changes[engine.GOLD_MARKET] is None
