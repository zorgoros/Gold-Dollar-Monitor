# Ledger — Market-situation

Every idea, gap, bug, and task lives here. One file, so "do we already have
this?" is one search.

**Never hand-write an entry.** Use `pos check` then `pos add` — they enforce
the dedup gate and the ID sequence.

## Format

```
## <TYPE>-<NNN> · <title> · <STATUS>
**Family:** comma,separated,tags        ← the dedup key. Be generous.
**Raised:** YYYY-MM-DD
**Summary:** one line, no more

### Phases
- [ ] P1 — ...
- [ ] P2 — ...

### Notes
```

- **TYPE** — `IDEA` (new scope, UI, rule, layer) · `GAP` (missing piece) ·
  `BUG` (broken behaviour) · `TASK` (agreed unit of work)
- **STATUS** — `OPEN` (captured, not scoped) · `ACTIVE` (phases running) ·
  `DONE` · `MERGED into <ID>` · `DROPPED — <reason>`
- **Phases** appear when the item is settled and scoped, not at capture time.
  An `OPEN` entry may carry a single `P1 — scope it`.

## Entries

## GAP-001 · EXTENSIONS.md and docs/ops/LEDGER.md are two parking lots for the same thing · DONE
**Family:** extensions,ledger,docs,process,duplication
**Raised:** 2026-08-12
**Summary:** EXTENSIONS.md and docs/ops/LEDGER.md are two parking lots for the same thing

### Phases
- [ ] P1 — scope it

### Notes

## GAP-002 · backfill command from spec section 30 is not implemented · OPEN
**Family:** backfill,cli,history,tgju,import
**Raised:** 2026-08-12
**Summary:** backfill command from spec section 30 is not implemented

### Phases
- [ ] P1 — scope it

### Notes

## GAP-003 · rial instruments are single-sourced on TGJU with no independent fallback · OPEN
**Family:** providers,tgju,fallback,redundancy,rial,resilience
**Raised:** 2026-08-12
**Summary:** rial instruments are single-sourced on TGJU with no independent fallback

### Phases
- [ ] P1 — scope it

### Notes

## TASK-004 · v1.1 upgrade: AED analytical input, FX board, publication gate · DONE
**Family:** v11,aed,fx,gate,reporting,settings,upgrade
**Raised:** 2026-08-12
**Summary:** cross-market monitoring upgrade — AED-implied USD, four FX instruments, temporal publication gate, two report types

### Phases
- [x] P1 — domain, units, AED formula, JPY per-100 handling
- [x] P2 — session alignment and the two-tier gate
- [x] P3 — migration 002, config schema, settings accessors
- [x] P4 — snapshot and analysis formatters, configurable footer
- [x] P5 — tests (189 green), docs, live dry-run

### Notes
Coin formula audited and left unchanged; the open economic question is EXTENSIONS Q.

## BUG-005 · absolute DATABASE_URL resolved relative to the repository · DONE
**Family:** settings,database,url,path,config
**Raised:** 2026-08-12
**Summary:** _db_path stripped every leading slash, so sqlite:////abs/path created the database inside the repo

### Notes
Found by hitting it during v1.1 dry-run validation; it silently created a private/ tree at the repo root. Fixed to honour the four-slash absolute form, with a regression test in test_database.py.

## GAP-006 · coin premium is not independent of the USD/gold gap · DONE
**Family:** coin,formula,premium,gold,economics,double-counting
**Raised:** 2026-08-12
**Closed:** 2026-08-13 (v1.2)
**Summary:** coin_intrinsic values the coin's gold via xau x usd, so coin_premium_pct contains gold_gap_pct in full

### Phases
- [x] P1 — owner decides the intended economic meaning (see EXTENSIONS Q)
- [x] P2 — verify geram24 live; cross-check against TGJU's published coin bubble
- [x] P3 — gold_24k instrument, domestic formula, migration 003, model bump to 1.2
- [x] P4 — retire the old metric names, keep the world route as a stored non-public series
- [x] P5 — docs: FORMULAS, CHANGELOG, README, PROVIDERS, BACKTESTING, pinned message

### Notes
Measured 2026-08-12: -2.34% via the world route vs +1.09% against domestic 18K gold, differing by exactly the 3.43% gold gap. Formula deliberately unchanged in v1.1 — changing it is an economic decision, not a bug fix.

Resolved 2026-08-13: owner chose the domestic denominator. TGJU's own `sekee_real` agrees with our domestic figure to 0.001%, which also validates the coin constants independently. `geram24` turned out to be derived from `geram18` (0.0007% apart), so the fallback is equivalent and the preference is about directness only.

## GAP-007 · session close is one configured hour, not a Tehran trading calendar · OPEN
**Family:** session,calendar,alignment,gate,tehran
**Raised:** 2026-08-12
**Summary:** analysis/session.py moves TGJU's zeroed session marker to a single configured close hour, which does not know holidays or early closes

### Phases
- [ ] P1 — scope it

### Notes
Marked with a ponytail: comment in analysis/session.py. The 12h alignment tolerance absorbs the error on an unusual day; a real calendar is the upgrade path if that proves too coarse.

## TASK-008 · first interactive RTL dashboard · DONE
**Family:** dashboard,web,ui,analysis,history,rtl
**Raised:** 2026-08-15
**Summary:** build the selected option-3 market board with a separate detailed analysis view over the bot's existing calculations

### Phases
- [x] P1 — read-only history query and public projection
- [x] P2 — JSON API and local CLI entry point
- [x] P3 — standalone responsive React dashboard
- [x] P4 — component, browser, responsive, and visual QA

### Notes
Implemented on `codex/dashboard-v1` in `.worktrees/dashboard-v1`. The dashboard
keeps gold-implied and AED-implied USD separate and reuses the existing session
gate. Deployment remains intentionally undecided until the owner accepts the
design.
