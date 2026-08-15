"""Project the bot's stored analysis into a small, public dashboard contract."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from ..analysis import engine
from ..domain.enums import AnalysisBasis, ReportType
from ..jobs.report import base_analysis, prepare
from ..normalization.validators import validate_snapshot
from ..reporting.models import widget_payload
from ..settings import Settings
from ..storage.repositories import Repository
from ..timeutil import now_utc, to_iso

PUBLIC_METRICS = frozenset(
    {
        engine.USD_MARKET,
        engine.USD_IMPLIED,
        engine.USD_GAP,
        engine.USD_AED_IMPLIED,
        engine.AED_GAP,
        engine.GOLD_MARKET,
        engine.GOLD_THEORETICAL,
        engine.GOLD_GAP,
        engine.XAU,
        engine.COIN_MARKET,
        engine.COIN_INTRINSIC_DOMESTIC,
        engine.COIN_PREMIUM_DOMESTIC,
        *engine.FX_METRICS.values(),
    }
)

RANGES = {
    "1d": timedelta(days=1),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
}


class DashboardProjection:
    """Read-only adapter between stored analysis and a browser-safe JSON API."""

    def __init__(
        self,
        repo: Repository,
        settings: Settings,
        clock: Callable[[], datetime] = now_utc,
    ) -> None:
        self._repo = repo
        self._settings = settings
        self._clock = clock

    def latest(self) -> dict[str, Any]:
        """Return the latest price board and only analysis that passed its gate."""
        snapshot = self._repo.latest_snapshot()
        if snapshot is None:
            return {
                "state": "NO_DATA",
                "cards": [],
                "analysis": {"state": "UNAVAILABLE"},
            }

        verdict = validate_snapshot(
            snapshot.quotes,
            self._settings.instrument_list("instruments", "mandatory"),
            snapshot.snapshot_at,
            timedelta(
                minutes=float(
                    self._settings.section("freshness").get("snapshot_window_minutes", 15)
                )
            ),
        )
        observation = base_analysis(self._repo, self._settings, snapshot, verdict)
        if observation is None:
            return {
                "state": "UNAVAILABLE",
                "as_of": to_iso(snapshot.snapshot_at),
                "cards": [],
                "analysis": {"state": "UNAVAILABLE"},
            }

        prepared = prepare(
            self._repo,
            self._settings,
            snapshot,
            verdict,
            ReportType.AYAR_ANALYSIS,
            observation,
        )
        analysis_payload: dict[str, Any] = {"state": "UNAVAILABLE"}
        if not prepared.gated and prepared.analysis is not None:
            analysis = prepared.analysis
            analysis_payload = {
                "state": "READY",
                "basis": analysis.basis.value,
                "reference_at": to_iso(analysis.reference_at or analysis.as_of),
                "metrics": {
                    name: value
                    for name, value in analysis.metrics.items()
                    if name in PUBLIC_METRICS
                },
                "signals": [
                    {
                        "instrument": signal.instrument.value,
                        "classification": signal.classification.value,
                        "severity": signal.severity,
                        "confidence": signal.confidence,
                        "summary_fa": signal.summary_fa,
                        "reason_codes": [code.value for code in signal.reason_codes],
                    }
                    for signal in analysis.signals
                ],
                # Conclusions are produced by the analysis layer. The browser
                # only presents them and never reinterprets a market formula.
                "summary_fa": [signal.summary_fa for signal in analysis.signals[:2]],
            }

        return {
            "state": "READY",
            "as_of": to_iso(observation.as_of),
            "basis": observation.basis.value,
            "model_version": observation.model_version,
            "data_status": self._data_status(observation.as_of, observation.basis),
            "cards": widget_payload(observation),
            "analysis": analysis_payload,
        }

    def _data_status(self, as_of: datetime, basis: AnalysisBasis) -> dict[str, Any]:
        """Describe data freshness without making an exchange-hours claim.

        The project has quote freshness rules but no official Tehran trading
        calendar. This status therefore reports only what the stored data can
        prove: current live inputs, a recent last close, or an old snapshot.
        """
        freshness = self._settings.section("freshness")
        required = self._settings.instrument_list("instruments", "mandatory")
        # The whole board is current only while every mandatory input remains
        # inside its own limit, so the strictest configured limit wins.
        limit_minutes = min(float(freshness.get(item.value, 0)) for item in required)
        age_seconds = max(0, round((self._clock() - as_of).total_seconds()))
        limit_seconds = round(limit_minutes * 60)
        if age_seconds > limit_seconds:
            code = "STALE"
        elif basis is AnalysisBasis.LAST_CLOSE:
            code = "LAST_CLOSE"
        else:
            code = "LIVE"
        return {
            "code": code,
            "as_of": to_iso(as_of),
            "age_seconds": age_seconds,
            "freshness_limit_seconds": limit_seconds,
        }

    def history(self, metric_names: tuple[str, ...], range_key: str) -> dict[str, Any]:
        """Return public time series with explicit range coverage information."""
        if range_key not in RANGES:
            raise ValueError(f"unsupported range: {range_key}")
        if not metric_names:
            raise ValueError("unsupported metric: ")
        invalid = next((name for name in metric_names if name not in PUBLIC_METRICS), None)
        if invalid is not None:
            raise ValueError(f"unsupported metric: {invalid}")

        snapshot = self._repo.latest_snapshot()
        if snapshot is None:
            return {
                "state": "NO_DATA",
                "range": range_key,
                "coverage_complete": False,
                "earliest_at": None,
                "series": {name: [] for name in metric_names},
            }

        end = snapshot.snapshot_at
        start = end - RANGES[range_key]
        points = self._repo.metric_history(metric_names, start, end)
        series: dict[str, list[dict[str, Any]]] = {name: [] for name in metric_names}
        for point in points:
            series[point.name].append({"at": to_iso(point.at), "value": point.value})
        earliest = min((point.at for point in points), default=None)
        coverage_complete = all(
            values and values[0]["at"] <= to_iso(start) for values in series.values()
        )
        return {
            "state": "READY",
            "range": range_key,
            "start": to_iso(start),
            "end": to_iso(end),
            "earliest_at": to_iso(earliest) if earliest else None,
            "coverage_complete": coverage_complete,
            "series": series,
        }

    def health(self) -> dict[str, Any]:
        """Return data availability without leaking configuration or paths."""
        snapshot = self._repo.latest_snapshot()
        return {
            "state": "READY" if snapshot else "NO_DATA",
            "latest_snapshot_at": to_iso(snapshot.snapshot_at) if snapshot else None,
        }
