# Changelog

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
