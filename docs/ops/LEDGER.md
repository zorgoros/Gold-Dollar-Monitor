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

## TASK-005 · v1.2.1 presentation refinements to both public reports · DONE
**Family:** v121,formatter,persian,wording,units,presentation,readability
**Raised:** 2026-08-15
**Summary:** readability-only edits to the two reports; no formula, no new indicator

### Phases
- [x] P1 — Market Snapshot: header `↕ تغییر از آخرین گزارش`; suppress the whole
      change block when every move rounds to ±0.00%
- [x] P2 — Ayar Analysis: `تومان` on the standalone دلار / طلا / سکه values;
      gold section relabelled `نظری بر مبنای دلار بازار` + `(همان واگرایی دلار/طلا از سمت طلا)`;
      trend heading → `📈 روند نرخ ضمنی دلار از طلا`
- [x] P3 — soften the AED wording in `analysis/signals.py::_usd_summary` —
      no `تأیید می‌کند` before F/G calibration exists
- [x] P4 — `🔄 آخرین به‌روزرسانی: HH:MM` from the render instant, timestamp only,
      no update counter

### Notes
Owner brief 2026-08-15, §2–§6 and §9. All of it lands in
`reporting/formatter_fa.py` except P3 (`analysis/signals.py`).
`_status()` already prints `🟢 داده‌ها به‌روز | HH:MM` on a live basis — P4 must
replace that half-line, not add a second clock beside it.
No counter: the owner's own stated minimum is the timestamp, and a counter needs
the persistent-message state that does not exist yet (EXTENSIONS Y/AE).

## TASK-006 · separate collection, message-update, and new-post frequencies · DONE
**Family:** v121,schedule,cron,frequency,collection,publication,github-actions,slot-tolerance
**Raised:** 2026-08-15
**Summary:** collect every 30 min, keep posting on the configured slots; the edit
path stays future work

### Phases
- [x] P1 — BUG-006 first. Raising the run count 12x without it multiplies the
      exposure to the one failure that cannot be undone
- [x] P2 — BUG-007 next, in the same change as P3. At 4 runs/day
      "previous collection" and "previous report" are the same row; at 48 they
      are not, and the published percentage silently changes meaning
- [x] P3 — `collect.yml` cron `*/30`; narrow `[schedule].slot_tolerance_minutes`
      from 90 to ~20; optionally lengthen the `[schedule].snapshot` list
- [x] P4 — `docs/OPERATIONS.md`, ARCHITECTURE §0/§36, CHANGELOG. One source of
      truth per concept: the schedule lives in config, the docs point at it

### Notes
Owner brief 2026-08-15, §7 and §14. Verified against GitHub's own docs:
cron floor is 5 min, public repos have no minute quota, scheduled runs are
best-effort (delayed at the top of the hour, dropped under load), and a public
repo's schedules are auto-disabled after 60 days with no repository activity —
the unattended force-push to `market-data` may not count as activity.

A/C need no new mechanism. Collection and publication are *already* separate:
`collect()` always stores, `due_report_types()` gates publication on
`[schedule]`, and `report_key = type|slot|model_version` + `already_delivered`
suppresses every extra run inside one slot window. So `*/30` buys 12x the data
at an unchanged post cadence. The 90-minute tolerance was set wide to survive a
missed 4x/day run; with a run every 30 minutes the next one covers the gap, so
tightening it is what keeps a post landing near its stated time.

B (change-aware editing) is deliberately NOT here — it is EXTENSIONS AE, needs
`Publisher.edit()` (only `sendMessage` exists today), a current-message concept,
a last-rendered-state cache, and an honest "meaningful change" threshold that
wants F/G. `reports.telegram_message_id` is already persisted and unread, which
is the whole foundation AE needs.

Shipped 2026-08-15. Two departures from the phase text above, both deliberate:

- The cron is `0,30 5-17` (08:30–21:00 Tehran, 26 runs), not a 24/7 `*/30`. The
  window ends at the last publication slot; past it a closed domestic market only
  restates its own close, and the brief asked not to collect redundant closes.
- ARCHITECTURE §36 was left alone. It is the *V1* definition-of-done checklist
  and nothing in v1.2.1 changes what V1 had to satisfy; the deltas went to §0,
  which is the section that records decisions.

