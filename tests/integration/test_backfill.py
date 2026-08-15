"""Backfill: TGJU daily closes -> snapshots -> the same metric series live runs write.

No network. The history endpoint is served from a synthetic payload built in the
same positional shape the real one uses (docs/PROVIDERS.md, endpoint 3), because
the point under test is the replay, not the parse of one captured file.
"""

import json
from datetime import date, datetime, time, timedelta
from pathlib import Path

import httpx
import pytest

from market_monitor.analysis.engine import USD_GAP, USD_MARKET
from market_monitor.analysis.trends import trend
from market_monitor.domain.enums import Instrument
from market_monitor.jobs.backfill import backfill
from market_monitor.providers.tgju import SYMBOLS, TgjuProvider
from market_monitor.settings import Settings
from market_monitor.storage.database import connect, migrate
from market_monitor.storage.repositories import Repository
from market_monitor.timeutil import TEHRAN

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "default.toml"

# Rial for everything Iranian, so the toman conversion has something to prove.
# Values are the 2026-08-11 closes from docs/PROVIDERS.md.
BASE_RIAL = {
    "price_dollar_rl": 1_878_000,
    "geram18": 192_056_000,
    "geram24": 256_073_000,
    "sekee": 1_894_850_000,
    "price_aed": 511_610,
    "price_eur": 2_167_600,
    "price_try": 39_100,
    "price_jpy": 1_176_000,
}
DAYS = [date(2026, 8, 9), date(2026, 8, 10), date(2026, 8, 11)]


def history_row(day: date, close: float) -> list[str]:
    """One DataTables row: [open, low, high, close, change, pct, gregorian, jalali]."""
    return [
        f"{close:,.2f}",
        f"{close:,.2f}",
        f"{close:,.2f}",
        f"{close:,.2f}",
        '<span class="high" dir="ltr">0</span>',
        '<span class="high" dir="ltr">0.00%</span>',
        day.strftime("%Y/%m/%d"),
        "1405/05/20",
    ]


def history_provider(ounce_days=DAYS, drift=0.01) -> TgjuProvider:
    """A TGJU whose history endpoint answers per symbol, one row per day.

    Each day is `drift` higher than the one before, so a 1-day trend that is
    computed against the wrong row cannot accidentally look right.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        symbol = request.url.path.rsplit("/", 1)[-1]
        if symbol == "ons":
            rows = [history_row(d, 4374.32 * (1 + drift) ** i) for i, d in enumerate(ounce_days)]
        elif symbol in BASE_RIAL:
            base = BASE_RIAL[symbol]
            rows = [history_row(d, base * (1 + drift) ** i) for i, d in enumerate(DAYS)]
        else:  # pragma: no cover - every mapped symbol is covered above
            rows = []
        return httpx.Response(200, json={"recordsTotal": len(rows), "data": list(reversed(rows))})

    return TgjuProvider(httpx.Client(transport=httpx.MockTransport(handler)))


@pytest.fixture
def repo(tmp_path):
    conn = connect(tmp_path / "backfill.db")
    migrate(conn)
    yield Repository(conn)
    conn.close()


@pytest.fixture
def settings(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    return Settings(
        config=json.loads(json.dumps(Settings.load(CONFIG_PATH).config)),
        db_path=tmp_path / "backfill.db",
        telegram_token=None,
        telegram_channel=None,
        log_level="INFO",
    )


def close_instant(day: date) -> datetime:
    return datetime.combine(day, time(17, 0), tzinfo=TEHRAN)


def test_every_session_becomes_a_snapshot_at_the_tehran_close(repo, settings):
    result = backfill(repo, settings, days=0, provider=history_provider())

    assert (result.sessions, result.first, result.last) == (3, DAYS[0], DAYS[-1])
    stored = repo.latest_snapshot()
    assert stored is not None
    assert stored.snapshot_at == close_instant(DAYS[-1])
    # Not the raw 1,878,000 rial, and not a midnight timestamp either.
    assert stored.value(Instrument.USD_IRR_FREE) == pytest.approx(187_800.0 * 1.01**2)
    assert stored.quotes[Instrument.USD_IRR_FREE].metadata["granularity"] == "daily_close"
    # The yen is the 100x trap: 1,176,000 rial per 100 yen is 1,176 toman per one.
    assert stored.value(Instrument.JPY_IRT) == pytest.approx(1_176.0 * 1.01**2)


def test_imported_history_is_what_a_trend_lookup_reads(repo, settings):
    """The payoff: 1d/3d/7d resolve on a database that has never collected live."""
    backfill(repo, settings, days=0, provider=history_provider())

    now = close_instant(DAYS[-1])
    current = repo.metric_near(USD_MARKET, now, timedelta(minutes=1))
    assert current is not None
    change = trend(repo, USD_MARKET, current[0], now, "1d", timedelta(hours=12))
    assert change == pytest.approx(1.0, abs=1e-6)
    # Derived series are stored too, not just the raw prices.
    assert repo.metric_near(USD_GAP, now, timedelta(minutes=1)) is not None


def test_rerunning_imports_nothing_twice(repo, settings):
    first = backfill(repo, settings, days=0, provider=history_provider())
    before = repo.counts()
    second = backfill(repo, settings, days=0, provider=history_provider())

    assert (second.sessions, second.skipped_existing) == (0, first.sessions)
    assert repo.counts() == before


def test_a_session_without_a_recent_ounce_is_skipped_not_paired_with_a_stale_one(repo, settings):
    """The v1.1 invariant, applied backwards: no ounce within reach, no session."""
    provider = history_provider(ounce_days=[DAYS[0]])
    result = backfill(repo, settings, days=0, provider=provider)

    # 08-09 has its own ounce; 08-10 and 08-11 carry it back one and two days.
    assert (result.sessions, result.skipped_no_ounce) == (3, 0)
    carried = repo.latest_snapshot()
    assert carried is not None
    assert carried.quotes[Instrument.XAU_USD].source_timestamp == datetime(
        2026, 8, 9, tzinfo=TEHRAN
    )

    far = history_provider(ounce_days=[date(2026, 7, 1)])
    conn = connect(settings.db_path.parent / "far.db")
    migrate(conn)
    assert backfill(Repository(conn), settings, days=0, provider=far).skipped_no_ounce == 3
    conn.close()


def test_days_bounds_the_import(repo, settings):
    assert backfill(repo, settings, days=1, provider=history_provider()).sessions == 0


def test_dry_run_writes_nothing(repo, settings):
    result = backfill(repo, settings, days=0, provider=history_provider(), dry_run=True)

    assert result.sessions == 3
    assert repo.counts()["snapshots"] == 0


def test_every_collected_instrument_has_a_history_symbol():
    """A symbol collected live but absent here would silently backfill as a hole."""
    assert set(SYMBOLS) == set(Instrument)
