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

    tab1, tab2, tab3 = st.tabs(["📊 Market Monitor", "📰 News Insights", "📋 Report Archive"])

    # --- TAB 1: Market Monitor ---
    with tab1:
        st.subheader("실거래가 조회")

        # 필터 영역
        with st.expander("🔍 필터", expanded=True):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                district_code = st.text_input("동코드 (예: 11680)", value="")
            with col2:
                date_from = st.text_input("조회 시작일 (YYYY-MM-DD)", value="")
            with col3:
                date_to = st.text_input("조회 종료일 (YYYY-MM-DD)", value="")
            with col4:
                limit = st.selectbox("최대 건수", [10, 20, 30, 50], index=1)

        if st.button("🔎 조회", type="primary"):
            with st.spinner("ChromaDB에서 조회 중..."):
                df = DashboardClient.get_real_estate_transactions(
                    district_code=district_code if district_code else None,
                    date_from=date_from if date_from else None,
                    date_to=date_to if date_to else None,
                    limit=limit,
                )

            if df.empty:
                st.info("조회 결과가 없습니다. 필터 조건을 확인하거나 데이터를 먼저 수집해주세요.")
            else:
                st.success(f"총 **{len(df)}건** 조회됨")

                # 컬럼 정리 및 포맷
                if "price" in df.columns:
                    df["거래가(억)"] = (df["price"] / 100_000_000).round(2)
                col_map = {
                    "deal_date": "거래일자",
                    "apt_name": "아파트명",
                    "exclusive_area": "전용면적(㎡)",
                    "floor": "층",
                    "build_year": "건축연도",
                    "district_code": "동코드",
                }
                display_cols = ["deal_date", "apt_name", "거래가(억)", "floor", "exclusive_area", "build_year", "district_code"]
                available = [c for c in display_cols if c in df.columns]
                display_df = df[available].rename(columns=col_map)

                st.dataframe(
                    display_df,
                    use_container_width=True,
                    hide_index=True,
                )

    # --- TAB 2: News Insights ---
    with tab2:
        st.subheader("Daily Real Estate Reports")

        report_files = DashboardClient.list_news_reports()

        if not report_files:
            st.warning("No news reports generated yet.")
            st.info("Trigger the 'News Analysis' agent to generate a report.")
        else:
            selected_file = st.selectbox("Select Report Date", report_files)

            if selected_file:
                with st.spinner("Loading report..."):
                    content = DashboardClient.get_news_content(selected_file)

                st.markdown("---")
                st.markdown(content)

    # --- TAB 3: Report Archive ---
    with tab3:
        st.subheader("Insight Report Archive")

        reports = DashboardClient.list_insight_reports()

        if not reports:
            st.warning("저장된 인사이트 리포트가 없습니다.")
            st.info("부동산 인사이트 리포트를 실행하면 자동으로 저장됩니다.")
        else:
            # 목록 테이블
            df_reports = pd.DataFrame(reports)
            df_reports["score_label"] = df_reports["score"].apply(
                lambda s: f"{'🟢' if s >= 80 else '🟡' if s >= 60 else '🔴'} {s}점"
            )
            st.dataframe(
                df_reports[["date", "score_label", "tx_count", "created_at"]].rename(columns={
                    "date": "날짜",
                    "score_label": "검증 점수",
                    "tx_count": "실거래 건수",
                    "created_at": "생성 시각"
                }),
                use_container_width=True,
                hide_index=True
            )

            st.markdown("---")

            # 상세 조회
            filenames = [r["filename"] for r in reports]
            labels = [f"{r['date']} (Score {r['score']})" for r in reports]
            selected_idx = st.selectbox("리포트 선택", range(len(labels)), format_func=lambda i: labels[i])
            selected_filename = filenames[selected_idx]

            if st.button("📄 리포트 보기"):
                with st.spinner("Loading report..."):
                    report = DashboardClient.get_insight_report(selected_filename)

                if not report:
                    st.error("리포트를 불러올 수 없습니다.")
                else:
                    st.markdown(f"### 📋 {report.get('date')} 인사이트 리포트")
                    st.caption(f"검증 점수: {report.get('score')}점 | 실거래 건수: {report.get('tx_count')}건 | 생성: {report.get('created_at', '')[:19]}")
                    st.markdown("---")

                    # Slack Block Kit blocks → Markdown 렌더링
                    for block in report.get("blocks", []):
                        block_type = block.get("type")
                        if block_type == "header":
                            st.markdown(f"## {block.get('text', {}).get('text', '')}")
                        elif block_type == "section":
                            text = block.get("text", {}).get("text", "")
                            st.markdown(text)
                        elif block_type == "context":
                            for elem in block.get("elements", []):
                                st.caption(elem.get("text", ""))
                        elif block_type == "divider":
                            st.markdown("---")
