# Handoff — Market-situation

Rolling log across agents. Auto-trimmed to the last 20 entries by `pos log` —
this file is a baton, not a history. History is git and the ledger.

**Read `pos status` before starting. Write one entry when you stop.**

## Roster

Whoever is working this project — any tools, any number, any roles. Name them
`<tool>-<role>`, keep this list current, and use these exact names in the log.

| Name | Tool | Role |
|---|---|---|
| `claude-solo` | Claude Code | builds and maintains the service |
| `codex-design` | Codex | dashboard discovery and design |

> Add rows as the roster grows (a `codex-builder`, a reviewer, whatever the
> work needs). Nothing in `pos` validates the names — this table is the guard.

## Format

Four lines, no prose:

```
## YYYY-MM-DD HH:MM · <agent>
Did: <what changed, and where>
Next: <the single next action>
Blocked: <what stopped you, or none>
```

## Log

## 2026-08-12 10:04 · claude-solo
Did: pos init; filled STRUCTURE map from ARCHITECTURE.md s17; trimmed CLAUDE/AGENTS to budget; renamed spec to ARCHITECTURE.md; git init + first commit
Next: Phase 0 bootstrap: pyproject, src/market_monitor skeleton, config/default.yaml, .env.example
Blocked: none

## 2026-08-12 10:35 · claude-solo
Did: built V1 phases 0-9: domain, storage, TGJU adapter, analysis, Persian report, Telegram publisher, CLI, ops; 117 tests green; live dry-run verified
Next: wire real Telegram credentials and do the section 9 controlled test publish
Blocked: none

## 2026-08-12 12:30 · claude-solo
Did: added MIT licence, DISCLAIMER, SECURITY, NOTICE, report attribution; pushed to github.com/zorgoros/Gold-Dollar-Monitor; CI green
Next: wire Telegram credentials and do the controlled test publish
Blocked: none

## 2026-08-12 15:30 · claude-solo
Did: V1 shipped: published to Telegram, footer channel line, Persian pinned-message doc, token-in-logs fix
Next: V1.1 scope
Blocked: none

## 2026-08-12 16:30 · claude-solo
Did: v1.1 shipped: AED-implied USD, 4 FX instruments, temporal publication gate, two report types, config-driven schedule/display/footer, coin audit; 189 tests green; migration 002 applied to prod db
Next: controlled Telegram test of both report types, then enable the new cron slots
Blocked: coin formula question open with the owner (EXTENSIONS Q) — formula left unchanged


## 2026-08-13 14:10 · claude-solo
Did: resolved the 403 (two channels with near-identical names; .env pointed at the one the bot was not in — now the numeric id); v1.1 committed and merged to main; v1.2 shipped: coin premium moved to a domestic gold denominator, gold_24k instrument, world route retired to a non-public series, migration 003 applied to prod db; 193 tests green; cross-checked against TGJU sekee_real to 0.001%
Next: pin the updated Persian message; decide whether `market-monitor health` should call Telegram live; watch the first post-bump slot for the expected duplicate-key extra message
Blocked: none — footer channel line stays absent until the channel has a public handle (§24)

## 2026-08-14 · claude-solo
Did: recorded ten owner ideas in EXTENSIONS.md as Y–AG plus a full entry expanding seeded L (dashboard mode, publishing modes, archive policy, on-demand history, per-destination config, personal chat, refresh/change engine, entitlements, deterministic state machine, AI commentary); all IDEA status, nothing implemented; added a family note under the seeded table
Next: owner triage — approve/reject individually; AC (destination registry) is the root dependency for the delivery family, AG is blocked on F/G/R
Blocked: none

## 2026-08-15  · codex-design
Did: reviewed the dashboard-ready analytical contract, persistence boundaries, extension scope, and public-site reference; the referenced domain did not resolve from this environment
Next: confirm whether the first public dashboard is embedded in zorgoros.x, standalone, or both
Blocked: visual reference unavailable until a reachable URL or screenshot is provided

## 2026-08-15  · codex-design
Did: confirmed visual design selection precedes deployment; prepared the visual-ideation workflow
Next: obtain a reachable Zorgoros reference or permission to explore an original design direction
Blocked: the named visual source remains unavailable from this environment

## 2026-08-15  · codex-design
Did: inspected the supplied Netlify visual reference and generated three original RTL Ayar Market dashboard directions, grounded in the existing market-card contract
Next: owner selects a visual direction or requests refinements before implementation planning
Blocked: none

## 2026-08-15  · codex-design
Did: verified that stored snapshots, metrics, signals, and the existing widget contract support the selected dashboard design; identified the missing read-only web projection and history query boundary
Next: create an isolated worktree, write the approved dashboard specification and implementation plan, then implement the API and separate UI layer
Blocked: current checkout contains unrelated uncommitted work; isolated-worktree consent required before creating files

## 2026-08-15  · codex-design
Did: created `.worktrees/dashboard-v1` on `codex/dashboard-v1` from `main` commit `c54438c`; recorded the branch, path, purpose, and merge gate in MEMORY.md
Next: write the dashboard specification and plan in the isolated worktree, then build the read-only API and separate UI layer
Blocked: none

## 2026-08-15 16:32 · claude-solo
Did: v1.2.1 shipped: BUG-006 (fetch failure could force-push an empty db over market-data) and BUG-007 (change line anchored on the last delivered report via Repository.published_baseline) fixed first; collection cron to every 30 min 08:30-21:00 Tehran with slot_tolerance 90->20, publication unchanged at 4+2; formatter/signals wording per owner brief 2-6 and 9; 217 tests green, ruff/mypy clean, live dry-run verified both reports
Next: watch the first 30-min cycles on Actions — confirm one post per slot and that the growth guard passes on the real branch
Blocked: none

## 2026-08-15 16:41 · codex-design
Did: checked current Codex project-removal guidance; official docs do not document the UI control
Next: provide removal steps if needed
Blocked: none

## 2026-08-15 23:05 · claude-solo
Did: GAP-002 closed — `market-monitor backfill` imports TGJU's daily OHLC history through the live store-then-derive path (TgjuProvider.fetch_history, jobs/backfill.py, CLI --days/--dry-run, idempotent); fixed Repository.last_value ordering which a backfill would otherwise have broken for live collection; corrected four "cannot be back-filled" claims in prose; 224 tests green, ruff/mypy clean; live run imported 294 sessions in 5.5s and reproduced the recorded +1.09% coin premium for 2026-08-11
Next: get the `last_value` fix onto `main` BEFORE any backfilled database reaches `market-data` — old code plus backfilled rows makes the live jump check compare against an arbitrary decade-old price and reject every honest quote. Then import 365 days into the branch database (owner chose that range; local `data/market.db` already has it, both CI guards pass on it)
Blocked: none — threshold recalibration off the imported distribution was explicitly deferred; recorded against EXTENSIONS G/S/F rather than as a new ledger entry, per the dedup rule
