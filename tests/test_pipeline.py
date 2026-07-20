from unittest.mock import MagicMock, patch
import pandas as pd
from src.pipeline import process_mpesa_statement

@patch("pdfplumber.open")
def test_end_to_end_pipeline_integration(mock_pdf_open):
    """
    Simulates loading a multi-page PDF document and asserts that 
    extracted strings are structurally mapped, cleaned, normalized,
    and accurately quantified by the accounting engine.
    """
    # 1. Setup Mock PDF Engine Output
    mock_pdf = MagicMock()
    mock_page_1 = MagicMock()
    
    # We provide a realistic sequential dataset: A transaction row followed by a fee row
    mock_page_1.extract_table.return_value = [
        ["Receipt No.", "Completion Time", "Details", "Paid In", "Paid Out", "Balance"],
        ["QA11111111", "2026-01-01", "Till - 5555 - Naivas", "KSh 150.00", "", "150.00"],
        ["QA11111111", "2026-01-01", "Customer Transfer of Funds Charge", "", "KSh 7.00", "143.00"],
        ["QA22222222", "2026-01-02", "Sent to 0712345678 Jane Doe", "", "KSh 2,500.00", "0.00"]
    ]
    
    mock_pdf.pages = [mock_page_1]
    mock_pdf_open.return_value.__enter__.return_value = mock_pdf

    # 2. Execute the actual system package pipeline
    # Note: If your clean.py merges Paid In/Paid Out into a column named 'Withdrawn' for the engine,
    # this integration path tests that conversion automatically.
    result_df = process_mpesa_statement("fake_path_to_statement.pdf")

    # 3. Structural Assertions
    assert isinstance(result_df, pd.DataFrame)
    assert len(result_df) == 3  # All three non-header rows must survive extraction and cleaning

    # 4. Phase 2: Core Text Normalization Assertions
    assert result_df.loc[0, "Details"] == "Naivas 5555"
    assert result_df.loc[2, "Details"] == "Jane Doe"

    # 5. Phase 3: Accounting Engine Categorization Assertions
    assert result_df.loc[0, "Category"] == "PURCHASE"
    assert result_df.loc[1, "Category"] == "FEE"
    assert result_df.loc[2, "Category"] == "OTHER"  # Standard P2P context

    # 6. Phase 3: Sequential Fee Absorption Assertions
    # The 7.00 charge (row 1) must be absorbed into the Grocery Shop purchase (row 0)
    assert result_df.loc[0, "Total Cost"] == 157.0  # 150.00 base + 7.00 fee
    assert result_df.loc[1, "Total Cost"] == 0.0    # Orphan child fee row zeroed out
    assert result_df.loc[2, "Total Cost"] == 2500.0 # Standard transfer amount preserved
