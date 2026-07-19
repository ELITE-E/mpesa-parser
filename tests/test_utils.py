import pytest
from src.utils import parse_currency

@pytest.mark.parametrize("raw_currency, expected_float", [
    ("KSh 1,000.00", 1000.0),
    ("1000", 1000.0),
    ("KSh 50", 50.0),
    ("1,234.50", 1234.5),
    ("-500.00", -500.0),       # Handling reversals
    ("Malformed text", 0.0),   # Testing exception boundary fallback
    ("", 0.0),
    (None, 0.0)
])
def test_currency_string_to_float(raw_currency, expected_float):
    assert parse_currency(raw_currency) == expected_float
