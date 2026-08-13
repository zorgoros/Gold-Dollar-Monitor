"""Rule-based classification. Deterministic, explainable, and deliberately timid.

Confidence stays low by construction: the bands in config are provisional
placeholders, not calibrated thresholds, so a signal here is a description of
where prices sit relative to each other — never a forecast (ARCHITECTURE.md §7, §40).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..domain.constants import SIGNAL_MODEL_VERSION
from ..domain.enums import AnalysisBasis, Classification, Instrument, ReasonCode
from ..domain.models import Signal

MAX_CONFIDENCE = 0.6

# Two references pointing the same way is worth saying; it is still not proof.
# The gold and AED gaps are independent measurements, unlike implied USD and
# theoretical gold, so agreement between them is information (§9) — but it does
# not raise confidence past the cap, because neither is calibrated yet.
AGREEMENT_BAND_PCT = 1.0


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
    aed_gap: float | None = None,
    basis: AnalysisBasis = AnalysisBasis.LIVE,
) -> Signal:
    """USD against the rates implied by the gold and dirham markets (§5.4, §9).

    One signal, not two. The dirham adds reason codes and metrics to the USD
    verdict rather than a second Signal object, because two Signals for one
    instrument would read as two independent judgements of the same fact.
    """
    codes: list[ReasonCode] = [
        ReasonCode.USD_ABOVE_GOLD_IMPLIED if gap > 0 else ReasonCode.USD_BELOW_GOLD_IMPLIED
    ]
    if aed_gap is None:
        codes.append(ReasonCode.AED_REFERENCE_UNAVAILABLE)
    else:
        codes.append(
            ReasonCode.USD_ABOVE_AED_IMPLIED if aed_gap > 0 else ReasonCode.USD_BELOW_AED_IMPLIED
        )
        codes.append(
            ReasonCode.GOLD_AND_AED_AGREE
            if abs(gap - aed_gap) <= AGREEMENT_BAND_PCT
            else ReasonCode.GOLD_AND_AED_DISAGREE
        )
    if basis is AnalysisBasis.LAST_CLOSE:
        codes.append(ReasonCode.BASIS_LAST_CLOSE)
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

    summary = _usd_summary(gap, aed_gap, implied_direction, momentum, bands)

    used = {"usd_gap_pct": round(gap, 4)}
    if aed_gap is not None:
        used["aed_usd_gap_pct"] = round(aed_gap, 4)

    return Signal(
        instrument=Instrument.USD_IRR_FREE,
        classification=classify(gap, bands),
        severity=severity(gap, bands),
        confidence=_confidence(implied_direction != "UNKNOWN", degraded),
        summary_fa=summary,
        reason_codes=codes,
        metrics_used=used,
        generated_at=generated_at,
        model_version=SIGNAL_MODEL_VERSION,
    )


def _usd_summary(
    gap: float, aed_gap: float | None, implied_direction: str, momentum: str, bands: Bands
) -> str:
    """One or two sentences, stated as distances rather than verdicts (§21, §40).

    Never "the dollar is expensive" — the model measures how far apart two
    prices sit, which is not the same claim.
    """
    if aed_gap is not None:
        if abs(gap - aed_gap) <= AGREEMENT_BAND_PCT:
            return (
                "بازار طلا و بازار درهم فاصله مشابهی با نرخ دلار نشان می‌دهند "
                f"({gap:+.2f}٪ و {aed_gap:+.2f}٪)."
            )
        if abs(aed_gap) <= bands.neutral:
            return (
                "بازار درهم نرخ دلار را تقریباً تأیید می‌کند، "
                f"اما فاصله دلار با نرخ ضمنی طلا {gap:+.2f}٪ است."
            )
        return (
            f"فاصله دلار با نرخ ضمنی طلا {gap:+.2f}٪ و با نرخ ضمنی درهم {aed_gap:+.2f}٪ است؛ "
            "دو بازار تصویر یکسانی نمی‌دهند."
        )

    above = gap > 0
    if above and implied_direction == "FALLING" and momentum == "EXPANDING":
        return "دلار بالاتر از نرخ ضمنی طلاست، نرخ ضمنی نزولی و فاصله در حال افزایش است."
    if above and implied_direction == "RISING" and momentum == "CONTRACTING":
        return "دلار بالاتر از نرخ ضمنی است، اما نرخ ضمنی صعودی و فاصله در حال کاهش است."
    if not above and implied_direction == "RISING":
        return "دلار پایین‌تر از نرخ ضمنی طلاست و نرخ ضمنی صعودی است."
    if abs(gap) <= bands.neutral:
        return "دلار و نرخ ضمنی طلا تقریباً هم‌تراز هستند."
    return f"فاصله دلار با نرخ ضمنی طلا {gap:+.2f}٪ است."


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
    """Coin against the value of the gold it contains, priced domestically.

    "ارزش طلای سکه", never "ارزش ذاتی" (§22) — this is metal content, which is a
    narrower and more defensible claim than intrinsic worth.

    The denominator is the Tehran pure-gold price, so a negative reading now
    means the coin genuinely trades under its metal — worth saying, and rare.
    Under the v1.1 world route it merely meant the gold gap was wide.
    """
    summary = (
        f"حباب سکه نسبت به ارزش طلای آن حدود {premium_pct:.1f} درصد است."
        if premium_pct >= 0
        else f"سکه حدود {abs(premium_pct):.1f} درصد زیر ارزش طلای خود معامله می‌شود."
    )
    return Signal(
        instrument=Instrument.EMAMI_COIN,
        classification=classify(premium_pct, bands),
        severity=severity(premium_pct, bands),
        confidence=_confidence(False, degraded),
        summary_fa=summary,
        reason_codes=[ReasonCode.STALE_SOURCE] if degraded else [],
        metrics_used={"coin_premium_domestic_pct": round(premium_pct, 4)},
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
