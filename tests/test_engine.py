import pytest
import pandas as pd
from src.engine import process_engine, calculate_transfer_efficiency

@pytest.fixture
def sample_transactions():
    """Mock Data representing a post-parsing transaction state."""
    return pd.DataFrame([
        {"Receipt No.": "A1", "Details": "Transfer to 0722000", "Withdrawn": 200.0},
        {"Receipt No.": "A1", "Details": "Customer Transfer of Funds Charge", "Withdrawn": 7.0},
        {"Receipt No.": "B1", "Details": "Fuliza Recovery", "Withdrawn": 500.0},
        {"Receipt No.": "B1", "Details": "Fuliza Fee", "Withdrawn": 15.0},
        {"Receipt No.": "C1", "Details": "Pay Bill KPLC", "Withdrawn": 100.0}
    ])

def test_sequential_fee_attribution(sample_transactions):
    """Ensure child fees are absorbed by the parent and original cost is zeroed."""
    processed = process_engine(sample_transactions)
    
    # Assert row-by-row to guarantee true parent attribution
    assert processed.loc[0, "Total Cost"] == 207.0  # Parent transaction absorbed fee
    assert processed.loc[1, "Total Cost"] == 0.0    # Original fee row is zeroed out

def test_fuliza_repayment_exclusion(sample_transactions):
    """Verify Fuliza Recovery is identified as a liability, not expenditure."""
    processed = process_engine(sample_transactions)
    
    # Isolate categories to ensure correct assignment
    purchases = processed[processed['Category'] == 'PURCHASE']
    repayments = processed[processed['Category'] == 'REPAYMENT']
    
    assert len(purchases) == 1
    assert len(repayments) == 1
    assert repayments.iloc[0]["Details"] == "Fuliza Recovery"

def test_fuliza_fee_inclusion_and_absorption(sample_transactions):
    """Verify Fuliza Fees are mapped as FEE but absorbed by their parent context."""
    processed = process_engine(sample_transactions)
    
    # Verify categories are tracked properly
    fee_rows = processed[processed['Category'] == 'FEE']
    assert len(fee_rows) == 2  # Both Customer Charge and Fuliza Fee are categorized
    
    # Verify the parent (Fuliza Recovery) successfully absorbed the Fuliza Fee
    assert processed.loc[2, "Total Cost"] == 515.0  # 500 base + 15 fee
    assert processed.loc[3, "Total Cost"] == 0.0    # Fee container zeroed

def test_transfer_efficiency_calculation(sample_transactions):
    """Verifies transfer efficiency avoids double-counting via Total Cost columns."""
    processed = process_engine(sample_transactions)
    efficiency = calculate_transfer_efficiency(processed)
    
    # Total Fees = 7.0 + 15.0 = 22.0
    # Total Expenditure (Sum of Total Cost) = 207 + 0 + 515 + 0 + 100 = 822.0
    # Expected: (22.0 / 822.0) * 100 = ~2.676%
    assert round(efficiency, 3) == 2.676

def test_transfer_efficiency_handles_zero_expenditure():
    """Defensive test to ensure calculation doesn't throw ZeroDivisionError."""
    empty_processed_df = pd.DataFrame(columns=["Category", "Withdrawn", "Total Cost"])
    efficiency = calculate_transfer_efficiency(empty_processed_df)
    assert efficiency == 0.0

def test_engine_handles_first_row_orphan_fee():
    """Ensures loop safely ignores a fee if it appears as the absolute first entry."""
    orphan_df = pd.DataFrame([
        {"Receipt No.": "Z1", "Details": "M-Pesa Statement Fee Rule", "Withdrawn": 10.0}
    ])
    processed = process_engine(orphan_df)
    assert processed.loc[0, "Category"] == "FEE"
    assert processed.loc[0, "Total Cost"] == 10.0  # Stays 10 because there is no parent row at index -1
