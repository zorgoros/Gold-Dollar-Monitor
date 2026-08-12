# Extensions

Parking lot for ideas that are **not** committed architecture. An entry here is
not permission to build it: implementation requires promotion to `APPROVED`
(ARCHITECTURE.md §18).

Division of labour with the ops ledger: this file holds long-horizon *product*
ideas; `docs/ops/LEDGER.md` holds actionable work — gaps, bugs, tasks, and any
extension already promoted to `APPROVED`. An idea moves from here to the ledger
when it becomes work.

## Adding an entry

New entries use the full template:

```markdown
## Extension: <name>

Status: IDEA | RESEARCH | APPROVED | IN_PROGRESS | DONE | REJECTED
Priority: LOW | MEDIUM | HIGH
Target version:
Dependencies:
Core changes required:
Backward compatibility:
Description:
Why it may be useful:
Open questions:
Acceptance criteria:
```

## Seeded ideas

All `IDEA` status, seeded from ARCHITECTURE.md §19. Expand one into the full
template above when it is picked up for research.

| Extension | Priority | Description |
|---|---|---|
| A. Web dashboard | MEDIUM | Lightweight responsive HTML over the same metrics API |
| B. Widget architecture | MEDIUM | One widget per component, consuming structured JSON, never parsed Telegram text |
| C. Personal-site integration | LOW | Embed widgets in an existing simple site (e.g. `zorgoros.x`) |
| D. REST API | MEDIUM | Read-only `/latest`, `/quotes`, `/metrics`, `/signals`, `/history`, `/health` |
| E. Interactive charts | LOW | Market vs implied, gap over time, z-score, coin bubble |
| F. Backtesting engine | HIGH | Do gap regimes predict 1/3/7/14/30-day forward returns; strictly offline |
| G. Statistical thresholds | HIGH | Replace provisional bands with percentiles, z-scores, volatility bands |
| H. Regime detection | LOW | Trend, volatility, and risk regimes |
| I. Abnormal-movement alerts | MEDIUM | Event-driven, independent of the scheduled report |
| J. Multi-source consensus | MEDIUM | Cross-validate two providers, flag divergence, defined failover policy |
| K. Additional markets | MEDIUM | USDT/IRT, AED/IRT, EUR/IRT, silver, Brent, BTC |
| L. Optional AI commentary | LOW | LLM summarises already-computed metrics; never the numeric source of truth |
| M. Authentication | LOW | Only if a private dashboard or admin console appears |
| N. Mobile/PWA | LOW | Installable dashboard |

`F` and `G` are the pair that matters: until they land, every threshold in
`config/default.toml` is a guess and reports must keep saying so.
