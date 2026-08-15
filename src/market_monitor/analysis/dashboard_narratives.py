"""Select dashboard prose from analysis decisions that already exist."""

from __future__ import annotations

from collections.abc import Sequence

from ..domain.enums import Classification, Instrument, ReasonCode
from ..domain.models import Signal
from .narrative_catalog import CATALOG, NarrativePayload

ABOVE = frozenset(
    {
        Classification.SLIGHTLY_EXPENSIVE,
        Classification.EXPENSIVE,
        Classification.STRETCHED,
    }
)
BELOW = frozenset(
    {
        Classification.SLIGHTLY_UNDERVALUED,
        Classification.UNDERVALUED,
    }
)


def _payload(key: str) -> NarrativePayload:
    return CATALOG[key].payload()


def _relation(classification: Classification, above: str, below: str, near: str) -> str:
    if classification in ABOVE:
        return above
    if classification in BELOW:
        return below
    return near


def select_dashboard_narratives(
    signals: Sequence[Signal],
) -> dict[str, list[NarrativePayload]]:
    """Map existing signal outcomes to approved text; calculate nothing."""
    result: dict[str, list[NarrativePayload]] = {
        "overview": [],
        "gold": [],
        "coin": [],
    }
    by_instrument = {signal.instrument: signal for signal in signals}

    usd = by_instrument.get(Instrument.USD_IRR_FREE)
    if usd is not None:
        if ReasonCode.STALE_SOURCE in usd.reason_codes:
            result["overview"].append(_payload("data.warning"))
        if ReasonCode.GOLD_AND_AED_DISAGREE in usd.reason_codes:
            result["overview"].append(_payload("usd.references.disagree"))
        elif ReasonCode.GOLD_AND_AED_AGREE in usd.reason_codes:
            result["overview"].append(_payload("usd.references.agree"))
        else:
            result["overview"].append(_payload("usd.references.gold_only"))
        relation = _relation(
            usd.classification,
            "above_reference",
            "below_reference",
            "near_reference",
        )
        result["overview"].append(_payload(f"usd.market.{relation}"))

    gold = by_instrument.get(Instrument.GOLD_18K)
    if gold is not None:
        relation = _relation(
            gold.classification,
            "above_theoretical",
            "below_theoretical",
            "near_theoretical",
        )
        result["gold"].append(_payload(f"gold.{relation}"))

    coin = by_instrument.get(Instrument.EMAMI_COIN)
    if coin is not None:
        relation = _relation(
            coin.classification,
            "positive_premium",
            "negative_premium",
            "near_metal_value",
        )
        result["coin"].append(_payload(f"coin.{relation}"))

    return result
