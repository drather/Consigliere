import streamlit as st
import os
import sys

# 프로젝트 루트를 PYTHONPATH에 추가하여 src/ 하위 모듈 임포트 가능하게 설정
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import Pages (Must be after sys.path update)
try:
    from dashboard.pages.finance import render_finance_page
    from dashboard.pages.real_estate import show_real_estate as render_real_estate_page
except ImportError:
    # Fallback if running from within src/dashboard/
    from pages.finance import render_finance_page
    from pages.real_estate import show_real_estate as render_real_estate_page

def main():
    st.set_page_config(
        page_title="Consigliere Dashboard",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    
    # ... (Sidebar code remains same) ...

    # 2. Page Routing Logic
    if menu == "🏠 Home":
        show_home()
    elif menu == "💰 Finance":
        render_finance_page()
    elif menu == "🏢 Real Estate":
        render_real_estate_page()

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

# show_finance is replaced by render_finance_page
# show_real_estate is replaced by render_real_estate_page

