-- v1.2: domestic pure-gold price (docs/FORMULAS.md, EXTENSIONS Q).
--
-- Additive only. One instrument row; no column altered, no row rewritten.
--
-- This is the denominator of the published coin premium. It is collected and
-- analysed but NOT displayed on the public board — the three enablement sets
-- are independent (§27) and this one exists to be divided by, not read.
--
-- TGJU derives `geram24` from `geram18` (they agree to 0.0007%), so this is not
-- an independent quote. It is preferred over `geram18 / 0.75` because it is
-- direct, not because it is more accurate; the fallback in
-- `pure_gold_toman_per_gram` is equivalent, and exists for a missing symbol.

INSERT INTO instruments (symbol, name_fa, asset_class, canonical_unit) VALUES
    ('gold_24k', 'طلای ۲۴ عیار', 'gold', 'toman/gram');
