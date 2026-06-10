import streamlit as st
import pandas as pd
from dashboard.api_client import DashboardClient

_STATUS_ICON = {
    "success": "✅",
    "error": "❌",
    "running": "⏳",
    "warning": "⚠️",
}

_DAYS_MAP = {"오늘": 1, "이번 주": 7, "최근 7일": 7}


def show_automation():
    st.title("⚙️ Automation")

    tab_wf, tab_jobs = st.tabs(["📋 워크플로우", "🕐 실행 내역"])

    # ── 탭 1: 워크플로우 목록 ──────────────────────────────────────────
    with tab_wf:
        st.markdown("백그라운드에서 실행 중인 n8n 워크플로우 목록입니다.")
        with st.spinner("Loading workflows..."):
            workflows = DashboardClient.get_workflows()

        if not workflows:
            st.info("연결된 n8n 인스턴스에 워크플로우가 없습니다.")
            return

        st.subheader("Active Agents & Triggers")
        for wf in workflows:
            name = wf.get("name", "Unnamed Workflow")
            active = wf.get("active", False)
            wf_id = wf.get("id")
            created_at = wf.get("createdAt", "Unknown")
            updated_at = wf.get("updatedAt", "Unknown")
            status_icon = "🟢" if active else "⚫"

            with st.expander(f"{status_icon} **{name}** (ID: `{wf_id}`)", expanded=False):
                st.markdown(f"""
                - **Status:** {'Active' if active else 'Inactive'}
                - **Created:** {created_at}
                - **Last Updated:** {updated_at}
                """)
                col1, col2 = st.columns([1, 4])
                with col1:
                    n8n_url = f"http://localhost:5678/workflow/{wf_id}"
                    st.link_button("🛠️ Open in n8n Editor", n8n_url)

    # ── 탭 2: 실행 내역 (기존 jobs.py 내용) ───────────────────────────
    with tab_jobs:
        st.markdown("n8n 워크플로우가 언제 실행되었는지 타임라인으로 확인합니다.")

        period = st.radio("조회 기간", list(_DAYS_MAP.keys()), horizontal=True)
        days = _DAYS_MAP[period]

        with st.spinner("실행 내역 로딩 중..."):
            result = DashboardClient.get_executions(days=days)

        executions = result.get("executions", [])
        summary = result.get("summary", {})

        col1, col2, col3 = st.columns(3)
        col1.metric("전체 실행", summary.get("total", 0))
        col2.metric("✅ 성공", summary.get("success", 0))
        col3.metric("❌ 실패", summary.get("error", 0))

        st.divider()

        if not executions:
            st.info("해당 기간에 실행 내역이 없습니다.")
            return

        rows = [
            {
                "상태": _STATUS_ICON.get(e.get("status", ""), "❓"),
                "워크플로우": e.get("workflow_name", "-"),
                "시작": e.get("started_at", "-"),
                "종료": e.get("finished_at", "-"),
                "소요(초)": e.get("duration_seconds", "-"),
            }
            for e in executions
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
