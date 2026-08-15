"""Approved bilingual sentences for the public dashboard analysis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict


class LocalizedNarrativeText(TypedDict):
    fa: str
    en: str


class NarrativePayload(TypedDict):
    id: str
    text: LocalizedNarrativeText


@dataclass(frozen=True)
class NarrativeTemplate:
    """One stable analytical statement in every supported language."""

    id: str
    fa: str
    en: str

    def payload(self) -> NarrativePayload:
        return {"id": self.id, "text": {"fa": self.fa, "en": self.en}}


CATALOG: dict[str, NarrativeTemplate] = {
    "data.warning": NarrativeTemplate(
        "data.warning",
        "این تحلیل از ورودی دارای هشدار کیفیت استفاده می‌کند و باید با احتیاط خوانده شود.",
        "This analysis uses an input with a data-quality warning and should be read with caution.",
    ),
    "usd.references.disagree": NarrativeTemplate(
        "usd.references.disagree",
        "مسیرهای طلا و درهم تصویر یکسانی از نرخ دلار نشان نمی‌دهند.",
        "The gold and dirham paths do not show the same picture for the dollar rate.",
    ),
    "usd.references.agree": NarrativeTemplate(
        "usd.references.agree",
        "مسیرهای طلا و درهم فاصله مشابهی با نرخ دلار بازار نشان می‌دهند.",
        "The gold and dirham paths show a similar gap from the market dollar rate.",
    ),
    "usd.references.gold_only": NarrativeTemplate(
        "usd.references.gold_only",
        "در این نوبت فقط مسیر طلا برای مقایسه با دلار بازار در دسترس است.",
        "Only the gold path is available for comparison with the market dollar "
        "in this observation.",
    ),
    "usd.market.above_reference": NarrativeTemplate(
        "usd.market.above_reference",
        "دلار بازار بالاتر از مرجع طبقه‌بندی شده است؛ این فاصله توصیفی است، نه توصیه معامله.",
        "The market dollar is classified above its reference; this describes "
        "a gap and is not trading advice.",
    ),
    "usd.market.below_reference": NarrativeTemplate(
        "usd.market.below_reference",
        "دلار بازار پایین‌تر از مرجع طبقه‌بندی شده است؛ این فاصله توصیفی است، نه توصیه معامله.",
        "The market dollar is classified below its reference; this describes "
        "a gap and is not trading advice.",
    ),
    "usd.market.near_reference": NarrativeTemplate(
        "usd.market.near_reference",
        "دلار بازار نزدیک به محدوده مرجع طبقه‌بندی شده است.",
        "The market dollar is classified near its reference range.",
    ),
    "gold.below_theoretical": NarrativeTemplate(
        "gold.below_theoretical",
        "طلای داخلی پایین‌تر از ارزش نظری مدل است و هنوز ورودی‌های دلار و اونس را کامل منعکس نمی‌کند.",
        "Domestic gold is below the model value and does not yet fully reflect "
        "the dollar and ounce inputs.",
    ),
    "gold.above_theoretical": NarrativeTemplate(
        "gold.above_theoretical",
        "طلای داخلی بالاتر از ارزش نظری مدل است و نسبت به ورودی‌های دلار و اونس فاصله مثبت دارد.",
        "Domestic gold is above the model value and has a positive gap from "
        "the dollar and ounce inputs.",
    ),
    "gold.near_theoretical": NarrativeTemplate(
        "gold.near_theoretical",
        "طلای داخلی نزدیک به ارزش نظری محاسبه‌شده از دلار و اونس است.",
        "Domestic gold is near the theoretical value calculated from the dollar and ounce inputs.",
    ),
    "coin.positive_premium": NarrativeTemplate(
        "coin.positive_premium",
        "قیمت سکه بالاتر از ارزش طلای داخل آن است؛ بخش مثبت فاصله، حباب داخلی را نشان می‌دهد.",
        "The coin price is above its domestic metal value; the positive gap is "
        "the domestic premium.",
    ),
    "coin.negative_premium": NarrativeTemplate(
        "coin.negative_premium",
        "قیمت سکه پایین‌تر از ارزش طلای داخل آن است و فاصله داخلی منفی است.",
        "The coin price is below its domestic metal value and the domestic premium is negative.",
    ),
    "coin.near_metal_value": NarrativeTemplate(
        "coin.near_metal_value",
        "قیمت سکه نزدیک به ارزش طلای داخل آن طبقه‌بندی شده است.",
        "The coin price is classified near its domestic metal value.",
    ),
}
