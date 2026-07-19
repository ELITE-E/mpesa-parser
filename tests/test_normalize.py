import pytest
from src.normalize import normalize_name

@pytest.mark.parametrize("raw, expected", [
    # Original Base Cases
    ("KPLC-888888", "KPLC 888888"),
    ("KPLC 888888 ", "KPLC 888888"),
    ("Unknown Entity", "Unknown Entity"),
    
    # PayBill Refactoring Cases
    ("PayBill - 888888 - KPLC", "KPLC 888888"),
    ("KPLC 888888 (Ref: 123)", "KPLC 888888"),
    
    # New Till / Buy Goods Cases
    ("Till - 123456 - Acme Shop", "Acme Shop 123456"),
    ("Buy Goods - 789012 - Naivas Supermarket", "Naivas Supermarket 789012"),
    
    # New Customer-to-Customer (P2P) Cases
    ("Sent to 0712345678 - John Doe", "John Doe"),
    ("Received from 254789012345 Jane Smith", "Jane Smith"),
    ("Sent to 0711223344 Peter Pen", "Peter Pen"),
    
    # Edge Cases
    ("", ""),
    (None, ""),
])
def test_recipient_normalization(raw, expected):
    assert normalize_name(raw) == expected
