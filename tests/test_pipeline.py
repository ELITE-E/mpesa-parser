from unittest.mock import patch, MagicMock, mock_open
from io import BytesIO
import pytest
import pypdf
import pandas as pd
from src.pipeline import process_mpesa_statement, ingest_statement_to_ledger


def _generate_authentic_mock_pdf_bytes(token: str = "JRZ3TLGT") -> bytes:
    """Generates valid, unencrypted PDF layout bytes containing the M-Pesa token."""
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=200, height=200)
    
    authentic_text = (
        "Safaricom M-PESA Statement\n"
        f"To verify the validity of this M-PESA statement dial *334#, select My account "
        f"and follow the prompts to enter the code. {token}"
    )
    writer.add_metadata({"/Comment": authentic_text})
    
    stream = BytesIO()
    writer.write(stream)
    return stream.getvalue()



@patch("pdfplumber.open")
def test_end_to_end_pipeline_integration(mock_pdfplumber_open):
    """Verifies text extraction, cleaning, and fee attribution on verified streams."""
    # 1. Setup Mock pdfplumber tabular layout response
    mock_pdf = MagicMock()
    mock_page_1 = MagicMock()
    mock_page_1.extract_table.return_value = [
        ["Receipt No.", "Completion Time", "Details", "Paid In", "Paid Out", "Balance"],
        ["QA11111111", "2026-01-01 12:00:00", "Till - 5555 - Naivas", "KSh 150.00", "", "150.00"],
        ["QA11111111", "2026-01-01 12:01:00", "Customer Transfer of Funds Charge", "", "KSh 7.00", "143.00"],
        ["QA22222222", "2026-01-02 14:00:00", "Sent to 0712345678 Jane Doe", "", "KSh 2,500.00", "0.00"]
    ]
    mock_pdf.pages = [mock_page_1]
    mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

    valid_pdf_bytes = _generate_authentic_mock_pdf_bytes(token="JRZ3TLGT")
    
    with patch("builtins.open", mock_open(read_data=valid_pdf_bytes)):
        result_df, token = process_mpesa_statement("fake_statement.pdf")

    
    assert token == "JRZ3TLGT"

    
    assert isinstance(result_df, pd.DataFrame)
    assert len(result_df) == 3

    
    assert result_df.loc[0, "details"] == "Naivas 5555"
    assert result_df.loc[0, "category"] == "PURCHASE"
    assert result_df.loc[0, "total_cost"] == 157.0  # 150.00 base + 7.00 fee absorbed
    assert result_df.loc[1, "total_cost"] == 0.0    # Original fee container zeroed
    assert result_df.loc[2, "details"] == "Jane Doe"


@pytest.fixture
def test_pipeline_db(tmp_path):
    """Creates a temporary database specifically for pipeline integration tests."""
    from src.database import init_db
    db_path = tmp_path / "pipeline_integration.db"
    init_db(str(db_path))
    return str(db_path)


@pytest.mark.filterwarnings("ignore::ResourceWarning")
@patch("pdfplumber.open")
def test_ingest_statement_to_ledger_writes_to_database(mock_pdfplumber_open, test_pipeline_db):
    """Verifies that data flowing through the secure pipeline successfully reaches SQL tables."""
    # 1. Setup Mock pdfplumber tabular response
    mock_pdf = MagicMock()
    mock_page_1 = MagicMock()
    mock_page_1.extract_table.return_value = [
        ["Receipt No.", "Completion Time", "Details", "Paid In", "Paid Out", "Balance"],
        ["QA99999999", "2026-01-01 10:00:00", "Till - 1234 - Naivas Supermarket", "KSh 500.00", "", "500.00"]
    ]
    mock_pdf.pages = [mock_page_1]
    mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

    
    valid_pdf_bytes = _generate_authentic_mock_pdf_bytes(token="ABC23XYZ")
    
    with patch("builtins.open", mock_open(read_data=valid_pdf_bytes)):
        rows_processed, token = ingest_statement_to_ledger("fake_statement.pdf", db_path=test_pipeline_db)

    
    assert rows_processed == 1
    assert token == "ABC23XYZ"

    
    from src.database import get_all_transactions
    saved_records_df = get_all_transactions(db_path=test_pipeline_db)
    print(saved_records_df)
    
    assert not saved_records_df.empty
    assert saved_records_df.loc[0, "receipt_no"] == "QA99999999"
    assert saved_records_df.loc[0, "details"] == "Naivas Supermarket 1234"


@patch("pdfplumber.open")
def test_pipeline_to_analytics_integration(mock_pdfplumber_open):
    """Verifies that pipeline data outputs plug smoothly into analytics modules without layout exceptions."""
    mock_pdf = MagicMock()
    mock_page_1 = MagicMock()
    mock_page_1.extract_table.return_value = [
        ["Receipt No.", "Completion Time", "Details", "Paid In", "Paid Out", "Balance"],
        ["QA11111111", "2026-07-01 10:00:00", "Till - 5555 - Naivas Supermarket", "KSh 5,000.00", "", "5000.00"],
        ["QA11111111", "2026-07-01 10:05:00", "Customer Transfer of Funds Charge", "", "KSh 29.00", "4971.00"]
    ]
    mock_pdf.pages = [mock_page_1]
    mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

    
    valid_pdf_bytes = _generate_authentic_mock_pdf_bytes(token="ANALYTICS")
    
    with patch("builtins.open", mock_open(read_data=valid_pdf_bytes)):
        cleaned_df, _ = process_mpesa_statement("fake_statement.pdf")

    
    from src.analytics import calculate_monthly_expenditure, get_heavy_hitters
    monthly_summary = calculate_monthly_expenditure(cleaned_df)
    heavy_hitters = get_heavy_hitters(cleaned_df, top_n=1)

    
    monthly_indexed = monthly_summary.set_index("month")
    assert "2026-07" in monthly_indexed.index
    assert monthly_indexed.loc["2026-07", "total"] == 5029.0  

    assert len(heavy_hitters) == 1
    assert heavy_hitters.loc[0, "details"] == "Naivas Supermarket 5555"
    assert heavy_hitters.loc[0, "total_cost"] == 5029.0
