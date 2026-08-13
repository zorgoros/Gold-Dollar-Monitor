# Gold-Dollar-Monitor

[![CI](https://github.com/zorgoros/Gold-Dollar-Monitor/actions/workflows/ci.yml/badge.svg)](https://github.com/zorgoros/Gold-Dollar-Monitor/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)

**عیار مارکت · Ayar Market** — fetches Iranian and global market prices on a
schedule, stores every raw observation, computes deterministic indicators, and
publishes two compact Persian reports to a Telegram channel: a **Market
Snapshot** price board and an **Ayar Analysis** cross-market read.

Not a trading bot. It executes nothing and advises nothing — every report is an
analytical indicator. Design: [ARCHITECTURE.md](ARCHITECTURE.md).

## Status

v1.2. 193 tests passing, `ruff` and `mypy --strict` clean. The full pipeline is
verified against live data in dry-run.

v1.1 added four FX instruments, a second independent USD reference from the
dirham market, and a publication gate that withholds the analysis rather than
publishing a temporally incoherent one. v1.2 moves the published coin premium
onto a domestic gold denominator so it stops restating the USD/gold gap.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env      # fill in TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID
```

## Use

```bash
market-monitor run-once --dry-run   # fetch, store, analyse, render — never sends
market-monitor run-once             # same, then publishes whichever slots are due
market-monitor fetch                # fetch and store a snapshot only
market-monitor report --dry-run     # re-render the latest stored snapshot
market-monitor report --dry-run --type analysis   # force one report type
market-monitor config               # effective schedule, instruments, footer
market-monitor health               # provider, credential, and database status
market-monitor db-info              # row counts and latest snapshot
```

```bash
python -m pytest
ruff check src tests && ruff format --check src tests && mypy src
```

---

## Data sources

Verified live on 2026-08-12. Full detail, response shapes, and captured
fixtures: [docs/PROVIDERS.md](docs/PROVIDERS.md).

| Instrument | Source | Endpoint | Provider unit | Conversion |
|---|---|---|---|---|
| USD free market | TGJU | `call1.tgju.org/ajax.json` → `current.price_dollar_rl.p` | **rial**/USD | ÷ 10 → toman |
| 18K gold | TGJU | `…ajax.json` → `current.geram18.p` | **rial**/gram | ÷ 10 → toman |
| World gold | TGJU | `…ajax.json` → `current.ons.p` | USD/troy oz | none |
| Emami coin | TGJU | `…ajax.json` → `current.sekee.p` | **rial**/coin | ÷ 10 → toman |
| AED | TGJU | `…ajax.json` → `current.price_aed.p` | **rial**/AED | ÷ 10 → toman |
| EUR | TGJU | `…ajax.json` → `current.price_eur.p` | **rial**/EUR | ÷ 10 → toman |
| TRY | TGJU | `…ajax.json` → `current.price_try.p` | **rial**/TRY | ÷ 10 → toman |
| JPY | TGJU | `…ajax.json` → `current.price_jpy.p` | **rial/100 JPY** | ÷ 10 **÷ 100** → toman/yen |

**Fallbacks**

| For | Source | Notes |
|---|---|---|
| World gold | `api.gold-api.com/price/XAU` | no key; agreed with TGJU to 0.02% |
| Whole feed | `call3.tgju.org/ajax.json` | byte-identical mirror of `call1` |

No key, no auth, no rate limits observed on any source. The three rial
instruments have **no independent second source** — they are cross-checked
arithmetically instead (see the sanity guard below).

### Source caveats

- TGJU quotes seven of eight instruments in **rial**. Read as toman, every
  published number is 10× too high. The unit is declared per symbol and
  converted in `normalization/units.py`, never assumed.
- **The yen is quoted per 100 yen**, so it needs a second division by 100 —
  a 100× trap that, unlike the rial one, does not look absurd on inspection.
  Verified against the USD/JPY cross on 2026-08-12.
- Outside Tehran market hours TGJU serves the **previous close**, marked by a
  `ts` of `00:00:00`. That is a date, not a closing bell — the analysis moves it
  to the configured session close before aligning a world ounce to it.
- Cloudflare caches the endpoint (`max-age=300`, observed ages up to ~19 min).
  Every request adds a cache-buster to force a MISS.

---

## Formulas

Constants defined once in `domain/constants.py`; derivations and interpretation
limits in [docs/FORMULAS.md](docs/FORMULAS.md).

| Constant | Value | Source |
|---|---|---|
| `TROY_OUNCE_GRAMS` | 31.1034768 | exact definition of the troy ounce |
| `GOLD_18_PURITY` | 0.75 | 18 karat = 18/24 |
| `GOLD_18_CONVERSION` | 41.4713024 | derived, not typed |
| `RIAL_PER_TOMAN` | 10 | 1 toman = 10 rial |
| `EMAMI_COIN_PURE_GRAMS` | 7.3197 | 8.133 g × 0.900 purity |
| `USD_AED_PEG` | 3.6725 | CBUAE conventional peg, since Nov 1997 |
| `JPY_QUOTE_UNITS` | 100 | TGJU quotes the yen per hundred |

```
usd_gold_implied     = gold_18k × GOLD_18_CONVERSION / xau_usd
usd_gap_pct          = (usd_market / usd_gold_implied − 1) × 100
usd_aed_implied      = aed_irt × USD_AED_PEG
aed_usd_gap_pct      = (usd_market / usd_aed_implied − 1) × 100
gold_18_theoretical  = xau_usd × usd_market / GOLD_18_CONVERSION
gold_gap_pct         = (gold_18_market / gold_18_theoretical − 1) × 100
gold_pure_domestic       = gold_24k          (fallback: gold_18k / GOLD_18_PURITY)
coin_intrinsic_domestic  = gold_pure_domestic × EMAMI_COIN_PURE_GRAMS
coin_premium_domestic_pct = (coin_market / coin_intrinsic_domestic − 1) × 100
```

The coin premium is measured against **domestic** gold — the حباب Iranian market
participants mean. Valuing it through the world ounce instead makes it inherit
`gold_gap_pct` in full, so it stops being independent evidence; that series is
still computed as `coin_premium_world_pct` but is never published. The audit
that settled this is in [docs/FORMULAS.md](docs/FORMULAS.md).

Golden-vector tests check them against the worked example in ARCHITECTURE.md §15
and against live figures captured on 2026-08-12.

**The two gold gaps are one fact.** Implied USD and theoretical gold are the
same equation inverted — never count them as two independent signals. The AED
route is genuinely independent (a currency peg, not a metal content), so it
*may* be compared with the gold one — but the two are never averaged into a
composite. That needs research the project has not done; see
[EXTENSIONS.md](EXTENSIONS.md) P and R.

**Note on the coin premium.** It is arithmetically correct but inherits the
USD/gold divergence, so it is not independent evidence. The audit and the
numbers are in [docs/FORMULAS.md](docs/FORMULAS.md).

**Sanity guard.** Because the rial instruments are single-sourced, a run is
refused if gold-implied USD diverges from market USD by more than 3×. That
catches a unit regression or a garbage print without a second provider.

---

## Update frequency

| What | Frequency |
|---|---|
| Market Snapshot | 4×/day — 09:00, 13:00, 17:00, 21:00 `Asia/Tehran` |
| Ayar Analysis | 2×/day — 13:00, 21:00 `Asia/Tehran` |
| Source polling | once per run; no continuous polling |
| Trend horizons | 1, 3, 7 days (30 available) |

Both schedules live in `config/default.toml` under `[schedule]` and must match
your cron or systemd timer, which fires at the union of the two. No count or
time is hard-coded. Scheduling is cron by default — see
[docs/OPERATIONS.md](docs/OPERATIONS.md).

**Data quality is a publication gate, not a footnote.** The snapshot board
publishes stale prices with an explicit `🕐 بر مبنای آخرین پایان معاملات`
label. The analysis is stricter: it refuses to pair a closed Tehran session
with a live world ounce, aligning the ounce from stored history instead — and
if no aligned observation exists, it publishes a short status message and no
numbers at all.

| Instrument | Staleness limit |
|---|---|
| USD, 18K gold, coin, all FX | 20 min |
| World gold | 30 min |
| Widest spread within one snapshot | 15 min |
| Widest spread between analysis inputs | 20 min |
| World-ounce alignment window | 12 h |

A run more than 90 minutes from a configured slot gets its own report key, so a
manual run never consumes a scheduled slot's single delivery. One delivered
report per `report_type|slot|model_version`, enforced by a database index.

---

## Caveats

Thresholds in `config/default.toml` are **provisional placeholders**, not
calibrated values. Signal confidence is capped at 0.6 in code for that reason.
Calibration needs the backtesting work in [EXTENSIONS.md](EXTENSIONS.md) (F, G).

---

## Licence, attribution, and legal

MIT — see [LICENSE](LICENSE). Not affiliated with TGJU or any data provider.

**This is not financial advice.** The software computes arithmetic
relationships between published prices; it does not forecast or recommend.
Every report carries a disclaimer. Read [DISCLAIMER.md](DISCLAIMER.md) before
publishing its output to an audience — market commentary is regulated in many
places.

**Attribution.** Reports carry `Gold-Dollar-Monitor · github.com/zorgoros/Gold-Dollar-Monitor`.
Set `[reporting.footer]` (brand name, bot and channel handles) and
`[reporting].channel_note` to add your own lines above it. Please keep the
attribution if you run a fork — see [NOTICE](NOTICE).

**Data.** Fetched at runtime from public endpoints, never redistributed;
fixtures are trimmed samples for offline tests. Four requests a day at the
default schedule.

**Security.** Token handling, trust boundaries, and how to report a
vulnerability: [SECURITY.md](SECURITY.md).
