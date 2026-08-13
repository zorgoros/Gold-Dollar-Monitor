# Iran Market Monitor

## Backbone Architecture & Agent Builder Specification

**Document role:** Canonical architecture/backbone for implementation\
**Status:** V1 specification with explicit extension points; **v1.1 deltas in
§0 below**\
**Brand:** عیار مارکت · Ayar Market\
**Primary output:** Automated Persian market reports to a Telegram
channel\
**Design principle:** Simple V1, deterministic calculations, auditable
data, modular architecture, future widget/web/API expansion\
**Default timezone:** `Asia/Tehran`\
**Primary language of reports:** Persian\
**Code/documentation language:** English recommended for maintainability

------------------------------------------------------------------------

# 0. v1.1 / v1.2 deltas

Shipped 2026-08-12 and 2026-08-13. Everything below this section describes V1
and remains accurate except where noted here. Detail lives in the document that
owns each subject — this section records the *decisions*, not the specifications.

**v1.2 — the coin premium's denominator.** The published `حباب` is the premium
over the *domestic* pure-gold value (`gold_24k`, fallback `gold_18k / 0.75`),
not over the world ounce converted at the market dollar. The old denominator
inherited `gold_gap_pct` in full, so the coin section restated the divergence
§4 already warns about, and could print a coin trading below its own melt
value. `coin_intrinsic` / `coin_premium_pct` are retired rather than redefined;
the world route survives as the stored, never-published
`coin_premium_world_pct`. Reasoning, the cross-check against TGJU's own
`sekee_real`, and the remaining caveat: `docs/FORMULAS.md`.

**Two public report types replace one.** `market_snapshot` is a price board;
`ayar_analysis` is the cross-market read. Schedules default to 4/day and 2/day
and are read from `[schedule]` at publish time. `scheduled_summary` is retained
as a report type because delivered rows reference it. Cadence and slot
behaviour: `docs/OPERATIONS.md`.

**A second, independent implied USD.** The dirham's USD peg gives a USD/toman
rate that does not come from a metal content, so unlike implied-USD versus
theoretical-gold (§4.4) it is *not* an inversion of the gold relationship. The
two may therefore be compared — §9 of the v1.1 brief — but are never blended.
No composite exists and none may be built without the research in
`docs/BACKTESTING.md`. Formulas and the peg's provenance: `docs/FORMULAS.md`.

**Data quality became a publication gate (supersedes the V1 behaviour in §7 and
§13).** V1 published a normal report and appended a staleness warning. That is
no longer sufficient for the analysis:

* The Tehran-session inputs must be mutually coherent.
* A closed Tehran session is **never** paired with a live world ounce. The
  ounce is aligned from stored history at the session's own instant, after the
  provider's zeroed session marker is moved to the real close hour.
* With no aligned ounce, the analysis is withheld and a short public status
  message is published instead.
* The price board keeps the tolerant V1 behaviour — it publishes and labels its
  basis, because quoting a last close is honest when it says so.

The concrete failure this prevents: a live ounce times the previous Iranian
close made the Emami coin appear to trade below its own metal content.

**Raw observations remain immutable (§2.2 unchanged, and now load-bearing).**
Alignment selects *which* stored observation an analysis reads. It never
rewrites a quote's value, source timestamp, or quality flag. The stored
`metrics` series is always computed from inputs as collected — the alignment
lookup reads that series, so writing aligned values into it would create a
feedback loop.

**Three enablement sets, not one.** Collection, display, and analysis are
configured independently (`[instruments]`, `[display]`). Collection is the
widest: instruments are stored that nothing yet reads, because a price nobody
recorded cannot be back-filled. This realises the §3 note that the data model
must allow arbitrary future instruments without schema redesign — v1.1 added
four instruments with four `INSERT`s and no DDL.

**Configuration is the only administrative surface.** There is no interactive
bot; the Telegram integration is publish-only. Everything an operator changes
is in `config/default.toml`, inspectable via `market-monitor config`. A bot
admin UX is parked in `EXTENSIONS.md`, not built.

**Wording.** `ارزش نظری` and `ارزش طلای سکه`, never `ارزش ذاتی`. Distances are
stated, not graded — no "expensive" or "cheap" while the bands remain
provisional. Public reports carry no engineering diagnostics.

------------------------------------------------------------------------

# 1. Project Mission

Build a small, reliable, extensible market-monitoring service that
periodically retrieves Iranian and global market prices, validates and
stores raw observations, calculates transparent derived indicators,
generates a concise Persian report, and publishes it automatically to a
Telegram channel.

The first version MUST remain deliberately small. It is not a trading
bot and must not execute trades. Its job is:

1.  acquire market data;
2.  preserve the original observations;
3.  calculate predefined formulas;
4.  compare market price with implied/theoretical values;
5.  calculate short historical trends and divergences;
6.  classify conditions using explicit rules;
7.  publish a compact Telegram report;
8.  accumulate a clean historical dataset for later backtesting;
9.  expose stable internal interfaces so future dashboards, widgets,
    alerts, APIs, statistical models, and other markets can be added
    without rewriting the core.

