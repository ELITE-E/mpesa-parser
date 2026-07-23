from io import BytesIO
from typing import Tuple
import pandas as pd
from src.security import verify_pdf_magic_bytes, decrypt_pdf_in_memory, attest_mpesa_structure
from src.extract import extract_table_from_pdf
from src.clean import clean_mpesa_dataframe
from src.engine import process_engine
from src.database import save_transactions

def process_mpesa_statement(pdf_path: str, password: str = None) -> Tuple[pd.DataFrame, str]:
    """
    Securely validates, decrypts, and processes an M-Pesa file.
    Returns a Tuple containing: final_processed_dataframe, verification_token_string
    """
    
    with open(pdf_path, "rb") as file_handle:
        file_stream = BytesIO(file_handle.read())
    
    verify_pdf_magic_bytes(file_stream)
    decrypted_stream = decrypt_pdf_in_memory(file_stream, password)
    verification_token = attest_mpesa_structure(decrypted_stream)
    
    
    # TODO: Update extract_table_from_pdf to accept either file paths or open streams
    raw_dataframe = extract_table_from_pdf(decrypted_stream)
    cleaned_dataframe = clean_mpesa_dataframe(raw_dataframe)
    final_dataframe = process_engine(cleaned_dataframe)
    
    return final_dataframe, verification_token

def ingest_statement_to_ledger(pdf_path: str, password: str = None, db_path: str = "mpesa.db") -> Tuple[int, str]:
    """
    Securely ingests a file and persists valid rows to the database.
    Returns a Tuple containing: (records_saved_count, verification_token_string)
    """
    processed_df, verification_token = process_mpesa_statement(pdf_path, password)
    
    if processed_df.empty:
        return 0, ""
        
    save_transactions(processed_df, db_path=db_path)
    return len(processed_df), verification_token