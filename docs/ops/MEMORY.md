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
- 2026-08-12 — coin_premium_pct is NOT independent of usd_gap_pct: it values the coin's gold via xau x usd, so it contains gold_gap_pct in full. Against domestic gold the same coin read +1.09% vs -2.34% via the world route. Formula left unchanged pending a decision (EXTENSIONS Q)
- 2026-08-12 — metric key `usd_gap_pct` means the GOLD divergence and keeps that name for history's sake; the AED one is `aed_usd_gap_pct`. There is deliberately no gold_usd_gap_pct alias
- 2026-08-12 — the stored metrics series is always computed from inputs as collected, never from an aligned analysis: session alignment reads xau_usd back out of it, so writing aligned values in would create a feedback loop
- 2026-08-12 — there is no interactive Telegram bot; the integration is publish-only sendMessage. config/default.toml plus `market-monitor config` is the entire admin surface, by decision, not omission
- 2026-08-12 — `pos` is not installed on this machine; the ops files in docs/ops/ are maintained by hand in their documented formats
