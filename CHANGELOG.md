# Changelog

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
