# Formulas

Formula version **1.1**. Every constant is defined once in
`src/market_monitor/domain/constants.py`; nothing below is re-typed as a literal
anywhere in the code.

## Constants

| Name | Value | Source |
|---|---|---|
| `TROY_OUNCE_GRAMS` | 31.1034768 | exact definition of the troy ounce |
| `GOLD_18_PURITY` | 0.75 | 18 karat = 18/24 |
| `GOLD_18_CONVERSION` | 41.4713024 (derived) | `TROY_OUNCE_GRAMS / GOLD_18_PURITY` |
| `RIAL_PER_TOMAN` | 10 | 1 toman = 10 rial |
| `EMAMI_COIN_GRAMS` | 8.133 | Bahar Azadi (Emami) coin gross weight |
| `EMAMI_COIN_PURITY` | 0.900 | coin gold purity |
| `EMAMI_COIN_PURE_GRAMS` | 7.3197 (derived) | gross × purity |
| `USD_AED_PEG` | 3.6725 | see below |
| `JPY_QUOTE_UNITS` | 100 | TGJU quotes the yen per hundred |

### The USD/AED peg, and what it is worth

The UAE dirham is pegged to the US dollar at **1 USD = 3.6725 AED**. The peg is
a policy of the Central Bank of the UAE, in force since **November 1997**, and
the IMF classifies the regime as a conventional peg to the dollar. The market
rate sits inside a band of roughly 3.6720–3.6730; TGJU's own `diff_usd_aed`
read 3.6715 on 2026-08-12, 0.03% from the official figure.

The default lives in `constants.py` and is overridden by `[peg].usd_aed` in
`config/default.toml`. **It is an assumption about another country's monetary
policy, not a constant of nature.** If the peg is ever re-set or abandoned,
change the config value and bump `model_version` in the same edit — the change
alters every AED-implied number the system has ever published.

## Relationships

**Gold-implied USD** — the USD/toman rate embedded in the domestic 18K market:

```
usd_gold_implied = gold_18k × GOLD_18_CONVERSION / xau_usd
```

**USD gap** — market USD above (+) or below (−) that implied rate:

```
usd_gap_pct = (usd_market / usd_gold_implied − 1) × 100
```

> **Naming.** `usd_gap_pct` is the *gold* divergence. It predates v1.1 and keeps
> its name because the stored series and every trend lookup depend on it;
> renaming it would orphan the history. The dirham divergence is a new series
> with an explicit name, `aed_usd_gap_pct`. There is deliberately no
> `gold_usd_gap_pct` alias — one number, one key.

**AED-implied USD** — the rate implied by the domestic dirham market and the peg:

```
usd_aed_implied = aed_irt × USD_AED_PEG
aed_usd_gap_pct = (usd_market / usd_aed_implied − 1) × 100
```

Persian: `نرخ ضمنی دلار از بازار درهم`. Also an implied rate — the dirham's peg
is another central bank's commitment, and says nothing about what the toman
*should* be. It is not "the true dollar".

**Why this one may be compared with the gold rate.** Unlike implied USD and
theoretical gold, the AED and gold routes are *not* inversions of one equation.
They reach a USD/toman figure through genuinely different mechanisms — a metal
content versus a currency peg — so their agreement or disagreement is
information, and §9's three-way view is legitimate. What is still forbidden is
blending them: see "No composite" below.

Worked example, live 2026-08-12:

| | value | gap vs market USD 187,800 |
|---|---|---|
| gold-implied USD | 180,496 | +4.05% |
| AED-implied USD | 187,889 | −0.05% |

The dirham market corroborated the free-market dollar almost exactly, while the
gold market did not. That is the observation the report states — not a verdict
about which one is right.

**Theoretical 18K gold** — toman per gram implied by the world ounce and the
market USD rate:

```
gold_18_theoretical = xau_usd × usd_market / GOLD_18_CONVERSION
```

**Gold gap**:

```
gold_gap_pct = (gold_18_market / gold_18_theoretical − 1) × 100
```

