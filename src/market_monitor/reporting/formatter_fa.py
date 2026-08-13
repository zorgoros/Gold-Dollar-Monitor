"""Persian rendering. Formatting only — nothing is calculated here.

Every number this module prints was computed in analysis/ and is read, not
derived. The one arithmetic it performs is the per-100-yen presentation, and
even that is a named conversion imported from normalization rather than a
literal written into a template (§6).

Two public surfaces (§3):

* `render_snapshot` — the price board. Tolerant: it shows what is there and says
  how old it is.
* `render_analysis` — the cross-market read. Strict: it is only ever called for
  inputs that already passed the gate, so it never has to hedge in prose.

Nothing here decides whether to publish, and nothing here prints an engineer's
diagnostic. Warning strings from the validators are for logs (§17, §38).
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Any

from ..analysis import engine
from ..analysis.engine import Analysis
from ..domain.constants import ATTRIBUTION
from ..domain.enums import AnalysisBasis, GateCode, Instrument
from ..normalization.units import per_one_to_per_hundred
from ..timeutil import to_tehran
from .jalali import format_date_fa

DISCLAIMER = "این گزارش یک شاخص تحلیلی مبتنی بر روابط قیمت است و توصیه خرید یا فروش نیست."

# The public status vocabulary. Deliberately three lines for every internal
# failure mode there is: a reader needs to know whether to trust the numbers,
# not which subsystem was unhappy (§17, §38).
STATUS_FRESH = "🟢 داده‌ها به‌روز"
STATUS_LAST_CLOSE = "🕐 بر مبنای آخرین پایان معاملات"
ANALYSIS_UNAVAILABLE = "⚠️ تحلیل این نوبت منتشر نشد؛ برخی داده‌های اصلی بازار به‌روز نیستند."
SNAPSHOT_UNAVAILABLE = "⚠️ داده‌های بازار در دسترس نیست."


@dataclass(frozen=True)
class Row:
    """One line of the price board."""

    label: str
    flag: str
    metric: str
    per_hundred: bool = False
    dollars: bool = False


ROWS: dict[Instrument, Row] = {
    Instrument.USD_IRR_FREE: Row("دلار", "🇺🇸", engine.USD_MARKET),
    Instrument.EUR_IRT: Row("یورو", "🇪🇺", Instrument.EUR_IRT.value),
    Instrument.AED_IRT: Row("درهم", "🇦🇪", Instrument.AED_IRT.value),
    Instrument.TRY_IRT: Row("لیر", "🇹🇷", Instrument.TRY_IRT.value),
    # Stored per one yen, shown per hundred, and the label says which so a
    # non-financial reader cannot mistake the scale (§6).
    Instrument.JPY_IRT: Row("۱۰۰ ین", "🇯🇵", Instrument.JPY_IRT.value, per_hundred=True),
    Instrument.GOLD_18K: Row("طلای ۱۸ عیار", "", engine.GOLD_MARKET),
    Instrument.XAU_USD: Row("اونس جهانی", "", engine.XAU, dollars=True),
    Instrument.EMAMI_COIN: Row("سکه امامی", "", engine.COIN_MARKET),
}

SHORT_LABEL: dict[str, str] = {
    engine.USD_MARKET: "دلار",
    engine.GOLD_MARKET: "طلا",
    engine.COIN_MARKET: "سکه",
}


@dataclass(frozen=True)
class ReportConfig:
    """Everything the operator may change about a report's shape (§35)."""

    fx: list[Instrument]
    metals: list[Instrument]
    brand_name: str = ""
    bot_username: str = ""
    channel_username: str = ""
    channel_note: str = ""
    show_change: bool = True

    @classmethod
    def from_settings(cls, settings: Any) -> ReportConfig:
        reporting = settings.section("reporting")
        footer = reporting.get("footer", {})
        display = settings.section("display")
        return cls(
            fx=settings.instrument_list("display", "fx"),
            metals=settings.instrument_list("display", "metals"),
            brand_name=str(footer.get("brand_name", "")).strip(),
            bot_username=str(footer.get("bot_username", "")).strip(),
            channel_username=str(footer.get("channel_username", "")).strip(),
            channel_note=str(reporting.get("channel_note", "")).strip(),
            show_change=bool(display.get("show_change_since_previous", True)),
        )


# ------------------------------------------------------------------ primitives


def toman(value: float) -> str:
    return f"{round(value):,}"


def usd(value: float) -> str:
    return f"{value:,.2f}"


def signed_pct(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:+.2f}%"


def trend_line(trends: dict[str, float | None]) -> str:
    """1D/3D/7D, omitting horizons with no history rather than printing dashes."""
    parts = [
        f"{h.upper()} {signed_pct(trends[h])}"
        for h in ("1d", "3d", "7d")
        if trends.get(h) is not None
    ]
    return " | ".join(parts)


def has_trend(trends: dict[str, float | None]) -> bool:
    return any(trends.get(h) is not None for h in ("1d", "3d", "7d"))


def _value(analysis: Analysis, row: Row) -> str | None:
    raw = analysis.metrics.get(row.metric)
    if raw is None:
        return None
    if row.dollars:
        return f"${usd(raw)}"
    return toman(per_one_to_per_hundred(raw) if row.per_hundred else raw)


