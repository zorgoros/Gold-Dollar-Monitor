# Market-situation — memory

Durable facts about this project that are **not** derivable from the code, the
git history, or the other ops files. Read once at session start, via
`pos status`. Written with `pos remember "<fact>"`.

A fact earns a line here only if an agent that skipped it would get something
wrong: decisions and their reasons, constraints, external identifiers, traps
that already cost someone an hour. Not code structure, not what a file does,
not anything a `grep` would answer.

Prune stale lines by hand — a wrong fact here is worse than a missing one.
Budget is 60 lines; `pos` warns past that.

## Facts
- 2026-08-12 — ARCHITECTURE.md was renamed from Iran_Market_Monitor_ARCHITECTURE.md on 2026-08-12 to match the tree it specifies in §17
- 2026-08-12 — TGJU quotes usd_irr_free/gold_18k/emami_coin in RIAL (divide by 10 for toman); only xau_usd (ons) is already canonical. Verified 2026-08-12 against live call1.tgju.org/ajax.json
- 2026-08-12 — A TGJU 'ts' with a 00:00:00 time component means previous close, not a live tick; Cloudflare also serves cached ajax.json (age up to ~1150s) unless a cache-buster query param is added
- 2026-08-12 — No independent second source exists for the rial instruments (bonbast needs a scraped token, alanchand 404s); cross-check them with the gold-parity and coin-intrinsic ratios instead. xau_usd fallback is api.gold-api.com/price/XAU, no key
- 2026-08-12 — TGJU `price_jpy` is quoted per **100** yen, not per yen. Verified against diff_usd_jpy (ratio 99.62). Canonical storage is toman per ONE yen; reports multiply by 100 and label it. A per-yen read is a silent 100x error
- 2026-08-12 — v1.1 decision: a closed Tehran session must never be paired with a live world ounce. The ounce is aligned from stored xau_usd history at the session instant, or Ayar Analysis is withheld. Pairing them made the Emami coin read -2.8%, below its own metal content
- 2026-08-12 — TGJU's `00:00:00` session marker is a date, not a closing bell. analysis/session.py moves it to [analysis].tehran_session_close (17:00) before aligning; anchoring on midnight picks an ounce ~17h early
- 2026-08-12 — coin_premium_pct is NOT independent of usd_gap_pct: it values the coin's gold via xau x usd, so it contains gold_gap_pct in full. Against domestic gold the same coin read +1.09% vs -2.34% via the world route. RESOLVED in v1.2 — see the next two lines
- 2026-08-13 — v1.2 decision: the published حباب is the premium over DOMESTIC gold (geram24, fallback geram18/0.75), not the world route. Old names coin_intrinsic/coin_premium_pct retired, not redefined; the world route survives as the non-public coin_premium_world_pct. Never model it beside gold_gap_pct
- 2026-08-13 — TGJU `geram24` is DERIVED from `geram18` (agree to 0.0007%), not a second opinion on domestic gold. Preferred as the coin denominator for being direct, not more accurate. TGJU also publishes `sekee_real` = geram24 x 7.3197, which our coin_intrinsic_domestic matches to 0.001% — an independent check on EMAMI_COIN_GRAMS/PURITY. Not collected: it is TGJU's derived output, not a raw observation
- 2026-08-12 — metric key `usd_gap_pct` means the GOLD divergence and keeps that name for history's sake; the AED one is `aed_usd_gap_pct`. There is deliberately no gold_usd_gap_pct alias
- 2026-08-12 — the stored metrics series is always computed from inputs as collected, never from an aligned analysis: session alignment reads xau_usd back out of it, so writing aligned values in would create a feedback loop
- 2026-08-12 — there is no interactive Telegram bot; the integration is publish-only sendMessage. config/default.toml plus `market-monitor config` is the entire admin surface, by decision, not omission
- 2026-08-12 — `pos` is not installed on this machine; the ops files in docs/ops/ are maintained by hand in their documented formats
- 2026-08-15 — pos add numbers IDs per type prefix (it greps '^## $TYPE-[0-9]+'), but LEDGER.md's existing 001-007 run was a single global sequence maintained by hand. TASK-005 and BUG-005, GAP-006 and BUG-006 therefore coexist. IDs are unique as full strings — do not renumber, the tool would just drift again
- 2026-08-15 — TGJU's history endpoint stops at the last *closed* Tehran session (`price_dollar_rl` ended 2026-08-11 while `ons` had 08-14), so `backfill` never covers the last day or two and the 1d/3d trends still need live collection to fill. Also: only ~64% of Iranian sessions have a same-date `ons` row — the ounce is carried back up to 4 days, which is why a backfilled analysis is not identical to what a live run that day would have produced
- 2026-08-15 — first web-dashboard work is isolated at `.worktrees/dashboard-v1` on branch `codex/dashboard-v1`, created from `main` commit `c54438c`; merge its commits back to `main` only after reviewing the dashboard API/UI boundary, tests, and the dashboard design/spec records
- 2026-08-15 — 2026-08-15 owner decision on the market-data single-copy risk: no automated backup for now. The owner pulls the market-data branch into the local clone regularly as the backup. Do not build a tagged-copy workflow unless the owner asks
- 2026-08-15 — 2026-08-15 owner decision on silent-collection-failure risk: accepted, no monitoring built. The owner is active daily and watches the channel; a VPS running the pipeline is the fallback if GitHub disables the schedule. Raise it again only if collection actually stops
