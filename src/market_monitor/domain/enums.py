from __future__ import annotations

from enum import StrEnum


class Instrument(StrEnum):
    USD_IRR_FREE = "usd_irr_free"
    GOLD_18K = "gold_18k"
    XAU_USD = "xau_usd"
    EMAMI_COIN = "emami_coin"
    # v1.1 FX. AED is a display asset and an analytical input; the rest are
    # display and history only (ARCHITECTURE.md §4.5, §13).
    AED_IRT = "aed_irt"
    EUR_IRT = "eur_irt"
    TRY_IRT = "try_irt"
    JPY_IRT = "jpy_irt"


class Unit(StrEnum):
    TOMAN_PER_USD = "toman/usd"
    TOMAN_PER_GRAM = "toman/gram"
    USD_PER_TROY_OUNCE = "usd/troy_oz"
    TOMAN_PER_COIN = "toman/coin"
    RIAL_PER_USD = "rial/usd"
    RIAL_PER_GRAM = "rial/gram"
    RIAL_PER_COIN = "rial/coin"
    TOMAN_PER_AED = "toman/aed"
    TOMAN_PER_EUR = "toman/eur"
    TOMAN_PER_TRY = "toman/try"
    TOMAN_PER_JPY = "toman/jpy"
    RIAL_PER_AED = "rial/aed"
    RIAL_PER_EUR = "rial/eur"
    RIAL_PER_TRY = "rial/try"
    # TGJU quotes the yen per *hundred*. Declaring that as its own unit is what
    # stops a 100x error: the conversion is forced through normalization
    # instead of being assumed anywhere (docs/PROVIDERS.md).
    RIAL_PER_100_JPY = "rial/100jpy"


CANONICAL_UNIT: dict[Instrument, Unit] = {
    Instrument.USD_IRR_FREE: Unit.TOMAN_PER_USD,
    Instrument.GOLD_18K: Unit.TOMAN_PER_GRAM,
    Instrument.XAU_USD: Unit.USD_PER_TROY_OUNCE,
    Instrument.EMAMI_COIN: Unit.TOMAN_PER_COIN,
    Instrument.AED_IRT: Unit.TOMAN_PER_AED,
    Instrument.EUR_IRT: Unit.TOMAN_PER_EUR,
    Instrument.TRY_IRT: Unit.TOMAN_PER_TRY,
    # Canonical is toman per ONE yen. Reports show 100 (§6) — presentation only.
    Instrument.JPY_IRT: Unit.TOMAN_PER_JPY,
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


class AnalysisBasis(StrEnum):
    """Which market session the analysis inputs belong to (ARCHITECTURE.md §14.1).

    LIVE       — every required input is inside its freshness limit.
    LAST_CLOSE — the Iranian inputs share one closed session and the ounce was
                 aligned to it from history, not taken live.
    """

    LIVE = "LIVE"
    LAST_CLOSE = "LAST_CLOSE"


class ReasonCode(StrEnum):
    USD_ABOVE_GOLD_IMPLIED = "USD_ABOVE_GOLD_IMPLIED"
    USD_BELOW_GOLD_IMPLIED = "USD_BELOW_GOLD_IMPLIED"
    USD_ABOVE_AED_IMPLIED = "USD_ABOVE_AED_IMPLIED"
    USD_BELOW_AED_IMPLIED = "USD_BELOW_AED_IMPLIED"
    # Which cross-market reference disagrees, and whether they agree with each
    # other. This is the §9 three-way read, expressed machine-readably.
    GOLD_AND_AED_AGREE = "GOLD_AND_AED_AGREE"
    GOLD_AND_AED_DISAGREE = "GOLD_AND_AED_DISAGREE"
    AED_REFERENCE_UNAVAILABLE = "AED_REFERENCE_UNAVAILABLE"
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
    BASIS_LAST_CLOSE = "BASIS_LAST_CLOSE"


class GateCode(StrEnum):
    """Why a report was or was not published. Structured so the public wording
    and the admin diagnostic are two renderings of one fact, never two texts
    that can drift apart (ARCHITECTURE.md §14, §17, §38).
    """

    OK = "OK"
    MISSING_MANDATORY = "MISSING_MANDATORY"
    INVALID_QUOTE = "INVALID_QUOTE"
    UNIT_SANITY_FAILED = "UNIT_SANITY_FAILED"
    STALE_REQUIRED_INPUT = "STALE_REQUIRED_INPUT"
    SESSION_INCOHERENT = "SESSION_INCOHERENT"
    XAU_NOT_ALIGNED = "XAU_NOT_ALIGNED"
    SNAPSHOT_WINDOW_EXCEEDED = "SNAPSHOT_WINDOW_EXCEEDED"
    OPTIONAL_ASSET_OMITTED = "OPTIONAL_ASSET_OMITTED"
    SUSPECT_MOVE = "SUSPECT_MOVE"


class ReportType(StrEnum):
    # v1.1 public surfaces (§3). SCHEDULED_SUMMARY is the v1.0 type: retained
    # because delivered rows reference it and history stays reproducible.
    MARKET_SNAPSHOT = "market_snapshot"
    AYAR_ANALYSIS = "ayar_analysis"
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
