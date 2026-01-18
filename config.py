"""Configuration constants for dbt observability dashboard."""

ELEMENTARY_SCHEMA = "DATA_LAKE__NCL.DBT_OBSERVABILITY"
WAREHOUSE = "WH_NCL_ENGINEERING_XS"
ROLE = "ENGINEER"

PAGE_CONFIG = {
    "page_title": "dbt Observability",
    "page_icon": ":bar_chart:",
    "layout": "wide",
    "initial_sidebar_state": "expanded",
}

# Default date ranges
DEFAULT_LOOKBACK_DAYS = 7
MAX_LOOKBACK_DAYS = 30

# Pagination
DEFAULT_PAGE_SIZE = 50

# Cache TTL (seconds) - mainly for UI rerender efficiency
CACHE_TTL = 300

# Thresholds
FLAKY_TEST_THRESHOLD = 0.2  # 20% failure rate = flaky
SLOW_MODEL_PERCENTILE = 90  # Top 10% by execution time = slow
SLOW_MODEL_MIN_SECONDS = 60  # Minimum 60s to be considered slow
