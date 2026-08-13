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
| K. Additional markets | MEDIUM | ~~AED/IRT, EUR/IRT~~ **shipped in v1.1** (plus TRY, JPY). Remaining: USDT/IRT (see O), silver, Brent, BTC |
| L. Optional AI commentary | LOW | LLM summarises already-computed metrics; never the numeric source of truth |
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

`F` and `G` are the pair that matters: until they land, every threshold in
`config/default.toml` is a guess and reports must keep saying so. `R` is now
their equal in importance — without it there is no basis for `P`.

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
