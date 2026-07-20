from unittest.mock import MagicMock, patch

import pandas as pd

from src.pipeline import process_mpesa_statement


@patch("pdfplumber.open")
def test_end_to_end_pipeline_integration(mock_pdf_open):
    """
    Simulates loading a multi-page PDF document and asserts that
    extracted strings are structurally mapped, cleaned, and normalized.
    """
    # 1. Setup Mock PDF Engine Output
    mock_pdf = MagicMock()
    mock_page_1 = MagicMock()

    # Mock data layout coming out of a raw pdf table extraction
    mock_page_1.extract_table.return_value = [
        ["Receipt No.", "Completion Time", "Details", "Paid In", "Paid Out", "Balance"],
        [
            "QA11111111",
            "2026-01-01",
            "Till - 5555 - Grocery Shop",
            "KSh 150.00",
            "",
            "150.00",
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

    # 2. Execute full package pipeline
    result_df = process_mpesa_statement("fake_path_to_statement.pdf")

    # 3. Structural Assertions
    assert isinstance(result_df, pd.DataFrame)
    assert len(result_df) == 2

    # 4. Core Transformation Assertions
    # First Row: Till Rule + Currency conversion verification
    assert result_df.loc[0, "Details"] == "Grocery Shop 5555"
    assert result_df.loc[0, "Paid In"] == 150.0

    # Second Row: P2P Rule + Comma/Currency separation verification
    assert result_df.loc[1, "Details"] == "Jane Doe"
    assert result_df.loc[1, "Paid Out"] == 2500.0
