from datetime import UTC, datetime

import pytest

from market_monitor.domain.enums import CANONICAL_UNIT, Instrument, SnapshotStatus
from market_monitor.domain.models import Quote, Snapshot
from market_monitor.storage.database import connect, migrate
from market_monitor.storage.repositories import Repository

AT = datetime(2026, 8, 12, 9, 30, tzinfo=UTC)

# Optional instruments a snapshot may carry, and their fixture defaults. Values
# are the live figures captured on 2026-08-12 (docs/PROVIDERS.md), converted to
# canonical units — the yen per ONE yen, not per hundred.
OPTIONAL_DEFAULTS = {
    "coin": (Instrument.EMAMI_COIN, 189_485_000.0),
    "aed": (Instrument.AED_IRT, 51_161.0),
    "eur": (Instrument.EUR_IRT, 216_760.0),
    "try_": (Instrument.TRY_IRT, 3_910.0),
    "jpy": (Instrument.JPY_IRT, 1_176.0),
}


@pytest.fixture
def repo(tmp_path):
    conn = connect(tmp_path / "test.db")
    migrate(conn)
    yield Repository(conn)
    conn.close()


def make_quote(instrument: Instrument, value: float, at: datetime = AT, **kwargs) -> Quote:
    return Quote(
        instrument=instrument,
        provider="test",
        provider_symbol="x",
        raw_value=str(value),
        normalized_value=value,
        unit=CANONICAL_UNIT[instrument],
        currency="USD" if instrument is Instrument.XAU_USD else "IRT",
        retrieved_at=at,
        source_timestamp=at,
        **kwargs,
    )


@pytest.fixture
def snapshot():
    def _make(at: datetime = AT, usd=185_400.0, gold=19_150_000.0, xau=4382.0, **optional):
        quotes = {
            Instrument.USD_IRR_FREE: make_quote(Instrument.USD_IRR_FREE, usd, at),
            Instrument.GOLD_18K: make_quote(Instrument.GOLD_18K, gold, at),
            Instrument.XAU_USD: make_quote(Instrument.XAU_USD, xau, at),
        }
        for name, (instrument, default) in OPTIONAL_DEFAULTS.items():
            value = optional.get(name)
            if value is True:
                value = default
            if value:
                quotes[instrument] = make_quote(instrument, float(value), at)
        return Snapshot(snapshot_at=at, quotes=quotes, status=SnapshotStatus.COMPLETE)

    return _make
