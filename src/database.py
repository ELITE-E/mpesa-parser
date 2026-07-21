import logging
import sqlite3

import pandas as pd

logger = logging.getLogger(__name__)


_TRANSACTIONS_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    receipt_no TEXT PRIMARY KEY,
    completion_time TEXT,
    details TEXT,
    category TEXT,
    paid_in REAL,
    withdrawn REAL,
    total_cost REAL,
    balance REAL
);
"""

_DF_TO_DB_COLUMN_MAPPING = {
    "Receipt No.": "receipt_no",
    "Completion Time": "completion_time",
    "Details": "details",
    "Category": "category",
    "Paid In": "paid_in",
    "Withdrawn": "withdrawn",
    "Total Cost": "total_cost",
    "Balance": "balance",
}


_UPSERT_TRANSACTIONS_QUERY = """
INSERT INTO transactions (
    receipt_no, completion_time, details, category,
    paid_in, withdrawn, total_cost, balance
) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(receipt_no) DO UPDATE SET
    completion_time = EXCLUDED.completion_time,
    details = EXCLUDED.details,
    category = EXCLUDED.category,
    paid_in = EXCLUDED.paid_in,
    withdrawn = EXCLUDED.withdrawn,
    total_cost = EXCLUDED.total_cost,
    balance = EXCLUDED.balance;
"""
_DB_SCHEMA_COLUMNS = [
    "receipt_no",
    "completion_time",
    "details",
    "category",
    "paid_in",
    "withdrawn",
    "total_cost",
    "balance",
]


def init_db(db_path: str = "mpesa.db") -> None:
    """
    Acts strictly as an error boundary for database initialization.
    """
    try:
        _execute_schema_initialization(db_path)
    except sqlite3.Error as error:
        _log_and_raise_db_failure(error)


def _execute_schema_initialization(db_path: str) -> None:
    """Executes the connection and runs table schema generation definitions."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(_TRANSACTIONS_TABLE_SCHEMA)
        conn.commit()


def _log_and_raise_db_failure(error: sqlite3.Error) -> None:
    logger.error(f"Database initialization failed: {error}")
    raise error


def save_transactions(df: pd.DataFrame, db_path: str = "mpesa.db") -> None:
    """
    Acts strictly as an error boundary and entry point for persisting transactions.
    """
    if df.empty:
        return

    try:
        _execute_batch_upsert(df, db_path)
    except sqlite3.Error as error:
        _log_and_raise_save_failure(error)


def _execute_batch_upsert(df: pd.DataFrame, db_path: str) -> None:
    """Transforms dataframe to align with database naming conventions and saves it."""
    db_ready_df = _prepare_dataframe_for_storage(df)
    transaction_records = db_ready_df.values.tolist()

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.executemany(_UPSERT_TRANSACTIONS_QUERY, transaction_records)
        conn.commit()

    logger.info(f"Successfully processed {len(transaction_records)} financial records.")


def _prepare_dataframe_for_storage(df: pd.DataFrame) -> pd.DataFrame:
    """Maps, standardizes, and reorders dataframe to match table layout."""
    renamed_df = df.rename(columns=_DF_TO_DB_COLUMN_MAPPING)

    # Ensure all target columns exist, filling missing fields with defaults
    for db_column in _DF_TO_DB_COLUMN_MAPPING.values():
        if db_column not in renamed_df.columns:
            renamed_df[db_column] = None

    # Return with columns strictly matching the order in _UPSERT_TRANSACTIONS_QUERY
    expected_order = list(_DF_TO_DB_COLUMN_MAPPING.values())
    return renamed_df[expected_order]


def _log_and_raise_save_failure(error: sqlite3.Error) -> None:
    logger.error(f"Failed to save transactions: {error}")
    raise error


def get_all_transactions(db_path: str = "mpesa.db") -> pd.DataFrame:
    """
    Acts strictly as an error boundary for fetching database records.
    """
    try:
        return _execute_transactions_query(db_path)
    except sqlite3.Error as error:
        _log_query_warning(error)
        return pd.DataFrame(columns=_DB_SCHEMA_COLUMNS)


def _execute_transactions_query(db_path: str) -> pd.DataFrame:
    """
    Performs the read query and explicitly terminates file handles
    to prevent memory and file lock leaks.
    """
    query = "SELECT * FROM transactions"
    conn = sqlite3.connect(db_path)

    try:
        return pd.read_sql_query(query, conn)
    finally:
        conn.close()


def _log_query_warning(error: sqlite3.Error) -> None:
    logger.warning(f"Could not retrieve transactions from ledger: {error}")
