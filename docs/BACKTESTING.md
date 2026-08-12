# Backtesting

Not built. This is the methodology the future module must follow, written now
so the data being accumulated today is usable later.

Backtesting never runs inside live execution. It reads the same `metrics` table
the live engine writes and lives in its own `backtesting/` package when it
arrives (EXTENSIONS F and G).

## Anti-look-ahead rules

1. For a historical timestamp `t`, reconstruct **only** rows whose `created_at`
   is at or before `t`. Never the closing value of the day being classified.
2. Thresholds must be fitted on data before `t` too. Fitting bands on the whole
   history and then testing on it is the most common way to produce a
   backtest that works everywhere except in production.
3. Forward returns are measured from the price available at `t`, not from an
   intraday extreme that was only visible afterwards.
4. Quotes flagged `STALE` or `SUSPECT` are excluded from fitting, and their
   exclusion is reported — a sample that quietly drops bad days overstates
   its own reliability.

5. **Recompute, do not replay.** The stored `metrics` series records the inputs
   as collected, which for a closed Tehran session means a rial price paired
   with whatever ounce was printing at collection time. A published report may
   have used a *different*, session-aligned ounce (`docs/FORMULAS.md`). A
   backtest must therefore recompute signals from the stored observations under
   the model version being tested, and must apply the same alignment rule the
   live gate applies — otherwise it tests a pipeline that never ran.
6. **Exclude what the gate would have withheld.** Periods where the live system
   would have published nothing must not contribute signals to the sample.
   Including them measures a system that does not exist and inflates coverage.

## Method

For each historical snapshot: reconstruct state as of `t`, compute the signal
under the model version being tested, then measure forward return at 1, 3, 7,
14, and 30 days. Report sample size per bucket, median and mean forward return,
win rate, and the distribution — not just the average. Compare against the
naive baseline of "always long" over the same window; a signal that beats
nothing is not a signal.

## Cross-market study (v1.1 onward)

From v1.1 there are two independent implied USD rates, and the stored series
carries both plus the agreement state (`GOLD_AND_AED_AGREE` /
`GOLD_AND_AED_DISAGREE` reason codes). The questions this enables are listed in
`EXTENSIONS.md` under R; the methodology constraints are here.

Treat the two gaps as **separate hypotheses**, never as one blended input. In
particular:

- Report each source's error distribution against subsequent market USD
  separately. An average error hides that one source may be reliable in calm
  regimes and useless in shocks.
- The agreement/disagreement split creates four buckets, not two, and the
  buckets are badly unbalanced — a pegged currency corroborates the market most
  of the time. State the count per bucket every time; the disagreement bucket
  will be small and small buckets produce confident nonsense.
- `coin_premium_pct` is **not** independent of `usd_gap_pct` — it contains it
  (see the audit in `docs/FORMULAS.md`). Do not enter both into one model.
- The AED gap is bounded by a peg and the gold gap is not. Their variances
  differ by construction, so any comparison must be scale-aware; a z-score on
  each series separately, not a shared threshold.

**Only after all of that** may a composite weighting be fitted, on out-of-sample
data, per `EXTENSIONS.md` P. Until then the reports show the rates side by side
and say nothing about which is right.

## Honest reporting

State the sample size next to every number. With four reports a day, one year
is ~1,460 observations but only ~365 independent days, and gap regimes persist
for weeks — so the effective sample is far smaller than the row count suggests.
Publish confidence intervals and the false-positive rate. A result that cannot
survive being stated with its sample size should not change a threshold.

## Until then

Every band in `config/default.toml` is a provisional placeholder. Signal
confidence is capped at 0.6 in code for exactly this reason, and reports carry
the disclaimer. Calibrated thresholds replace the placeholders only after this
module exists and its output has been reviewed.
