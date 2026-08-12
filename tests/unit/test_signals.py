import pytest

from market_monitor.analysis.signals import (
    Bands,
    classify,
    gold_signal,
    severity,
    usd_signal,
)
from market_monitor.domain.enums import Classification, ReasonCode
from tests.conftest import AT

BANDS = Bands(neutral=1.0, slight=3.0, stretched=7.0)


@pytest.mark.parametrize(
    ("gap", "expected"),
    [
        (0.4, Classification.NEUTRAL),
        (-0.9, Classification.NEUTRAL),
        (2.3, Classification.SLIGHTLY_EXPENSIVE),
        (5.0, Classification.EXPENSIVE),
        (9.0, Classification.STRETCHED),
        (-2.25, Classification.SLIGHTLY_UNDERVALUED),
        (-6.0, Classification.UNDERVALUED),
    ],
)
def test_classification_bands(gap, expected):
    assert classify(gap, BANDS) is expected


def test_severity_scales_with_distance():
    assert [severity(g, BANDS) for g in (0.5, 2.0, 5.0, 12.0)] == [0, 1, 2, 3]


def test_case_a_stretched_usd_carries_its_reason_codes():
    signal = usd_signal(2.32, "FALLING", "EXPANDING", BANDS, AT)
    assert set(signal.reason_codes) >= {
        ReasonCode.USD_ABOVE_GOLD_IMPLIED,
        ReasonCode.IMPLIED_USD_FALLING,
        ReasonCode.GAP_EXPANDING,
    }
    assert "افزایش" in signal.summary_fa


def test_case_b_says_implied_is_catching_up():
    signal = usd_signal(2.32, "RISING", "CONTRACTING", BANDS, AT)
    assert ReasonCode.GAP_CONTRACTING in signal.reason_codes
    assert "کاهش" in signal.summary_fa


def test_no_history_is_reported_as_insufficient_not_invented():
    signal = usd_signal(2.32, "UNKNOWN", "UNKNOWN", BANDS, AT)
    assert ReasonCode.INSUFFICIENT_HISTORY in signal.reason_codes


def test_case_d_domestic_gold_lagging():
    signal = gold_signal(-2.25, "RISING", "RISING", BANDS, AT)
    assert ReasonCode.DOMESTIC_GOLD_LAGGING in signal.reason_codes
    assert ReasonCode.XAU_RISING in signal.reason_codes


def test_stale_input_is_flagged_and_lowers_confidence():
    fresh = usd_signal(2.32, "RISING", "STABLE", BANDS, AT)
    stale = usd_signal(2.32, "RISING", "STABLE", BANDS, AT, degraded=True)
    assert ReasonCode.STALE_SOURCE in stale.reason_codes
    assert stale.confidence < fresh.confidence


def test_confidence_never_pretends_to_be_calibrated():
    """Bands are provisional, so no signal may claim high confidence."""
    assert usd_signal(9.0, "RISING", "EXPANDING", BANDS, AT).confidence <= 0.6
