"""Error taxonomy from ARCHITECTURE.md §24. Retry policy keys off these types."""

from __future__ import annotations


class MarketMonitorError(Exception):
    """Base for everything this service raises."""


class TransientError(MarketMonitorError):
    """Worth a bounded retry."""


class PermanentError(MarketMonitorError):
    """Never retried in a loop."""


class ProviderUnavailable(TransientError): ...


class RateLimitError(TransientError): ...


class TelegramDeliveryError(TransientError): ...


class ProviderParseError(PermanentError): ...


class AuthenticationError(PermanentError): ...


class InvalidQuote(PermanentError): ...


class StaleQuote(PermanentError): ...


class UnitNormalizationError(PermanentError): ...


class InsufficientSnapshot(PermanentError): ...


class DatabaseError(PermanentError): ...


class AnalysisError(PermanentError): ...


class ReportRenderError(PermanentError): ...


class ConfigurationError(PermanentError): ...
