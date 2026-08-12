"""Persian rendering. Formatting only — nothing is calculated here.

Every number this module prints was computed in analysis/ and is read, not derived.
"""

from __future__ import annotations

from html import escape

from ..analysis import engine
from ..analysis.engine import Analysis
from ..domain.constants import ATTRIBUTION
from ..domain.enums import Classification, Instrument
from ..timeutil import to_tehran
from .jalali import format_date_fa

DISCLAIMER = "این گزارش یک شاخص تحلیلی مبتنی بر روابط قیمت است و توصیه خرید یا فروش نیست."

CLASSIFICATION_FA: dict[Classification, str] = {
    Classification.UNDERVALUED: "پایین‌تر از ارزش نظری این مدل",
    Classification.SLIGHTLY_UNDERVALUED: "کمی پایین‌تر از ارزش نظری این مدل",
    Classification.NEUTRAL: "نزدیک به ارزش نظری این مدل",
    Classification.SLIGHTLY_EXPENSIVE: "نسبتاً گران نسبت به این مدل",
    Classification.EXPENSIVE: "گران نسبت به این مدل",
    Classification.STRETCHED: "فاصله زیاد از ارزش نظری این مدل",
    Classification.INSUFFICIENT_DATA: "داده کافی نیست",
    Classification.DATA_QUALITY_WARNING: "هشدار کیفیت داده",
}

_ARROWS = {"RISING": "↑", "FALLING": "↓", "STABLE": "→", "UNKNOWN": ""}


def toman(value: float) -> str:
    return f"{round(value):,}"


def usd(value: float) -> str:
    return f"{value:,.2f}"


def signed_pct(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:+.2f}%"


def trend_line(trends: dict[str, float | None]) -> str:
    parts = [f"{h.upper()} {signed_pct(trends.get(h))}" for h in ("1d", "3d", "7d")]
    return " | ".join(parts)


def _arrow(trends: dict[str, float | None], tolerance: float = 0.05) -> str:
    change = trends.get("1d")
    if change is None:
        return ""
    if change > tolerance:
        return _ARROWS["RISING"]
    if change < -tolerance:
        return _ARROWS["FALLING"]
    return _ARROWS["STABLE"]


def render(analysis: Analysis, channel_note: str = "") -> str:
    """Render the scheduled summary (ARCHITECTURE.md §15).

    `channel_note` adds an operator line above the attribution; it cannot
    replace the attribution.
    """
    local = to_tehran(analysis.as_of)
    metrics = analysis.metrics
    signals = {s.instrument: s for s in analysis.signals}
    lines: list[str] = [
        "📊 گزارش بازار",
        f"{format_date_fa(local)} | {local:%H:%M}",
        "",
        "💵 دلار آزاد",
        f"بازار: {toman(metrics[engine.USD_MARKET])} تومان",
        f"ضمنی طلا: {toman(metrics[engine.USD_IMPLIED])} تومان",
        f"فاصله: {signed_pct(metrics[engine.USD_GAP])}",
        "",
        "روند ضمنی:",
        trend_line(analysis.trends[engine.USD_IMPLIED]),
    ]

    usd_signal = signals.get(Instrument.USD_IRR_FREE)
    if usd_signal:
        lines += [
            "",
            "ارزیابی:",
            escape(usd_signal.summary_fa),
            "",
            f"وضعیت: {CLASSIFICATION_FA[usd_signal.classification]}",
        ]

    gold_signal = signals.get(Instrument.GOLD_18K)
    lines += [
        "",
        "🥇 طلای ۱۸ عیار",
        f"بازار: {toman(metrics[engine.GOLD_MARKET])} تومان",
        f"نظری: {toman(metrics[engine.GOLD_THEORETICAL])} تومان",
        f"فاصله: {signed_pct(metrics[engine.GOLD_GAP])}",
        "",
        f"اونس: {usd(metrics[engine.XAU])} USD {_arrow(analysis.trends[engine.XAU])}".strip(),
        f"دلار: {toman(metrics[engine.USD_MARKET])} "
        f"{_arrow(analysis.trends[engine.USD_MARKET])}".strip(),
    ]
    if gold_signal:
        lines += ["", f"وضعیت: {CLASSIFICATION_FA[gold_signal.classification]}"]

    if engine.COIN_MARKET in metrics:
        coin_signal = signals.get(Instrument.EMAMI_COIN)
        lines += [
            "",
            "🪙 سکه امامی",
            f"قیمت: {toman(metrics[engine.COIN_MARKET])} تومان",
            f"ارزش ذاتی: {toman(metrics[engine.COIN_INTRINSIC])} تومان",
            f"حباب: {signed_pct(metrics[engine.COIN_PREMIUM])}",
        ]
        if coin_signal:
            lines += [f"وضعیت: {CLASSIFICATION_FA[coin_signal.classification]}"]

    if analysis.warnings:
        lines += ["", "⚠️ هشدار داده:"] + [escape(w) for w in analysis.warnings]

    oldest = min((q.observed_at for q in analysis.snapshot.quotes.values()), default=analysis.as_of)
    lines += [
        "",
        f"آخرین داده: {to_tehran(oldest):%H:%M}",
        f"مدل: v{analysis.model_version}",
        "",
        DISCLAIMER,
    ]
    if channel_note:
        lines.append(escape(channel_note))
    lines.append(ATTRIBUTION)
    return "\n".join(lines)
