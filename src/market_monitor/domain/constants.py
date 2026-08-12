"""Every constant defined once. Nothing here is re-derived by hand elsewhere."""

TROY_OUNCE_GRAMS = 31.1034768
GOLD_18_PURITY = 0.75

# ~41.4713024. Never write the rounded value inline (ARCHITECTURE.md §4).
GOLD_18_CONVERSION = TROY_OUNCE_GRAMS / GOLD_18_PURITY

RIAL_PER_TOMAN = 10

FORMULA_VERSION = "1.0"
SIGNAL_MODEL_VERSION = "1.0"
REPORT_TEMPLATE_VERSION = "1.0"
