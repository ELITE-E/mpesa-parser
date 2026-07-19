import pandas as pd
from src.clean import clean_mpesa_dataframe

def test_parser_handles_malformed_and_empty_rows():
    """Ensures empty, repeated headers, and null rows are dropped safely."""
    raw_data = [
        {"Receipt No.": None, "Details": "Ghost transaction", "Paid In": "10"},
        {"Receipt No.": "  ", "Details": "Empty spaces string", "Paid In": "20"},
        {"Receipt No.": "Receipt No.", "Details": "Header Repeat Row", "Paid In": "Paid In"},
        {"Receipt No.": "QK12345678", "Details": "PayBill - 456 - Airtel", "Paid In": "KSh 1,200.00"}
    ]
    df = pd.DataFrame(raw_data)
    
    cleaned_df = clean_mpesa_dataframe(df)
    
    # Only the valid row should survive the filters
    assert len(cleaned_df) == 1
    assert cleaned_df.loc[0, "Receipt No."] == "QK12345678"
    
    # Validates that nested transformation mappings triggered successfully
    assert cleaned_df.loc[0, "Details"] == "Airtel 456"
    assert cleaned_df.loc[0, "Paid In"] == 1200.0
