from datetime import UTC, datetime

import pytest

from market_monitor.domain.enums import Instrument, SnapshotStatus, Unit
from market_monitor.domain.models import Quote, Snapshot
from market_monitor.storage.database import connect, migrate
from market_monitor.storage.repositories import Repository

AT = datetime(2026, 8, 12, 9, 30, tzinfo=UTC)


@pytest.fixture
def repo(tmp_path):
    conn = connect(tmp_path / "test.db")
    migrate(conn)
    yield Repository(conn)
    conn.close()


def make_quote(instrument: Instrument, value: float, at: datetime = AT, **kwargs) -> Quote:
    units = {
        Instrument.USD_IRR_FREE: Unit.TOMAN_PER_USD,
        Instrument.GOLD_18K: Unit.TOMAN_PER_GRAM,
        Instrument.XAU_USD: Unit.USD_PER_TROY_OUNCE,
        Instrument.EMAMI_COIN: Unit.TOMAN_PER_COIN,
    }
    return Quote(
        instrument=instrument,
        provider="test",
        provider_symbol="x",
        raw_value=str(value),
        normalized_value=value,
        unit=units[instrument],
        currency="USD" if instrument is Instrument.XAU_USD else "IRT",
        retrieved_at=at,
        source_timestamp=at,
        **kwargs,
    )


@pytest.fixture
def snapshot():
    def _make(at: datetime = AT, usd=185_400.0, gold=19_150_000.0, xau=4382.0, coin=None):
        quotes = {
            Instrument.USD_IRR_FREE: make_quote(Instrument.USD_IRR_FREE, usd, at),
            Instrument.GOLD_18K: make_quote(Instrument.GOLD_18K, gold, at),
            Instrument.XAU_USD: make_quote(Instrument.XAU_USD, xau, at),
        }
        if coin is not None:
            quotes[Instrument.EMAMI_COIN] = make_quote(Instrument.EMAMI_COIN, coin, at)
        return Snapshot(snapshot_at=at, quotes=quotes, status=SnapshotStatus.COMPLETE)

    return _make
