from src.clean import clean_mpesa_dataframe
from src.extract import extract_table_from_pdf
from src.engine import process_engine


def process_mpesa_statement(pdf_path: str):
    raw_dataframe = extract_table_from_pdf(pdf_path)
    clean_data_frame = clean_mpesa_dataframe(raw_dataframe)
    final_dataframe = process_engine(clean_data_frame)

    return final_dataframe
