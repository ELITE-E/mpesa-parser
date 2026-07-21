import pandas as pd


def process_engine(df: pd.DataFrame) -> pd.DataFrame:
    """
    Applies transactional accounting rules to calculate true expenditure metrics.
    Orchestrates categorization, fee attribution, and ledger modifications.
    """
    if df.empty:
        return df

    processed = _initialize_accounting_columns(df)
    processed["Category"] = processed["Details"].apply(_categorize_transaction)
    processed = _attribute_sequential_fees(processed)

    return processed


def calculate_transfer_efficiency(df: pd.DataFrame) -> float:
    """
    Calculates the 'Transfer Efficiency' metric:
    (Total Fees / Total Economic Expenditure) * 100
    """
    total_fees = _sum_absorbed_transaction_fees(df)
    total_expenditure = df["Total Cost"].sum()

    if total_expenditure == 0.0:
        return 0.0

    return (total_fees / total_expenditure) * 100


def _initialize_accounting_columns(df: pd.DataFrame) -> pd.DataFrame:
    processed = df.copy()
    processed["Total Cost"] = processed["Withdrawn"].astype(float)
    return processed


def _categorize_transaction(details: str) -> str:
    """Evaluates text rules to flag standard financial movements."""
    details_upper = str(details).upper()

    if "FULIZA RECOVERY" in details_upper:
        return "REPAYMENT"
    if "CHARGE" in details_upper or "FEE" in details_upper:
        return "FEE"
    if any(
        kw in details_upper
        for kw in ["PAY BILL", "BUY GOODS", "KPLC", "NAIVAS", "TILL"]
    ):
        return "PURCHASE"

    return "OTHER"


def _attribute_sequential_fees(df: pd.DataFrame) -> pd.DataFrame:
    """
    Links orphan fee entries back to their preceding parent transaction
    if they share a matching Receipt Number.
    """
    for current_idx in range(1, len(df)):
        parent_idx = current_idx - 1

        current_row = df.iloc[current_idx]
        parent_row = df.iloc[parent_idx]

        if _is_child_fee_of_parent(current_row, parent_row):
            fee_amount = float(current_row["Withdrawn"])

            # Absorb fee into parent total cost, strip cost from orphan row
            df.at[df.index[parent_idx], "Total Cost"] += fee_amount
            df.at[df.index[current_idx], "Total Cost"] = 0.0

    return df


def _is_child_fee_of_parent(current_row: pd.Series, parent_row: pd.Series) -> bool:
    is_fee = current_row["Category"] == "FEE"
    is_same_receipt = current_row["Receipt No."] == parent_row["Receipt No."]
    return is_fee and is_same_receipt


def _sum_absorbed_transaction_fees(df: pd.DataFrame) -> float:
    fee_rows = df[df["Category"] == "FEE"]
    return float(fee_rows["Withdrawn"].sum())