**Coin premium** — market price against the value of the gold it contains,
priced where the coin is actually traded:

```
gold_pure_domestic        = gold_24k          (fallback: gold_18k / GOLD_18_PURITY)
coin_intrinsic_domestic   = gold_pure_domestic × EMAMI_COIN_PURE_GRAMS
coin_premium_domestic_pct = (coin_market / coin_intrinsic_domestic − 1) × 100
```

Reports say `ارزش طلای سکه` and `حباب`, never `ارزش ذاتی` — this is metal
content, a narrower and more defensible claim than intrinsic worth.

`geram24` is TGJU's direct pure-gold quote and the preferred input. It is
itself derived from `geram18` — on 2026-08-11 the two agreed to **0.0007%** —
so the 18K fallback is arithmetically *equivalent*, not degraded. It exists
because a provider symbol can go missing, not because it is worse. `geram24` is
preferred for being direct: one fewer assumption, and immune to TGJU changing
how it defines its 18K series.

The world-route calculation is retained as a non-public analytical series:

```
coin_intrinsic_world      = (xau_usd × usd_market / TROY_OUNCE_GRAMS) × EMAMI_COIN_PURE_GRAMS
coin_premium_world_pct    = (coin_market / coin_intrinsic_world − 1) × 100
```

It is stored, never rendered, and never entered into a model beside
`gold_gap_pct` or `usd_gap_pct` — see the audit below for why.

### Coin audit, 2026-08-12

The constants and the arithmetic were checked against the Bahar Azadi (Emami)
specification and recomputed from first principles in `test_formulas.py`:

| Item | Value | Verdict |
|---|---|---|
| gross weight | 8.133 g | correct |
| fineness | 0.900 | correct |
| fine gold | 7.3197 g (derived) | correct |
| troy ounce | 31.1034768 | exact |
| chain | `xau × usd / TROY_OZ × fine_g` | correct |

**The formula is arithmetically sound. What it measures is narrower than it
looks**, and two limitations belong on the record:

1. **It inherits the USD/gold divergence.** `coin_intrinsic` values the coin's
   gold through `xau_usd × usd_market`, i.e. through the *theoretical* domestic
   gold price. So `coin_premium_pct` already contains `gold_gap_pct`. On
   2026-08-12 the coin priced against the world route showed **−2.34%**, and
   against the domestic 18K price **+1.09%** — a difference of 3.43%, which is
   exactly the gold gap. A coin apparently trading below its own metal content
   is the tell.
2. **It is therefore not independent evidence.** Reading "USD is 3.5% above the
   gold-implied rate" and "the coin is 2.3% below its metal value" as two
   findings double-counts one divergence, the same trap §4 names for implied
   USD and theoretical gold.

The formula was **unchanged in v1.1** — changing it is an economic decision, not
a bug fix. That decision was taken for **v1.2**; the rest of this section
records it.

### Resolution, v1.2 — the denominator moved to domestic gold

The published `حباب` now means *premium over the domestic gold value*. Two
things settled it.

**1. The sign was not merely imprecise, it was implausible.** −2.34% asserts
that a minted, verified, freely resold coin trades below its own melt value —
which would be an open arbitrage. It was never a statement about coins; it was
`gold_gap_pct` wearing a disguise, one section below where the report had
already stated it plainly.

**2. TGJU publishes its own intrinsic coin value, and we match it.** The
`sekee_real` symbol carries exactly this figure. Cross-checked at the
2026-08-11 Tehran close:

| | toman | vs `sekee_real` |
|---|---|---|
| TGJU `sekee_real` | 187,439,300 | — |
| ours, `geram24 × 7.3197` | 187,437,754 | **−0.0008%** |
| ours, `geram18 / 0.75 × 7.3197` | 187,438,974 | −0.0002% |
| ours, world route | 193,486,527 | **+3.23%** |

Agreeing to 0.001% is an independent check on `EMAMI_COIN_GRAMS` and
`EMAMI_COIN_PURITY`, not just on the arithmetic: TGJU is using the same
7.3197 g of fine gold. The resulting premium is **+1.09%** against either
domestic route and **−2.07%** against the world route, the difference being the
gold gap in full. The identity is pinned by a test:

