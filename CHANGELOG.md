# Changelog

## Unreleased

**One post an hour, refreshed every ten minutes** (TASK-008, EXTENSIONS Y)

The channel was a feed: six messages a day, each a snapshot of the moment it was
sent and stale by the time anyone read it. It is now a board.

- Thirteen hourly slots, 09:00–21:00 Tehran, and **both report types are on
  every slot** — a price board and an analysis always arrive together.
- The first run inside a slot posts the two messages. Each of the five after it
  rewrites them in place via `editMessageText`. So 84 collection runs a day
  produce 26 messages, and the board a reader is looking at is never more than
  ten minutes old.
- Collection moves to every ten minutes, 08:32–22:22 Tehran. The cron sits two
  minutes past rather than on the mark: GitHub documents the top of the hour as
  its heaviest window for scheduled runs, and runs here were already starting 7
  to 22 minutes late without help.
- `🔄 آخرین به‌روزرسانی` needed no change. It has read the observation instant
  since v1.2.1, so an edited message already states its own freshness.

No new storage. `reports.telegram_message_id` on the delivered row *is* the
message id, because an hourly panel and its report row have exactly the same
lifetime — the registry table EXTENSIONS Y assumed a panel would need is not
needed for a panel that rotates. The row is the message rather than an archive of
every render: an edit moves its `content`, `snapshot_id`, and `sent_at`.
`metrics` and `signals` still record every ten-minute reading, so nothing about
the stored history depends on what the chat currently shows.

**Fix: a late run no longer loses its slot**

`[schedule].slot_tolerance_minutes` → **`slot_window_minutes`**, renamed because
the meaning changed and not only the bound. The window now looks *backward only*:
a run belongs to the last slot it has passed, never to one still ahead.

A symmetric tolerance was wrong in both directions at once. It let a run arrive
early enough to claim the next slot and post ahead of its stated time, and on
2026-08-16 — the first full day on the 30-minute cadence — it lost the 17:00
snapshot outright. The two nearest runs landed 22.7 minutes early and 20.4
minutes late against a window of 20 either side, so neither claimed the slot and
five of six reports went out that day. What bounds the value now is the gap
between slots, not the collection interval, and a test asserts that against the
config's own slot list.

**`↕ تغییر از آخرین گزارش` → `↕ تغییر از به‌روزرسانی قبل`**

The anchor is unchanged: `Repository.published_baseline` still reads the metrics
behind the last board a reader actually saw, never the last stored row (BUG-007).
What changed is that a board rewritten every ten minutes makes "the last thing
you saw" ten minutes old rather than hours, so the label moved to say so. Below
±0.005% the section still drops entirely, which on a quiet session is most of the
time — that is the intended noise control, not a missing section.

**Known cost, recorded rather than engineered around**: a flat market still
spends one edit per run on a clock that moved and prices that did not. Editing
only when something moved enough to matter is `EXTENSIONS.md` AE, and it stays
unbuilt until the thresholds are measured (F/G/S).

**`market-monitor backfill` — history is no longer only what we watched happen**
(GAP-002, spec §30)

- TGJU publishes a daily OHLC series per symbol going back to 2011–2014
  (2011 for the dollar, 1979 for the ounce). `backfill` replays it through the
  same store-then-derive path collection uses — same symbol map, same unit
  conversion, same `analyze`, same model version — so imported and collected
  rows are one homogeneous series rather than two.
- One snapshot per Tehran session, stamped at `[analysis].tehran_session_close`.
  Daily is all the source publishes; nothing intraday is invented. The ounce is
  carried back up to 4 days, never forward, because Tehran trades Saturday–
  Wednesday and the metal Monday–Friday and only two thirds of sessions have an
  ounce printed the same day.
- Re-runnable: a session already stored is skipped. `--days` bounds the range
  (365 by default, `0` for everything), because on the Actions deployment the
  database is force-pushed on every run and a decade is ~19 MB.
- `model_version` unchanged. No formula moved; this adds observations, not
  arithmetic.

**Fix: `last_value` ordered by insertion time, not observation time**

The jump check compared a new quote against `ORDER BY retrieved_at DESC`. A
backfill inserts thousands of rows retrieved now but observed years ago, so that
ordering would have fed it an arbitrary old price and rejected every honest live
quote. It orders by `COALESCE(source_timestamp, retrieved_at)` now.

**Relicensed from MIT to AGPL-3.0-or-later**

This software's normal use is as a network service: readers receive its reports,
never a copy of it. Under MIT — or under a plain GPL — that use carried no
obligation at all, because nothing is distributed. AGPL section 13 does: anyone
running a modified version, for any audience, must offer that audience the
modified source.

- The report attribution line is now a **licence condition** under AGPL section
  7(b), not a request. It was unenforceable under MIT, and `NOTICE` said so in
  as many words. Removing it now removes the permission to use the software.
- Versions up to and including v1.2.1 (`b543aad`) stay MIT for anyone who
  obtained them. An MIT grant cannot be withdrawn from the commits it covered.
