from typing import List, Optional
import logging
import pdfplumber
import pandas as pd

logger = logging.getLogger(__name__)
MANDATORY_COLUMNS = ['Receipt No.', 'Completion Time', 
               'Details', 'Paid In', 'Paid Out', 'Balance'
               ]

def extract_table_from_pdf(pdf_path: str) -> pd.DataFrame:
    """Orchestrates the extraction process and handles any runtime exceptions."""
    try:
        return _execute_table_extraction(pdf_path)
    except Exception as error:
        _log_extraction_failure(pdf_path, error)
        return pd.DataFrame(columns=MANDATORY_COLUMNS)

def _execute_table_extraction(pdf_path: str) -> pd.DataFrame:
    raw_rows = _extract_raw_rows_from_pdf(pdf_path)
    if not raw_rows:
        return pd.DataFrame(columns=MANDATORY_COLUMNS)

    cleaned_rows = _filter_and_clean_rows(raw_rows)
    df = pd.DataFrame(cleaned_rows, columns=MANDATORY_COLUMNS)
    return _ensure_mandatory_columns(df)

def _extract_raw_rows_from_pdf(pdf_path: str) -> List[List[Optional[str]]]:
    raw_rows = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if table:
                raw_rows.extend(table)
    return raw_rows

def _filter_and_clean_rows(raw_rows: List[List[Optional[str]]]) -> List[List[Optional[str]]]:
    cleaned_rows = []
    for row in raw_rows:
        cleaned_row = [str(cell).replace('\n', ' ').strip() if cell else None for cell in row]
        if "Receipt No." in cleaned_row:
            continue
        cleaned_rows.append(cleaned_row)
    return cleaned_rows

def _ensure_mandatory_columns(df: pd.DataFrame) -> pd.DataFrame:
    for col in MANDATORY_COLUMNS:
        if col not in df.columns:
            df[col] = None
    return df[MANDATORY_COLUMNS]

def _log_extraction_failure(pdf_path: str, error: Exception) -> None:
    logger.error(f"Failed to extract PDF {pdf_path}: {error}")
