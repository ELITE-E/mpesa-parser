import pandas as pd


def calculate_monthly_expenditure(df: pd.DataFrame) -> pd.DataFrame:
    """
    Groups transactions by Year-Month and sums the total economic cost.
    Orchestrates date standardization, parsing boundaries, and aggregations.
    """
    if df.empty:
        return pd.DataFrame(columns=["month", "total"])

    processed_df = df.copy()
    processed_df["month"] = _extract_standardized_months(processed_df)

    return _aggregate_cost_by_month(processed_df)


def _extract_standardized_months(df: pd.DataFrame) -> pd.Series:
    """
    Converts timestamps into standard YYYY-MM strings.
    Gracefully catches malformed or null values and places them in an 'Unknown' bucket.
    """
    # Defensive namespace fallback selector
    raw_dates = (
        df["completion_time"]
        if "completion_time" in df.columns
        else df["Completion Time"]
    )

    # coerce turning errors into NaT (Not a Time) instead of crashing
    datetime_series = pd.to_datetime(
        raw_dates, format="%Y-%m-%d %H:%M:%S", errors="coerce"
    )

    # Format valid dates to strings, filling missing/corrupt values with 'Unknown'
    month_strings = datetime_series.dt.strftime("%Y-%m")
    return month_strings.fillna("Unknown")


def _aggregate_cost_by_month(df: pd.DataFrame) -> pd.DataFrame:
    """Groups dataset by month slices and computes total expenditure."""
    target_cost_col = "total_cost" if "total_cost" in df.columns else "Total Cost"

    summary = df.groupby("month")[target_cost_col].sum().reset_index()
    summary.columns = ["month", "total"]

    return summary


def get_heavy_hitters(df: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    """
    Identifies the top N entities/merchants by total capital spent.
    """
    if df.empty:
        return pd.DataFrame(columns=["details", "total_cost"])

    aggregated_df = _calculate_merchant_expenditure_totals(df)
    ranked_df = _rank_expenditure_descending(aggregated_df)

    return ranked_df.head(top_n)


def _calculate_merchant_expenditure_totals(df: pd.DataFrame) -> pd.DataFrame:
    """Groups dataset by recipient entity and returns un-sorted summed aggregates."""
    details_col = "details" if "details" in df.columns else "Details"
    cost_col = "total_cost" if "total_cost" in df.columns else "Total Cost"

    totals_df = df.groupby(details_col)[cost_col].sum().reset_index()
    totals_df.columns = ["details", "total_cost"]
    return totals_df


def _rank_expenditure_descending(df: pd.DataFrame) -> pd.DataFrame:
    """Sorts a standardized totals dataframe to place largest expenses at the top."""
    ranked_df = df.sort_values(by="total_cost", ascending=False)
    return ranked_df.reset_index(drop=True)


def get_frequent_merchants(df: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    """
    Identifies the top N entities by frequency of interactions (velocity).
    """
    if df.empty:
        return pd.DataFrame(columns=["details", "transaction_count"])

    counted_df = _calculate_merchant_interaction_frequencies(df)
    ranked_df = _rank_frequency_descending(counted_df)

    return ranked_df.head(top_n)


def _calculate_merchant_interaction_frequencies(df: pd.DataFrame) -> pd.DataFrame:
    """Groups dataset by recipient entity and returns interaction counts."""
    details_col = "details" if "details" in df.columns else "Details"
    receipt_col = "receipt_no" if "receipt_no" in df.columns else "Receipt No."

    # Aggregate by size to get row frequency counts
    freq_df = df.groupby(details_col)[receipt_col].count().reset_index()
    freq_df.columns = ["details", "transaction_count"]
    return freq_df


def _rank_frequency_descending(df: pd.DataFrame) -> pd.DataFrame:
    """Sorts a standardized frequency dataframe from most to least frequent."""
    ranked_df = df.sort_values(by="transaction_count", ascending=False)
    return ranked_df.reset_index(drop=True)
