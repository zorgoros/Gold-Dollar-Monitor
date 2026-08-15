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
| A. Web dashboard | MEDIUM | **Promoted for active work** — first read-only RTL dashboard over the same metrics API; see `docs/superpowers/specs/2026-08-15-first-dashboard-design.md` |
| B. Widget architecture | MEDIUM | One widget per component, consuming structured JSON, never parsed Telegram text |
| C. Personal-site integration | LOW | Embed widgets in an existing simple site (e.g. `zorgoros.x`) |
| D. REST API | MEDIUM | Read-only `/latest`, `/quotes`, `/metrics`, `/signals`, `/history`, `/health` |
| E. Interactive charts | LOW | Market vs implied, gap over time, z-score, coin bubble |
| F. Backtesting engine | HIGH | Do gap regimes predict 1/3/7/14/30-day forward returns; strictly offline |
| G. Statistical thresholds | HIGH | Replace provisional bands with percentiles, z-scores, volatility bands |
| H. Regime detection | LOW | Trend, volatility, and risk regimes |
| I. Abnormal-movement alerts | MEDIUM | Event-driven, independent of the scheduled report |
| J. Multi-source consensus | MEDIUM | Cross-validate two providers, flag divergence, defined failover policy |
| K. Additional markets | MEDIUM | ~~AED/IRT, EUR/IRT~~ **shipped in v1.1** (plus TRY, JPY). Remaining: USDT/IRT (see O), silver, Brent, BTC |
| L. Optional AI commentary | LOW | LLM summarises already-computed metrics; never the numeric source of truth — full entry below |
| M. Authentication | LOW | Only if a private dashboard or admin console appears |
| N. Mobile/PWA | LOW | Installable dashboard |
| O. USDT analytical reference | MEDIUM | A third implied-USD route, from a market that never closes — full entry below |
| P. Composite USD reference | LOW | Blending the implied rates into one number, *after* the research in R proves a weighting — full entry below |
| Q. Coin premium against domestic gold | MEDIUM | ~~The premium inherits the USD/gold gap~~ **shipped in v1.2** — full entry below |
| R. Cross-market lead/lag research | HIGH | Which implied rate moves first, and whether divergence predicts anything — full entry below |
| S. Statistical divergence thresholds | HIGH | Percentiles and z-scores per gap series, replacing the provisional bands (extends G to the AED gap) |
| T. Volatility-regime analysis | LOW | Whether gap behaviour differs by regime; a precondition for trusting any threshold |
| U. Telegram group and bot discovery | LOW | Bot usable in groups, `/start` deep links from a forwarded footer, an inline query surface |
| V. Admin/config dashboard | LOW | A UI over `config/default.toml`; today the file plus `market-monitor config` is the whole surface |
| W. Cross-rate research on stored FX | MEDIUM | EUR/TRY/JPY are collected and stored but nothing reads them — full entry below |
| X. Tala.ir / GoldPrice market-rate integration | MEDIUM | A second AED source; test whether its rate x the USD/AED peg tracks the real Iranian market floor — full entry below |
| Y. Telegram dashboard mode | MEDIUM | A few persistent messages edited in place instead of an endless feed — full entry below |
| Z. Configurable publishing modes | MEDIUM | Feed / dashboard / hybrid, chosen per destination; routing only, not the dashboard itself — full entry below |
| AA. Configurable historical archive policy | MEDIUM | REQUIRED / ENABLED / DISABLED per series; not displaying must never mean not storing — full entry below |
| AB. On-demand historical reports | LOW | Ask the bot for history the chat no longer shows, served from the database — full entry below |
| AC. Per-destination configuration | MEDIUM | Every group/channel keeps its own settings, admin-gated — full entry below |
| AD. Personal chat mode | LOW | Private 1:1 use with a deliberately smaller feature set than a channel — full entry below |
| AE. Configurable refresh and update-on-change engine | MEDIUM | Fetch on an interval, publish only on meaningful change or max age — full entry below |
| AF. Premium update frequencies and feature entitlements | LOW | Research only: plans, quotas, payment rails; no pricing invented yet — full entry below |
| AG. Deterministic analysis state machine | HIGH | Metrics → state → approved Persian text, versioned and backtested, no LLM — full entry below |

