# tests/test_app.py
from io import BytesIO

import pytest

from src.app import format_currency_display, validate_uploaded_file


@pytest.mark.parametrize(
    "raw_value, expected_string",
    [
        (1500.5, "KSh 1,500.50"),
        (0.0, "KSh 0.00"),
        (-500.00, "-KSh 500.00"),  # Financial reversal representation boundary
        (None, "KSh 0.00"),  # Null data handling guard
    ],
)
def test_currency_formatting(raw_value, expected_string):
    """Ensures raw data types format cleanly
    into professional financial currency strings."""
    assert format_currency_display(raw_value) == expected_string


def test_file_validation_rejects_non_pdfs():
    """Ensures the app security framework catches and blocks incorrect file types."""
    # Build a proper file buffer object matching standard framework engines
    mock_txt_file = BytesIO(b"Fake raw text content data statement data string")
    mock_txt_file.name = "mpesa_statement.txt"

    assert validate_uploaded_file(mock_txt_file) is False


def test_file_validation_accepts_valid_pdfs():
    """Ensures true statement documents
    pass cleanly through boundary verification gates."""
    # Build a mock PDF file buffer with standard PDF headers
    mock_pdf_file = BytesIO(b"%PDF-1.4 mock pdf structure bytes stream")
    mock_pdf_file.name = "MPESA_Statement_2026.pdf"

    assert validate_uploaded_file(mock_pdf_file) is True
