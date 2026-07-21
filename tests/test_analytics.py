# tests/test_analytics.py
import pytest
import pandas as pd
import numpy as np
from src.analytics import calculate_monthly_expenditure, get_heavy_hitters

@pytest.fixture
def analyzed_transactions():
    """Mock Data representing standardized database output schema."""
    return pd.DataFrame([
        {"receipt_no": "1", "completion_time": "2026-07-01 10:00:00", "details": "KPLC 888888", "category": "PURCHASE", "withdrawn": 1000.0, "total_cost": 1000.0},
        {"receipt_no": "2", "completion_time": "2026-07-05 12:00:00", "details": "Naivas Supermarket", "category": "PURCHASE", "withdrawn": 5000.0, "total_cost": 5000.0},
        {"receipt_no": "3", "completion_time": "2026-07-10 14:00:00", "details": "Withdrawal Charge", "category": "FEE", "withdrawn": 29.0, "total_cost": 29.0},
        {"receipt_no": "4", "completion_time": "2026-08-01 09:00:00", "details": "KPLC 888888", "category": "PURCHASE", "withdrawn": 2000.0, "total_cost": 2000.0},
    ])

def test_monthly_expenditure_sum(analyzed_transactions):
    """Verifies that expenditure is correctly grouped and summed by year-month."""
    summary = calculate_monthly_expenditure(analyzed_transactions)
    
    # Set Month as index for clean, error-informative lookups
    summary_indexed = summary.set_index("month")
    
    # July 2026 total (1000 + 5000 + 29 = 6029)
    assert summary_indexed.loc["2026-07", "total"] == 6029.0
    # August 2026 total (2000)
    assert summary_indexed.loc["2026-08", "total"] == 2000.0

def test_heavy_hitters_ranking(analyzed_transactions):
    """Ranks top recipients/merchants by total capital spent, descending."""
    hitters = get_heavy_hitters(analyzed_transactions, top_n=2)
    
    # Limit check
    assert len(hitters) == 2
    
    # Naivas (5000) should be #1, KPLC (3000 total across months) should be #2
    assert hitters.iloc[0]['details'] == 'Naivas Supermarket'
    assert hitters.iloc[0]['total_cost'] == 5000.0
    
    assert hitters.iloc[1]['details'] == 'KPLC 888888'
    assert hitters.iloc[1]['total_cost'] == 3000.0

def test_analytics_handles_empty_dataframe():
    """Defensive boundary check confirming empty inputs return clean empty structures."""
    empty_df = pd.DataFrame(columns=["receipt_no", "completion_time", "details", "category", "withdrawn", "total_cost"])
    
    summary = calculate_monthly_expenditure(empty_df)
    hitters = get_heavy_hitters(empty_df, top_n=5)
    
    assert summary.empty
    assert "month" in summary.columns
    assert hitters.empty
    assert "details" in hitters.columns

def test_analytics_handles_malformed_and_missing_dates(analyzed_transactions):
    """Ensures corrupt or missing completion times are safely bucketed as 'Unknown' instead of crashing."""
    corrupt_data = analyzed_transactions.copy()
    # Inject malformed and missing date entries
    corrupt_data.loc[0, "completion_time"] = "Malformed Date String"
    corrupt_data.loc[2, "completion_time"] = None
    
    summary = calculate_monthly_expenditure(corrupt_data)
    summary_indexed = summary.set_index("month")
    
    # The unmodified August entry should survive perfectly
    assert summary_indexed.loc["2026-08", "total"] == 2000.0
    
    # The broken rows (1000.0 + 29.0) should accumulate safely into an 'Unknown' categorization bucket
    assert summary_indexed.loc["Unknown", "total"] == 1029.0

def test_frequent_merchants_counting(analyzed_transactions):
    """Verifies that entities are ranked by transaction count descending."""
    from src.analytics import get_frequent_merchants
    
    # KPLC appears 2 times in our fixture, Naivas appears 1 time
    frequency_df = get_frequent_merchants(analyzed_transactions, top_n=2)
    
    assert len(frequency_df) == 2
    
    # KPLC 888888 must be #1 because it has the highest frequency (velocity)
    assert frequency_df.iloc[0]['details'] == 'KPLC 888888'
    assert frequency_df.iloc[0]['transaction_count'] == 2
    
    assert frequency_df.iloc[1]['details'] == 'Naivas Supermarket'
    assert frequency_df.iloc[1]['transaction_count'] == 1
