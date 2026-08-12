"""Unit conversion. A value never travels without the unit it was measured in."""

from __future__ import annotations

from ..domain.constants import JPY_QUOTE_UNITS, RIAL_PER_TOMAN, TROY_OUNCE_GRAMS
from ..domain.enums import CANONICAL_UNIT, Instrument, Unit
from ..domain.errors import UnitNormalizationError

_PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

_RIAL_TO_TOMAN: dict[Unit, Unit] = {
    Unit.RIAL_PER_USD: Unit.TOMAN_PER_USD,
    Unit.RIAL_PER_GRAM: Unit.TOMAN_PER_GRAM,
    Unit.RIAL_PER_COIN: Unit.TOMAN_PER_COIN,
    Unit.RIAL_PER_AED: Unit.TOMAN_PER_AED,
    Unit.RIAL_PER_EUR: Unit.TOMAN_PER_EUR,
    Unit.RIAL_PER_TRY: Unit.TOMAN_PER_TRY,
}

# Two divisions, not one: rial->toman and per-100-yen->per-yen. Both are exact.
_RIAL_PER_100_TO_TOMAN_PER_1: dict[Unit, Unit] = {
    Unit.RIAL_PER_100_JPY: Unit.TOMAN_PER_JPY,
}


def parse_number(raw: str) -> float:
    """Provider text -> float. Handles thousands separators and Persian digits."""
    text = str(raw).translate(_PERSIAN_DIGITS).strip()
    for junk in (",", "٬", "٬", "‏", "‎", " ", "\xa0"):
        text = text.replace(junk, "")
    if not text:
        raise UnitNormalizationError("empty price string")
    try:
        return float(text)
    except ValueError as exc:
        raise UnitNormalizationError(f"not a number: {raw!r}") from exc


def rial_to_toman(value: float) -> float:
    return value / RIAL_PER_TOMAN


def ounce_to_gram(value_per_ounce: float) -> float:
    """A per-troy-ounce price expressed per gram."""
    return value_per_ounce / TROY_OUNCE_GRAMS


def per_hundred_to_per_one(value: float) -> float:
    """A price quoted per 100 units expressed per single unit."""
    return value / JPY_QUOTE_UNITS


def per_one_to_per_hundred(value: float) -> float:
    """Presentation inverse: a per-unit price shown per 100 units (§6)."""
    return value * JPY_QUOTE_UNITS


def to_canonical(instrument: Instrument, value: float, unit: Unit) -> tuple[float, Unit]:
    """Convert a provider value to the instrument's canonical unit.

    Every conversion here is exact. Anything not listed must already arrive
    canonical, because guessing is how a 10x — or, for the yen, a 100x — error
    reaches a report.
    """
    canonical = CANONICAL_UNIT[instrument]
    if unit == canonical:
        return value, canonical
    if _RIAL_TO_TOMAN.get(unit) == canonical:
        return rial_to_toman(value), canonical
    if _RIAL_PER_100_TO_TOMAN_PER_1.get(unit) == canonical:
        return per_hundred_to_per_one(rial_to_toman(value)), canonical
    raise UnitNormalizationError(f"cannot convert {unit} to {canonical} for {instrument}")
