"""Every constant defined once. Nothing here is re-derived by hand elsewhere."""

TROY_OUNCE_GRAMS = 31.1034768
GOLD_18_PURITY = 0.75

# ~41.4713024. Never write the rounded value inline (ARCHITECTURE.md §4).
GOLD_18_CONVERSION = TROY_OUNCE_GRAMS / GOLD_18_PURITY

RIAL_PER_TOMAN = 10

# Bahar Azadi (Emami) coin: 8.133 g at 900 purity, i.e. 7.3197 g of pure gold.
EMAMI_COIN_GRAMS = 8.133
EMAMI_COIN_PURITY = 0.900
EMAMI_COIN_PURE_GRAMS = EMAMI_COIN_GRAMS * EMAMI_COIN_PURITY

# Attribution carried by every published report. Deliberately in source rather
# than config: config is for values an operator is meant to change, and this is
# not one of them. See NOTICE.
PROJECT_NAME = "Gold-Dollar-Monitor"
PROJECT_URL = "github.com/zorgoros/Gold-Dollar-Monitor"
ATTRIBUTION = f"{PROJECT_NAME} · {PROJECT_URL}"

FORMULA_VERSION = "1.0"
SIGNAL_MODEL_VERSION = "1.0"
REPORT_TEMPLATE_VERSION = "1.0"
