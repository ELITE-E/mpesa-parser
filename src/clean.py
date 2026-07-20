import pandas as pd

from src.normalize import normalize_name
from src.utils import parse_currency


def clean_mpesa_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Cleans and standardizes an M-Pesa transaction DataFrame."""
    if df.empty:
        return df

    cleaned_df = _filter_invalid_receipt_rows(df)
    cleaned_df = _parse_numeric_columns(cleaned_df)
    return _normalize_transaction_details(cleaned_df).reset_index(drop=True)


def _filter_invalid_receipt_rows(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(subset=["Receipt No."]).copy()
    df = df[df["Receipt No."].str.strip() != ""]
    return df[df["Receipt No."] != "Receipt No."]


def _parse_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    numeric_cols = ["Paid In", "Paid Out", "Balance"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].apply(parse_currency)
    return df


def _normalize_transaction_details(df: pd.DataFrame) -> pd.DataFrame:
    if "Details" in df.columns:
        df["Details"] = df["Details"].apply(normalize_name)
    return df
