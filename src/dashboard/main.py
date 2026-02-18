import streamlit as st
import os
import sys

# Ensure proper path setup for imports
current_file_path = os.path.abspath(__file__)
dashboard_dir = os.path.dirname(current_file_path) # src/dashboard
src_dir = os.path.dirname(dashboard_dir) # src
project_root = os.path.dirname(src_dir) # project root

if src_dir not in sys.path:
    sys.path.insert(0, src_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import Views
try:
    from dashboard.views.finance import render_finance_page
    from dashboard.views.real_estate import show_real_estate as render_real_estate_page
except ImportError:
    try:
        from views.finance import render_finance_page
        from views.real_estate import show_real_estate as render_real_estate_page
    except ImportError as e:
        st.error(f"Critical Error: Failed to import views. {e}")
        st.stop()

def show_home():
    st.title("🏠 Welcome to Consigliere")
    st.markdown("""
    이 대시보드는 **Consigliere Agent**의 통합 관리 도구입니다.
    좌측 메뉴를 선택하여 가계부 관리 및 부동산 모니터링 결과를 확인하세요.
    """)
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("💰 Finance Status")
        st.write("- 최근 지출 내역 요약 보이기")
    with col2:
        st.subheader("🏢 Real Estate Status")
        st.write("- 최근 거래 알림/뉴스 요약 보이기")

def main():
    st.set_page_config(
        page_title="Consigliere Dashboard",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    
    # Sidebar Navigation
    with st.sidebar:
        st.title("Consigliere 🤖")
        menu = st.radio(
            "Go to",
            ["🏠 Home", "💰 Finance", "🏢 Real Estate"]
        )
        st.info(f"Current Module: {menu.split()[-1]}")

    # 2. Page Routing Logic
    if menu == "🏠 Home":
        show_home()
    elif menu == "💰 Finance":
        render_finance_page()
    elif menu == "🏢 Real Estate":
        render_real_estate_page()

if __name__ == "__main__":
    main()