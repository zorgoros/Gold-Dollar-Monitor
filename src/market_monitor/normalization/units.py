"""Unit conversion. A value never travels without the unit it was measured in."""

from __future__ import annotations

from ..domain.constants import RIAL_PER_TOMAN, TROY_OUNCE_GRAMS
from ..domain.enums import CANONICAL_UNIT, Instrument, Unit
from ..domain.errors import UnitNormalizationError

_PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

_RIAL_TO_TOMAN: dict[Unit, Unit] = {
    Unit.RIAL_PER_USD: Unit.TOMAN_PER_USD,
    Unit.RIAL_PER_GRAM: Unit.TOMAN_PER_GRAM,
    Unit.RIAL_PER_COIN: Unit.TOMAN_PER_COIN,
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


def to_canonical(instrument: Instrument, value: float, unit: Unit) -> tuple[float, Unit]:
    """Convert a provider value to the instrument's canonical unit.

    Only rial->toman is a real conversion today; anything else must already
    arrive canonical, because guessing is how a 10x error reaches a report.
    """
    canonical = CANONICAL_UNIT[instrument]
    if unit == canonical:
        return value, canonical
    if _RIAL_TO_TOMAN.get(unit) == canonical:
        return rial_to_toman(value), canonical
    raise UnitNormalizationError(f"cannot convert {unit} to {canonical} for {instrument}")
