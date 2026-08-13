# CLAUDE.md

Guidance for Claude Code (claude.ai/code) in this repository.

## State of the repository

Shipped, at v1.2. Python 3.12+, `src/market_monitor/`, SQLite, `httpx` the only
runtime dependency; cron schedules it. [ARCHITECTURE.md](ARCHITECTURE.md) is the
spec — read the section you need, not the file: **v1.1/v1.2 deltas §0**, formulas §4,
DB §10, tree §17, error taxonomy §24, non-goals §37.

```bash
python -m pytest                                     # all; -k or ::name for one
ruff check src tests && ruff format --check src tests && mypy src
market-monitor run-once --dry-run                    # full pipeline, never sends
market-monitor report --dry-run --type analysis      # force one report type
market-monitor config                                # effective settings
```

## Architecture in one paragraph

providers → normalization → immutable raw storage → analysis → signals →
reporting → publishers. Every arrow is a boundary that stays replaceable.
Providers are adapters returning normalized `Quote` objects; nothing downstream
knows TGJU exists. Analysis is pure and deterministic — no LLM in the numeric
path. Reporting consumes serializable output (widget JSON, §20), so Telegram is
one surface, not the model. Two public reports: a price board and a
cross-market analysis, gated separately on data quality.

## Invariants that are easy to violate

- **Units are never implicit** — toman, gram, USD/troy oz, toman per **one** FX
  unit, UTC in storage; Jalali and Persian only at the reporting boundary. TGJU
  quotes rial (÷10) and the yen per 100 (÷100 too).
- **Constants once**: `TROY_OUNCE_GRAMS`, `GOLD_18_PURITY`, `USD_AED_PEG`;
  `GOLD_18_CONVERSION` derived. Never `41.46` inline.
- **Implied USD and theoretical gold are one relationship** algebraically
  inverted — never two pieces of evidence. AED-implied USD *is* independent, so
  it may be compared with them, but never averaged into a composite.
- **A closed Tehran session is never paired with a live world ounce** — align
  the ounce from stored history, or withhold the analysis.
- **Raw observations are immutable**, carry full provenance, and are stored
  before anything is derived from them. Thresholds live in config, provisional.
- **Failure is visible, but not to the reader**: gated reports publish a short
  status line; diagnostics go to `job_runs` and the log, never the channel.
- **Signals are objects** with machine-readable `reason_codes`. Indicators, not
  advice: `نرخ ضمنی`, `ارزش نظری`, `ارزش طلای سکه`, never `ارزش ذاتی`; state
  distances, not verdicts.
- **Idempotency key** `report_type + scheduled_slot + model_version`; record the
  Telegram message id after. Analytical changes bump a persisted model version.

Verify a provider's live API against official docs before coding against it.

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
