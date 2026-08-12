# CLAUDE.md

Guidance for Claude Code (claude.ai/code) in this repository.

## State of the repository

No code yet. [ARCHITECTURE.md](ARCHITECTURE.md) is the canonical V1 spec and
source of truth (~1500 lines): target tree (§17), DB schema (§10), formulas
(§4), error taxonomy (§24), phased build order (§35), definition of done (§36).
Read the section you need, not the file.

Target: Python 3.12+, package under `src/market_monitor/`, SQLite, few
dependencies (`httpx`, pydantic/dataclasses, pytest, ruff, mypy; APScheduler
only if app-level scheduling wins over cron).

```bash
python -m pytest                                     # all tests
python -m pytest tests/unit/test_gold.py::test_name  # one test
ruff check src tests && ruff format --check src tests
mypy src
market-monitor run-once                              # full pipeline once
market-monitor report --dry-run                      # render only, never sends
```

## Architecture in one paragraph

providers → normalization → immutable raw storage → analysis → signals →
reporting → publishers. Every arrow is a boundary that stays replaceable.
Providers are adapters returning normalized `Quote` objects; nothing downstream
knows TGJU exists. Analysis is pure and deterministic — no LLM in the numeric
path. Reporting and publishers consume serializable analytical output (widget
JSON contract, §20), so Telegram is only the first surface.

## Invariants that are easy to violate

- **Units are never implicit.** Canonical: toman, gram, USD/troy oz, UTC in
  storage. Jalali and Persian formatting only at the reporting boundary.
- **Constants once**: `TROY_OUNCE_GRAMS = 31.1034768`, `GOLD_18_PURITY = 0.75`,
  `GOLD_18_CONVERSION` derived. Never `41.46` inline.
- **The two gap formulas are one relationship** — implied USD and theoretical
  gold are algebraic inversions, not independent evidence in any scoring.
- **Raw observations are immutable** and carry provenance (provider, symbol,
  source ts, retrieval ts, unit, currency, quality flag). Store before deriving.
- **Thresholds live in YAML, marked provisional** — never in source, never
  asserted as economic truth.
- **Failure is visible.** Stale or missing mandatory data ⇒ no normal report;
  store the failure event instead.
- **Signals are objects** carrying machine-readable `reason_codes`.
- **Indicators, not advice.** "gold-implied USD" / `نرخ ضمنی دلار`, never
  "intrinsic value"; no guarantees in report wording.
- **Idempotency key**: `report_type + scheduled_slot + model_version`; check
  delivery before sending, record the Telegram message id after.
- **Model versioning**: analytical changes bump a version, persisted with the
  report.

V1 is deliberately small — non-goals in §37. Verify a provider's live API
against official docs before coding against it (§42).

<!-- project-os:rules -->
## Working rules

Binding on every agent on this project, whatever tool it runs on. The detail
lives in `docs/ops/` — read a file when a rule below sends you there, not
before.

| File | Answers | Read it |
|---|---|---|
| `MEMORY.md` | durable facts, decisions, traps | session start (`pos status`) |
| `HANDOFF.md` | roster, what the last agent did | session start (`pos status`) |
| `LEDGER.md` | every idea, gap, bug, task | before capturing anything |
| `STRUCTURE.md` | where a file goes | before creating or moving one |

### Context budget

This file is re-sent to the model on **every** request — each line is re-billed
every turn, all session, every session. It stays under 120 lines. Durable facts
go to `docs/ops/MEMORY.md` via `pos remember "<fact>"`, never here; project
detail goes to the ops file that owns it.

The same reflex governs reading. **Open on need** — a file is opened because
this task needs something in it, and then only that part.

1. Locate first, read second — `grep` / `glob` / `pos impact` for the lines,
   then read that span with `offset`/`limit`.
2. Over ~400 lines, read the outline (`grep -n '^#'`, or the signatures), then
   only the span you need. Whole-file reads are for changing a file's
   structure, or for genuinely not being able to locate the behaviour.
3. Never re-read a file you read this session; never re-read one you just
   edited to confirm the edit landed — the edit tool fails loudly if it didn't.
4. Never open a file because it is nearby, similarly named, or "for context".
5. One exception, no budget: **the file you are about to delete or overwrite.
   Read it fully first.**

### Consistency — a change is not done until its dependents are

Renaming, moving, retyping, or deleting anything other files may reference — a
function, signature, type, env var, config key, path, directory, or a rule
written in these ops files:

```bash
pos impact "<old name or old path>"
```

Update every hit **in the same change**; say out loud any you deliberately
leave alone; re-run until clean. Prose counts — the README, CI configs, and
`STRUCTURE.md` are dependents too. Fix at the shared definition, not at each
call site: if every caller needs the same guard, the guard belongs in the
callee.

### Capture

Something new mid-conversation — an idea, a scope, a rule, a defect:

1. `pos check "<key terms>"` — always, before creating anything.
2. Exit 1 means a related entry exists. **Stop, show it, ask whether to
   merge.** Never open a second entry in a family that already has one.
3. Exit 0 → `pos add <IDEA|BUG|GAP|TASK> "<title>" "<family,tags>"`.
4. Capture is not a detour: log it, say the ID in one line, resume. Do not
   start work on it.

Settled and scoped → set the entry `ACTIVE`, write `### Phases` (one session's
work each, independently verifiable, in dependency order), tick each box as it
lands, then `pos done <ID>`. Scope found mid-phase is not absorbed — it goes
through capture like anything else.

### Session start and stop

```bash
pos status                                              # before you start
pos log <agent> "<did>" "<next>" "<blocked|none>"       # before you stop
```

Use the exact names in the `## Roster` table of `HANDOFF.md`. A new top-level
directory needs a row in `STRUCTURE.md` in the same change.
<!-- /project-os:rules -->
