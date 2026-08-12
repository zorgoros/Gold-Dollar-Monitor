from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .enums import (
    Classification,
    DeliveryStatus,
    Instrument,
    QualityStatus,
    ReasonCode,
    ReportType,
    SnapshotStatus,
    Unit,
)


@dataclass(frozen=True)
class Quote:
    """One observation of one instrument, with the provenance that makes it auditable."""

    instrument: Instrument
    provider: str
    provider_symbol: str
    raw_value: str
    normalized_value: float
    unit: Unit
    currency: str
    retrieved_at: datetime
    source_timestamp: datetime | None = None
    quality_status: QualityStatus = QualityStatus.OK
    raw_payload_hash: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    id: int | None = None

    @property
    def observed_at(self) -> datetime:
        """Source time when the provider gives one, retrieval time otherwise."""
        return self.source_timestamp or self.retrieved_at

    def age_seconds(self, now: datetime) -> float:
        return (now - self.observed_at).total_seconds()


@dataclass(frozen=True)
class Snapshot:
    """Contemporaneous quotes, keyed by instrument."""

    snapshot_at: datetime
    quotes: dict[Instrument, Quote]
    status: SnapshotStatus = SnapshotStatus.COMPLETE
    id: int | None = None

    def value(self, instrument: Instrument) -> float | None:
        quote = self.quotes.get(instrument)
        return quote.normalized_value if quote else None

    def require(self, instrument: Instrument) -> float:
        value = self.value(instrument)
        if value is None:
            raise KeyError(f"snapshot has no quote for {instrument}")
        return value


@dataclass(frozen=True)
class Metric:
    name: str
    value: float
    unit: str
    model_version: str


@dataclass(frozen=True)
class Signal:
    instrument: Instrument
    classification: Classification
    severity: int
    confidence: float
    summary_fa: str
    reason_codes: list[ReasonCode]
    metrics_used: dict[str, float]
    generated_at: datetime
    model_version: str


@dataclass(frozen=True)
class Report:
    report_type: ReportType
    report_key: str
    content: str
    channel: str
    generated_at: datetime
    model_version: str
    snapshot_id: int | None = None
    delivery_status: DeliveryStatus = DeliveryStatus.PENDING
    telegram_message_id: int | None = None