`F` and `G` are the pair that matters: until they land, every threshold in
`config/default.toml` is a guess and reports must keep saying so. `R` is now
their equal in importance — without it there is no basis for `P`. `AG` is HIGH
for the same reason and sits downstream of all three: a state taxonomy built on
provisional thresholds is a pile of confident claims resting on guesses.

`Y` through `AF` are the product/delivery family — how and to whom the engine
publishes. They form one dependency chain: `AC` (a destination registry) is the
root, `Y` and `AE` are the mechanism, `Z` routes between them, and `AA`, `AB`,
`AD`, `AF` hang off those. None of them changes a number.

---

## Extension: USDT analytical reference

Status: IDEA
Priority: MEDIUM
Target version: —
Dependencies: a working USDT/IRT source (TGJU's `usdt-irr` is **dead** — last
tick 2020-11-11, see `docs/PROVIDERS.md`), and R for interpretation
Core changes required: one instrument, one provider adapter, one formula
(`usdt_implied_usd`), one metric pair. The v1.1 AED work is the template — the
analytical layer already carries more than one implied rate without blending.
Backward compatibility: additive; nothing existing changes

Description: treat USDT/IRT as a third route to an implied USD/toman rate,
alongside gold and the dirham.

Why it may be useful:
- **It never closes.** Gold and the rial FX market are shut most of the day and
  all weekend, which is exactly when v1.1 withholds the analysis. A 24/7 series
  could carry information across precisely the gap the current gate refuses to
  guess across.
- Holiday and weekend price discovery when nothing else prints.
- Shock response: crypto rails typically reprice first on a sanctions or
  political event.
- A third independent reference makes "two of three agree" a meaningful
  statement, where two sources can only agree or disagree.

Open questions — all of which must be answered before it is trusted:
- **The USDT premium.** USDT/IRT embeds a stablecoin premium or discount that
  is itself a risk indicator. Is the implied rate measuring the toman, or
  measuring demand for offshore settlement?
- **Exchange-specific liquidity.** Which venue, and does its book support the
  quoted price? A thin book quotes a price nobody can trade.
- **Crypto-market distortions.** USDT's own peg has broken before; a
  de-pegging event would corrupt the implied rate exactly when it is most
  consulted.
- **Access constraints.** Local exchange access is legally and technically
  unstable; a source that vanishes mid-series poisons a backtest.
- Does a 24/7 series even *help*, or does it mostly add noise between sessions?

Acceptance criteria: a live source verified per the `docs/PROVIDERS.md`
standard; premium behaviour characterised over ≥6 months of history; R shows it
adds information the other two do not.

---

## Extension: Composite USD reference

Status: IDEA
Priority: LOW
Target version: not before R completes
Dependencies: R (mandatory), S, ideally O
Core changes required: one formula and one metric; the reporting layer already
renders whatever the analysis emits
Backward compatibility: additive — and the component rates must remain visible
alongside it, never replaced by it

Description: a single USD reference blending the gold-implied, AED-implied and
(if it lands) USDT-implied rates.

**Explicitly not built in v1.1, and not to be built on judgement.** Averaging
them — 50/50 or any other split — asserts known relative reliability, and
nothing establishes that. The v1.1 report shows the rates side by side for that
reason.

Required research pipeline, in order:

```
gold-implied · AED-implied · USDT-implied · market USD
        ↓  historical lead/lag analysis
        ↓  error distribution per source
        ↓  forward-return backtesting
        ↓  regime testing
        ↓  validated weighting
   Composite USD Reference
```

Open questions: is the correct weighting static or regime-dependent? Does a
composite beat simply reporting the *most divergent* source? What happens to it
when one input's source dies mid-series?

Acceptance criteria: a weighting derived from out-of-sample data, an error
distribution published with sample sizes per `docs/BACKTESTING.md`, and a
demonstration that the composite outperforms each component *and* the naive
baseline. Failing any of these, the extension is rejected, not shipped with a
caveat.

---

## Extension: Coin premium against domestic gold

Status: **DONE** (v1.2, 2026-08-13)
Priority: MEDIUM
Target version: 1.2
Dependencies: none technically; it was an economic decision
Core changes required: `gold_24k` instrument, `pure_gold_toman_per_gram` and
`emami_coin_intrinsic_domestic` formulas, two new metric names, migration 003
Backward compatibility: additive. `coin_premium_pct` and `coin_intrinsic` were
**retired, not redefined** — rows carrying them are model version 1.1 or earlier
and keep their original meaning