def footer(config: ReportConfig) -> list[str]:
    """Identity block (§24). Compact, and every line is optional but the last.

    The attribution is not configurable and is never omitted — see NOTICE. The
    brand and handles above it are the operator's and default to empty rather
    than to an invented username.
    """
    lines: list[str] = []
    if config.brand_name:
        lines.append(escape(config.brand_name))
    handles = " · ".join(h for h in (config.bot_username, config.channel_username) if h)
    if handles:
        lines.append(escape(handles))
    if config.channel_note:
        lines.append(escape(config.channel_note))
    lines.append(ATTRIBUTION)
    return lines


def _header(analysis: Analysis, title: str) -> list[str]:
    local = to_tehran(analysis.as_of)
    return [f"{title} | {format_date_fa(local)} • {local:%H:%M}", ""]


def _status(analysis: Analysis) -> str:
    if analysis.basis is AnalysisBasis.LAST_CLOSE:
        return STATUS_LAST_CLOSE
    local = to_tehran(analysis.reference_at or analysis.as_of)
    return f"{STATUS_FRESH} | {local:%H:%M}"


# --------------------------------------------------------------------- surfaces


def render_snapshot(analysis: Analysis, config: ReportConfig) -> str:
    """The public price board (§18).

    Sections appear only when they have content, and an instrument that was not
    collected is simply absent — never a row with a dash in it (§20).
    """
    lines = _header(analysis, "📊 عیار مارکت")

    fx = [(i, _value(analysis, ROWS[i])) for i in config.fx if i in ROWS]
    fx_present = [(i, v) for i, v in fx if v is not None]
    if fx_present:
        lines.append("💱 ارز")
        for instrument, value in fx_present:
            row = ROWS[instrument]
            lines.append(f"{row.flag} {row.label}: {value} تومان".strip())
        lines.append("")

    metals = [(i, _value(analysis, ROWS[i])) for i in config.metals if i in ROWS]
    metals_present = [(i, v) for i, v in metals if v is not None]
    if metals_present:
        lines.append("🥇 طلا و سکه")
        for instrument, value in metals_present:
            row = ROWS[instrument]
            suffix = "" if row.dollars else " تومان"
            lines.append(f"{row.label}: {value}{suffix}")
        lines.append("")

    if config.show_change:
        moves = [
            f"{SHORT_LABEL[metric]} {signed_pct(analysis.changes[metric])}"
            for metric in (engine.USD_MARKET, engine.GOLD_MARKET, engine.COIN_MARKET)
            if analysis.changes.get(metric) is not None
        ]
        if moves:
            lines += ["↕ تغییر از گزارش قبل", " | ".join(moves), ""]

    lines.append(_status(analysis))
    lines.append("")
    lines += footer(config)
    return "\n".join(lines)


def render_analysis(analysis: Analysis, config: ReportConfig) -> str:
    """The cross-market read (§19). Compact by design — never an essay."""
    metrics = analysis.metrics
    signals = {s.instrument: s for s in analysis.signals}
    lines = _header(analysis, "⚖️ تحلیل عیار")

    lines.append("💵 دلار")
    lines.append(f"بازار: {toman(metrics[engine.USD_MARKET])}")
    lines.append(f"ضمنی طلا: {toman(metrics[engine.USD_IMPLIED])}")
    if engine.USD_AED_IMPLIED in metrics:
        lines.append(f"ضمنی درهم: {toman(metrics[engine.USD_AED_IMPLIED])}")
    lines.append("")
    lines.append(f"فاصله با طلا: {signed_pct(metrics[engine.USD_GAP])}")
    if engine.AED_GAP in metrics:
        lines.append(f"فاصله با درهم: {signed_pct(metrics[engine.AED_GAP])}")

    usd_signal = signals.get(Instrument.USD_IRR_FREE)
    if usd_signal:
        lines += ["", "برداشت:", escape(usd_signal.summary_fa)]

    lines += [
        "",
        "🥇 طلای ۱۸ عیار",
        f"بازار: {toman(metrics[engine.GOLD_MARKET])}",
        f"ارزش نظری: {toman(metrics[engine.GOLD_THEORETICAL])}",
        f"فاصله: {signed_pct(metrics[engine.GOLD_GAP])}",
    ]

    if engine.COIN_MARKET in metrics:
        lines += [
            "",
            "🪙 سکه امامی",
            f"بازار: {toman(metrics[engine.COIN_MARKET])}",
            f"ارزش طلای سکه: {toman(metrics[engine.COIN_INTRINSIC_DOMESTIC])}",
            f"حباب: {signed_pct(metrics[engine.COIN_PREMIUM_DOMESTIC])}",
        ]

    implied_trends = analysis.trends.get(engine.USD_IMPLIED, {})
    if has_trend(implied_trends):
        lines += ["", "📈 روند نرخ ضمنی دلار", trend_line(implied_trends)]

    lines += [
        "",
        _status(analysis),
        f"مدل: v{analysis.model_version}",
        "",
        DISCLAIMER,
        "",
    ]
    lines += footer(config)
    return "\n".join(lines)


def render_unavailable(codes: list[GateCode], config: ReportConfig, analysis_report: bool) -> str:
    """The public message when a report is withheld.

    It says that the data is not current and stops. Which input, how stale, and
    how far the quotes spanned are engineering facts and stay in `job_runs` and
    the logs (§17).
    """
    del codes  # the public wording is deliberately the same for every cause
    lines = [ANALYSIS_UNAVAILABLE if analysis_report else SNAPSHOT_UNAVAILABLE, ""]
    lines += footer(config)
    return "\n".join(lines)
