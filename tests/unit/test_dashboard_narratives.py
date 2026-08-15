"""Dashboard narratives describe existing signals without recalculating them."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime

from market_monitor.analysis.dashboard_narratives import select_dashboard_narratives
from market_monitor.domain.enums import Classification, Instrument, ReasonCode
from market_monitor.domain.models import Signal

AT = datetime(2026, 8, 12, 9, 30, tzinfo=UTC)


def make_signal(
    instrument: Instrument,
    classification: Classification,
    reasons: Iterable[ReasonCode] = (),
) -> Signal:
    return Signal(
        instrument=instrument,
        classification=classification,
        severity=1,
        confidence=0.5,
        summary_fa="existing signal",
        reason_codes=list(reasons),
        metrics_used={},
        generated_at=AT,
        model_version="1.2",
    )


def test_selects_bilingual_gold_and_coin_context_from_existing_classifications():
    payload = select_dashboard_narratives(
        [
            make_signal(Instrument.GOLD_18K, Classification.SLIGHTLY_UNDERVALUED),
            make_signal(Instrument.EMAMI_COIN, Classification.EXPENSIVE),
        ]
    )

    assert payload["gold"][0]["id"] == "gold.below_theoretical"
    assert payload["coin"][0]["id"] == "coin.positive_premium"
    assert set(payload["gold"][0]["text"]) == {"fa", "en"}
    assert all(payload["gold"][0]["text"].values())


def test_usd_overview_reports_reference_disagreement_and_market_relation():
    payload = select_dashboard_narratives(
        [
            make_signal(
                Instrument.USD_IRR_FREE,
                Classification.SLIGHTLY_EXPENSIVE,
                [ReasonCode.GOLD_AND_AED_DISAGREE],
            )
        ]
    )

    assert [item["id"] for item in payload["overview"]] == [
        "usd.references.disagree",
        "usd.market.above_reference",
    ]


def test_data_warning_precedes_the_existing_usd_relationship():
    payload = select_dashboard_narratives(
        [
            make_signal(
                Instrument.USD_IRR_FREE,
                Classification.NEUTRAL,
                [ReasonCode.STALE_SOURCE, ReasonCode.AED_REFERENCE_UNAVAILABLE],
            )
        ]
    )

    assert [item["id"] for item in payload["overview"]] == [
        "data.warning",
        "usd.references.gold_only",
        "usd.market.near_reference",
    ]


def test_missing_optional_signals_leave_only_their_sections_empty():
    payload = select_dashboard_narratives(
        [make_signal(Instrument.GOLD_18K, Classification.NEUTRAL)]
    )

    assert payload["overview"] == []
    assert payload["gold"][0]["id"] == "gold.near_theoretical"
    assert payload["coin"] == []
