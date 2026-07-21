from src.clean import clean_mpesa_dataframe
from src.database import save_transactions
from src.engine import process_engine
from src.extract import extract_table_from_pdf


def process_mpesa_statement(pdf_path: str):
    raw_dataframe = extract_table_from_pdf(pdf_path)
    clean_data_frame = clean_mpesa_dataframe(raw_dataframe)
    final_dataframe = process_engine(clean_data_frame)

    return final_dataframe


def ingest_statement_to_ledger(pdf_path: str, db_path: str = "mpesa.db") -> None:
    """
    Orchestrates the parsing and persists the results.
    """
    processed_df = process_mpesa_statement(pdf_path)
    save_transactions(processed_df, db_path=db_path)