The repository itself should be treated as the long-lived source of
truth.

------------------------------------------------------------------------

# 2. Non-Negotiable Design Principles

## 2.1 Deterministic before intelligent

V1 MUST NOT require an LLM to calculate or classify the market.
Calculations and signals must be deterministic, reproducible, testable,
and explainable.

An LLM may later be added as an optional presentation/commentary layer,
but it must never silently replace the numerical engine.

## 2.2 Raw data is immutable

Every successfully acquired market observation must be stored before
derived calculations are performed. Never overwrite historical raw
observations.

## 2.3 Source provenance

Every price must carry: - source/provider name; - source
symbol/identifier; - source timestamp when available; - retrieval
timestamp; - normalized unit; - currency; - quality/status flag.

## 2.4 Units must never be implicit

The code must distinguish: - IRR vs toman; - gram vs troy ounce; - 18K
vs 24K; - rial-based vs toman-based provider outputs.

Internally, use one canonical representation. Recommended: - Iranian
monetary values: **toman**; - gold weight: **gram**; - international
gold: **USD per troy ounce**; - timestamps: timezone-aware UTC in
storage, rendered as Tehran local time.

## 2.5 Provider independence

No formula or analysis module may depend directly on TGJU or any other
particular website/API. Providers are adapters. Replacing a data source
must not require changing the analytical core.

## 2.6 No invented thresholds

Do not hard-code claims such as "+5% means expensive" as economic truth
unless explicitly configured as provisional. Final thresholds should
eventually be derived from historical distributions/backtests.

## 2.7 Failure must be visible

Stale, incomplete, inconsistent, or unavailable data must never be
presented as a fresh report.

## 2.8 Expansion without core rewrite

Future modules---web dashboard, widgets, REST API, USDT, AED, coin
premium, technical indicators, alerts, statistical models---must consume
the same normalized data and analytical services.

------------------------------------------------------------------------

# 3. V1 Market Inputs

Required inputs:

  Field            Meaning                           Canonical unit
  ---------------- --------------------------------- ----------------
  `usd_irr_free`   Iranian free-market USD price     toman/USD
  `gold_18k`       Iranian 18K gold price per gram   toman/gram
  `xau_usd`        International gold spot/ounce     USD/troy oz
  `emami_coin`     Emami coin market price           toman/coin