- Single copyright holder, so no contributor agreement was needed. `httpx`
  (BSD-3-Clause) is AGPL-compatible.
- The AGPL permits commercial use, but not closed-source commercial use.
  Separate commercial terms remain available from the copyright holder.

**Local backup of the collected history**

The `market-data` branch is a single force-pushed commit; the pre-push guards
protect the push, not the branch. New `scripts/backup_remote_db.sh` fetches the
committed database and hands it to the existing `backup_db.sh` for a dated,
gzipped, 30-day-pruned copy. A launchd agent in `deploy/launchd/` runs it daily
at 22:00 local. A machine that is off does not back up — an accepted limit,
recorded rather than engineered around.

## 1.2.1 — 2026-08-15

No formula changed, no indicator was added, and no report gained a section.
`model_version` stays **1.2**: nothing here alters a computed number, so bumping
it would fragment history for a wording and scheduling change. v1.2 is the frozen
analytical baseline; this release is about collecting more of it and reading it
more easily.

**Collection, publication, and message update are three frequencies**
- Collection moves to every 30 minutes, 08:30–21:00 Tehran
  (`0,30 5-17` UTC in `collect.yml`). Publication is unchanged at 4 snapshots
  and 2 analyses a day.
- Raising one did not raise the other, and that is structural, not incidental:
  off-slot runs get an `adhoc` key and publish nothing, and a second run inside
  one slot is refused by the delivered-key index. A test walks the real cron
  through the shipped config and asserts 26 runs still produce 6 messages.
- `[schedule].slot_tolerance_minutes` 90 → **20**. It has to stay under the
  collection interval or the run before a slot claims it and posts early. 90 was
  right when a missed run meant a missed report; the next attempt is now 30
  minutes away.
- Message update — editing a published report rather than sending a new one — is
  deliberately not built. `reports.telegram_message_id` is already recorded and
  still unread; `EXTENSIONS.md` AE and Y own that work.

**Two data-integrity fixes, shipped before the frequency change**
- `git fetch` failing was indistinguishable from the `market-data` branch not
  existing, so a transient network error would build a fresh database and
  force-push it over the entire dataset — irrecoverable, the branch being a
  single amended commit. The fetch step now asks `git ls-remote --exit-code`
  which case it is in and fails the job on anything that is not a genuinely
  absent branch.
- New `scripts/guard_db_growth.py` refuses to push a database holding fewer rows
  than the one fetched. The observation tables only ever grow.

**"Change since the last report" now means it**
- It was computed from the previous stored metrics row — correct only while
  collection and publication shared a cron. At 30-minute collection that would
  have reported the last half hour under a label promising the last report.
- `Repository.published_baseline` reads the metrics behind the last *delivered*
  report of that type. A gated delivery showed no numbers so it is skipped; no
  baseline at all drops the section rather than inventing a zero.

**Presentation**
- `↕ تغییر از گزارش قبل` → `↕ تغییر از آخرین گزارش`, and the section is dropped
  entirely when every move rounds to ±0.00%.
- Standalone monetary values in Ayar Analysis carry `تومان` explicitly.
- The gold section names its own construction: `نظری بر مبنای دلار بازار`, with
  `(همان واگرایی دلار/طلا از سمت طلا)` so the gap is not counted as second
  evidence for what the dollar section already said.
- `📈 روند نرخ ضمنی دلار` → `📈 روند نرخ ضمنی دلار از طلا`, the report now
  carrying an AED-implied dollar too.
- The AED reading no longer says the dirham `تأیید می‌کند` the dollar. It states
  two distances; confirmation is a claim about a backtested signal, and no
  backtest exists yet.
- One clock in the status block: `🔄 آخرین به‌روزرسانی: HH:MM`, from the
  observation instant rather than the scheduler's. It replaces the time that used
  to ride on the freshness line instead of joining it.

**Operations**: the 60-day scheduled-workflow disable is documented honestly —
whether the unattended push to `market-data` counts as repository activity is
undocumented, no synthetic keepalive was added, and GitHub's notification email
is the signal to re-enable.

## 1.2.0 — 2026-08-13

Formula version 1.2, signal model 1.2, report template 1.2. One change, to what
the published coin premium means. Additive in storage — no stored row is
rewritten and every 1.1 report keeps its own model version.

**The coin premium is now measured against domestic gold**
- `حباب سکه` is the premium over the Tehran pure-gold value, which is what
  Iranian market participants mean by the word. Previously it valued the coin's
  gold through `xau_usd × usd_market` and so inherited `gold_gap_pct` in full —
  it restated the USD/gold divergence the report had already given one section
  earlier, and could print the implausible result of a minted coin trading
  below its own melt value.
- New instrument `gold_24k` from TGJU's `geram24`, with `geram18 / 0.75` as an
  equivalent fallback. `geram24` is derived from `geram18` (they agree to
  0.0007%), so it is preferred for being direct, not for being independent.
