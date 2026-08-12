# Formulas

Formula version **1.0**. Every constant is defined once in
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

## Relationships

**Gold-implied USD** — the USD/toman rate embedded in the domestic 18K market:

```
usd_gold_implied = gold_18k × GOLD_18_CONVERSION / xau_usd
```

**USD gap** — market USD above (+) or below (−) that implied rate:

```
usd_gap_pct = (usd_market / usd_gold_implied − 1) × 100
```

**Theoretical 18K gold** — toman per gram implied by the world ounce and the
market USD rate:

```
gold_18_theoretical = xau_usd × usd_market / GOLD_18_CONVERSION
```

**Gold gap**:

```
gold_gap_pct = (gold_18_market / gold_18_theoretical − 1) × 100
```

**Coin premium** — market price against melt value:

```
coin_intrinsic  = (xau_usd × usd_market / TROY_OUNCE_GRAMS) × EMAMI_COIN_PURE_GRAMS
coin_premium_pct = (coin_market / coin_intrinsic − 1) × 100
```

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

## Units

| Quantity | Canonical unit |
|---|---|
| Iranian money | toman |
| gold weight | gram |
| world gold | USD per troy ounce |
| timestamps in storage | timezone-aware UTC |

TGJU reports the three Iranian instruments in **rial**. The adapter declares
the source unit per symbol and conversion happens in `normalization/units.py` —
a missed division by ten is a 10× error in every published number, so
`check_unit_sanity` refuses to publish when the implied and market USD diverge
by more than 3×.

## Trends

Lookbacks (1d, 3d, 7d) resolve to the **nearest stored observation** to the
target instant, within `trend_tolerance_hours`. Missing history yields `None`
and prints as `—`; it is never rendered as 0%. Gap momentum compares
`abs(gap)` over time, so a gap moving −2% → −4% reads as expanding.