```
(1 + premium_domestic) / (1 + premium_world) == 1 / (1 + gold_gap)
```

**What changed and what did not.** `coin_premium_pct` and `coin_intrinsic` are
retired rather than redefined — rows written under those names are model version
1.1 or earlier and remain valid on their own terms. The new series are
`coin_premium_domestic_pct` (published) and `coin_premium_world_pct` (stored,
not published). `model_version` moved to 1.2, which re-keys idempotency, so no
1.1 report is overwritten.

**The remaining caveat.** The 18K fallback assumes `geram18` is clean metal
content; Iranian 18K retail pricing carries workmanship and dealer margin. That
bias is smaller and more stable than a 3.4% FX gap, but it is not zero. With
`geram24` present — the normal case — it does not arise.

## The inversion, stated once

`usd_gold_implied` and `gold_18_theoretical` are the same equation solved for
different variables. A test (`test_the_two_formulas_are_one_relationship`)
asserts the round trip. **They must never be counted as two independent pieces
of evidence** in any score, weighting, or confidence calculation. When the USD
gap is +3.9%, the gold gap is −3.7% — that is one fact reported twice, not two
facts agreeing.

## Interpretation limits

The gold-implied rate is an *implied* rate, not an intrinsic or fair value for
the USD. The theoretical gold price is what the world ounce and the market USD
imply, not a guaranteed fair value. Neither accounts for import friction,
domestic supply, sanctions premia, or demand for physical gold as a store of
value. Reports say `نرخ ضمنی دلار` and `ارزش نظری`, never "intrinsic value".

## No composite

There is no blended USD reference and v1.1 does not create one. Averaging the
gold-implied and AED-implied rates — at any weighting, 50/50 included — would
assert that the two carry known relative reliability. Nothing establishes that
yet: no lead/lag study, no error distribution, no regime analysis. The two
numbers stay separate in the metrics, in the widget payload (`references` is a
list of two), and in the report. The research that would have to come first is
specified in `docs/BACKTESTING.md` and parked in `EXTENSIONS.md`.

## Units

| Quantity | Canonical unit |
|---|---|
| Iranian money | toman |
| gold weight | gram |
| world gold | USD per troy ounce |
| foreign currency | toman per **one** unit — including the yen |
| timestamps in storage | timezone-aware UTC |

TGJU reports every Iranian instrument in **rial**. The adapter declares the
source unit per symbol and conversion happens in `normalization/units.py` — a
missed division by ten is a 10× error in every published number, so
`check_unit_sanity` refuses to publish when the implied and market USD diverge
by more than 3×.

**The yen carries a second divisor.** `price_jpy` is quoted per **100** yen, so
it converts by 10 *and* by 100. Both divisions are exact. It is stored per one
yen, like every other currency, and multiplied back to 100 only for display,
where the label states the unit (`۱۰۰ ین`) so no reader can mistake the scale.
Verification and the trap itself: `docs/PROVIDERS.md`.

## Which numbers are stored, and which are published

They are not always the same figure, and the difference is deliberate.

* **Stored** in `metrics`: computed from the inputs exactly as collected. This
  is the observation record, and `analysis/session.py` reads `xau_usd` back out
  of it to align a closed session. Writing an aligned value into that series
  would make the lookup consume its own output.
* **Published**: computed with the aligned ounce when the basis is
  `LAST_CLOSE`. The exact text is preserved verbatim in `reports.content`, so a
  published report stays reproducible even though the series behind it records
  the raw observation.

A backtest must therefore treat the stored series as observations and recompute
signals under the model version being tested, which is what
`docs/BACKTESTING.md` already requires.

## Trends

Lookbacks (1d, 3d, 7d) resolve to the **nearest stored observation** to the
target instant, within `trend_tolerance_hours`. Missing history yields `None`
and prints as `—`; it is never rendered as 0%. Gap momentum compares
`abs(gap)` over time, so a gap moving −2% → −4% reads as expanding.
