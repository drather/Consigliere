import streamlit as st
import pandas as pd
from datetime import datetime
import sys
import os

# Import API Client
try:
    from dashboard.api_client import DashboardClient
except ImportError:
    from src.dashboard.api_client import DashboardClient

def render_finance_page():
    st.title("💰 Finance Management")
    
    # 1. Date Selector
    col1, col2 = st.columns([1, 3])
    with col1:
        current_date = datetime.now()
        selected_date = st.date_input("Select Month", value=current_date)
        year, month = selected_date.year, selected_date.month

    # 2. Load Data via API
    # Use cache_data to prevent re-fetching on every interaction unless necessary
    # For now, we fetch fresh to support real-time updates if needed
    df = DashboardClient.get_finance_ledger(year, month)

    if df.empty:
        st.warning(f"No ledger found for {year}-{month:02d}.")
        if st.button("Create New Ledger"):
            st.info("Please add a transaction via chat to initialize the ledger.")
        return

    # 3. Summary Metrics
    if 'Amount' in df.columns:
        total_expense = df['Amount'].sum()
        st.metric("Total Expense", f"{total_expense:,} KRW")

    # Ensure 'Date' column is datetime compatible for st.data_editor
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date']).dt.date

    # 4. Data Editor (Grid)
    st.subheader("Transactions")
    
    # Configure column settings for better UX
    column_config = {
        "Amount": st.column_config.NumberColumn(
            "Amount (KRW)",
            format="%d KRW"
        ),
        "Date": st.column_config.DateColumn(
            "Date",
            format="YYYY-MM-DD"
        ),
        "Category": st.column_config.SelectboxColumn(
            "Category",
            options=["Food", "Transport", "Shopping", "Housing", "Health", "Entertainment", "Income", "Other"]
        )
    }

    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        column_config=column_config,
        key="finance_editor"
    )

    # 5. Save Changes (Placeholder for now)
    if st.button("Save Changes"):
        st.warning("Save functionality via API is under construction.")
