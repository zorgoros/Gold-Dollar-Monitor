"""Serializable analytical output — the contract a future API or widget consumes.

Shape follows ARCHITECTURE.md §20 so the web surface never has to parse Telegram
text. Telegram is one consumer of this, not the source of it (§43): a dashboard
showing the three-way USD view reads `references` below and needs no knowledge
of Persian formatting, emoji, or slot scheduling.
"""

from __future__ import annotations

from typing import Any

from ..analysis import engine
from ..analysis.engine import Analysis
from ..domain.enums import Instrument
from ..timeutil import to_iso

# key: (instrument, market metric). References and gaps are attached separately
# because the USD card carries two of them and every other card carries none.
_CARDS: dict[str, tuple[Instrument, str]] = {
    "USD_IRT": (Instrument.USD_IRR_FREE, engine.USD_MARKET),
    "GOLD_18K": (Instrument.GOLD_18K, engine.GOLD_MARKET),
    "XAU_USD": (Instrument.XAU_USD, engine.XAU),
    "EMAMI_COIN": (Instrument.EMAMI_COIN, engine.COIN_MARKET),
    "AED_IRT": (Instrument.AED_IRT, Instrument.AED_IRT.value),
    "EUR_IRT": (Instrument.EUR_IRT, Instrument.EUR_IRT.value),
    "TRY_IRT": (Instrument.TRY_IRT, Instrument.TRY_IRT.value),
    "JPY_IRT": (Instrument.JPY_IRT, Instrument.JPY_IRT.value),
}

# The references each card is compared against, in the order a UI should show
# them. Two entries on USD is the whole point of v1.1 — and they stay two
# entries, never averaged into one (§11).
_REFERENCES: dict[str, list[tuple[str, str, str]]] = {
    "USD_IRT": [
        ("gold", engine.USD_IMPLIED, engine.USD_GAP),
        ("aed", engine.USD_AED_IMPLIED, engine.AED_GAP),
    ],
    "GOLD_18K": [("theoretical", engine.GOLD_THEORETICAL, engine.GOLD_GAP)],
    "EMAMI_COIN": [("metal_content", engine.COIN_INTRINSIC, engine.COIN_PREMIUM)],
}


def widget_payload(analysis: Analysis) -> list[dict[str, Any]]:
    signals = {s.instrument: s for s in analysis.signals}
    payload: list[dict[str, Any]] = []
    for key, (instrument, market_key) in _CARDS.items():
        if market_key not in analysis.metrics:
            continue
        quote = analysis.snapshot.quotes.get(instrument)
        signal = signals.get(instrument)
        references = [
            {
                "name": name,
                "implied_value": analysis.metrics[implied_key],
                "gap_pct": analysis.metrics.get(gap_key),
            }
            for name, implied_key, gap_key in _REFERENCES.get(key, [])
            if implied_key in analysis.metrics
        ]
        payload.append(
            {
                "instrument": key,
                "market_value": analysis.metrics[market_key],
                # Retained for v1.0 consumers: the primary reference, flattened.
                "implied_value": references[0]["implied_value"] if references else None,
                "gap_pct": references[0]["gap_pct"] if references else None,
                "references": references,
                "trends": analysis.trends.get(market_key, {}),
                "change_since_previous_pct": analysis.changes.get(market_key),
                "signal": (
                    {
                        "classification": signal.classification.value,
                        "severity": signal.severity,
                        "confidence": signal.confidence,
                        "reason_codes": [c.value for c in signal.reason_codes],
                        "summary_fa": signal.summary_fa,
                    }
                    if signal
                    else None
                ),
                "data_quality": quote.quality_status.value if quote else "MISSING",
                "as_of": to_iso(quote.observed_at) if quote else to_iso(analysis.as_of),
                "basis": analysis.basis.value,
                "model_version": analysis.model_version,
            }
        )
    return payload
