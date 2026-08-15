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
`main`'s history 26 times a day — roughly 9,500 copies a year, removable only by
a `git filter-repo` rewrite that breaks every clone. The branch instead holds
exactly one commit, amended and force-pushed each run, and retiring it is:

```bash
git push origin --delete market-data
```

The runner has no persistent disk, so each job fetches that branch into `_data/`,
points `DATABASE_URL` at it, and pushes it back. The push runs even when the
pipeline step fails: raw observations are stored before anything derives from
them, and a dropped collection loses an intraday observation that no source
sells back. Only the daily close is recoverable, via `backfill`.

### The two guards before the push

The branch is one amended commit that is force-pushed, so there is no earlier
commit to restore from. Both guards fail the job instead of publishing, and both
run `if: always()`:

- `scripts/scan_db_for_secrets.py` — refuses a database containing anything
  credential-shaped. The branch is pushed unattended to a public repository, so
  this is checked, not assumed.
- `scripts/guard_db_growth.py` — refuses a database holding fewer rows than the
  one fetched. The observation tables only ever grow, so a count that fell means
  the file was replaced rather than appended to.

The fetch step is the other half of that protection. `git fetch` exits non-zero
both for "branch does not exist yet" and for "the network is down", and treating
the second as the first once would force-push an empty database over the whole
dataset. It therefore asks `git ls-remote --exit-code` first: exit 2 is a genuinely
absent branch and starts fresh, anything else fails the job.

### Known behaviour

- **Scheduled runs are late**, routinely by 5–20 minutes under load, and GitHub's
  own docs say queued jobs may be *dropped* entirely when load is high enough. A
  dropped run now costs one collection cycle rather than a quarter of the day.
