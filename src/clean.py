import pandas as pd

from src.normalize import normalize_name
from src.utils import parse_currency


def clean_mpesa_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Cleans and standardizes an M-Pesa transaction DataFrame."""
    if df.empty:
        return df

    cleaned_df = _filter_invalid_receipt_rows(df)
    cleaned_df = _parse_numeric_columns(cleaned_df)
    cleaned_df = _normalize_transaction_details(cleaned_df)
    cleaned_df = _align_engine_column_schema(cleaned_df)
    
    return cleaned_df.reset_index(drop=True)


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

def _align_engine_column_schema(df:pd.DataFrame) ->pd.DataFrame:
    """Ensures the accounting engine receives its expected field nomenclature.
    Orcherstrates the consolidation of fund vectors."""
    df = df.copy()
    df['Withdrawn'] = _build_unified_monetary_series(df)
    return df 

def _build_unified_monetary_series(df:pd.DataFrame) -> pd.Series:
    """Combines extracted financial paths into one structured sequence."""
    paid_out = _extract_safe_series(df, column_name='Paid Out')
    paid_in = _extract_safe_series(df, column_name='Paid In')

    return _merge_vectors_with_fallback(paid_out, fallback_vector=paid_in)


def _extract_safe_series(
    df:pd.DataFrame,
    column_name:str) -> pd.Series:
    """Safely extracts a column sequence , replacing nulls with zero floats."""
    raw_series = df.get(column_name, pd.Series(0.0, index=df.index))
    return raw_series.fillna(0.0)


def _merge_vectors_with_fallback(
    primary_vector:pd.Series,
    fallback_vector:pd.Series) -> pd.Series:
    """Selects the primary value ,dropping down to the fallback is zero."""
    return primary_vector.where(primary_vector != 0.0,fallback_vector)