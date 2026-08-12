"""Quality gates. A number that fails here never reaches a report as if it were fresh."""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta

from ..analysis.formulas import gold_implied_usd
from ..domain.enums import GateCode, Instrument, QualityStatus, SnapshotStatus
from ..domain.errors import InvalidQuote
from ..domain.models import Quote

# A domestic gold market this far from parity with the world ounce means a unit
# error (typically rial read as toman, a factor of 10), not a market move.
PARITY_SANITY_RATIO = 3.0


def validate_quote(
    quote: Quote,
    now: datetime,
    max_age: timedelta,
    last_value: float | None = None,
    max_jump_pct: float = 25.0,
) -> Quote:
    """Return the quote with a quality flag set. Raises only on unusable data."""
    value = quote.normalized_value
    if not math.isfinite(value) or value <= 0:
        raise InvalidQuote(f"{quote.instrument}: non-positive or non-finite value {value!r}")
    if quote.observed_at > now + timedelta(minutes=5):
        raise InvalidQuote(f"{quote.instrument}: source timestamp is in the future")

    status = quote.quality_status
    if quote.age_seconds(now) > max_age.total_seconds():
        status = QualityStatus.STALE
    if last_value and last_value > 0:
        jump = abs(value / last_value - 1.0) * 100.0
        if jump > max_jump_pct:
            # Most likely a parser reading a changed layout, not a real move.
            status = QualityStatus.SUSPECT
    return replace(quote, quality_status=status)


@dataclass(frozen=True)
class SnapshotVerdict:
    """The verdict on a set of quotes.

    `codes` is the machine-readable finding; `warnings` is the engineer-readable
    detail behind it. Only `codes` may influence what a reader sees — the
    warning strings are for logs, `job_runs`, and admin diagnostics, never for a
    public report (§17, §38).
    """

    status: SnapshotStatus
    warnings: list[str]
    publishable: bool
    codes: list[GateCode] = field(default_factory=list)

    @property
    def blocking_code(self) -> GateCode:
        return self.codes[0] if self.codes and not self.publishable else GateCode.OK


def validate_snapshot(
    quotes: dict[Instrument, Quote],
    mandatory: list[Instrument],
    now: datetime,
    window: timedelta,
) -> SnapshotVerdict:
    """Decide whether this set of quotes may be published at all.

    This is the *snapshot* gate and it is the tolerant one (§15): it refuses
    only data that is absent, unusable, or a unit regression. Staleness is
    recorded but does not block, because a price board quoting the last close is
    honest as long as it says so. The strict gate that staleness does block is
    the analysis one — `analysis/session.py` plus this verdict together.
    """
    warnings: list[str] = []
    codes: list[GateCode] = []

    missing = [i.value for i in mandatory if i not in quotes]
    if missing:
        return SnapshotVerdict(
            SnapshotStatus.FAILED,
            [f"missing mandatory data: {', '.join(missing)}"],
            False,
            [GateCode.MISSING_MANDATORY],
        )

    invalid = [i.value for i, q in quotes.items() if q.quality_status is QualityStatus.INVALID]
    if invalid:
        return SnapshotVerdict(
            SnapshotStatus.FAILED,
            [f"invalid quotes: {', '.join(invalid)}"],
            False,
            [GateCode.INVALID_QUOTE],
        )

    parity = check_unit_sanity(quotes)
    if parity:
        # A unit regression is not a market condition — refuse to publish it.
        return SnapshotVerdict(
            SnapshotStatus.FAILED, [parity], False, [GateCode.UNIT_SANITY_FAILED]
        )

    observed = [q.observed_at for i, q in quotes.items() if i in mandatory]
    spread = max(observed) - min(observed)
    if spread > window:
        warnings.append(f"quotes span {int(spread.total_seconds() / 60)} minutes")
        codes.append(GateCode.SNAPSHOT_WINDOW_EXCEEDED)

    stale = [i.value for i, q in quotes.items() if q.quality_status is QualityStatus.STALE]
    if stale:
        warnings.append(f"stale: {', '.join(sorted(stale))}")
        codes.append(GateCode.STALE_REQUIRED_INPUT)

    suspect = [i.value for i, q in quotes.items() if q.quality_status is QualityStatus.SUSPECT]
    if suspect:
        warnings.append(f"suspect move: {', '.join(sorted(suspect))}")
        codes.append(GateCode.SUSPECT_MOVE)

    status = SnapshotStatus.PARTIAL if warnings else SnapshotStatus.COMPLETE
    return SnapshotVerdict(status, warnings, True, codes or [GateCode.OK])


def check_unit_sanity(quotes: dict[Instrument, Quote]) -> str | None:
    """Cross-check the rial instruments against the world ounce.

    The Iranian prices are single-sourced, so this arithmetic stands in for a
    second provider: it catches a 10x unit regression and a garbage print.
    """
    gold = quotes.get(Instrument.GOLD_18K)
    xau = quotes.get(Instrument.XAU_USD)
    usd = quotes.get(Instrument.USD_IRR_FREE)
    if not (gold and xau and usd):
        return None
    implied = gold_implied_usd(gold.normalized_value, xau.normalized_value)
    ratio = implied / usd.normalized_value
    if ratio > PARITY_SANITY_RATIO or ratio < 1 / PARITY_SANITY_RATIO:
        return (
            f"gold-implied USD is {ratio:.1f}x the market USD — unit or parser error, "
            "not a market move"
        )
    return None