- **Cron here is UTC.** `0,30 5-17` is 08:30–21:00 Tehran every 30 minutes. Iran
  abolished DST in 2022, so the +3:30 offset holds year-round, which is why
  Tehran's o'clock falls on UTC's half hour. This is the *collection* cadence;
  see [Scheduling](#scheduling) for why it is not the publication one.
- **Public repositories have no Actions minute quota** on standard runners, so
  the run count is not a billing question.
- **GitHub disables schedules after 60 days of repository inactivity.** Whether
  the unattended per-run push to `market-data` counts as activity is *not*
  documented, and we are deliberately not adding a synthetic keepalive to find
  out. GitHub emails the repository owner when it disables a workflow; that
  notification is the signal, and re-enabling is one click in the Actions tab.
  Collection stops until it is done, so do not ignore the mail.

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
so history accumulates for instruments nothing displays or analyses yet. An
intraday price nobody stored is the one thing that cannot be back-filled — TGJU
sells back the daily close and nothing finer.

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

Three frequencies, deliberately not one. Confusing them is how a system ends up
posting every time it looks at a price.

| | How often | Set by |
|---|---|---|
| **Collection** | every 30 min, 08:30–21:00 Tehran | the cron in `collect.yml` |
| **Publication** | 4 snapshots + 2 analyses a day | `[schedule]` in `config/default.toml` |
| **Message update** | not implemented | — see below |

**Raising collection does not raise publication**, and that is a property of the
code rather than a coincidence of the cron:

1. `collect()` stores its raw observations on every run, whatever happens next.
2. `due_report_types()` publishes only within `[schedule].slot_tolerance_minutes`
   of a configured slot. Every other run gets an `adhoc` key and posts nothing.
3. The second run *inside* one slot renders the same `report_type|slot|model_version`
   key, and the unique index on delivered keys refuses it.

So the 26 runs a day produce the same 6 messages that 6 runs a day did. The
[`test_thirty_minute_collection_does_not_raise_the_post_rate`](../tests/integration/test_pipeline.py)
test walks the real cron through the shipped config and asserts exactly that.

**`slot_tolerance_minutes` must stay under 30**, the collection interval. Above
it, the run *before* a slot falls inside the slot's window and claims it, and the
report goes out early. It was 90 when collection ran four times a day and a
missed run meant a missed report; the next attempt is now 30 minutes away, so it
can be tight enough to keep a post near its stated time. A test asserts the
bound.

**Message update** — editing an already-published report instead of sending a new
one — is not built. `reports.telegram_message_id` is recorded on every delivery
and nothing reads it back yet; that column is the foundation the work would start
from. Scope and open questions live in `EXTENSIONS.md` under *Configurable
refresh and update-on-change engine* (AE) and *Telegram dashboard mode* (Y).

### On a VPS instead

`deploy/cron/market-monitor.cron`. One entry covers both report types — the run
publishes whichever slots the current time matches:

```cron
CRON_TZ=Asia/Tehran
0,30 8-21 * * * cd /srv/market-monitor && .venv/bin/market-monitor run-once >> logs/run.log 2>&1
```

systemd equivalent in `deploy/systemd/` — enable with:

```bash
sudo systemctl enable --now market-monitor.timer
```

Cron must fire at least at the **union** of the two slot lists, so **keep cron
and the config in agreement**. Off-slot runs publish nothing unless `--type`
forces a report, which is what keeps manual runs from adding channel noise.

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
expected — or until `market-monitor backfill` supplies it. In steady state the
21:00 and 09:00 runs bracket a 17:00 close well inside the tolerance, so a
closed-session analysis finds its ounce.

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

Under the GitHub deployment the database is **one commit**, amended and
force-pushed 26 times a day. The two pre-push guards stop a bad push; nothing
there survives the branch being deleted. The second copy is local:

```bash
scripts/backup_remote_db.sh                     # -> ~/market-monitor-backups
```

It fetches `market-data`, writes the committed blob to a temporary file, and
hands that to `backup_db.sh` for the copy itself. It never pushes and never
touches the working tree.

A launchd agent runs it daily at 22:00 local, after the 21:00 Tehran collection
closes the day:

```bash
cp deploy/launchd/com.zorgoros.market-monitor-backup.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.zorgoros.market-monitor-backup.plist
```

launchd rather than cron because cron is deprecated on macOS, and because
launchd runs a missed calendar job once when the machine next wakes. **The
accepted limit: a machine that is off does not back up.** A backup taken most
days beats one taken never; if that stops being enough, the answer is the VPS
deployment below, not a cleverer laptop.

Log: `~/market-monitor-backups/backup.log`. Check it occasionally — a silent
failure here is invisible until the day it matters.

On a VPS instead, the database is local and there is no branch to fetch:

```bash
scripts/backup_db.sh /var/backups/market-monitor      # daily, via cron
```

Both paths use `sqlite3 .backup`, which is safe against a live writer, then gzip
and prune beyond 30 days. Restore:

```bash
systemctl stop market-monitor.timer
gunzip -c /var/backups/market-monitor/market-2026-08-12.db.gz > data/market.db
.venv/bin/market-monitor db-info      # confirm row counts
systemctl start market-monitor.timer
```

Test a restore occasionally. The accumulated raw history is the asset here. A
lost *daily close* can be re-imported from TGJU (see below); a lost intraday
observation is gone, because nobody but us wrote it down.

## Backfilling history

```bash
market-monitor backfill --dry-run     # count sessions, write nothing
market-monitor backfill               # the last 365 Tehran sessions
market-monitor backfill --days 0      # everything TGJU has, back to 2013
```

TGJU publishes a daily OHLC series per symbol (`docs/PROVIDERS.md`, endpoint 3).
`backfill` replays it through the same store-then-derive path collection uses:
one snapshot per Tehran session, stamped at `[analysis].tehran_session_close`,
then the same metrics and signals the live pipeline writes. That is what gives a
fresh install working trends, and what gives §7's provisional thresholds a real
distribution to be replaced by.

Operational notes:

- **Re-runnable.** A session already stored is skipped, so running it twice is a
  no-op and running it again next month adds only what is new.
- **Daily granularity, not intraday.** One row per session, which is all the
  source publishes. It does not compete with collection: the newest history row
  is the *previous* session's close.
- **Size.** A year is ~300 sessions and ~1.5 MB. `--days 0` is ~3,400 sessions
  and ~19 MB — and on the Actions deployment that file is force-pushed on every
  run, so decide the range with the push cost in mind, not just the disk.
- **The ounce is carried back, never forward.** Tehran trades Saturday–Wednesday
  and the metal Monday–Friday, so only about two thirds of Iranian sessions have
  an ounce printed the same day. A Saturday close is paired with Friday's ounce —
  the last one the world had set — up to 4 days back, and the session is skipped
  entirely beyond that. It is the same rule the live gate applies.

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
| No trend section in the analysis | fewer than 24h of history | expected on a new install; `market-monitor backfill` imports it, or wait for it to accumulate |
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
