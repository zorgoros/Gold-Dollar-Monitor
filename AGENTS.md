# AGENTS.md

Project brief: [CLAUDE.md](CLAUDE.md) — read it once per session.
Spec and source of truth: [ARCHITECTURE.md](ARCHITECTURE.md).

## Conventions

Python 3.12+, four-space indent, type hints on public interfaces, English
identifiers. `snake_case` modules/functions, `PascalCase` classes,
`UPPER_SNAKE_CASE` constants. Calculations pure and deterministic; a formula is
defined once, never scattered. Providers implement the adapter interface and
leak nothing provider-specific into analysis.

Tests in `tests/unit/`, `tests/integration/`, fixtures in `tests/fixtures/`.
Files `test_<module>.py`, tests `test_<behavior>_<expected_result>`. Golden
vectors for implied USD, theoretical gold, gaps, unit conversions; cover
malformed, stale, missing, duplicate data; mock Telegram and providers in CI.

Commits are short and imperative (`Add gold gap calculator`). PRs name the
architectural boundary changed, tests run, and a dry-run output when formatting
changes. Never commit `.env`, API keys, Telegram tokens, databases, or
secret-bearing logs.

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
