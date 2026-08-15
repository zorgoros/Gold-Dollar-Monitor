# Operations

## Deploy (GitHub Actions — no server)

The default. `.github/workflows/collect.yml` runs the same `run-once` the cron
file would, on GitHub's runners, at the union of the configured slots. Standard
runners are free without a minute cap on public repositories.

Two secrets, set once — the values never enter the repository:

```bash
gh secret set TELEGRAM_BOT_TOKEN
gh secret set TELEGRAM_CHANNEL_ID
```

Then trigger it by hand before trusting the schedule:

```bash
gh workflow run collect.yml -f dry_run=true    # renders, sends nothing
gh workflow run collect.yml                    # publishes for real
```

### Where the database lives

On the orphan **`market-data`** branch, not on `main`. A SQLite file does not
delta, so a commit per run would bury a fresh copy of a growing binary in
`main`'s history four times a day — roughly 1,500 copies a year, removable only
by a `git filter-repo` rewrite that breaks every clone. The branch instead holds
exactly one commit, amended and force-pushed each run, and retiring it is:

```bash
git push origin --delete market-data
```

The runner has no persistent disk, so each job fetches that branch into `_data/`,
points `DATABASE_URL` at it, and pushes it back. The push runs even when the
pipeline step fails: raw observations are stored before anything derives from
them, and a dropped collection is the one loss that cannot be back-filled.

`scripts/scan_db_for_secrets.py` runs between the two and fails the job rather
than publish a database containing anything credential-shaped. The branch is
pushed unattended to a public repository, so this is checked, not assumed.

### Known behaviour

- **Scheduled runs are late**, routinely by 5–20 minutes under load. Absorbed by
  `[schedule].slot_tolerance_minutes = 90`, which is why it is that wide.
- **Cron here is UTC.** `30 5,9,13,17` is 09:00/13:00/17:00/21:00 Tehran. Iran
  abolished DST in 2022, so the +3:30 offset holds year-round. Changing
  `[schedule]` means changing this cron in the same edit.
- **GitHub disables schedules after 60 days of repository inactivity.** The
  per-run push to `market-data` counts as activity, so this only bites if
  collection is already broken.

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
use at `data/market.db`. `DATABASE_URL` takes `sqlite:///relative/to/repo` or
`sqlite:////absolute/path` — the fourth slash is what makes it absolute.

## Local dashboard review

Run the JSON API and browser application in separate terminals:

```bash
.venv/bin/market-monitor dashboard --host 127.0.0.1 --port 8000
cd dashboard && npm install && npm run dev
```

The API has GET-only `/api/v1/latest`, `/api/v1/history`, and `/api/v1/health`
routes. It reads the configured SQLite database and never starts Telegram. Vite
proxies the API during local review. Neither service is a production server.

## Configuration

Everything an operator is meant to change lives in `config/default.toml`; there
is no second settings system and no runtime admin surface — the Telegram
integration is publish-only. Inspect the effective values with:

```bash
market-monitor config
```

| Section | Controls |
|---|---|
| `[schedule]` | how many of each report type per day, and when |
| `[display]` | which instruments appear on the public board, in order |
| `[instruments]` | what is collected, what analysis requires, what it merely uses |
| `[reporting.footer]` | brand name and handles (§24) |
| `[peg]` | the USD/AED peg |
| `[freshness]`, `[analysis]` | the gate's thresholds and windows |

The three instrument sets are independent on purpose: collection is the widest,
so history accumulates for instruments nothing displays or analyses yet. A
price nobody stored is the one thing that cannot be back-filled.

## Deploy (Docker)

```bash
cp .env.example .env    # fill in, then:
docker compose -f deploy/docker-compose.yml up -d
```

The compose file mounts `./data` so the SQLite file survives a container
rebuild, and sets `TZ=Asia/Tehran`.

## Two report types

The channel carries two surfaces and nothing else (§37):

| Report | Default schedule | Tolerance to stale data |
|---|---|---|
| Market Snapshot (`📊 عیار مارکت`) | 09:00, 13:00, 17:00, 21:00 | tolerant — publishes and labels the basis |
| Ayar Analysis (`⚖️ تحلیل عیار`) | 13:00, 21:00 | strict — withheld rather than published wrong |

Both lists live in `config/default.toml` under `[schedule].snapshot` and
`[schedule].analysis`. Counts and times are read at publish time; changing the
cadence is a config edit and nothing else. `market-monitor config` prints what
is actually in force.

## Scheduling

Cron is the default (`deploy/cron/market-monitor.cron`). One entry covers both
report types — the run publishes whichever slots the current time matches:

