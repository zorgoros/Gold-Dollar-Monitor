"""Every constant defined once. Nothing here is re-derived by hand elsewhere."""

TROY_OUNCE_GRAMS = 31.1034768
GOLD_18_PURITY = 0.75

# ~41.4713024. Never write the rounded value inline (ARCHITECTURE.md §4).
GOLD_18_CONVERSION = TROY_OUNCE_GRAMS / GOLD_18_PURITY

RIAL_PER_TOMAN = 10

# Bahar Azadi (Emami) coin: 8.133 g at 900 purity, i.e. 7.3197 g of pure gold.
# Audited 2026-08-12 against the live market; see docs/FORMULAS.md.
EMAMI_COIN_GRAMS = 8.133
EMAMI_COIN_PURITY = 0.900
EMAMI_COIN_PURE_GRAMS = EMAMI_COIN_GRAMS * EMAMI_COIN_PURITY

# The UAE dirham's conventional peg: 1 USD = 3.6725 AED, set by the Central Bank
# of the UAE and unchanged since November 1997. It is a *default*, not a law of
# nature — `[peg].usd_aed` in config overrides it if the peg is ever re-set.
# Provenance for this assumption lives in docs/FORMULAS.md, once.
USD_AED_PEG = 3.6725

# TGJU quotes the yen per hundred and so does the report (§6). Storage is per
# one yen; this is the presentation multiplier and the divisor at the boundary.
JPY_QUOTE_UNITS = 100

# Attribution carried by every published report. Deliberately in source rather
# than config: config is for values an operator is meant to change, and this is
# not one of them. See NOTICE. The brand and handle lines above it are
# configurable — `[reporting.footer]` — because those are the operator's.
PROJECT_NAME = "Gold-Dollar-Monitor"
PROJECT_URL = "github.com/zorgoros/Gold-Dollar-Monitor"
ATTRIBUTION = f"{PROJECT_NAME} · {PROJECT_URL}"

FORMULA_VERSION = "1.1"
SIGNAL_MODEL_VERSION = "1.1"
REPORT_TEMPLATE_VERSION = "1.1"
