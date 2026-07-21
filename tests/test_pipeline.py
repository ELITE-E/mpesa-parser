from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.database import get_all_transactions
from src.pipeline import ingest_statement_to_ledger, process_mpesa_statement
from src.analytics import calculate_monthly_expenditure, get_heavy_hitters


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
        [
            "QA11111111",
            "2026-01-01",
            "Till - 5555 - Naivas",
            "KSh 150.00",
            "",
            "150.00",
        ],
        [
            "QA11111111",
            "2026-01-01",
            "Customer Transfer of Funds Charge",
            "",
            "KSh 7.00",
            "143.00",
        ],
        [
            "QA22222222",
            "2026-01-02",
            "Sent to 0712345678 Jane Doe",
            "",
            "KSh 2,500.00",
            "0.00",
        ],
    ]

    mock_pdf.pages = [mock_page_1]
    mock_pdf_open.return_value.__enter__.return_value = mock_pdf

    # 2. Execute the actual system package pipeline
    # Note: If your clean.py merges Paid In/Paid Out into a column named
    #  'Withdrawn' for the engine,
    # this integration path tests that conversion automatically.
    result_df = process_mpesa_statement("fake_path_to_statement.pdf")

    # 3. Structural Assertions
    assert isinstance(result_df, pd.DataFrame)
    assert (
        len(result_df) == 3
    )  # All three non-header rows must survive extraction and cleaning

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
    assert result_df.loc[1, "Total Cost"] == 0.0  # Orphan child fee row zeroed out
    assert (
        result_df.loc[2, "Total Cost"] == 2500.0
    )  # Standard transfer amount preserved


@pytest.fixture
def test_pipeline_db(tmp_path):
    """Creates a temporary database for tests"""
    from src.database import init_db

    db_path = tmp_path / "pipeline_integration.db"

    init_db(str(db_path))
    return str(db_path)


@pytest.mark.filterwarnings("ignore::ResourceWarning")
@patch("pdfplumber.open")
def test_ingest_statement_to_ledger_writes_to_database(mock_pdf_open, test_pipeline_db):
    """
    Verifies that data flowing through ingest_statement_to_ledger
    reaches the physical database tables successfully.
    """
    # 1. Setup Mock PDF Table Structure
    mock_pdf = MagicMock()
    mock_page_1 = MagicMock()
    mock_page_1.extract_table.return_value = [
        ["Receipt No.", "Completion Time", "Details", "Paid In", "Paid Out", "Balance"],
        [
            "QA99999999",
            "2026-01-01",
            "Till - 1234 - Naivas Supermarket",
            "KSh 500.00",
            "",
            "500.00",
        ],
    ]
    mock_pdf.pages = [mock_page_1]
    mock_pdf_open.return_value.__enter__.return_value = mock_pdf

    # 2. Run the Command to process and write directly to our temp database
    ingest_statement_to_ledger("fake_statement.pdf", db_path=test_pipeline_db)

    # 3. Read back from the database to prove it saved correctly
    saved_records_df = get_all_transactions(db_path=test_pipeline_db)

    # 4. Assertions
    assert not saved_records_df.empty
    assert len(saved_records_df) == 1
    assert saved_records_df.loc[0, "receipt_no"] == "QA99999999"
    assert saved_records_df.loc[0, "details"] == "Naivas Supermarket 1234"
    assert saved_records_df.loc[0, "category"] == "PURCHASE"
    assert saved_records_df.loc[0, "total_cost"] == 500.0

@patch("pdfplumber.open")

def test_pipeline_to_analytics_integration(mock_pdf_open):
    """
    Verifies that the clean output from the main pipeline is completely 
    compatible with the data requirements of the analytics module.
    """
    # 1. Setup Mock Multi-Page PDF output containing an expenditure and an associated fee
    mock_pdf = MagicMock()
    mock_page_1 = MagicMock()
    mock_page_1.extract_table.return_value = [
        ["Receipt No.", "Completion Time", "Details", "Paid In", "Paid Out", "Balance"],
        ["QA11111111", "2026-07-01 10:00:00", "Till - 5555 - Naivas Supermarket", "KSh 5,000.00", "", "5000.00"],
        ["QA11111111", "2026-07-01 10:05:00", "Customer Transfer of Funds Charge", "", "KSh 29.00", "4971.00"]
    ]
    mock_pdf.pages = [mock_page_1]
    mock_pdf_open.return_value.__enter__.return_value = mock_pdf

    # 2. Execute the in-memory data processing pipeline
    cleaned_df = process_mpesa_statement("fake_statement.pdf")

    # 3. Pass pipeline data output directly into the analytics engines
    monthly_summary = calculate_monthly_expenditure(cleaned_df)
    heavy_hitters = get_heavy_hitters(cleaned_df, top_n=1)

    # 4. Assert Monthly Summary Insights (5000.00 base + 29.00 fee = 5029.0)
    monthly_indexed = monthly_summary.set_index("month")
    assert "2026-07" in monthly_indexed.index
    assert monthly_indexed.loc["2026-07", "total"] == 5029.0

    # 5. Assert Heavy Hitter Structural Output
    assert len(heavy_hitters) == 1
    assert heavy_hitters.iloc[0]["details"] == "Naivas Supermarket 5555"
    assert heavy_hitters.iloc[0]["total_cost"] == 5029.0
