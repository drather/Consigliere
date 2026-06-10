import streamlit as st
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"
))

current_file_path = os.path.abspath(__file__)
dashboard_dir = os.path.dirname(current_file_path)
src_dir = os.path.dirname(dashboard_dir)
project_root = os.path.dirname(src_dir)

if src_dir not in sys.path:
    sys.path.insert(0, src_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from dashboard.views.career import show_career as render_career_page
    from dashboard.views.finance import render_finance_page
    from dashboard.views.real_estate import show_real_estate as render_real_estate_page
    from dashboard.views.automation import show_automation as render_automation_page
    from dashboard.api_client import DashboardClient
except ImportError:
    try:
        from views.career import show_career as render_career_page
        from views.finance import render_finance_page
        from views.real_estate import show_real_estate as render_real_estate_page
        from views.automation import show_automation as render_automation_page
        from api_client import DashboardClient
    except ImportError as e:
        st.error(f"Critical Error: Failed to import views. {e}")
        st.stop()


def show_home():
    st.title("🏠 Consigliere")
    st.caption("오늘의 현황을 한눈에 확인합니다.")

    now = datetime.now()
    col1, col2, col3 = st.columns(3)

    with col1:
        try:
            df = DashboardClient.get_finance_ledger(now.year, now.month)
            total = int(df["amount"].sum()) if not df.empty and "amount" in df.columns else 0
            st.metric("💰 이번달 지출", f"{total:,}원")
        except Exception:
            st.metric("💰 이번달 지출", "-")

    with col2:
        try:
            dates = DashboardClient.list_daily_reports()
            latest = dates[0] if dates else None
            st.metric("🏢 데일리 브리핑", latest or "없음")
        except Exception:
            st.metric("🏢 데일리 브리핑", "-")

    with col3:
        try:
            result = DashboardClient.get_executions(days=1)
            summary = result.get("summary", {})
            total_jobs = summary.get("total", 0)
            err_jobs = summary.get("error", 0)
            delta = f"실패 {err_jobs}건" if err_jobs else "정상"
            st.metric("⚙️ 오늘 실행", f"{total_jobs}건", delta=delta,
                      delta_color="inverse" if err_jobs else "normal")
        except Exception:
            st.metric("⚙️ 오늘 실행", "-")


def main():
    st.set_page_config(
        page_title="Consigliere Dashboard",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    domain_options = ["🏠 Home", "🚀 Career", "💰 Finance", "🏢 Real Estate"]
    ops_options = ["⚙️ Automation"]

    # 현재 선택된 메뉴(전체 그룹 통틀어 단일 값)
    if "current_menu" not in st.session_state:
        st.session_state.current_menu = domain_options[0]

    def _select_domain():
        st.session_state.current_menu = st.session_state.domain_radio

    def _select_ops():
        st.session_state.current_menu = st.session_state.ops_radio

    current_menu = st.session_state.current_menu
    domain_index = domain_options.index(current_menu) if current_menu in domain_options else None
    ops_index = ops_options.index(current_menu) if current_menu in ops_options else None

    with st.sidebar:
        st.title("Consigliere 🤖")

        st.caption("도메인")
        st.radio(
            "domain",
            domain_options,
            index=domain_index,
            label_visibility="collapsed",
            key="domain_radio",
            on_change=_select_domain,
        )

        st.divider()
        st.caption("시스템 운영")
        st.radio(
            "ops",
            ops_options,
            index=ops_index,
            label_visibility="collapsed",
            key="ops_radio",
            on_change=_select_ops,
        )

    menu = st.session_state.current_menu

    if menu == "🏠 Home":
        show_home()
    elif menu == "🚀 Career":
        render_career_page()
    elif menu == "💰 Finance":
        render_finance_page()
    elif menu == "🏢 Real Estate":
        render_real_estate_page()
    elif menu == "⚙️ Automation":
        render_automation_page()


if __name__ == "__main__":
    main()
