# Changelog

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
