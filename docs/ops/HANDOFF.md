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