Description: `coin_intrinsic` valued the coin's gold through `xau_usd ×
usd_market`, i.e. through the theoretical domestic gold price, and therefore
inherited `gold_gap_pct` in full. The published premium is now measured against
`geram24`, TGJU's direct domestic pure-gold quote, with `geram18 / 0.75` as an
equivalent fallback.

Resolution of the open questions:

- **Which denominator** — `geram24`, because it is direct. It is *derived* from
  `geram18` (they agree to 0.0007%), so the fallback is equivalent rather than
  degraded; the preference buys one fewer assumption, not more accuracy.
- **Publish both?** No. The world route is computed and stored as
  `coin_premium_world_pct` but never rendered — printed beside the gold section
  it restates `gold_gap_pct`, which is the defect that prompted the change.
- **Comparability** — handled by retiring the old names and bumping
  `model_version` to 1.2, not by a parallel transition series. `docs/BACKTESTING.md`
  states the filter rule for anyone reading across the boundary.

Acceptance criteria, all met: the economic meaning is recorded in
`docs/FORMULAS.md` together with a cross-check against TGJU's own `sekee_real`
(agreement to 0.001%, which also independently validates the coin constants);
new metric names; model version bumped; the old series left intact.

Follow-on, not committed: nothing here reads `gerami_blubber`, `nim_blubber`,
`rob_blubber` or `sekeb_blubber` — TGJU's published bubbles for the other coin
denominations. A multi-coin bubble board would be a display feature, and the
same denominator question would need answering for each coin's own spec.

---

## Extension: Cross-market lead/lag research

Status: IDEA
Priority: HIGH
Target version: —
Dependencies: F (backtesting engine); ≥6 months of stored history
Core changes required: none in the live path — strictly offline, reading the
`metrics` table
Backward compatibility: read-only

Description: characterise the relationship between market USD, gold-implied
USD, AED-implied USD, and any future USDT-implied USD.

Research questions:
- Which series moves first, and by how much?
- Which lags, and is the lag stable?
- Does that ordering change by regime — calm, trending, shock?
- What is each source's error distribution against subsequent market USD?
- What happens when gold and AED **agree**? Does agreement predict anything
  that either alone does not?
- What happens when they **disagree** — does one systematically win?
- Does divergence predict forward USD returns at 1, 3, 7, 14, 30 days?
- Which lag window is most informative?
- Does predictive behaviour survive sanctions or political shocks, or invert?
- Do the stored EUR/TRY/JPY series improve any of the above (see W)?

The v1.1 signal already emits `GOLD_AND_AED_AGREE` / `GOLD_AND_AED_DISAGREE`
reason codes, so the agreement state is being recorded from day one and this
research will have a labelled series to work from.

Acceptance criteria: results reported per the honesty rules in
`docs/BACKTESTING.md` — sample size beside every number, confidence intervals,
comparison against the naive baseline. A finding that cannot survive being
stated with its sample size changes nothing.

---

## Extension: Cross-rate research on stored FX

Status: IDEA
Priority: MEDIUM
Target version: —
Dependencies: ≥6 months of stored history
Core changes required: none in the live path
Backward compatibility: read-only

Description: EUR/TRY/JPY are collected and stored from v1.1 but no calculation
reads them. This is deliberate (§13, §27) — the data is being accumulated now
so the research is possible later.

Research questions: do the domestic cross-rates (EUR/USD, USD/TRY implied from
the Tehran board) deviate from world crosses, and does that spread indicate
capital-control pressure or arbitrage friction? Is the lira informative given
Turkey's role in Iranian trade routing? Does FX correlation structure shift
before rial moves? Can the board's internal consistency serve as a data-quality
check on TGJU itself?

Acceptance criteria: as R.

---

## Extension: Tala.ir / GoldPrice market-rate integration

Status: IDEA
Priority: MEDIUM
Target version: —
Dependencies: a verified live source (per the `docs/PROVIDERS.md` standard);
R for interpretation once a second AED reference exists
Core changes required: one provider adapter, one candidate formula
(`aed_tala_implied_usd` or similar), stored alongside — not blended into —
the existing TGJU-sourced `usd_aed_implied` (§11: no composite)
Backward compatibility: additive; nothing existing changes

Description: investigate Tala.ir / GoldPrice as an additional market-data
source, particularly for its AED quote. The hypothesis: market participants use
`Tala.ir AED rate x USD/AED peg (~3.6725)` as a practical proxy for the
Iranian USD market-floor rate — potentially a cleaner or faster-moving signal
than the TGJU-derived `usd_aed_implied` already shipped in v1.1.

Not the same source as the `goldprice.org` global XAU/USD API already tested
and rejected in `docs/PROVIDERS.md` (403, no browser headers) — that was
evaluated as a world-ounce fallback. This is a distinct Tala.ir/domestic-facing
AED quote and needs its own evaluation from scratch.

Future work, in order:
- Obtain and evaluate the official GoldPrice API rather than scraping the
  webpage — scraping is fragile and against the spirit of §31/§35's insistence
  on verified, documented providers.
- Determine exactly what the AED quote represents: Dubai remittance rate, cash
  AED, an inferred Tehran market rate, bid/ask/last — this changes what the
  number means before any formula touches it.
- Verify update frequency, timestamps, reliability, and historical
  availability, per the `docs/PROVIDERS.md` verification standard.
- Compute `Tala AED x USD/AED peg` as a candidate AED-implied USD /
  market-floor proxy.
- Compare it historically against TGJU `usd_aed_implied`, `usd_gold_implied`,
  and observed real market-floor rates.
- Measure spread, bias, lag, and predictive usefulness — per
  `docs/BACKTESTING.md`, sample size stated beside every number.
- If validated, consider it as an input to a future multi-source consensus
  engine (see J), never as a silent replacement for the TGJU AED series.

Open questions: is Tala.ir's AED quote actually independent of TGJU's, or do
both ultimately trace to the same underlying Dubai exchanges (in which case it
corroborates rather than adds information, the same trap named in R)? Does it
update on weekends/holidays when TGJU's rial board is closed — if so, it may
fill exactly the gap USDT (see O) is meant to fill, and the two ideas should be
evaluated together rather than separately.

Acceptance criteria: a live source verified per `docs/PROVIDERS.md`; the
AED-quote definition confirmed, not assumed; an error/lag distribution against
TGJU's series and real market-floor observations, published with sample sizes;
a finding on whether it adds information R and O do not already cover.

---

## Extension: Telegram dashboard mode

Status: IDEA
Priority: MEDIUM
Target version: —
Dependencies: none hard; Z routes to it, AE decides *when* it fires
Core changes required: a panel registry (panel key → chat, message id, last
rendered state) separate from the per-report `reports` row; `editMessageText`
in `publishers/telegram.py` beside the existing `sendMessage`; a re-create path
when an edit returns "message to edit not found"
Backward compatibility: additive and opt-in. Feed publishing stays the default
and untouched; a destination without a dashboard config behaves exactly as today

Description: a publishing mode in which the bot maintains a small fixed set of
persistent dashboard messages and edits them in place, rather than posting a
new message on every schedule tick. Candidate panels: market price board, ayar
analysis, market chart.

History keeps being written to the database regardless of what the chat shows.
A panel that no longer scrolls the chat is a display decision, never a storage
one — see AA, which states that rule generally.

Deliberately scoped to the dashboard mechanism itself. The choice of *which*
destination uses it belongs to Z; the change-detection that decides whether an
edit is warranted at all belongs to AE.

Why it may be useful: a channel that posts every 15 minutes becomes unreadable
and unfollowable. Three always-current pinned panels are a better fit for a
price board than an infinite feed, and they cost far fewer Telegram API calls
than a post per tick.

Likely prerequisites, per the original note: persistent storage of Telegram
message ids; edit support in the publisher; recovery when a dashboard message
is deleted by an admin; last-rendered-state tracking; data-freshness handling;
conditional update logic.

Open questions: today `reports.telegram_message_id` is stored *per report row*,
which is the right shape for a feed and the wrong shape for a panel that
outlives every individual report — is the panel registry a new table, or a
`report_type + slot`-keyed view over the existing one? What is the idempotency
key for an edit, given the shipped key is
`report_type + scheduled_slot + model_version` and a panel has no slot? Does an
edited panel still carry the gated status line, or does a stale panel need a
visibly different treatment from a stale post — a reader cannot tell an edited
message is old the way a timestamped post makes obvious. What happens to the
panel when the analysis is withheld for data quality: leave the last good
render, or blank it to the status line?

Acceptance criteria: panels survive a process restart, a deleted message, and
a Telegram API failure without duplicating themselves; no reader-visible
diagnostics; feed mode demonstrably unchanged; edit volume measured against
Telegram's rate limits before it ships anywhere real.

---

## Extension: Configurable publishing modes — feed, dashboard, hybrid

Status: IDEA
Priority: MEDIUM
Target version: —
Dependencies: Y (dashboard mode) for one of the three modes; AC
(per-destination configuration) for where the setting lives
Core changes required: a routing layer between reporting and publishers that
maps (destination, report or event) → feed post | panel edit | both; an event
classification so "routine tick" and "threshold crossed" are distinguishable
Backward compatibility: additive. Feed is the default mode and is what every
existing destination gets

Description: let each Telegram destination choose how it is published to.

- **Feed** — every scheduled report or event becomes a new post. Today's
  behaviour.
- **Dashboard** — a small set of persistent messages is edited and refreshed
  (Y).
- **Hybrid** — panels stay current, and selected events *additionally* post a
  standalone message.

Events worth a standalone post in hybrid mode: an important divergence
threshold crossed, a significant market move, the daily close, a weekly
summary, a user-configured alert.

This entry is about routing and orchestration only. It is deliberately not the
dashboard implementation, and it does not decide what an "important" event is —
that threshold work is F/G/S, and until those land any event trigger here is a
guess and must say so.

Why it may be useful: a price-board channel and an alerts channel want opposite
things from the same engine. Routing is the seam that lets one pipeline serve
both without either surface leaking into the analysis code.

Open questions: is the mode a property of the destination, of the report type,
or of the pair? In hybrid mode, does the standalone event post duplicate
content already visible in a panel, and is that redundancy a feature or noise?
How does an event post interact with the idempotency key, given events have no
scheduled slot?

Acceptance criteria: mode is data, not a code path per surface; adding a fourth
mode later touches the routing layer and nothing upstream of it; every mode
honours the same gating rules — a report withheld for data quality is withheld
in all three.

---

## Extension: Configurable historical archive policy

Status: IDEA
Priority: MEDIUM
Target version: —
Dependencies: none to state the policy; F and R make parts of it binding
Core changes required: a dependency registry mapping each stored series to the
analyses that consume it; a retention state per series; validation that refuses
a configuration which would starve an enabled feature
Backward compatibility: additive, and strictly non-destructive — existing
history is never dropped by introducing the policy

Description: distinguish data that must always be archived from data whose
retention is a choice.

- **REQUIRED** — needed for active analysis, backtesting, validation, or
  reproducibility. Cannot be disabled while a dependent feature is on.
- **ENABLED** — optional, and the administrator has chosen to keep it.
- **DISABLED** — optional, may be collected or displayed without long-term
  archival where that is technically sound.

The governing principle: **not displaying something must never silently mean
not storing it.** USD, gold 18k, XAU, and AED become REQUIRED the moment an
analysis that depends on them is enabled — which, for the shipped cross-market
report, is already the case.

Why it may be useful: dashboard mode (Y) removes history from the *chat*, and
that is exactly the moment someone reasons "we don't show it, so we don't need
it" and quietly breaks F's ability to backtest anything. Writing the dependency
down is cheaper than discovering the hole a year of missing history later.

Open questions: does DISABLED mean "not written" or "written then pruned"? Is
retention expressed as a duration, a row count, or a downsampling rule — a
5-minute series kept forever and a daily close kept forever are very different
storage stories. How does this interact with the immutability invariant: is
pruning old raw observations compatible with "raw observations are immutable",
or does immutability only govern mutation and not deletion? Who is allowed to
change a series from REQUIRED, and what proves no dependent is left?

Acceptance criteria: the registry is the single source of truth for what
depends on what; a configuration that would disable a REQUIRED series fails
validation loudly at load, not at the next report; no migration path deletes
existing history without an explicit, separately approved action.

---

## Extension: On-demand historical reports

Status: IDEA
Priority: LOW
Target version: —
Dependencies: an inbound command surface (U); AC for who is authorized; AA so
the history being queried is guaranteed to exist
Core changes required: a historical query service over the stored series; a
bounded/paginated result contract; authorization; optionally a chart renderer
Backward compatibility: additive; read-only; no change to scheduled publishing

Description: let authorized users ask the bot for historical information even
when the destination runs in dashboard mode and history is no longer scrolling
in the chat.

Plausible requests: USD history, gold history, AED history, a previous daily
report, a 7-day or 30-day summary, a historical chart. Illustrative syntax
only, not a committed interface:

```text
/history usd 7d
/history gold 30d
/report yesterday
```

History is served from the stored dataset. It is never reconstructed by parsing
old Telegram messages — the database is the record, the channel is a view of
it, and inverting that would make the chat authoritative over storage.

Why it may be useful: it is the missing half of dashboard mode. Panels answer
"what is it now"; this answers "what was it", without either question forcing
the channel back into a feed.

Open questions: what bounds a query — max range, max rows, max cost — so one
`/history usd 5y` cannot pin the process? Are answers posted into the channel
(where everyone sees them) or DM'd back to the requester (AD)? Does a
historical answer carry the same gating and provenance treatment as a scheduled
report, including a data-quality status line when the requested window is
patchy? Rendering a chart is a real dependency, not a detail — text tables may
be the honest first version.

Acceptance criteria: every answer traceable to stored rows with provenance;
bounded work per request; unauthorized requests refused without leaking data;
gaps in the requested window stated rather than interpolated over.

---

## Extension: Per-destination configuration

Status: IDEA
Priority: MEDIUM
Target version: —
Dependencies: a destination registry, which Z, AD, AE, and AF all also want;
Telegram admin verification
Core changes required: a persistent destination registry (chat id, type,
settings, audit trail); a scheduler able to run destination-specific jobs;
configuration validation; extension of the existing settings model rather than
a parallel one
Backward compatibility: today there is exactly one destination, a single
`chat_id` handed to the publisher. That single-destination setup must keep
working untouched as the degenerate case of the registry

Description: let every group or channel using the bot hold its own independent
configuration. Candidate destination-level settings: publishing mode, displayed
assets, enabled analyses, report schedule, refresh frequency, alert types,
archive preferences, AI-commentary setting, subscription/plan level, and
footer/branding where appropriate.

Only administrators authorized for *that* destination may change its settings.
Ordinary members of a group or channel cannot reconfigure the bot.

Explicit constraint from the original note, and the one most likely to be
violated: **do not build a second settings architecture.** Destination
configuration extends the same settings/domain model that `config/default.toml`
and `market-monitor config` already serve. Two config systems is the failure
mode here, not too few features.

Why it may be useful: it is the precondition for the bot being used by anyone
other than its author. Every other multi-tenant idea in this file — Z, AD, AE,
AF — is blocked on there being a destination to attach settings to.

Open questions: what is the precedence order between file defaults and
per-destination overrides, and is it the same order `market-monitor config`
already prints? Which settings are global-only on purpose (provider endpoints,
thresholds, model version) and must *not* become per-destination — a threshold
that varies by channel makes the analysis unreproducible. How is Telegram
admin status verified, and how often is it re-checked? What is audited, and
for how long (see AA)?

Acceptance criteria: one settings model, not two; the current single-channel
deployment runs unchanged with no registry rows; a non-admin cannot change
anything; every change is attributable; scheduler behaviour with N destinations
is bounded and does not multiply provider calls by N.

---

## Extension: Personal chat mode

Status: IDEA
Priority: LOW
Target version: —
Dependencies: an inbound command surface (U); AB for the history requests; a
permission model; rate limiting
Core changes required: a user registry; private-chat command routing distinct
from channel publishing; per-user rate limits; entitlement hooks if AF ever
lands
Backward compatibility: additive; channel behaviour untouched

Description: let any user interact with the bot in a private Telegram chat,
with a deliberately smaller feature set than a group or channel deployment.

Basic private capabilities: request the current market snapshot, request the
current ayar analysis, request a limited historical report, trigger selected
reports manually.

Private users do **not** get permanent scheduling or high-frequency monitoring
in the basic tier. Scheduled reporting, dashboard mode, alerts, higher refresh
rates, and destination-specific configuration remain group/channel features.

Kept separate from AC on purpose: a private chat is a different kind of
principal from a channel, with different limits and a different default answer
to "can this thing schedule work on my behalf".

Why it may be useful: a zero-commitment way to try the bot, and a natural place
to answer one-off questions that do not belong in a channel.

Open questions: is a private chat just a destination with a restrictive default
config (reusing AC's registry), or a genuinely separate surface? What stops N
private users from becoming N times the provider load — is the answer a shared
cache of the last computed snapshot rather than per-user computation? Where is
the line between "manual trigger" and "de-facto scheduling" when a user can
send the same command every minute?

Acceptance criteria: private use cannot increase provider call volume
proportionally to user count; rate limits enforced and observable; the same
gating rules apply — a withheld analysis is withheld in DMs too; no diagnostics
leak to private users that would not be shown in a channel.

---

## Extension: Configurable refresh and update-on-change engine

Status: IDEA
Priority: MEDIUM
Target version: —
Dependencies: Y for the edit path it drives; provider rate-limit facts;
ideally G/S so "meaningful change" is a measured number rather than a guess
Core changes required: cached last-rendered state; a comparison step between
fetch and publish; configurable thresholds; provider and Telegram rate-limit
awareness
Backward compatibility: additive. The current cron-driven schedule is the
degenerate configuration — check interval equals publish interval, threshold
zero

Description: separate *how often data is checked* from *how often the public
message changes*, so a frequent fetch does not mean a frequent edit.

1. Fetch on a configured interval.
2. Compare the new state with the last rendered state.
3. Publish or edit only when the price moved meaningfully, the analysis state
   changed (AG), or a configured maximum display age was reached.

Configuration surface: data-check interval, price-change threshold,
analysis-state-change trigger, maximum refresh age. Designed against both
provider API limits and Telegram API limits.

No interval is hard-coded. Ten or fifteen minutes are examples, not defaults to
bake in — and any threshold shipped before F/G is provisional and must be
labelled that way, exactly as `config/default.toml`'s existing bands are.

Why it may be useful: it is what makes dashboard mode affordable. Without it, a
panel either goes stale or burns an edit per tick for a number that did not
move.

Open questions: what *is* a meaningful change — absolute toman, percent, or a
z-score against realised volatility (the honest answer is the third, and it
needs G)? Does "analysis state changed" require AG to exist first, or can it be
approximated by a signal's `reason_codes` changing? Does the maximum display
age interact with the freshness gating already in `[freshness]`, or duplicate
it? If a fetch fails, does the display age clock keep running toward a refresh
that has nothing new to show?

Acceptance criteria: fetch cadence and publish cadence independently
configurable; a flat market produces no edits until max age; measured reduction
in Telegram calls versus fixed-interval publishing; no configuration can exceed
a provider's documented rate limit.

---

## Extension: Premium update frequencies and feature entitlements

Status: IDEA (research only)
Priority: LOW
Target version: —
Dependencies: AC and AD for identity; AE for what "faster" would even mean; a
real cost model
Core changes required: a plan/entitlement model; quota enforcement; payment
verification; a premium feature registry; abuse prevention
Backward compatibility: N/A while it stays research

Description: explore a subscription/entitlement model in which higher update
frequencies and selected advanced features are limited to premium users or
destinations.

Possible differentiation — free/basic: normal scheduled reports, lower refresh
frequency, standard deterministic analysis. Premium: shorter update intervals,
advanced alerts, higher-frequency dashboard refresh, premium analytical
features, AI commentary (L).

Payment rails to research, not to build: Telegram Stars, cryptocurrency,
whatever else is actually supported for this audience.

This entry is about commercial entitlement and quotas. It is not the refresh
engine — that is AE, and AE must work with a single free tier before any of
this is meaningful.

**No pricing is invented at this stage, and no payment functionality is
implemented.** A paid tier also drags in obligations the current
`DISCLAIMER.md` posture does not cover: charging money for something that
publishes indicators changes what a reader may reasonably infer from them.

Why it may be useful: it is the only entry here that asks who pays for the
provider calls, and knowing whether that question will ever be asked changes
how AC and AE should be shaped.

Open questions: what does a premium update actually cost in provider calls, and
does any provider's terms permit reselling access to its data? Is the unit of
sale a user or a channel? What happens to a destination whose plan lapses —
degrade quietly or announce? Does a paid tier oblige an availability
commitment the current single-host cron deployment cannot honour? Is the
regulatory picture for taking payment for market-data commentary in this
jurisdiction actually understood, or assumed?

Acceptance criteria (for the research, not a build): a cost model per tier
grounded in measured call volume; a written finding on provider terms and on
the disclosure obligations of a paid tier; a decision to proceed or reject,
recorded here.

---

## Extension: Deterministic analysis state machine

Status: IDEA (research)
Priority: HIGH
Target version: —
Dependencies: F, G, R and S — the taxonomy cannot be designed before the
metrics it classifies are statistically characterised
Core changes required: a state taxonomy; detection rules with explicit conflict
and priority handling; a versioned Persian text library; conditional report
rendering; historical validation
Backward compatibility: this changes published analytical output, so it bumps
the persisted model version by definition

Description: a structured deterministic layer mapping computed metrics to
predefined analytical states, each with an approved Persian text:

```text
market metrics → state detection → predefined text/state template → report
```

States might later represent combinations such as: USD above gold-implied USD;
USD near gold-implied USD; AED confirming USD; AED/USD divergence; gold gap
expanding; gold gap contracting; several markets confirming one direction.

Remains deterministic, reproducible, versioned, and independent of any LLM —
consistent with the standing rule that no LLM sits in the numeric path.

The taxonomy is designed and backtested, not invented casually, and no large
state library is written until the taxonomy itself is separately approved. A
state is a claim about the market; a state library built on provisional
thresholds is a large pile of confident-sounding claims resting on guesses.

Why it may be useful: it is the natural home for everything the reports
currently express ad hoc, it gives AE a clean "analysis state changed" trigger,
and it is the structured payload L needs in order to be a commentary layer
rather than an analyst.

Open questions: how many states before the taxonomy is unfalsifiable — every
outcome matching some state is the failure mode. What happens when two states
fire at once, and is priority a fixed order or a scoring rule? Does a state
change require persistence over N observations to avoid flapping across a
boundary (which AE will faithfully publish as churn)? How is the text library
versioned against the model version, and does correcting a typo in a Persian
string count as an analytical change? Every text must survive the wording
invariant: `نرخ ضمنی`, `ارزش نظری`, `ارزش طلای سکه`, never `ارزش ذاتی`, and
distances rather than verdicts — a state named "divergence confirmed" is a
verdict wearing a taxonomy's clothes.

Acceptance criteria: taxonomy documented and approved before any text is
written; every state has machine-readable detection with no overlap ambiguity;
historical validation over a stated sample showing the states are both
reachable and discriminating; every published string reviewed against the
indicator-not-advice rule; model version bumped.

---

## Extension: Optional premium AI commentary

Status: IDEA
Priority: LOW
Target version: —
Dependencies: AG (a structured analytical payload to comment on) — hard, not
soft; AF if it is ever gated commercially
Core changes required: an LLM provider abstraction; cost and token controls;
prompt and version management; a validation/safety layer; a deterministic
fallback that is the normal path, not the error path
Backward compatibility: additive and disableable. With AI off, output is
exactly the deterministic text

Description: the full entry for seeded idea **L**. An optional AI-generated
commentary layer:

```text
raw market data
  → deterministic calculation engine
  → deterministic analysis/state engine
  → structured analytical payload
  → optional LLM commentary
  → user-facing text
```

The model **never** calculates prices, formulas, gaps, signals, or states. It
explains or summarises information that has already been computed. If the model
is unavailable, over budget, fails validation, or is switched off, the system
falls back to the deterministic fixed text.

Possible premium use: more natural explanations, richer summaries, contextual
comparison across several signals, wording tailored to a destination.

Why it may be useful: the deterministic text of AG will be correct and
repetitive. Commentary is the layer that can vary the wording without varying
the numbers.

Open questions: what does the validation layer actually check — that no number
in the output is absent from the payload is checkable and worth doing; that no
sentence implies advice is much harder, and it is the one that matters given
the standing indicator-not-advice rule and `DISCLAIMER.md`. How is output
reproducibility handled when the numeric path is deterministic and the prose is
not — is the generated text stored alongside the report so a published claim
can be reconstructed later? Does a commentary failure count as a report
failure, or silently degrade? Who is accountable for a sentence the model wrote
about a real market?

Acceptance criteria: numbers in commentary provably a subset of the structured
payload; deterministic fallback exercised in tests and observed in production;
per-report token/cost ceiling enforced; generated text persisted with its
prompt version; the whole layer switchable off by configuration with no
behavioural residue.