- Cross-checked against TGJU's own `sekee_real`: agreement to **0.001%**, which
  independently validates `EMAMI_COIN_GRAMS` and `EMAMI_COIN_PURITY` as well as
  the arithmetic. On the 2026-08-11 close the premium reads +1.09% domestic
  against −2.07% world, the difference being the gold gap exactly.
- `coin_intrinsic` and `coin_premium_pct` are **retired, not redefined**. The
  published series are `coin_intrinsic_domestic` and `coin_premium_domestic_pct`;
  `coin_intrinsic_world` and `coin_premium_world_pct` are computed and stored
  but never rendered and never entered into a model beside `gold_gap_pct`.
- `gold_pure_domestic` records the denominator actually used, so a stored
  premium is reproducible whichever input supplied it.

**Migration**: `003_gold_24k.sql` inserts one instrument row. No column is
altered and no data is deleted.

## 1.1.0 — 2026-08-12

Formula version 1.1, signal model 1.1, report template 1.1. Brand: عیار مارکت /
Ayar Market. Additive throughout — no stored row is rewritten and every v1.0
report keeps its own model version.

**Cross-market**
- AED/IRT is a display asset *and* an analytical input. `usd_aed_implied` gives
  a second USD reference from the dirham's USD peg, and `aed_usd_gap_pct` its
  divergence. Independent of the gold route, so the two may be compared.
- Three-way USD view in the analysis report: market, gold-implied, AED-implied.
- No composite. The rates stay separate everywhere, pending the research in
  EXTENSIONS P and R.
- EUR/IRT, TRY/IRT, JPY/IRT collected and stored for future research; they are
  display and history only, never valuation inputs.

**Data quality is now a publication gate**
- Two report types with different tolerance: Market Snapshot publishes and
  labels its basis; Ayar Analysis is withheld rather than published wrong.
- A closed Tehran session is never paired with a live world ounce. The ounce is
  aligned from stored history at the session's own instant; with no aligned
  observation the analysis publishes a status message and no numbers.
- Tehran-session inputs must be mutually coherent or the analysis is withheld.
- Raw quotes keep their original timestamps and quality flags — alignment
  chooses which stored observation to read, it never rewrites one.

**Reporting**
- Market Snapshot: configurable FX board, metals, change since the previous
  report, explicit freshness line.
- Ayar Analysis: three-way USD, gaps, one-sentence read, gold, coin, trends.
- Conditional rendering throughout — absent data means an absent section, never
  a placeholder dash.
- Engineering diagnostics removed from public reports; they go to `job_runs`
  and the structured log as `report_gated` events with machine-readable codes.
- `ارزش ذاتی` replaced by `ارزش نظری` / `ارزش طلای سکه`; verdict wording
  ("expensive", "cheap") replaced by stated distances.
- Configurable footer: brand name, bot and channel handles. The repository
  attribution remains non-configurable (see NOTICE).

**Configuration**
- `[schedule].snapshot` and `[schedule].analysis` — counts and times are read,
  never hard-coded.
- `[display]` chooses the public board independently of collection and analysis;
  `[instruments]` names all three sets separately.
- `[peg].usd_aed`, `[analysis].tehran_session_close`,
  `[analysis].xau_alignment_tolerance_hours`, `[freshness].session_window_minutes`.
- New `market-monitor config` command; `--type` flag on `report`/`run-once`.

**Fixed**
- `price_jpy` is quoted per 100 yen. Reading it per-yen would have published a
  100× error; it is stored per one yen and displayed per hundred with the unit
  stated.
- `DATABASE_URL=sqlite:////absolute/path` resolved relative to the repository
  because every leading slash was stripped, silently creating the database
  inside the project.

**Audited, unchanged**
- The Emami coin formula is arithmetically correct. It does, however, inherit
  the USD/gold divergence and so is not independent evidence — documented in
  docs/FORMULAS.md, with the alternative parked as EXTENSIONS Q rather than
  changed silently.

**Migration**: `002_fx_instruments.sql` inserts four instrument rows. No column
is altered and no data is deleted.

## 0.1.0 — 2026-08-12

First working version. Formula version 1.0, signal model 1.0, report template 1.0.

- Fetches USD, 18K gold, world ounce, and the Emami coin from TGJU, with
  gold-api as a fallback for the ounce.
- Stores every raw observation with provenance; snapshots group contemporaneous
  quotes.
- Computes gold-implied USD, theoretical 18K gold, both gaps, the coin premium,
  and 1/3/7-day trends.
- Rule-based signals with machine-readable reason codes; confidence capped at
  0.6 while thresholds remain provisional.
- Persian report published to Telegram, once per `type|slot|model_version`.
- CLI: `fetch`, `report`, `run-once` (both with `--dry-run`), `health`, `db-info`.
- Attribution line on every report; `[reporting].channel_note` adds to it.
- MIT licence, DISCLAIMER.md, SECURITY.md, NOTICE.

Known gaps: thresholds are placeholders pending backtesting (EXTENSIONS F, G);
the three rial instruments are single-sourced; no `backfill` command.
