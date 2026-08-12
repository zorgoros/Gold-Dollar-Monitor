# Structure Hygiene — Market-situation

Binding on every agent (Claude, Codex, human). Read this before creating,
moving, renaming, or deleting any file.

## The map

The tree mandated by `ARCHITECTURE.md` §17. Directories marked *planned* do not
exist yet; create them when the phase that needs them lands (§35), not before.

| Path | Holds | Never holds |
|---|---|---|
| `src/market_monitor/domain/` | models, constants, enums | I/O, provider or DB detail |
| `src/market_monitor/providers/` | one adapter per data source, scraping included | formulas, DB writes |
| `src/market_monitor/normalization/` | unit conversion, validators | provider quirks, analysis |
| `src/market_monitor/analysis/` | pure deterministic formulas and signals | HTTP, SQL, Persian text |
| `src/market_monitor/storage/` | database, repositories, migration runner | business rules |
| `src/market_monitor/reporting/` | report models, Persian formatter, templates | any calculation |
| `src/market_monitor/publishers/` | Telegram and future delivery surfaces | rendering, analysis |
| `src/market_monitor/jobs/` | collect, report, alerts, health entrypoints | logic worth unit-testing |
| `src/market_monitor/observability/` | logging setup, health checks | secrets, tokens |
| `config/` | `default.yaml`, `logging.yaml` — thresholds, schedules | secrets, `.env` |
| `migrations/` | forward schema migrations | hand-applied SQL |
| `tests/unit/` `tests/integration/` `tests/fixtures/` | tests and captured provider payloads | live network calls |
| `scripts/` | bootstrap, backup, one-shot import | anything imported by `src/` |
| `deploy/` | Dockerfile, compose, systemd, cron | application code |
| `docs/` | FORMULAS, PROVIDERS, OPERATIONS, BACKTESTING | code |
| `docs/ops/` | LEDGER, HANDOFF, MEMORY, this file | anything else |
| `data/` | the SQLite database — gitignored | anything tracked |

Root holds only: `README.md`, `ARCHITECTURE.md`, `EXTENSIONS.md`,
`CHANGELOG.md`, `LICENSE`, `CLAUDE.md`, `AGENTS.md`, `.env.example`,
`.gitignore`, `pyproject.toml`, the lock file, and an optional `Makefile`.

## Rules

1. **No new top-level directory** without a row added here in the same change.
2. **One purpose per file.** If a file needs "and" to describe it, split it.
3. **Names are lowercase-kebab** for dirs and scripts; language convention for
   source files. No spaces, ever.
4. **Nothing lands at the repo root** beyond the list under the map above.
5. **Deleting is a normal act.** Dead code, superseded docs, and stale scripts
   get removed, not archived in place. Git remembers.
6. **Generated output is gitignored** and never edited by hand.
7. **Before adding a file, check whether an existing one should grow instead.**
   Fewer, fuller files beat a scatter of stubs.
8. **Moving a file is a standalone change.** Do not mix a move with an edit —
   the diff becomes unreviewable.
9. **A move is not done until every reference follows it.** Run
   `pos impact "<old/path>"` before and after; imports, CI configs, docs, and
   this table are all dependents.
10. **Changing a rule on this page is itself a change with dependents.** Run
    `pos impact` on the old wording and update whatever quoted it.

## When a change breaks a rule

Say so, in one line, and propose the smallest structural fix. Do not silently
create a directory that has no row in the table above.
