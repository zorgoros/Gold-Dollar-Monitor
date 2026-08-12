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

## Method

For each historical snapshot: reconstruct state as of `t`, compute the signal
under the model version being tested, then measure forward return at 1, 3, 7,
14, and 30 days. Report sample size per bucket, median and mean forward return,
win rate, and the distribution — not just the average. Compare against the
naive baseline of "always long" over the same window; a signal that beats
nothing is not a signal.

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
