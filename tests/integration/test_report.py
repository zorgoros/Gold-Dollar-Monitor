import json
from datetime import timedelta

from market_monitor.analysis import engine
from market_monitor.analysis.engine import analyze
from market_monitor.domain.models import Metric
from market_monitor.reporting.formatter_fa import DISCLAIMER, render, signed_pct, trend_line
from market_monitor.reporting.models import widget_payload
from tests.conftest import AT
from tests.integration.test_engine import CONFIG


def test_report_contains_the_sections_the_spec_prescribes(repo, snapshot):
    text = render(analyze(snapshot(coin=189_485_000.0), repo, CONFIG))
    for expected in (
        "📊 گزارش بازار",
        "💵 دلار آزاد",
        "🥇 طلای ۱۸ عیار",
        "🪙 سکه امامی",
        "مدل: v1.0",
    ):
        assert expected in text


def test_report_prints_market_and_implied_side_by_side(repo, snapshot):
    text = render(analyze(snapshot(), repo, CONFIG))
    assert "بازار: 185,400 تومان" in text
    assert "ضمنی طلا: 181,236 تومان" in text
    assert "فاصله: +2.30%" in text


def test_report_always_carries_the_disclaimer(repo, snapshot):
    assert DISCLAIMER in render(analyze(snapshot(), repo, CONFIG))


def test_missing_history_prints_a_dash_not_a_zero(repo, snapshot):
    text = render(analyze(snapshot(), repo, CONFIG))
    assert "1D — | 3D — | 7D —" in text


def test_trend_line_formats_available_horizons():
    assert trend_line({"1d": 0.4, "3d": 1.7, "7d": None}) == "1D +0.40% | 3D +1.70% | 7D —"


def test_signed_pct_marks_direction():
    assert signed_pct(2.32) == "+2.32%" and signed_pct(-2.25) == "-2.25%"


def test_data_warnings_are_visible_in_the_report(repo, snapshot):
    analysis = analyze(snapshot(), repo, CONFIG, warnings=["stale: xau_usd"])
    text = render(analysis)
    assert "⚠️ هشدار داده:" in text and "stale: xau_usd" in text


def test_widget_payload_is_json_serializable_and_shaped_for_the_api(repo, snapshot):
    sid = repo.save_snapshot(snapshot())
    repo.save_metrics(
        sid, [Metric(engine.USD_MARKET, 180_000.0, "toman/usd", "1.0")], AT - timedelta(days=1)
    )
    payload = widget_payload(analyze(snapshot(coin=189_485_000.0), repo, CONFIG))
    encoded = json.loads(json.dumps(payload, ensure_ascii=False))

    usd_widget = next(w for w in encoded if w["instrument"] == "USD_IRT")
    assert usd_widget["market_value"] == 185_400.0
    assert usd_widget["gap_pct"] is not None
    assert usd_widget["trends"]["1d"] is not None
    assert usd_widget["signal"]["reason_codes"]
    assert usd_widget["data_quality"] == "OK"
    assert {w["instrument"] for w in encoded} == {"USD_IRT", "GOLD_18K", "XAU_USD", "EMAMI_COIN"}
