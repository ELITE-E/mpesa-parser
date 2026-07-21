# utils.py
import logging

import pandas as pd

logger = logging.getLogger(__name__)


def parse_currency(raw_currency: str) -> float:
    """Safely converts an M-Pesa currency string to a float (Error Boundary)."""
    try:
        return _execute_currency_parsing(raw_currency)
    except ValueError:
        logger.warning(f"Could not parse currency value: {raw_currency}")
        return 0.0


def _execute_currency_parsing(raw_currency: str) -> float:
    """The formatting rules for string-to-float conversions."""
    if pd.isna(raw_currency) or raw_currency == "":
        return 0.0

    if isinstance(raw_currency, (int, float)):
        return float(raw_currency)

    clean_val = raw_currency.replace("KSh", "").replace(",", "").strip()
    return float(clean_val)
