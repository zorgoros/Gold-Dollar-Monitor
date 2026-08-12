from __future__ import annotations

from enum import StrEnum


class Instrument(StrEnum):
    USD_IRR_FREE = "usd_irr_free"
    GOLD_18K = "gold_18k"
    XAU_USD = "xau_usd"
    EMAMI_COIN = "emami_coin"


class Unit(StrEnum):
    TOMAN_PER_USD = "toman/usd"
    TOMAN_PER_GRAM = "toman/gram"
    USD_PER_TROY_OUNCE = "usd/troy_oz"
    TOMAN_PER_COIN = "toman/coin"
    RIAL_PER_USD = "rial/usd"
    RIAL_PER_GRAM = "rial/gram"
    RIAL_PER_COIN = "rial/coin"


CANONICAL_UNIT: dict[Instrument, Unit] = {
    Instrument.USD_IRR_FREE: Unit.TOMAN_PER_USD,
    Instrument.GOLD_18K: Unit.TOMAN_PER_GRAM,
    Instrument.XAU_USD: Unit.USD_PER_TROY_OUNCE,
    Instrument.EMAMI_COIN: Unit.TOMAN_PER_COIN,
}


class QualityStatus(StrEnum):
    OK = "OK"
    STALE = "STALE"
    SUSPECT = "SUSPECT"
    INVALID = "INVALID"


class SnapshotStatus(StrEnum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class Classification(StrEnum):
    UNDERVALUED = "UNDERVALUED"
    SLIGHTLY_UNDERVALUED = "SLIGHTLY_UNDERVALUED"
    NEUTRAL = "NEUTRAL"
    SLIGHTLY_EXPENSIVE = "SLIGHTLY_EXPENSIVE"
    EXPENSIVE = "EXPENSIVE"
    STRETCHED = "STRETCHED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    DATA_QUALITY_WARNING = "DATA_QUALITY_WARNING"


class ReasonCode(StrEnum):
    USD_ABOVE_GOLD_IMPLIED = "USD_ABOVE_GOLD_IMPLIED"
    USD_BELOW_GOLD_IMPLIED = "USD_BELOW_GOLD_IMPLIED"
    IMPLIED_USD_RISING = "IMPLIED_USD_RISING"
    IMPLIED_USD_FALLING = "IMPLIED_USD_FALLING"
    GAP_EXPANDING = "GAP_EXPANDING"
    GAP_CONTRACTING = "GAP_CONTRACTING"
    GAP_STABLE = "GAP_STABLE"
    XAU_RISING = "XAU_RISING"
    XAU_FALLING = "XAU_FALLING"
    DOMESTIC_GOLD_LAGGING = "DOMESTIC_GOLD_LAGGING"
    DOMESTIC_GOLD_LEADING = "DOMESTIC_GOLD_LEADING"
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
    STALE_SOURCE = "STALE_SOURCE"


class ReportType(StrEnum):
    SCHEDULED_SUMMARY = "scheduled_summary"
    MOVEMENT_ALERT = "movement_alert"
    GAP_ALERT = "gap_alert"
    DATA_WARNING = "data_warning"
    DAILY_CLOSE = "daily_close"
    WEEKLY_REVIEW = "weekly_review"


class DeliveryStatus(StrEnum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    SKIPPED_DUPLICATE = "SKIPPED_DUPLICATE"
