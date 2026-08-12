"""Rule-based classification. Deterministic, explainable, and deliberately timid.

Confidence stays low by construction: the bands in config are provisional
placeholders, not calibrated thresholds, so a signal here is a description of
where prices sit relative to each other — never a forecast (ARCHITECTURE.md §7, §40).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..domain.constants import SIGNAL_MODEL_VERSION
from ..domain.enums import Classification, Instrument, ReasonCode
from ..domain.models import Signal

MAX_CONFIDENCE = 0.6


@dataclass(frozen=True)
class Bands:
    neutral: float
    slight: float
    stretched: float

    @classmethod
    def from_config(cls, analysis: dict[str, float]) -> Bands:
        return cls(
            neutral=float(analysis.get("gap_neutral_band_pct", 1.0)),
            slight=float(analysis.get("gap_slight_band_pct", 3.0)),
            stretched=float(analysis.get("gap_stretched_pct", 7.0)),
        )


def classify(gap: float, bands: Bands) -> Classification:
    if abs(gap) <= bands.neutral:
        return Classification.NEUTRAL
    if gap > 0:
        if gap <= bands.slight:
            return Classification.SLIGHTLY_EXPENSIVE
        if gap <= bands.stretched:
            return Classification.EXPENSIVE
        return Classification.STRETCHED
    if gap >= -bands.slight:
        return Classification.SLIGHTLY_UNDERVALUED
    return Classification.UNDERVALUED


def severity(gap: float, bands: Bands) -> int:
    magnitude = abs(gap)
    if magnitude <= bands.neutral:
        return 0
    if magnitude <= bands.slight:
        return 1
    if magnitude <= bands.stretched:
        return 2
    return 3


def _confidence(has_history: bool, degraded: bool) -> float:
    score = 0.3 + (0.2 if has_history else 0.0) - (0.15 if degraded else 0.0)
    return round(min(MAX_CONFIDENCE, max(0.1, score)), 2)


def usd_signal(
    gap: float,
    implied_direction: str,
    momentum: str,
    bands: Bands,
    generated_at: datetime,
    degraded: bool = False,
) -> Signal:
    """USD against the rate implied by the domestic gold market (§5.4 cases A–C)."""
    codes: list[ReasonCode] = [
        ReasonCode.USD_ABOVE_GOLD_IMPLIED if gap > 0 else ReasonCode.USD_BELOW_GOLD_IMPLIED
    ]
    if implied_direction == "RISING":
        codes.append(ReasonCode.IMPLIED_USD_RISING)
    elif implied_direction == "FALLING":
        codes.append(ReasonCode.IMPLIED_USD_FALLING)
    else:
        codes.append(ReasonCode.INSUFFICIENT_HISTORY)

    momentum_code = {
        "EXPANDING": ReasonCode.GAP_EXPANDING,
        "CONTRACTING": ReasonCode.GAP_CONTRACTING,
        "STABLE": ReasonCode.GAP_STABLE,
    }.get(momentum)
    if momentum_code:
        codes.append(momentum_code)
    if degraded:
        codes.append(ReasonCode.STALE_SOURCE)

    above = gap > 0
    if above and implied_direction == "FALLING" and momentum == "EXPANDING":
        summary = "دلار بالاتر از نرخ ضمنی طلاست، نرخ ضمنی نزولی و فاصله در حال افزایش است."
    elif above and implied_direction == "RISING" and momentum == "CONTRACTING":
        summary = "دلار بالاتر از نرخ ضمنی است، اما نرخ ضمنی صعودی و فاصله در حال کاهش است."
    elif not above and implied_direction == "RISING":
        summary = "دلار پایین‌تر از نرخ ضمنی طلاست و نرخ ضمنی صعودی است."
    elif abs(gap) <= bands.neutral:
        summary = "دلار و نرخ ضمنی طلا تقریباً هم‌تراز هستند."
    elif above:
        summary = "دلار بالاتر از نرخ ضمنی طلاست."
    else:
        summary = "دلار پایین‌تر از نرخ ضمنی طلاست."

    return Signal(
        instrument=Instrument.USD_IRR_FREE,
        classification=classify(gap, bands),
        severity=severity(gap, bands),
        confidence=_confidence(implied_direction != "UNKNOWN", degraded),
        summary_fa=summary,
        reason_codes=codes,
        metrics_used={"usd_gap_pct": round(gap, 4)},
        generated_at=generated_at,
        model_version=SIGNAL_MODEL_VERSION,
    )


def gold_signal(
    gap: float,
    xau_direction: str,
    usd_direction: str,
    bands: Bands,
    generated_at: datetime,
    degraded: bool = False,
) -> Signal:
    """Domestic 18K against its theoretical value (§5.4 case D)."""
    codes: list[ReasonCode] = []
    if xau_direction == "RISING":
        codes.append(ReasonCode.XAU_RISING)
    elif xau_direction == "FALLING":
        codes.append(ReasonCode.XAU_FALLING)
    else:
        codes.append(ReasonCode.INSUFFICIENT_HISTORY)

    lagging = gap < -bands.neutral
    if lagging:
        codes.append(ReasonCode.DOMESTIC_GOLD_LAGGING)
    elif gap > bands.neutral:
        codes.append(ReasonCode.DOMESTIC_GOLD_LEADING)
    if degraded:
        codes.append(ReasonCode.STALE_SOURCE)

    if lagging and xau_direction == "RISING" and usd_direction == "RISING":
        summary = "اونس و دلار صعودی‌اند و طلای داخلی از ارزش نظری عقب مانده است."
    elif lagging:
        summary = "طلای داخلی پایین‌تر از ارزش نظری این مدل است."
    elif gap > bands.neutral:
        summary = "طلای داخلی بالاتر از ارزش نظری این مدل است."
    else:
        summary = "طلای داخلی نزدیک به ارزش نظری این مدل است."

    return Signal(
        instrument=Instrument.GOLD_18K,
        classification=classify(gap, bands),
        severity=severity(gap, bands),
        confidence=_confidence(xau_direction != "UNKNOWN", degraded),
        summary_fa=summary,
        reason_codes=codes,
        metrics_used={"gold_gap_pct": round(gap, 4)},
        generated_at=generated_at,
        model_version=SIGNAL_MODEL_VERSION,
    )


def coin_signal(
    premium_pct: float, bands: Bands, generated_at: datetime, degraded: bool = False
) -> Signal:
    """Coin against its melt value. The premium is normally positive."""
    summary = (
        f"حباب سکه نسبت به ارزش ذاتی حدود {premium_pct:.1f} درصد است."
        if premium_pct >= 0
        else f"سکه حدود {abs(premium_pct):.1f} درصد زیر ارزش ذاتی معامله می‌شود."
    )
    return Signal(
        instrument=Instrument.EMAMI_COIN,
        classification=classify(premium_pct, bands),
        severity=severity(premium_pct, bands),
        confidence=_confidence(False, degraded),
        summary_fa=summary,
        reason_codes=[ReasonCode.STALE_SOURCE] if degraded else [],
        metrics_used={"coin_premium_pct": round(premium_pct, 4)},
        generated_at=generated_at,
        model_version=SIGNAL_MODEL_VERSION,
    )


def insufficient_data_signal(instrument: Instrument, generated_at: datetime) -> Signal:
    return Signal(
        instrument=instrument,
        classification=Classification.INSUFFICIENT_DATA,
        severity=0,
        confidence=0.0,
        summary_fa="داده کافی برای ارزیابی موجود نیست.",
        reason_codes=[ReasonCode.INSUFFICIENT_HISTORY],
        metrics_used={},
        generated_at=generated_at,
        model_version=SIGNAL_MODEL_VERSION,
    )
