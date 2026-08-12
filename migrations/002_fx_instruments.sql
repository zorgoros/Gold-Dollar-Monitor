-- v1.1: four FX instruments (ARCHITECTURE.md §4.5).
--
-- Additive only. No column is altered, no row is rewritten, and every quote,
-- metric, signal and report written under model version 1.0 keeps its meaning.
--
-- The generic `instruments` table already models this, so there is no per-
-- currency table (§28). Note the yen's canonical unit: toman per ONE yen, while
-- TGJU quotes per hundred — the conversion happens in normalization and the
-- report shows 100 as presentation (§6, docs/PROVIDERS.md).
--
-- collection / display / analysis enablement is deliberately NOT stored here.
-- It lives in config/default.toml, which is the operator-facing settings model;
-- duplicating it into the schema would create two sources of truth (§26, §47).

INSERT INTO instruments (symbol, name_fa, asset_class, canonical_unit) VALUES
    ('aed_irt', 'درهم امارات', 'currency', 'toman/aed'),
    ('eur_irt', 'یورو',        'currency', 'toman/eur'),
    ('try_irt', 'لیر ترکیه',   'currency', 'toman/try'),
    ('jpy_irt', 'ین ژاپن',     'currency', 'toman/jpy');
