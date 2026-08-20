"""The two public surfaces (§3, §18, §19).

Several assertions here are the exact inverse of their v1.0 versions. That is
deliberate: v1.0 printed engineering diagnostics and dash-filled placeholders to
the channel, and §17 and §20 remove both.
"""

import json
from datetime import timedelta
from pathlib import Path

from market_monitor.analysis import engine
from market_monitor.analysis.engine import analyze
from market_monitor.domain.constants import ATTRIBUTION
from market_monitor.domain.enums import AnalysisBasis, Instrument
from market_monitor.domain.models import Metric
from market_monitor.reporting.formatter_fa import (
    ANALYSIS_UNAVAILABLE,
    DISCLAIMER,
    STATUS_LAST_CLOSE,
    ReportConfig,
    render_analysis,
    render_snapshot,
    render_unavailable,
    signed_pct,
    trend_line,
)
from market_monitor.reporting.models import widget_payload
from tests.conftest import AT, publish_baseline
from tests.integration.test_engine import CONFIG

CONFIG_FA = ReportConfig(
    fx=[
        Instrument.USD_IRR_FREE,
        Instrument.EUR_IRT,
        Instrument.AED_IRT,
        Instrument.TRY_IRT,
        Instrument.JPY_IRT,
    ],
    metals=[Instrument.GOLD_18K, Instrument.XAU_USD, Instrument.EMAMI_COIN],
    brand_name="عیار مارکت | Ayar Market",
)


def full(snapshot):
    return snapshot(coin=True, aed=True, eur=True, try_=True, jpy=True)


# ------------------------------------------------------------ market snapshot


def test_snapshot_shows_the_configured_fx_board(repo, snapshot):
    text = render_snapshot(analyze(full(snapshot), repo, CONFIG), CONFIG_FA)
    assert "💱 ارز" in text
    for label in ("دلار", "یورو", "درهم", "لیر"):
        assert label in text
    assert "🥇 طلا و سکه" in text


def test_snapshot_shows_the_yen_per_hundred_with_the_unit_stated(repo, snapshot):
    """Stored per one yen, published per hundred, and the label says so (§6)."""
    text = render_snapshot(analyze(full(snapshot), repo, CONFIG), CONFIG_FA)
    assert "۱۰۰ ین: 117,600 تومان" in text
    assert "ین: 1,176 تومان" not in text


def test_snapshot_omits_instruments_that_were_not_collected(repo, snapshot):
    """No row with a dash in it — an absent instrument is simply absent (§20)."""
    text = render_snapshot(analyze(snapshot(), repo, CONFIG), CONFIG_FA)
    assert "یورو" not in text and "درهم" not in text and "سکه امامی" not in text
    assert "—" not in text
    assert "دلار" in text


def test_snapshot_hides_an_asset_removed_from_the_display_config(repo, snapshot):
    hidden = ReportConfig(fx=[Instrument.USD_IRR_FREE], metals=[Instrument.GOLD_18K])
    text = render_snapshot(analyze(full(snapshot), repo, CONFIG), hidden)
    assert "درهم" not in text and "سکه امامی" not in text
    assert "دلار" in text


def test_display_config_does_not_change_what_is_analysed(repo, snapshot):
    """Hiding the dirham from the board must not remove it from the model (§27)."""
    analysis = analyze(full(snapshot), repo, CONFIG)
    hidden = ReportConfig(fx=[Instrument.USD_IRR_FREE], metals=[])
    assert "درهم" not in render_snapshot(analysis, hidden)
    assert engine.AED_GAP in analysis.metrics


def test_snapshot_prints_change_since_the_previous_report(repo, snapshot):
    publish_baseline(repo, snapshot(), {engine.USD_MARKET: 180_000.0}, AT - timedelta(hours=4))
    text = render_snapshot(analyze(snapshot(), repo, CONFIG), CONFIG_FA)
    assert "↕ تغییر از به‌روزرسانی قبل" in text
    assert "دلار +3.00%" in text


def test_change_section_disappears_when_there_is_no_previous_report(repo, snapshot):
    text = render_snapshot(analyze(snapshot(), repo, CONFIG), CONFIG_FA)
    assert "↕ تغییر از به‌روزرسانی قبل" not in text


def test_a_flat_market_drops_the_change_section_rather_than_printing_zeroes(repo, snapshot):
    """§2: three lines of ±0.00% are noise, not information."""
    publish_baseline(
        repo,
        snapshot(),
        {
            engine.USD_MARKET: 185_400.0,
            engine.GOLD_MARKET: 19_150_000.0,
            engine.COIN_MARKET: 189_485_000.0,
        },
        AT - timedelta(hours=4),
    )
    text = render_snapshot(analyze(snapshot(coin=True), repo, CONFIG), CONFIG_FA)
    assert "↕ تغییر از به‌روزرسانی قبل" not in text
    assert "0.00%" not in text


