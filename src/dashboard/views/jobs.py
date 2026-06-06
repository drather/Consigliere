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


def show_jobs():
    st.title("🕐 Jobs: 실행 내역")
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
            "실행 시간 (KST)": e.get("startedAt", "-"),
            "워크플로우": e.get("workflowName", "-"),
            "상태": f"{_STATUS_ICON.get(e.get('status', ''), '❓')} {e.get('status', '-')}",
            "소요 시간(초)": e.get("duration_sec", "-"),
        }
        for e in executions
    ]

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
