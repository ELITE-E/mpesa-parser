from src.clean import clean_mpesa_dataframe
from src.extract import extract_table_from_pdf

def process_mpesa_statement(pdf_path: str):
	raw_dataframe = extract_table_from_pdf(pdf_path)
	return clean_mpesa_dataframe(raw_dataframe)
