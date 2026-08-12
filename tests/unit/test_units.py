import pytest

from market_monitor.domain.enums import Instrument, Unit
from market_monitor.domain.errors import UnitNormalizationError
from market_monitor.normalization.units import (
    ounce_to_gram,
    parse_number,
    per_hundred_to_per_one,
    per_one_to_per_hundred,
    rial_to_toman,
    to_canonical,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1,854,000", 1_854_000.0),
        ("۱۹,۱۵۰,۰۰۰", 19_150_000.0),
        ("4382.5", 4382.5),
        (" 1 854 000 ", 1_854_000.0),
    ],
)
def test_parse_number_handles_separators_and_persian_digits(raw, expected):
    assert parse_number(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", "abc", "12,3x4"])
def test_parse_number_rejects_junk_instead_of_guessing(raw):
    with pytest.raises(UnitNormalizationError):
        parse_number(raw)


def test_rial_to_toman_divides_by_ten():
    assert rial_to_toman(1_854_000.0) == 185_400.0


def test_ounce_to_gram_uses_the_troy_constant():
    assert ounce_to_gram(31.1034768) == pytest.approx(1.0)


def test_to_canonical_converts_rial_quotes():
    value, unit = to_canonical(Instrument.USD_IRR_FREE, 1_854_000.0, Unit.RIAL_PER_USD)
    assert (value, unit) == (185_400.0, Unit.TOMAN_PER_USD)


def test_to_canonical_passes_through_a_canonical_quote():
    value, unit = to_canonical(Instrument.XAU_USD, 4382.0, Unit.USD_PER_TROY_OUNCE)
    assert (value, unit) == (4382.0, Unit.USD_PER_TROY_OUNCE)


def test_to_canonical_refuses_a_conversion_it_does_not_know():
    with pytest.raises(UnitNormalizationError):
        to_canonical(Instrument.GOLD_18K, 4382.0, Unit.USD_PER_TROY_OUNCE)


# ------------------------------------------------------------- v1.1 additions


def test_to_canonical_converts_the_new_rial_fx_quotes():
    for instrument, source, expected_unit in (
        (Instrument.AED_IRT, Unit.RIAL_PER_AED, Unit.TOMAN_PER_AED),
        (Instrument.EUR_IRT, Unit.RIAL_PER_EUR, Unit.TOMAN_PER_EUR),
        (Instrument.TRY_IRT, Unit.RIAL_PER_TRY, Unit.TOMAN_PER_TRY),
    ):
        value, unit = to_canonical(instrument, 511_610.0, source)
        assert (value, unit) == (51_161.0, expected_unit)


def test_the_yen_is_divided_by_ten_and_by_a_hundred():
    """TGJU quotes price_jpy per 100 yen. Verified 2026-08-12 against the
    USD/JPY cross: reading it per-yen would publish a 100x error."""
    value, unit = to_canonical(Instrument.JPY_IRT, 1_176_000.0, Unit.RIAL_PER_100_JPY)
    assert (value, unit) == (1_176.0, Unit.TOMAN_PER_JPY)


def test_the_yen_conversion_round_trips_for_display():
    stored, _ = to_canonical(Instrument.JPY_IRT, 1_176_000.0, Unit.RIAL_PER_100_JPY)
    assert per_one_to_per_hundred(stored) == 117_600.0
    assert per_hundred_to_per_one(per_one_to_per_hundred(stored)) == stored


def test_a_yen_quote_declared_as_plain_rial_is_refused():
    """The 100x guard: the source unit has to say per-hundred, not be assumed."""
    with pytest.raises(UnitNormalizationError):
        to_canonical(Instrument.JPY_IRT, 1_176_000.0, Unit.RIAL_PER_USD)


def test_every_instrument_has_a_canonical_unit():
    from market_monitor.domain.enums import CANONICAL_UNIT

    assert set(CANONICAL_UNIT) == set(Instrument)
