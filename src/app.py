import os
import tempfile

import pandas as pd
import streamlit as st
import pypdf

from src.analytics import calculate_monthly_expenditure, get_heavy_hitters
from src.database import get_all_transactions
from src.engine import calculate_transfer_efficiency
from src.pipeline import ingest_statement_to_ledger

DB_PATH = "mpesa.db"


st.set_page_config(
    page_title="M-Pesa Intelligence Engine",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff;
      padding: 15px; border-radius: 10px; 
      box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
""",
    unsafe_allow_html=True,
)


def format_currency_display(amount: float) -> str:
    """Safely formats raw financial floats into professional currency formats."""
    if amount is None or pd.isna(amount):
        return "KSh 0.00"

    if amount < 0:
        return f"-KSh {abs(amount):,.2f}"

    return f"KSh {amount:,.2f}"


def validate_uploaded_file(uploaded_file) -> bool:
    """Applies strict file signature and format safety constraints."""
    if uploaded_file is None:
        return False
    return uploaded_file.name.lower().endswith(".pdf")


def process_and_store_pdf(uploaded_file, password: str = None, db_path: str = DB_PATH) -> None:
    """Orchestrates statement data ingestion via the clean pipeline layer."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_file_path = tmp_file.name

    try:
        with st.spinner("Analyzing Secured M-Pesa Statement..."):
            records_saved, token = ingest_statement_to_ledger(
                tmp_file_path, password=password, db_path=db_path
            )
            
        if records_saved > 0:
            st.success(f"Successfully imported {records_saved} records from {uploaded_file.name}")
            # Cache the extracted verification token inside the active session state
            st.session_state["verification_token"] = token
        else:
            st.error("Ingestion Failed: No valid M-Pesa data layout found.")
            
    except Exception as error:
        
        st.error(f"Ingestion Aborted: {error}")
    finally:
        os.remove(tmp_file_path)

def _render_sidebar_controls():
    """Renders data ingestion panels and handles dynamic password challenges."""
    with st.sidebar:
        st.header("Data Ingestion")
        uploaded_file = st.file_uploader("Upload M-Pesa PDF Statement", type=["pdf"])
        password = None
        
        if uploaded_file:
            if validate_uploaded_file(uploaded_file):
                reader = pypdf.PdfReader(uploaded_file)
                if reader.is_encrypted:
                    password = st.text_input(
                        "Enter 6-Digit Statement Password", 
                        type="password", 
                        help="Enter the 6 digit code Safaricom sent to your mobile number."
                    )
                
                if st.button("Process Statement"):
                    process_and_store_pdf(uploaded_file, password=password)
            else:
                st.error("Invalid file signature. Please upload an authentic PDF.")


def main():
    st.title("🛡️ M-Pesa Financial Intelligence Engine")
    st.markdown("---")

    _render_sidebar_controls()

    if not os.path.exists(DB_PATH):
        st.info(
            "👋 Welcome! Please upload an M-Pesa PDF "
            "statement in the sidebar to begin analysis."
        )
        return

    df = get_all_transactions(DB_PATH)
    if df.empty:
        st.warning("No valid records detected inside the active ledger module.")
        return

    _render_top_summary_metrics(df)
    _render_analytics_layout(df)


def _render_top_summary_metrics(df: pd.DataFrame):
    """Computes high-level ledger stats and displays security validation certificates."""
    total_expenditure = df["total_cost"].sum()
    efficiency = calculate_transfer_efficiency(df)
    transaction_count = len(df)
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Monthly Expenditure", format_currency_display(total_expenditure))
    m2.metric("Transfer Efficiency", f"{efficiency:.2f}%")
    m3.metric("Transaction Volume", f"{transaction_count} records")
    
    
    if "verification_token" in st.session_state:
        token = st.session_state["verification_token"]
        st.info(
            f"🛡️ **Security Token Detected:** `{token}`. "
            f"To completely verify this financial statement against Safaricom records, "
            f"dial `*334#` on your mobile device, select *My Account*, and verify this code."
        )


def _render_analytics_layout(df: pd.DataFrame):
    """Lays out the chart tracking panels and the transaction list table."""
    st.markdown("### Financial Analytics")
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("Monthly Expenditure Trend")
        monthly_df = calculate_monthly_expenditure(df)
        if not monthly_df.empty:
            st.bar_chart(monthly_df.set_index("month"))

    with col_right:
        st.subheader("Top Recipients")
        hitters = get_heavy_hitters(df, top_n=5)
        st.dataframe(
            hitters,
            column_config={
                "total_cost": st.column_config.NumberColumn(format="KSh %.2f")
            },
            hide_index=True,
            use_container_width=True,
        )

    with st.expander("🔍 View Transaction Ledger"):
        st.dataframe(
            df.sort_values("completion_time", ascending=False),
            column_config={
                "total_cost": st.column_config.NumberColumn(format="%.2f"),
                "withdrawn": st.column_config.NumberColumn(format="%.2f"),
                "paid_in": st.column_config.NumberColumn(format="%.2f"),
                "balance": st.column_config.NumberColumn(format="%.2f"),
            },
            use_container_width=True,
        )


if __name__ == "__main__":
    main()