```cron
CRON_TZ=Asia/Tehran
0 9,13,17,21 * * * cd /srv/market-monitor && .venv/bin/market-monitor run-once >> logs/run.log 2>&1
```

systemd equivalent in `deploy/systemd/` — enable with:

```bash
sudo systemctl enable --now market-monitor.timer
```

Cron must fire at the **union** of the two slot lists, so **keep cron and the
config in agreement**. A run more than `[schedule].slot_tolerance_minutes` from
any configured slot gets its own `adhoc` key; off-slot runs publish nothing
unless `--type` forces a report, which is what keeps manual runs from adding
channel noise.

## The publication gate

Data quality is decided *before* anything is rendered, not appended as a
warning afterwards. The two surfaces gate differently on purpose.

**Market Snapshot** publishes unless the data is missing, unusable, or a unit
regression. Stale prices are shown with `🕐 بر مبنای آخرین پایان معاملات`
rather than suppressed — a price board quoting the last close is honest as long
as it says so. Instruments that were not collected are omitted entirely; no row
ever carries a placeholder dash.

**Ayar Analysis** additionally requires temporal coherence:

1. The Tehran-session inputs must agree with each other within
   `[freshness].session_window_minutes`. A dollar from today and a gold price
   from last week is not a market state.
2. If every required input is inside its freshness limit, the live world ounce
   is used — basis `LIVE`.
3. Otherwise Tehran is closed. The ounce is **not** taken live. TGJU's session
   marker is moved to `[analysis].tehran_session_close` and the nearest stored
   `xau_usd` observation within `[analysis].xau_alignment_tolerance_hours` is
   used instead — basis `LAST_CLOSE`, labelled as such in the report.
4. If no aligned ounce exists, the analysis is **withheld** and the channel
   gets `⚠️ تحلیل این نوبت منتشر نشد…` — no numbers.

Step 4 fires on a fresh install until roughly a day of history exists, which is
expected. In steady state the 21:00 and 09:00 runs bracket a 17:00 close well
inside the tolerance, so a closed-session analysis finds its ounce.

Why this matters concretely: pairing a live ounce with the previous Iranian
close made the Emami coin read as trading 2.8% *below* its own metal content on
2026-08-12 — an impossible number produced entirely by the timing mismatch.

Public reports never carry instrument names, minute counts, or subsystem names.
Those go to `job_runs.metadata_json` and the structured log as `report_gated`
events with a `codes` list.

## Duplicate protection

A report key is `report_type|slot|model_version`, and a partial unique index
enforces one *delivered* report per key. Running `run-once` twice for the same
slot prints `duplicate` and sends nothing. A failed delivery does not burn the
key — the retry can still send.

Because `report_type` is part of the key, a snapshot and an analysis sharing a
slot (13:00 and 21:00 by default) are two independent deliveries and neither
suppresses the other.

Bumping `model_version` changes every key, so a report may publish into a slot
an earlier version already used — expect one extra message in the slots either
side of a bump. Stored rows keep the version they were made under and are never
rewritten.

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
| Snapshot shows `🕐 بر مبنای آخرین پایان معاملات` | Iranian market closed; TGJU serves the previous close | expected — the board is labelled, not suppressed |
| Analysis withheld, log says `XAU_NOT_ALIGNED` | no stored ounce near the Tehran session | expected for the first ~day after install; persisting means runs are being missed, check `job_runs` |
| Analysis withheld, log says `SESSION_INCOHERENT` | Iranian inputs come from different sessions | one symbol has frozen while others tick; check `ts` per symbol at TGJU |
| `gold-implied USD is 10.0x the market USD` | a rial/toman unit regression | the run refused to publish; fix the unit mapping in the adapter |
| Yen looks ~100× too small on the board | `price_jpy` read per-yen instead of per-100 | the source unit must be `rial/100jpy`; see `docs/PROVIDERS.md` |
| `AuthenticationError` from Telegram | bad token, or bot is not a channel admin | re-check `.env`; add the bot to the channel as admin |
| `duplicate` | the slot already went out | intended; use a different slot or bump `model_version` |
| No trend section in the analysis | fewer than 24h of history | expected on a new install; the section appears once history exists |
| `no report slot due` | run fired away from every configured slot | intended noise control; `--type` forces one |

## Logs

Structured JSON on stderr, one object per event, secrets never passed to the
logger. Under cron they land in `logs/run.log`. Every run writes a `job_runs`
row with status, error type, and metadata — `market-monitor db-info` and
`market-monitor health` read from it.

## Token rotation

Create the new token in BotFather, update `.env`, run
`market-monitor health` to confirm, then revoke the old one. No code change and
no restart is needed — the token is read per run.