def test_a_move_below_the_rounding_boundary_still_drops_the_section(repo, snapshot):
    """A change that renders as +0.00% is not a change the reader can act on."""
    publish_baseline(repo, snapshot(), {engine.USD_MARKET: 185_400.4}, AT - timedelta(hours=4))
    assert "↕ تغییر از به‌روزرسانی قبل" not in render_snapshot(
        analyze(snapshot(), repo, CONFIG), CONFIG_FA
    )


def test_one_real_move_keeps_the_whole_section(repo, snapshot):
    """Suppression is all-or-nothing: a flat line beside a real one is context."""
    publish_baseline(
        repo,
        snapshot(),
        {engine.USD_MARKET: 185_400.0, engine.GOLD_MARKET: 18_000_000.0},
        AT - timedelta(hours=4),
    )
    text = render_snapshot(analyze(snapshot(), repo, CONFIG), CONFIG_FA)
    assert "↕ تغییر از به‌روزرسانی قبل" in text
    assert "دلار +0.00%" in text
    assert "طلا +6.39%" in text


def test_both_reports_carry_one_clock_in_the_status_block(repo, snapshot):
    """§9, and the decision that it replaces the old status clock rather than joining it."""
    analysis = analyze(full(snapshot), repo, CONFIG)
    for text in (render_snapshot(analysis, CONFIG_FA), render_analysis(analysis, CONFIG_FA)):
        assert "🔄 آخرین به‌روزرسانی: 13:00" in text
        assert text.count("آخرین به‌روزرسانی") == 1
        # The clock that used to ride on the freshness line is gone from it.
        assert "داده‌ها به‌روز | " not in text


def test_stale_board_says_it_is_a_previous_close(repo, snapshot):
    from dataclasses import replace

    analysis = replace(analyze(snapshot(), repo, CONFIG), basis=AnalysisBasis.LAST_CLOSE)
    assert STATUS_LAST_CLOSE in render_snapshot(analysis, CONFIG_FA)


# ------------------------------------------------------------- ayar analysis


def test_analysis_shows_all_three_usd_views(repo, snapshot):
    text = render_analysis(analyze(full(snapshot), repo, CONFIG), CONFIG_FA)
    assert "بازار:" in text
    assert "ضمنی طلا:" in text
    assert "ضمنی درهم:" in text
    assert "فاصله با طلا:" in text
    assert "فاصله با درهم:" in text


def test_analysis_drops_the_dirham_rows_when_aed_is_absent(repo, snapshot):
    text = render_analysis(analyze(snapshot(), repo, CONFIG), CONFIG_FA)
    assert "ضمنی طلا:" in text
    assert "ضمنی درهم:" not in text and "فاصله با درهم:" not in text


def test_analysis_never_says_intrinsic_value(repo, snapshot):
    """§22: theoretical value and metal content, never 'ارزش ذاتی'."""
    text = render_analysis(analyze(full(snapshot), repo, CONFIG), CONFIG_FA)
    assert "ارزش ذاتی" not in text
    assert "نظری بر مبنای دلار بازار" in text and "ارزش طلای سکه" in text


def test_analysis_avoids_verdict_language(repo, snapshot):
    """§21: state the distance, do not call a price expensive or cheap."""
    text = render_analysis(analyze(full(snapshot), repo, CONFIG), CONFIG_FA)
    for banned in ("گران", "ارزان", "ارزش واقعی"):
        assert banned not in text


def test_trend_section_is_absent_until_there_is_history(repo, snapshot):
    """§20: no '1D — | 3D — | 7D —' line on a fresh install."""
    text = render_analysis(analyze(full(snapshot), repo, CONFIG), CONFIG_FA)
    assert "📈" not in text
    assert "—" not in text


def test_trend_section_appears_once_history_exists(repo, snapshot):
    sid = repo.save_snapshot(snapshot())
    repo.save_metrics(
        sid,
        [Metric(engine.USD_IMPLIED, 178_000.0, "toman/usd", "1.1")],
        AT - timedelta(days=1),
    )
    text = render_analysis(analyze(full(snapshot), repo, CONFIG), CONFIG_FA)
    assert "📈 روند نرخ ضمنی دلار" in text and "1D" in text


def test_analysis_always_carries_the_disclaimer_and_model_version(repo, snapshot):
    text = render_analysis(analyze(full(snapshot), repo, CONFIG), CONFIG_FA)
    assert DISCLAIMER in text and "مدل: v1.1" in text


# ---------------------------------------------------------- withheld reports


