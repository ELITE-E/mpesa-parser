import sqlite3

import pandas as pd
import pytest

from src.database import get_all_transactions, init_db, save_transactions


@pytest.fixture
def temp_db(tmp_path):
    """Creates an isolated temporary SQLite database for testing (Clean Boundary)."""
    db_path = tmp_path / "test_mpesa.db"
    init_db(str(db_path))
    return str(db_path)


def test_db_schema_integrity(temp_db):
    """Verifies that all columns, including newly
    supported fields, exist.
    """
    with sqlite3.connect(temp_db) as conn:
        cursor = conn.cursor()

        # 1. Assert table existence
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='transactions';"
        )
        assert cursor.fetchone() is not None, "Transactions table missing"

        # 2. Assert complete database schema column alignment
        cursor.execute("PRAGMA table_info(transactions);")
        columns = [col[1] for col in cursor.fetchall()]

    expected_columns = [
        "receipt_no",
        "completion_time",
        "details",
        "category",
        "paid_in",
        "withdrawn",
        "total_cost",
        "balance",
    ]
    for col in expected_columns:
        assert col in columns, f"Missing critical schema layout column: {col}"


def test_upsert_idempotency_and_overwrites(temp_db):
    """Verifies that duplicate entries trigger safe
    upserts without inflating row counts.
    """
    mock_row = {
        "Receipt No.": "UGHP6BML95",
        "Completion Time": "2026-07-17 21:55:45",
        "Details": "KPLC 888888",
        "Category": "PURCHASE",
        "Paid In": 0.0,
        "Withdrawn": 10.0,
        "Total Cost": 10.0,
        "Balance": 500.0,
    }

    # Save base mock record
    save_transactions(pd.DataFrame([mock_row]), db_path=temp_db)

    # Simulate a second import where something changed
    # (e.g. fee calculations updated 'Total Cost')
    updated_row = mock_row.copy()
    updated_row["Total Cost"] = 12.0
    save_transactions(pd.DataFrame([updated_row]), db_path=temp_db)

    saved_df = get_all_transactions(db_path=temp_db)

    assert len(saved_df) == 1, (
        "Primary Key constraint failed: Duplicate records created"
    )
    assert saved_df.loc[0, "total_cost"] == 12.0, (
        "Upsert failed to overwrite outdated transaction state"
    )


def test_save_transactions_handles_empty_dataframe(temp_db):
    """Defensive boundary check confirming empty datasets
    exit cleanly without crashes."""
    empty_df = pd.DataFrame()
    save_transactions(empty_df, db_path=temp_db)

    saved_df = get_all_transactions(db_path=temp_db)
    assert saved_df.empty


def test_get_all_transactions_returns_empty_dataframe_on_fresh_db(temp_db):
    """Ensures query engine returns a valid, empty typed
    dataframe structure when no rows exist."""
    saved_df = get_all_transactions(db_path=temp_db)
    assert isinstance(saved_df, pd.DataFrame)
    assert saved_df.empty
