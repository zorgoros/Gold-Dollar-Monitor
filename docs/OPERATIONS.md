# Operations

## Deploy (VPS, no Docker)

```bash
git clone <repo> /srv/market-monitor && cd /srv/market-monitor
python3 -m venv .venv && .venv/bin/pip install -e .
cp .env.example .env      # fill in TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID
chmod 600 .env
.venv/bin/market-monitor health
.venv/bin/market-monitor run-once --dry-run   # verify before anything is sent
```

Migrations run automatically on every command; the database is created on first
use at `data/market.db`.

## Deploy (Docker)

```bash
cp .env.example .env    # fill in, then:
docker compose -f deploy/docker-compose.yml up -d
```

The compose file mounts `./data` so the SQLite file survives a container
rebuild, and sets `TZ=Asia/Tehran`.

## Scheduling

Cron is the V1 default (`deploy/cron/market-monitor.cron`):

```cron
CRON_TZ=Asia/Tehran
0 9,13,17,21 * * * cd /srv/market-monitor && .venv/bin/market-monitor run-once >> logs/run.log 2>&1
```

systemd equivalent in `deploy/systemd/` — enable with:

```bash
sudo systemctl enable --now market-monitor.timer
```

Slot times also live in `config/default.toml` under `[schedule].reports`; the
report key is derived from them, so **keep cron and the config in agreement**.
A run more than 90 minutes from any configured slot gets its own `adhoc` key
and will not consume the scheduled slot's single delivery.

## Duplicate protection

A report key is `report_type|slot|model_version`, and a partial unique index
enforces one *delivered* report per key. Running `run-once` twice for the same
slot prints `skipped (already delivered)` and sends nothing. A failed delivery
does not burn the key — the retry can still send.

## Backup and restore

```bash
scripts/backup_db.sh /var/backups/market-monitor      # daily, via cron
```

It uses `sqlite3 .backup`, which is safe against a live writer, then gzips and
prunes beyond 30 days. Restore:

```bash
systemctl stop market-monitor.timer
gunzip -c /var/backups/market-monitor/market-2026-08-12.db.gz > data/market.db
.venv/bin/market-monitor db-info      # confirm row counts
systemctl start market-monitor.timer
```

Test a restore occasionally. The accumulated raw history is the asset here —
prices can be re-fetched only for today, never for last month.

## Troubleshooting

| Symptom | Cause | Action |
|---|---|---|
| `not publishable: missing mandatory data` | provider down or a symbol vanished | `market-monitor health`; check `docs/PROVIDERS.md` mapping |
| Report shows `stale:` warnings overnight | Iranian market closed; TGJU serves the previous close | expected — the report is labelled, not suppressed |
| `gold-implied USD is 10.0x the market USD` | a rial/toman unit regression | the run refused to publish; fix the unit mapping in the adapter |
| `AuthenticationError` from Telegram | bad token, or bot is not a channel admin | re-check `.env`; add the bot to the channel as admin |
| `skipped (already delivered)` | the slot already went out | intended; use a different slot or bump `model_version` |
| Every trend prints `—` | fewer than 24h of history | expected on a new install; it fills in after a day |

## Logs

Structured JSON on stderr, one object per event, secrets never passed to the
logger. Under cron they land in `logs/run.log`. Every run writes a `job_runs`
row with status, error type, and metadata — `market-monitor db-info` and
`market-monitor health` read from it.

## Token rotation

Create the new token in BotFather, update `.env`, run
`market-monitor health` to confirm, then revoke the old one. No code change and
no restart is needed — the token is read per run.