`slot_tolerance_minutes` landed at 20, and a test now asserts it stays under the
collection interval — above 30 the preceding run claims the slot and the report
goes out early, which is the quiet way this regresses.

The VPS deployment moved with it: `deploy/cron/market-monitor.cron` and
`deploy/systemd/market-monitor.timer` both collect every 30 minutes too, so the
two deployments do not disagree about what the schedule means.

## BUG-006 · a failed market-data fetch starts a fresh database and force-pushes over all history · DONE
**Family:** workflow,market-data-branch,force-push,history-loss,persistence,actions
**Raised:** 2026-08-15
**Summary:** transient fetch failure is read as "no branch yet", and the empty
database is then force-pushed over the real one

### Phases
- [x] P1 — split the two cases: `git ls-remote --exit-code origin market-data`
      decides whether the branch exists. Branch absent → fresh database, as now.
      Branch present but fetch failed → fail the job, push nothing
- [x] P2 — refuse to push a database with fewer `snapshots` rows than the one
      fetched. Cheap, and it catches every other way an empty file could reach
      the branch. Sits next to the existing secret scan
- [x] P3 — one test over the guard

### Notes
`.github/workflows/collect.yml`, "Fetch the database" step:
`if git fetch -q --depth 1 origin market-data 2>/dev/null; then ... else
"starting a fresh database"`. Network error and missing branch are the same exit
status, and the publish step then runs `git commit --amend` + `git push --force`.
The branch is a single amended commit, so there is no earlier commit to recover
from — one bad run ends the dataset.

Low exposure at 4 runs/day. TASK-006 makes it 48. Fix before the cron changes,
not after.

## BUG-007 · snapshot change line compares against the previous collection, not the previous published report · DONE
**Family:** changes,baseline,metric-before,percent-change,snapshot-board
**Raised:** 2026-08-15
**Summary:** `↕ تغییر از آخرین گزارش` is computed from the last metrics row, so a
faster cron silently redefines what the published percentage measures

### Phases
- [x] P1 — a repository query for the snapshot behind the last *delivered*
      report of this type, and the metrics row at that instant
- [x] P2 — `engine.analyze` takes that baseline instead of
      `repo.metric_before(name, now)`; no baseline → omit the section, never a
      dash and never a zero
- [x] P3 — tests: same-slot re-run, a gap of several collections, first-ever run

### Notes
`analysis/engine.py:196` calls `repo.metric_before(name, now)` — literally the
previous row. Its docstring already claims it "asks what the last thing we
published said", which is true only while collection and publication share a
cron. TASK-006 breaks that.

Owner brief §2 asks for exactly this ("the latest valid comparable snapshot, not
simply the immediately preceding database row"). The frequency change is what
makes it urgent rather than cosmetic: after it, a 13:00 post would report the
move since 12:30 under a header saying "since the last report".

## TASK-007 · first read-only web dashboard · ACTIVE
**Family:** dashboard,web,api,widgets,public-surface
**Raised:** 2026-08-15
**Summary:** build the first responsive RTL Ayar Market dashboard over a
read-only structured API, without Telegram parsing or repeated formula logic

### Phases
- [ ] P1 — repository-backed web projection and bounded read-only API, with
      the existing session-alignment gate for detailed analysis
- [ ] P2 — separate static RTL UI: market board, compact analysis summary,
      full analysis view, historical ranges, and no-data states
- [ ] P3 — API/UI tests, responsive browser verification, documentation, and
      merge review into `main`

### Notes
Active worktree: `.worktrees/dashboard-v1`; branch: `codex/dashboard-v1`;
starting commit: `c54438c`; merge target: `main`. Read the design and merge
gate in `docs/superpowers/specs/2026-08-15-first-dashboard-design.md` on that
branch before merging. Dashboard JSON comes from a read-only projection of
snapshots, metrics, and signals. It never reads Telegram text or recomputes
economic values in JavaScript. Detailed cross-market analysis must use the
existing session-alignment gate; if it cannot align a closed Tehran session to
the world ounce, the UI shows an unavailable state rather than analysis data.
