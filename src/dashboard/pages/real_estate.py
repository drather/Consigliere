import streamlit as st
import pandas as pd
import sys
import os

# Import API Client
try:
    from dashboard.api_client import DashboardClient
except ImportError:
    from src.dashboard.api_client import DashboardClient

def show_real_estate():
    st.title("🏢 Real Estate Insights")
    
    tab1, tab2 = st.tabs(["📊 Market Monitor", "📰 News Insights"])
    
    # --- TAB 1: Market Monitor ---
    with tab1:
        st.subheader("Apartment Transaction Monitor")
        
        col1, col2 = st.columns(2)
        with col1:
            district_code = st.text_input("District Code (e.g., 41135)", value="")
        with col2:
            limit = st.slider("Limit Records", 10, 100, 50)
            
        if st.button("Fetch Transactions"):
            with st.spinner("Fetching data from ChromaDB..."):
                df = DashboardClient.get_real_estate_transactions(district_code if district_code else None, limit)
                
            if df.empty:
                st.info("No transaction records found.")
            else:
                st.success(f"Found {len(df)} transactions.")
                
                # Reorder columns for better readability if keys exist
                preferred_cols = ["deal_date", "apt_name", "price", "floor", "exclusive_area"]
                available_cols = [c for c in preferred_cols if c in df.columns]
                remaining_cols = [c for c in df.columns if c not in preferred_cols]
                
                st.dataframe(
                    df[available_cols + remaining_cols],
                    use_container_width=True,
                    hide_index=True
                )

    # --- TAB 2: News Insights ---
    with tab2:
        st.subheader("Daily Real Estate Reports")
        
        # 1. Get List of Reports
        report_files = DashboardClient.list_news_reports()
        
        if not report_files:
            st.warning("No news reports generated yet.")
            st.info("Trigger the 'News Analysis' agent to generate a report.")
        else:
            # 2. Select Report
            selected_file = st.selectbox("Select Report Date", report_files)
            
            # 3. View Content
            if selected_file:
                with st.spinner("Loading report..."):
                    content = DashboardClient.get_news_content(selected_file)
                    
                st.markdown("---")
                st.markdown(content)
