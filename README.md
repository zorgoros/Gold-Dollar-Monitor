# Iran Market Monitor

Fetches Iranian and global market prices on a schedule, stores every raw
observation, computes deterministic indicators (gold-implied USD, theoretical
18K gold, gaps, short trends), and publishes a compact Persian report to a
Telegram channel.

Not a trading bot. It executes nothing and advises nothing — every report is an
analytical indicator. Design and rationale: [ARCHITECTURE.md](ARCHITECTURE.md).

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env      # then fill in TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID
```

## Use

```bash
market-monitor run-once --dry-run   # fetch, store, analyse, render — never sends
market-monitor run-once             # same, then publishes
market-monitor fetch                # fetch and store a snapshot only
market-monitor report --dry-run     # re-render the latest snapshot
market-monitor health               # provider + database + last-run status
market-monitor db-info              # row counts and latest snapshot
```

Behaviour is configured in [config/default.toml](config/default.toml) — report
slots, thresholds, staleness limits, provider priority. Secrets only in `.env`.

Thresholds shipped today are **provisional** placeholders, not calibrated
values (ARCHITECTURE.md §7).

## Development

```bash
python -m pytest
ruff check src tests && ruff format --check src tests
mypy src
```

## Scheduling

Cron is the V1 default. With the venv at `.venv` and Tehran slots from the
config:

```cron
CRON_TZ=Asia/Tehran
0 9,13,17,21 * * * cd /srv/market-monitor && .venv/bin/market-monitor run-once >> logs/run.log 2>&1
```

See [docs/OPERATIONS.md](docs/OPERATIONS.md) for deployment, backup, and restore.
