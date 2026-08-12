from datetime import timedelta

import pytest

from market_monitor.domain.enums import Instrument, QualityStatus, SnapshotStatus
from market_monitor.domain.errors import InvalidQuote
from market_monitor.normalization.validators import validate_quote, validate_snapshot
from tests.conftest import AT, make_quote

FRESH = timedelta(minutes=20)
MANDATORY = [Instrument.USD_IRR_FREE, Instrument.GOLD_18K, Instrument.XAU_USD]


def test_fresh_positive_quote_passes():
    quote = validate_quote(make_quote(Instrument.XAU_USD, 4382.0), AT, FRESH)
    assert quote.quality_status is QualityStatus.OK


@pytest.mark.parametrize("bad", [0.0, -5.0, float("nan"), float("inf")])
def test_unusable_values_are_rejected(bad):
    with pytest.raises(InvalidQuote):
        validate_quote(make_quote(Instrument.XAU_USD, bad), AT, FRESH)


def test_old_observation_is_flagged_stale_not_dropped():
    quote = validate_quote(
        make_quote(Instrument.XAU_USD, 4382.0, AT - timedelta(hours=9)), AT, FRESH
    )
    assert quote.quality_status is QualityStatus.STALE


def test_future_timestamp_is_rejected():
    with pytest.raises(InvalidQuote):
        validate_quote(make_quote(Instrument.XAU_USD, 4382.0, AT + timedelta(hours=2)), AT, FRESH)


def test_implausible_jump_is_marked_suspect():
    quote = validate_quote(
        make_quote(Instrument.USD_IRR_FREE, 1_854_000.0), AT, FRESH, last_value=185_400.0
    )
    assert quote.quality_status is QualityStatus.SUSPECT


def test_complete_snapshot_is_publishable(snapshot):
    verdict = validate_snapshot(snapshot().quotes, MANDATORY, AT, timedelta(minutes=15))
    assert verdict.status is SnapshotStatus.COMPLETE
    assert verdict.publishable and verdict.warnings == []


def test_missing_mandatory_instrument_blocks_publication(snapshot):
    quotes = snapshot().quotes
    del quotes[Instrument.XAU_USD]
    verdict = validate_snapshot(quotes, MANDATORY, AT, timedelta(minutes=15))
    assert not verdict.publishable
    assert verdict.status is SnapshotStatus.FAILED
    assert "missing mandatory data" in verdict.warnings[0]


def test_stale_quote_downgrades_to_partial_but_still_publishes(snapshot):
    quotes = snapshot().quotes
    quotes[Instrument.XAU_USD] = validate_quote(
        make_quote(Instrument.XAU_USD, 4382.0, AT - timedelta(hours=9)), AT, FRESH
    )
    verdict = validate_snapshot(quotes, MANDATORY, AT, timedelta(minutes=15))
    assert verdict.publishable
    assert verdict.status is SnapshotStatus.PARTIAL
    assert any("stale" in w for w in verdict.warnings)


def test_ten_times_unit_regression_is_refused(snapshot):
    """The single-source guard: rial leaking through as toman must never publish."""
    quotes = snapshot(gold=191_500_000.0).quotes  # 10x the real toman figure
    verdict = validate_snapshot(quotes, MANDATORY, AT, timedelta(minutes=15))
    assert not verdict.publishable
    assert "unit or parser error" in verdict.warnings[0]


def test_wide_time_spread_is_warned(snapshot):
    quotes = snapshot().quotes
    quotes[Instrument.XAU_USD] = make_quote(Instrument.XAU_USD, 4382.0, AT - timedelta(minutes=40))
    verdict = validate_snapshot(quotes, MANDATORY, AT, timedelta(minutes=15))
    assert any("span" in w for w in verdict.warnings)