v1.1 additions:

  Field       Meaning                     Canonical unit   Role
  ----------- --------------------------- ---------------- --------------------------
  `aed_irt`   UAE dirham                  toman/AED        display + analysis
  `eur_irt`   Euro                        toman/EUR        display + history
  `try_irt`   Turkish lira                toman/TRY        display + history
  `jpy_irt`   Japanese yen                toman/**JPY**    display + history

The yen is stored per **one** yen and published per hundred; the provider quotes
it per hundred, which is a 100x trap documented in `docs/PROVIDERS.md`.

Still-optional future inputs: - 24K gold; - melted gold / آبشده; - USDT/IRT
(source needed — TGJU's is dead, see `EXTENSIONS.md` O); - other coin types;
- provider-reported coin bubble/premium; - market open/closed state.

The data model must allow arbitrary future instruments without schema
redesign.

------------------------------------------------------------------------

# 4. Core Financial Relationships

Use the exact troy-ounce conversion constant:

`TROY_OUNCE_GRAMS = 31.1034768`

For 18K gold:

`GOLD_18_PURITY = 0.75`

Therefore:

`GOLD_18_CONVERSION = TROY_OUNCE_GRAMS / GOLD_18_PURITY`

Approximately:

`41.4713024`

Do not use a manually scattered `41.46` throughout the code. Define the
exact constants once and derive the conversion factor programmatically.

## 4.1 Gold-implied USD

The Iranian 18K gold market implies an exchange rate:

`usd_gold_implied = gold_18k * GOLD_18_CONVERSION / xau_usd`

Interpretation: \> The USD/toman rate embedded in Iranian 18K gold given
the international ounce price.

This is an **implied rate**, not an independent intrinsic/fundamental
valuation of USD.

## 4.2 USD gap/premium

`usd_gap_pct = ((usd_market / usd_gold_implied) - 1) * 100`

Positive: - market USD is above the gold-implied USD.

Negative: - market USD is below the gold-implied USD.

## 4.3 Theoretical Iranian 18K gold

`gold_18_theoretical = xau_usd * usd_market / GOLD_18_CONVERSION`

## 4.4 Gold gap/premium

`gold_gap_pct = ((gold_18_market / gold_18_theoretical) - 1) * 100`

Important: The USD implied-value equation and theoretical-gold equation
are algebraic inversions of the same relationship. They MUST NOT be
treated as two independent pieces of evidence in a scoring model.

------------------------------------------------------------------------

# 5. Analytical Layer

The analytical engine should be separated into modules.

## 5.1 Snapshot analysis

For every valid snapshot calculate: - gold-implied USD; - USD gap
percentage; - theoretical 18K gold; - gold gap percentage; - optional
coin metrics.

## 5.2 Historical trend analysis

Once sufficient history exists calculate, at minimum: - 1-day change; -
3-day change; - 7-day change; - optionally 30-day change.

Apply these to: - market USD; - gold-implied USD; - Iranian 18K gold; -
international ounce; - gap/premium; - coin and coin premium where
available.

Do not assume "one day" means one database row. Historical lookup should
find the closest valid observation to the target lookback
timestamp/window.

## 5.3 Gap momentum

Determine whether the gap is: - expanding; - contracting; -
approximately stable.

The tolerance must be configurable.

## 5.4 Direction matrix

A useful deterministic classification layer should distinguish
situations such as:

### Case A

-   market USD above implied USD;
-   implied USD falling;
-   gap expanding.

Interpretation:
`Elevated correction risk / stretched USD relative to gold-implied rate.`

### Case B

-   market USD above implied USD;
-   implied USD rising;
-   gap contracting.

Interpretation:
`USD is above implied value, but implied value is catching up.`

### Case C

-   market USD below implied USD;
-   implied USD rising.

Interpretation:
`Potential relative undervaluation of USD within this model.`

### Case D

-   USD rising;
-   global ounce rising;
-   Iranian gold lagging theoretical gold.

Interpretation: `Potential relative lag in domestic gold.`

All wording must explicitly avoid guarantees.

------------------------------------------------------------------------

# 6. Signal Architecture

Create a `Signal` object rather than returning arbitrary strings.

Suggested fields:

``` text
signal_id
instrument
classification
severity
confidence
summary_fa
reason_codes[]
metrics_used{}
generated_at
model_version
```

Initial classifications may be:

``` text
UNDERVALUED
SLIGHTLY_UNDERVALUED
NEUTRAL
SLIGHTLY_EXPENSIVE
EXPENSIVE
STRETCHED
INSUFFICIENT_DATA
DATA_QUALITY_WARNING
```

However, V1 should use conservative labels until historical calibration
exists.

Every signal MUST retain machine-readable `reason_codes`, for example:

``` text
USD_ABOVE_GOLD_IMPLIED
IMPLIED_USD_RISING
GAP_CONTRACTING
XAU_RISING
DOMESTIC_GOLD_LAGGING
STALE_SOURCE
```

This allows Telegram, future HTML widgets, APIs, and alerts to render
the same analysis differently.

------------------------------------------------------------------------

# 7. Threshold Strategy

Thresholds must live in configuration, not source code.

Example:

``` yaml
analysis:
  gap_neutral_band_pct: 1.0
  gap_expansion_tolerance_pct: 0.25
  stale_after_minutes:
    usd: 20
    gold_18k: 20
    xau_usd: 30
    coin: 20
```

These values are examples only and MUST be marked provisional.

Future calibrated thresholds should be generated from: - historical
percentiles; - rolling z-scores; - volatility regimes; - forward-return
backtests.

The system should preserve the threshold/model version used for every
published report.

------------------------------------------------------------------------

# 8. Data Acquisition Architecture

Create a provider interface.

Conceptually:

``` text
MarketDataProvider
    fetch_quote(symbol)
    fetch_quotes(symbols)
    health_check()
```

Implement providers separately:

``` text
providers/
    base.py
    tgju.py
    xau_provider.py
    fallback_provider.py
```

The analytical engine must only receive normalized `Quote` objects.

## 8.1 Provider priority

Configuration should support:

``` yaml
providers:
  usd:
    primary: provider_a
    fallback: provider_b
  gold_18k:
    primary: provider_a
    fallback: provider_b
  xau_usd:
    primary: provider_a
    fallback: provider_c
```

## 8.2 API preferred; scraping isolated

Prefer documented APIs when practical.

If HTML scraping is required: - isolate it inside the provider
adapter; - respect applicable site terms and rate limits; - set a clear
user-agent; - use short timeouts; - retry only transient errors; -
detect parser failure; - never allow page-layout changes to silently
produce a numeric price.

## 8.3 Cross-source sanity check

Future-ready option: Fetch important prices from two independent sources
and flag abnormal divergence.

Do not average contradictory providers automatically without a defined
policy.

------------------------------------------------------------------------

# 9. Validation Pipeline

Every fetched quote passes through:

``` text
FETCH
  ↓
PARSE
  ↓
NORMALIZE UNIT
  ↓
VALIDATE
  ↓
QUALITY CHECK
  ↓
STORE RAW/NORMALIZED SNAPSHOT
  ↓
ANALYZE
```

Validation should include: - numeric and positive; - expected unit; -
timestamp plausible; - not stale; - not absurdly different from recent
observation; - source response structurally valid; - all mandatory
instruments available within an acceptable time window.

If mandatory data fails validation: - store the failure event; - do not
publish a normal report; - optionally send an admin-only warning.

------------------------------------------------------------------------

# 10. Database

## 10.1 V1

Use SQLite.

Reasons: - no database server; - reliable for a small single-service
workload; - easy backup; - easy inspection; - migration path to
PostgreSQL later.

## 10.2 Required tables

### `instruments`

``` text
id
symbol
name_fa
asset_class
canonical_unit
active
metadata_json
```

### `quotes`

``` text
id
instrument_id
provider
provider_symbol
raw_value
normalized_value
currency
unit
source_timestamp
retrieved_at
quality_status
raw_payload_hash
metadata_json
```

### `snapshots`

Groups contemporaneous quotes.

``` text
id
snapshot_at
status
created_at
```

### `snapshot_quotes`

``` text
snapshot_id
quote_id
```

### `metrics`

``` text
id
snapshot_id
metric_name
metric_value
unit
model_version
created_at
```

### `signals`

``` text
id
snapshot_id
instrument
classification
severity
confidence
reason_codes_json
model_version
created_at
```

### `reports`

``` text
id
snapshot_id
report_type
content
channel
generated_at
sent_at
delivery_status
telegram_message_id
model_version
```

### `job_runs`

``` text
id
job_name
started_at
finished_at
status
error_type
error_message
metadata_json
```

### `configuration_audit`

Optional but recommended later for tracking threshold/model changes.

------------------------------------------------------------------------

# 11. Database Migration Strategy

Use a migration mechanism from the beginning, even if SQLite is used.

Never make schema changes manually in production.

Repository should contain:

``` text
migrations/
```

Future migration target: - PostgreSQL when concurrency, web users, or
larger analytics justify it.

The domain/repository layer should minimize SQLite-specific assumptions.

------------------------------------------------------------------------

# 12. Scheduling

Two supported modes:

## Mode A --- OS scheduler

For a simple Linux VPS: - cron/systemd timer starts a single report
command at configured times.

This is operationally simple.

## Mode B --- Application scheduler

Use APScheduler when: - multiple schedules are required; - schedules
should be configurable inside the app; - alert jobs and reporting jobs
differ; - future dashboard/admin controls will manage schedules.

Schedule MUST use explicit timezone `Asia/Tehran`.

Example configuration:

``` yaml
schedule:
  timezone: Asia/Tehran
  reports:
    - "09:00"
    - "13:00"
    - "17:00"
    - "21:00"
```

Do not embed these times in code.

------------------------------------------------------------------------

# 13. Telegram Integration

Create a Telegram bot through BotFather and configure the destination
channel.

Required secrets: - `TELEGRAM_BOT_TOKEN` - `TELEGRAM_CHANNEL_ID`

The bot must have permission to post to the channel.

Create:

``` text
publishers/
    base.py
    telegram.py
```

Generic publisher contract:

``` text
Publisher
    publish(report)
```

This is important: Telegram is only the first presentation surface.

Future publishers can include: - web dashboard; - email; - Discord; -
Slack; - push notification; - REST webhook; - archive file.

## 13.1 Telegram delivery requirements

-   support Persian/Unicode;
-   use one consistent Telegram parse mode;
-   escape markup correctly;
-   disable unwanted link previews;
-   capture Telegram message ID;
-   retry transient network/server failures;
-   avoid duplicate publication;
-   log permanent failures.

------------------------------------------------------------------------

# 14. Idempotency / Duplicate Prevention

A scheduled job may be invoked twice after restart or scheduler error.

Create a unique report key, for example:

`report_type + scheduled_slot + model_version`

Before sending: 1. check whether this report key has already been
successfully delivered; 2. if yes, do not send again; 3. if no, proceed;
4. record Telegram message ID after success.

------------------------------------------------------------------------

# 15. Telegram Report Format

V1 should remain compact.

Example:

``` text
📊 گزارش بازار
20 مرداد 1405 | 13:00

💵 دلار آزاد
بازار: 185,400 تومان
ضمنی طلا: 181,200 تومان
فاصله: +2.32%

روند ضمنی:
1D +0.4% | 3D +1.7% | 7D +4.1%

ارزیابی:
دلار بالاتر از نرخ ضمنی طلاست،
اما نرخ ضمنی صعودی و فاصله در حال کاهش است.

وضعیت: نسبتاً گران، بدون سیگنال قوی اصلاح

🥇 طلای ۱۸ عیار
بازار: 19,150,000 تومان
نظری: 19,590,000 تومان
فاصله: -2.25%

اونس: 4,382 USD ↑
دلار: 185,400 ↑

وضعیت: پایین‌تر از ارزش نظری این مدل

🪙 سکه
قیمت: ...
حباب/فاصله: ...
وضعیت: ...

آخرین داده: 13:00
مدل: v1.x
```

The formatter must be separate from analysis. Never calculate inside the
Telegram template.

------------------------------------------------------------------------

# 16. Report Types

Architecture should support multiple report types:

### `scheduled_summary`

Regular scheduled report.

### `movement_alert`

Future: triggered by unusual market movement.

### `gap_alert`

Future: gap exceeds calibrated historical threshold.

### `data_warning`

Admin warning only.

### `daily_close`

Future daily archival summary.

### `weekly_review`

Future statistical weekly review.

Each report is a renderer consuming the same analytical output.

------------------------------------------------------------------------

# 17. Suggested Repository Structure

``` text
iran-market-monitor/
│
├── README.md
├── ARCHITECTURE.md              # THIS backbone, maintained as source of truth
├── EXTENSIONS.md                # future ideas/proposals; mandatory
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── .env.example
├── .gitignore
├── pyproject.toml
├── requirements.lock            # or equivalent reproducible lock file
├── Makefile                     # optional convenience commands
│
├── config/
│   └── default.toml            # v1.1: TOML, read by stdlib tomllib
│
├── src/
│   └── market_monitor/
│       ├── __init__.py
│       ├── cli.py
│       ├── settings.py
│       │
│       ├── domain/
│       │   ├── models.py
│       │   ├── constants.py
│       │   └── enums.py
│       │
│       ├── providers/
│       │   ├── base.py
│       │   ├── tgju.py
│       │   └── fallback.py
│       │
│       ├── normalization/
│       │   ├── units.py
│       │   └── validators.py
│       │
│       ├── analysis/
│       │   ├── dollar.py
│       │   ├── gold.py
│       │   ├── coin.py
│       │   ├── trends.py
│       │   ├── gaps.py
│       │   └── signals.py
│       │
│       ├── storage/
│       │   ├── database.py
│       │   ├── repositories.py
│       │   └── migrations.py
│       │
│       ├── reporting/
│       │   ├── models.py
│       │   ├── formatter_fa.py
│       │   └── templates/
│       │
│       ├── publishers/
│       │   ├── base.py
│       │   └── telegram.py
│       │
│       ├── jobs/
│       │   ├── collect.py
│       │   ├── report.py
│       │   ├── alerts.py
│       │   └── health.py
│       │
│       └── observability/
│           ├── logging.py
│           └── health.py
│
├── migrations/
│
├── data/
│   └── .gitkeep
│
├── tests/
│   ├── unit/
│   │   ├── test_dollar.py
│   │   ├── test_gold.py
│   │   ├── test_trends.py
│   │   ├── test_units.py
│   │   └── test_signals.py
│   ├── integration/
│   │   ├── test_provider.py
│   │   ├── test_database.py
│   │   └── test_telegram.py
│   └── fixtures/
│
├── scripts/
│   ├── bootstrap.sh
│   ├── backup_db.sh
│   └── import_history.py
│
├── deploy/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── systemd/
│   └── cron/
│
└── docs/
    ├── DATA_MODEL.md
    ├── FORMULAS.md
    ├── PROVIDERS.md
    ├── OPERATIONS.md
    ├── BACKTESTING.md
    └── API_FUTURE.md
```

------------------------------------------------------------------------

# 18. Mandatory `EXTENSIONS.md`

The repository MUST contain an `EXTENSIONS.md`.

Purpose: - parking lot for future ideas; - prevent premature feature
creep; - give future coding agents a clear map of intended extensions; -
distinguish committed architecture from speculative ideas.

Every extension entry should use:

``` markdown
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

Agents MUST NOT automatically implement an `IDEA` merely because it
appears in `EXTENSIONS.md`. Implementation requires promotion to
`APPROVED`.

------------------------------------------------------------------------

# 19. Initial Entries for `EXTENSIONS.md`

Seed it with at least:

## A. Web Dashboard

A lightweight responsive HTML interface consuming the same
metrics/report API.

## B. Widget Architecture

Each market component becomes an independent widget: - USD Market; -
Gold-Implied USD; - USD Gap; - 18K Gold; - Theoretical Gold; - Gold
Gap; - XAU/USD; - Coin; - Coin Bubble; - USDT; - AED; - trend chart; -
alert status; - data freshness.

Widgets should consume structured JSON, not parse Telegram text.

## C. Existing personal site integration

Future ability to add these widgets to an existing simple site such as
**zorgoros.x** (or another domain/front end selected later).

The core service must therefore be capable of later exposing data via a
read-only API without coupling calculation logic to the website.

Possible future shape:

``` text
Market Monitor Core
       ↓
REST/JSON API
       ↓
┌─────────────┬──────────────┬─────────────┐
Telegram      HTML Widgets   Other Clients
```

## D. REST API

Potential endpoints:

``` text
GET /api/v1/latest
GET /api/v1/quotes
GET /api/v1/metrics
GET /api/v1/signals
GET /api/v1/history
GET /api/v1/health
```

## E. Interactive charts

Historical: - USD market vs gold-implied USD; - gold market vs
theoretical gold; - gap over time; - z-score; - coin bubble; - XAU/USD.

## F. Historical backtesting engine

Test whether gap regimes predict 1D/3D/7D/14D/30D forward returns.

## G. Statistical thresholds

Percentiles, z-scores, volatility-adjusted bands.

## H. Regime detection

Trend/volatility/risk regimes.

## I. Abnormal-movement alerts

Event-driven alerts independent from scheduled reports.

## J. Multiple data sources / consensus

Provider cross-validation and failover.

## K. Additional markets

USDT/IRT, AED/IRT, EUR/IRT, Brent, Bitcoin, silver, etc.

## L. Optional AI commentary

LLM receives already-calculated structured metrics and may summarize
them. It must not become the numerical source of truth.

## M. User authentication

Only if a private dashboard/admin console is eventually required.

## N. Mobile/PWA

Potential installable dashboard.

------------------------------------------------------------------------

# 20. Future Widget Contract

Design now so future HTML widgets receive a stable object such as:

``` json
{
  "instrument": "USD_IRT",
  "market_value": 185400,
  "implied_value": 181200,
  "gap_pct": 2.32,
  "trends": {
    "1d": 0.4,
    "3d": 1.7,
    "7d": 4.1
  },
  "signal": {
    "classification": "SLIGHTLY_EXPENSIVE",
    "reason_codes": [
      "USD_ABOVE_GOLD_IMPLIED",
      "IMPLIED_USD_RISING",
      "GAP_CONTRACTING"
    ]
  },
  "data_quality": "OK",
  "as_of": "..."
}
```

The exact public API may evolve, but domain output should already be
serializable.

------------------------------------------------------------------------

# 21. Configuration

Use environment variables only for secrets/deployment-specific values.

`.env.example`:

``` text
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHANNEL_ID=
PRIMARY_MARKET_API_KEY=
FALLBACK_MARKET_API_KEY=
DATABASE_URL=sqlite:///data/market.db
APP_ENV=development
LOG_LEVEL=INFO
```

Non-secret behavior belongs in YAML/TOML configuration: - report
times; - timezone; - provider priority; - stale-data limits; -
thresholds; - enabled instruments; - enabled reports; - alert policies.

Never commit `.env`.

------------------------------------------------------------------------

# 22. Security

Minimum requirements: - secrets only via environment/secret manager; -
`.env` ignored by Git; - no token in logs; - no raw API credentials in
exception traces; - Telegram token rotation documented; - dependency
versions locked; - input/provider responses treated as untrusted; - no
arbitrary code execution; - dashboard/API later read-only by default; -
admin endpoints, if ever added, require authentication.

------------------------------------------------------------------------

# 23. Logging and Observability

Use structured logs.

Every scheduled run should log: - run ID; - job; - start/end; - provider
calls; - fetch latency; - quote validation; - snapshot ID; - analysis
version; - report ID; - Telegram delivery result; - error category.

Never log secrets.

Recommended future metrics: - provider availability; - stale quote
count; - report success rate; - job duration; - last successful
snapshot; - last successful Telegram publication.

------------------------------------------------------------------------

# 24. Error Handling

Classify errors:

``` text
ProviderUnavailable
ProviderParseError
AuthenticationError
RateLimitError
InvalidQuote
StaleQuote
UnitNormalizationError
InsufficientSnapshot
DatabaseError
AnalysisError
ReportRenderError
TelegramDeliveryError
ConfigurationError
```

Policy: - transient network errors: limited exponential retry; - invalid
numeric data: no retry loop; reject; - stale data: mark quality issue; -
mandatory quote unavailable: no normal market report; - Telegram
failure: retry delivery without refetching/recalculating if report
already exists; - persistent failures: admin alert/log.

------------------------------------------------------------------------

# 25. Data Freshness

Every report should know: - when each market value was observed; - when
it was retrieved; - age at report generation.

A snapshot should only combine quotes within a configurable temporal
tolerance.

This is particularly important when the Iranian market and international
gold have different trading hours.

When XAU is closed: - do not pretend it is live; - label it with its
timestamp/market state; - optionally still calculate using the latest
available ounce, but mark the report accordingly.

------------------------------------------------------------------------

# 26. Persian Calendar and Formatting

Store ISO/Gregorian timezone-aware timestamps internally.

Convert to Persian/Jalali only in presentation.

Do not store Jalali dates as the primary database timestamp.

Formatting helpers should handle: - Persian report date; - thousands
separators; - percentage signs; - positive/negative arrows; - toman
labels; - decimal precision.

------------------------------------------------------------------------

# 27. Testing Requirements

## 27.1 Unit tests

Mandatory for: - ounce/gram conversion; - 18K purity conversion; -
implied USD; - theoretical gold; - gap percentage; - unit
normalization; - IRR/toman conversion; - trend lookup; - gap momentum; -
signal reason codes; - stale-data logic.

## 27.2 Golden test vectors

Create fixed known inputs and expected outputs.

Example:

``` text
gold18 = X
xau = Y
usd = Z
expected implied USD = ...
expected theoretical gold = ...
```

Use high-precision arithmetic/tolerances.

## 27.3 Integration tests

-   provider fixture → normalized quote;
-   quotes → DB;
-   DB → analysis;
-   analysis → Persian report;
-   Telegram client mocked in CI.

## 27.4 Failure tests

Test: - provider timeout; - malformed HTML/JSON; - zero price; -
negative price; - missing instrument; - stale XAU; - duplicate scheduler
run; - Telegram 429/5xx; - DB locked/error.

------------------------------------------------------------------------

# 28. Backtesting Architecture

Do not mix backtesting into live execution.

Future module:

``` text
backtesting/
    datasets.py
    forward_returns.py
    regimes.py
    thresholds.py
    evaluation.py
```

For each historical timestamp: 1. reconstruct only information available
at that time; 2. calculate signal; 3. calculate future return at
horizons; 4. avoid look-ahead bias; 5. report sample size; 6. evaluate
hit rate and return distribution; 7. compare against baseline.

Potential horizons: - 1 day; - 3 days; - 7 days; - 14 days; - 30 days.

Potential metrics: - conditional forward return; - median; - mean; - win
rate; - drawdown; - confidence intervals; - false-positive rate.

------------------------------------------------------------------------

# 29. Model Versioning

Every analytical change must increment a model version.

Example:

``` text
formula_version = "1.0"
signal_model_version = "1.0"
report_template_version = "1.0"
```

Published reports should retain the relevant version in the DB.

This enables historical reproducibility after formulas or thresholds
change.

------------------------------------------------------------------------

# 30. CLI

Provide a CLI so an agent/operator can test each stage independently.

Suggested commands:

``` text
market-monitor fetch
market-monitor analyze
market-monitor report --dry-run
market-monitor publish
market-monitor run-once
market-monitor health
market-monitor backfill
market-monitor db-info
```

`run-once` should execute the entire pipeline once.

`report --dry-run` must never send to Telegram.

------------------------------------------------------------------------

# 31. Deployment

V1 preferred deployment: - small Linux VPS; - Docker optional but
recommended; - persistent volume for SQLite; - automatic restart; -
timezone explicitly configured; - scheduled DB backup.

Alternative: - native Python virtual environment + systemd.

Do not require Kubernetes/serverless architecture for V1.

------------------------------------------------------------------------

# 32. Backup and Recovery

At minimum: - daily SQLite backup; - retention policy; - backup outside
the live DB directory; - documented restore command; - occasional
restore test.

Future: - remote encrypted backup; - PostgreSQL managed backups.

Raw historical data is strategically valuable and should be preserved.

------------------------------------------------------------------------

# 33. CI/CD

GitHub Actions or equivalent should run on pull request:

``` text
lint
format-check
type-check
unit-tests
integration-tests
security/dependency checks
```

Deployment should occur only after tests pass.

Production secrets must never be available to untrusted pull-request
jobs.

------------------------------------------------------------------------

# 34. Documentation Requirements

## `README.md`

Short: - what project does; - quick start; - commands; - deployment
overview.

## `ARCHITECTURE.md`

Canonical architectural decisions and system boundaries.

## `FORMULAS.md`

Every formula, constant, unit, interpretation, limitation, and version.

## `PROVIDERS.md`

Source mappings, units, fallbacks, limitations.

## `OPERATIONS.md`

Deployment, backup, restore, scheduler, troubleshooting.

## `BACKTESTING.md`

Methodology and anti-look-ahead rules.

## `EXTENSIONS.md`

Future proposals/ideas.

Agents should update documentation whenever architecture changes.

------------------------------------------------------------------------

# 35. Agent Builder Instructions

The implementation agent should follow this order.

## Phase 0 --- Repository bootstrap

Create: - project structure; - environment configuration; - test
framework; - lint/type configuration; - docs skeleton; -
`EXTENSIONS.md`.

## Phase 1 --- Domain and formulas

Implement: - constants; - domain models; - units; - exact formulas; -
unit tests.

No networking yet.

## Phase 2 --- Persistence

Implement: - SQLite; - migrations; - repositories; - snapshot
persistence; - tests.

## Phase 3 --- Provider adapter

Implement one real provider plus fixtures.

The provider must return normalized domain objects.

## Phase 4 --- Analysis

Implement: - implied USD; - theoretical gold; - gaps; - trends; - gap
momentum; - conservative signals.

## Phase 5 --- Reporting

Implement Persian formatter and dry-run CLI.

## Phase 6 --- Telegram

Implement Telegram publisher, idempotency, retries, delivery logging.

## Phase 7 --- Scheduler

Implement configurable schedules.

## Phase 8 --- Operations

Docker/systemd, backup, health command, structured logs.

## Phase 9 --- Acceptance test

Run full pipeline using real data without publishing. Then publish one
explicitly controlled test message.

Only after that enable recurring production publication.

------------------------------------------------------------------------

# 36. Definition of Done --- V1

V1 is complete only when:

-   [ ] Prices for mandatory instruments can be retrieved.
-   [ ] Units are normalized and validated.
-   [ ] Raw observations are stored.
-   [ ] Snapshots are reproducible.
-   [ ] Gold-implied USD is calculated correctly.
-   [ ] USD gap is calculated correctly.
-   [ ] Theoretical 18K gold is calculated correctly.
-   [ ] Gold gap is calculated correctly.
-   [ ] Historical trends work when data exists.
-   [ ] Insufficient history is handled explicitly.
-   [ ] Gap direction is calculated.
-   [ ] Signal output contains reason codes.
-   [ ] Persian report renders correctly.
-   [ ] Dry-run works.
-   [ ] Telegram publication works.
-   [ ] Duplicate reports are prevented.
-   [ ] Provider/Telegram failures are logged safely.
-   [ ] Scheduler uses Tehran timezone.
-   [ ] SQLite backup is documented/tested.
-   [ ] Unit/integration tests pass.
-   [ ] `.env.example` exists.
-   [ ] No secrets are committed.
-   [ ] `ARCHITECTURE.md` exists.
-   [ ] `FORMULAS.md` exists.
-   [ ] `EXTENSIONS.md` exists and is seeded.
-   [ ] README contains reproducible setup instructions.

------------------------------------------------------------------------

# 37. Explicit V1 Non-Goals

Do NOT expand V1 into: - automated trading; - portfolio management; -
investment advice; - ML price prediction; - LLM-dependent analysis; -
complex React dashboard; - multi-user authentication; - microservices; -
Kubernetes; - high-frequency data ingestion.

These belong in future extensions only if justified.

------------------------------------------------------------------------

# 38. Future Target Architecture

The system should be able to evolve toward:

``` text
                         ┌──────────────────┐
                         │ Data Providers   │
                         └────────┬─────────┘
                                  ↓
                         ┌──────────────────┐
                         │ Ingestion Layer  │
                         └────────┬─────────┘
                                  ↓
                         ┌──────────────────┐
                         │ Normalized Store │
                         └────────┬─────────┘
                                  ↓
                    ┌─────────────┴─────────────┐
                    ↓                           ↓
             ┌─────────────┐             ┌─────────────┐
             │ Live Engine │             │ Backtesting │
             └──────┬──────┘             └─────────────┘
                    ↓
             ┌─────────────┐
             │ Metrics &   │
             │ Signals     │
             └──────┬──────┘
                    ↓
             ┌─────────────┐
             │ Read API    │
             └──────┬──────┘
                    │
       ┌────────────┼────────────┬─────────────┐
       ↓            ↓            ↓             ↓
   Telegram     HTML Widgets   zorgoros.x   Other Clients
```

V1 does not need the API box yet. It needs domain outputs clean enough
that the API can later be inserted without changing calculations.

------------------------------------------------------------------------

# 39. Architectural Decisions to Keep Open

The following MUST remain replaceable:

  Concern        V1                      Future option
  -------------- ----------------------- --------------------------
  Storage        SQLite                  PostgreSQL/Timescale
  Scheduling     cron/APScheduler        task queue
  Provider       initial market source   multiple providers
  Output         Telegram                API/web/email/etc.
  Front end      none                    widget dashboard
  Hosting        small VPS               cloud/container platform
  Signals        rules                   calibrated/statistical
  Commentary     deterministic text      optional LLM
  Data cadence   scheduled               event/stream based

------------------------------------------------------------------------

# 40. Economic Interpretation Guardrails

Reports must not call the gold-implied USD an objectively proven
"intrinsic value."

Preferred terminology: - `نرخ ضمنی دلار از بازار طلا` -
`Gold-Implied USD`

For theoretical gold: - `ارزش نظری بر اساس اونس و دلار` - not guaranteed
fair value.

Every report is an analytical indicator, not a certainty.

The system should be capable of displaying a short disclaimer such as:

`این گزارش یک شاخص تحلیلی مبتنی بر روابط قیمت است و توصیه خرید یا فروش نیست.`

------------------------------------------------------------------------

# 41. Initial Technical Stack

Recommended V1: - Python 3.12+; - standard `sqlite3` or a lightweight
repository/ORM layer; - `httpx` or `requests` for HTTP; -
`pydantic`/dataclasses for validated domain objects; - `python-dotenv`
or settings library for local development; - APScheduler only if
application-level scheduling is selected; - pytest; - Ruff; -
mypy/pyright; - Docker optional but recommended.

Keep dependency count small.

------------------------------------------------------------------------

# 42. Source/Dependency Verification Before Implementation

The builder MUST verify the currently supported API/interface of every
selected provider before coding against it. Do not assume that a
previously documented endpoint still exists.

Authoritative implementation references should be preferred: - Telegram
Bot API documentation for message publication; - official Python
documentation for runtime/SQLite behavior; - official APScheduler
documentation if APScheduler is used; - official/documented market-data
provider interface where available.

Provider-specific credentials, quotas, pricing, symbols, and terms must
be documented in `PROVIDERS.md` after verification.

------------------------------------------------------------------------

# 43. Final Builder Directive

Build the smallest reliable version that satisfies V1, but preserve the
boundaries described above.

Do not "improve" the architecture by prematurely adding speculative
infrastructure.

When implementation choices are uncertain: 1. preserve raw data; 2.
preserve units and provenance; 3. preserve deterministic formulas; 4.
preserve modular provider/publisher interfaces; 5. preserve serializable
analytical output; 6. document the decision; 7. put nonessential ideas
into `EXTENSIONS.md`.

`ARCHITECTURE.md` is the backbone. `EXTENSIONS.md` is the controlled
expansion space. The implementation must remain compatible with a future
widget-based web surface, including integration into a simple existing
site such as `zorgoros.x`.
