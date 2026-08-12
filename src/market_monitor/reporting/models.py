"""Serializable analytical output — the contract a future API or widget consumes.

Shape follows ARCHITECTURE.md §20 so the web surface never has to parse Telegram text.
"""

from __future__ import annotations

from typing import Any

from ..analysis import engine
from ..analysis.engine import Analysis
from ..domain.enums import Instrument
from ..timeutil import to_iso

_WIDGETS: dict[str, tuple[Instrument, str, str | None, str]] = {
    # key: (instrument, market metric, implied/reference metric, gap metric)
    "USD_IRT": (Instrument.USD_IRR_FREE, engine.USD_MARKET, engine.USD_IMPLIED, engine.USD_GAP),
    "GOLD_18K": (Instrument.GOLD_18K, engine.GOLD_MARKET, engine.GOLD_THEORETICAL, engine.GOLD_GAP),
    "XAU_USD": (Instrument.XAU_USD, engine.XAU, None, ""),
    "EMAMI_COIN": (
        Instrument.EMAMI_COIN,
        engine.COIN_MARKET,
        engine.COIN_INTRINSIC,
        engine.COIN_PREMIUM,
    ),
}


def widget_payload(analysis: Analysis) -> list[dict[str, Any]]:
    signals = {s.instrument: s for s in analysis.signals}
    payload: list[dict[str, Any]] = []
    for key, (instrument, market_key, reference_key, gap_key) in _WIDGETS.items():
        if market_key not in analysis.metrics:
            continue
        quote = analysis.snapshot.quotes.get(instrument)
        signal = signals.get(instrument)
        payload.append(
            {
                "instrument": key,
                "market_value": analysis.metrics[market_key],
                "implied_value": analysis.metrics.get(reference_key) if reference_key else None,
                "gap_pct": analysis.metrics.get(gap_key) if gap_key else None,
                "trends": analysis.trends.get(market_key, {}),
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
                "model_version": analysis.model_version,
            }
        )
    return payload
