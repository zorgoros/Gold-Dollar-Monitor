from datetime import timedelta

import pytest

from market_monitor.analysis import engine
from market_monitor.analysis.engine import analyze
from market_monitor.domain.enums import Classification, Instrument
from market_monitor.domain.models import Metric
from tests.conftest import AT

CONFIG = {
    "model_version": "1.0",
    "analysis": {
        "gap_neutral_band_pct": 1.0,
        "gap_slight_band_pct": 3.0,
        "gap_stretched_pct": 7.0,
        "gap_expansion_tolerance_pct": 0.25,
        "trend_tolerance_hours": 12,
    },
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
    assert engine.COIN_PREMIUM not in without.metrics

    with_coin = analyze(snapshot(coin=189_485_000.0), repo, CONFIG)
    assert with_coin.metrics[engine.COIN_PREMIUM] == pytest.approx(
        (189_485_000.0 / with_coin.metrics[engine.COIN_INTRINSIC] - 1) * 100
    )
    assert len(with_coin.signals) == 3


def test_metric_rows_carry_units_and_model_version(repo, snapshot):
    rows = analyze(snapshot(), repo, CONFIG).metric_rows()
    by_name = {m.name: m for m in rows}
    assert by_name[engine.USD_MARKET].unit == "toman/usd"
    assert by_name[engine.USD_GAP].unit == "pct"
    assert all(m.model_version == "1.0" for m in rows)
