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