def test_withheld_analysis_says_nothing_technical(repo, snapshot):
    """§17: no instrument names, no minute counts, no subsystem names."""
    from market_monitor.domain.enums import GateCode

    text = render_unavailable([GateCode.XAU_NOT_ALIGNED], CONFIG_FA, analysis_report=True)
    assert ANALYSIS_UNAVAILABLE in text
    for leak in ("xau", "stale", "span", "minutes", "emami_coin", "usd_irr_free"):
        assert leak not in text.lower()


def test_withheld_report_still_carries_the_footer(repo):
    from market_monitor.domain.enums import GateCode

    text = render_unavailable([GateCode.XAU_NOT_ALIGNED], CONFIG_FA, analysis_report=True)
    assert ATTRIBUTION in text and "عیار مارکت" in text


# ------------------------------------------------------------------- footer


def test_footer_carries_the_brand_and_the_attribution(repo, snapshot):
    text = render_snapshot(analyze(snapshot(), repo, CONFIG), CONFIG_FA)
    assert "عیار مارکت | Ayar Market" in text
    assert ATTRIBUTION in text


def test_footer_omits_handles_that_are_not_configured(repo, snapshot):
    """§24: no invented usernames. An unset handle prints nothing at all."""
    text = render_snapshot(analyze(snapshot(), repo, CONFIG), CONFIG_FA)
    assert "@" not in text


def test_footer_prints_configured_handles(repo, snapshot):
    from dataclasses import replace

    config = replace(CONFIG_FA, bot_username="@Ayar_Market_bot", channel_username="@AyarMarket")
    text = render_snapshot(analyze(snapshot(), repo, CONFIG), config)
    assert "@Ayar_Market_bot · @AyarMarket" in text


def test_attribution_survives_every_footer_setting(repo, snapshot):
    """See NOTICE. Removing this is a deliberate act, not an accident."""
    bare = ReportConfig(fx=[Instrument.USD_IRR_FREE], metals=[])
    assert ATTRIBUTION in render_snapshot(analyze(snapshot(), repo, CONFIG), bare)


def test_channel_handle_is_used_when_no_note_is_configured():
    from market_monitor.jobs.report import channel_note
    from market_monitor.settings import Settings

    def settings_with(channel):
        return Settings(
            config={"reporting": {"channel_note": ""}},
            db_path=Path("x.db"),
            telegram_token=None,
            telegram_channel=channel,
            log_level="INFO",
        )

    assert channel_note(settings_with("@my_channel")) == "@my_channel"
    # a numeric private-channel id means nothing to a reader
    assert channel_note(settings_with("-1001234567890")) == ""


# ----------------------------------------------------------------- primitives


def test_trend_line_omits_horizons_without_history():
    assert trend_line({"1d": 0.4, "3d": 1.7, "7d": None}) == "1D +0.40% | 3D +1.70%"


def test_signed_pct_marks_direction():
    assert signed_pct(2.32) == "+2.32%" and signed_pct(-2.25) == "-2.25%"


# -------------------------------------------------------------- widget payload


def test_widget_payload_is_json_serializable_and_shaped_for_the_api(repo, snapshot):
    sid = repo.save_snapshot(snapshot())
    repo.save_metrics(
        sid, [Metric(engine.USD_MARKET, 180_000.0, "toman/usd", "1.1")], AT - timedelta(days=1)
    )
    payload = widget_payload(analyze(full(snapshot), repo, CONFIG))
    encoded = json.loads(json.dumps(payload, ensure_ascii=False))

    usd_widget = next(w for w in encoded if w["instrument"] == "USD_IRT")
    assert usd_widget["market_value"] == 185_400.0
    assert usd_widget["gap_pct"] is not None
    assert usd_widget["trends"]["1d"] is not None
    assert usd_widget["signal"]["reason_codes"]
    assert usd_widget["data_quality"] == "OK"
    assert usd_widget["basis"] == "LIVE"
    assert {w["instrument"] for w in encoded} == {
        "USD_IRT",
        "GOLD_18K",
        "XAU_USD",
        "EMAMI_COIN",
        "AED_IRT",
        "EUR_IRT",
        "TRY_IRT",
        "JPY_IRT",
    }


def test_widget_payload_carries_both_usd_references_separately(repo, snapshot):
    """§11: the web surface gets two references, never one blended number."""
    payload = widget_payload(analyze(full(snapshot), repo, CONFIG))
    usd_widget = next(w for w in payload if w["instrument"] == "USD_IRT")
    names = [r["name"] for r in usd_widget["references"]]
    assert names == ["gold", "aed"]
    assert usd_widget["references"][0]["gap_pct"] != usd_widget["references"][1]["gap_pct"]
