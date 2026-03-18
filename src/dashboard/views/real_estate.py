import streamlit as st
import pandas as pd
import sys
import os
from datetime import date, timedelta

# Import API Client
try:
    from dashboard.api_client import DashboardClient
except ImportError:
    from src.dashboard.api_client import DashboardClient


def _render_tx_dataframe(df: pd.DataFrame):
    """실거래가 DataFrame을 포맷해서 표시한다."""
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
    st.dataframe(display_df, use_container_width=True, hide_index=True)


def show_real_estate():
    st.title("🏢 Real Estate Insights")

    tab1, tab2, tab3 = st.tabs(["📊 Market Monitor", "📰 News Insights", "📋 Report Archive"])

    # --- TAB 1: Market Monitor ---
    with tab1:
        st.subheader("실거래가 조회")

        # 필터 영역
        with st.expander("🔍 필터", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                district_code = st.text_input("동코드 (예: 11680)", value="", placeholder="비워두면 전체")
            with col2:
                apt_name_filter = st.text_input("아파트명 (부분 검색)", value="", placeholder="예: 래미안")

            col3, col4, col5 = st.columns(3)
            with col3:
                date_from_val = st.date_input(
                    "조회 시작일",
                    value=date.today() - timedelta(days=90),
                    format="YYYY-MM-DD"
                )
            with col4:
                date_to_val = st.date_input(
                    "조회 종료일",
                    value=date.today(),
                    format="YYYY-MM-DD"
                )
            with col5:
                limit = st.selectbox("최대 건수", [10, 20, 30, 50], index=1)

        filter_btn = st.button("🔎 필터 적용", type="primary")

        # 초기 로드 또는 필터 적용 시 데이터 조회
        if "tx_df" not in st.session_state:
            with st.spinner("최신 실거래가 로딩 중..."):
                st.session_state.tx_df = DashboardClient.get_real_estate_transactions(limit=20)

        if filter_btn:
            with st.spinner("ChromaDB에서 조회 중..."):
                st.session_state.tx_df = DashboardClient.get_real_estate_transactions(
                    district_code=district_code if district_code else None,
                    apt_name=apt_name_filter if apt_name_filter else None,
                    date_from=date_from_val.strftime("%Y-%m-%d"),
                    date_to=date_to_val.strftime("%Y-%m-%d"),
                    limit=limit,
                )

        df = st.session_state.tx_df
        if df.empty:
            st.info("조회 결과가 없습니다. 필터 조건을 확인하거나 '🔄 데이터 수집' 탭에서 실거래가를 수집하세요.")
        else:
            st.caption(f"총 **{len(df)}건** 표시 중")
            _render_tx_dataframe(df)

    # --- TAB 2: News Insights ---
    with tab2:
        news_tab1, news_tab2, news_tab3 = st.tabs(["📰 뉴스 리포트", "📌 정책 팩트", "🔄 데이터 수집"])

        # ── 서브탭 1: 뉴스 리포트 ──────────────────────────
        with news_tab1:
            st.subheader("일별 뉴스 분석 리포트")
            report_files = DashboardClient.list_news_reports()
            if not report_files:
                st.warning("생성된 뉴스 리포트가 없습니다.")
                st.info("'🔄 데이터 수집' 탭에서 뉴스 수집을 실행하세요.")
            else:
                selected_file = st.selectbox("리포트 날짜 선택", report_files)
                if selected_file:
                    with st.spinner("리포트 로딩 중..."):
                        content = DashboardClient.get_news_content(selected_file)
                    st.markdown("---")
                    st.markdown(content)

        # ── 서브탭 2: 정책 팩트 ──────────────────────────
        with news_tab2:
            st.subheader("정책·개발 팩트 검색")
            st.caption("ChromaDB에 저장된 정책/개발 팩트를 의미 기반으로 검색합니다. 데이터가 없으면 '🔄 데이터 수집' 탭에서 정책 팩트 수집을 먼저 실행하세요.")

            col_q, col_n, col_btn = st.columns([3, 1, 1])
            with col_q:
                policy_query = st.text_input("검색어", value="부동산 정책 공급 개발", label_visibility="collapsed")
            with col_n:
                n_results = st.selectbox("건수", [5, 10, 20], label_visibility="collapsed")
            with col_btn:
                policy_search_btn = st.button("🔍 검색", key="policy_search", use_container_width=True)

            # 초기 로드
            if "policy_facts" not in st.session_state:
                facts_init = DashboardClient.search_policy_facts("부동산 정책 공급 개발", 10)
                st.session_state.policy_facts = facts_init

            if policy_search_btn:
                with st.spinner("ChromaDB 검색 중..."):
                    st.session_state.policy_facts = DashboardClient.search_policy_facts(policy_query, n_results)

            facts = st.session_state.policy_facts
            if not facts:
                st.warning("저장된 정책 팩트가 없습니다.")
                st.info("👉 '🔄 데이터 수집' 탭 → **'정책 팩트 수집'** 버튼을 실행하세요. (LLM 분석 포함, 1~2분 소요)")
            else:
                st.success(f"**{len(facts)}건** 검색됨")
                for fact in facts:
                    meta = fact.get("metadata", {})
                    title = meta.get("short_title") or meta.get("title") or fact.get("id", "")
                    with st.expander(f"📌 {title}", expanded=False):
                        st.caption(f"분류: {meta.get('category', '-')} | 출처: {meta.get('source', '-')} | 날짜: {meta.get('date', '-')}")
                        st.markdown(fact.get("content", ""))

        # ── 서브탭 3: 데이터 수집 ──────────────────────────
        with news_tab3:
            st.subheader("데이터 수집 Job 수동 실행")
            st.caption("각 Job은 독립적으로 실행 가능합니다. 전체 파이프라인은 Job 1~4를 순서대로 실행합니다.")

            col_dc, col_ym = st.columns(2)
            with col_dc:
                job_district = st.text_input("동코드 (Job1·Job4)", value="11680")
            with col_ym:
                job_ym = st.text_input("년월 YYYYMM (Job1, 빈값=현재월)", value="")

            st.markdown("---")

            col1, col2, col3, col4, col5 = st.columns(5)

            with col1:
                if st.button("1️⃣ 실거래가 수집", use_container_width=True):
                    with st.spinner("실거래가 수집 중..."):
                        r = DashboardClient.trigger_fetch_transactions(
                            job_district, job_ym if job_ym else None
                        )
                    if "error" in r:
                        st.error(r["error"])
                    else:
                        st.success(f"✅ 수집 {r.get('fetched_count',0)}건 / 저장 {r.get('saved_count',0)}건")
                        st.session_state.pop("tx_df", None)  # 캐시 초기화

            with col2:
                if st.button("2️⃣ 뉴스 수집", use_container_width=True):
                    with st.spinner("뉴스 수집·분석 중... (30초~1분 소요)"):
                        r = DashboardClient.trigger_fetch_news()
                    if "error" in r:
                        st.error(r["error"])
                    else:
                        st.success(f"✅ {r.get('report_date','')} 리포트 생성 완료")

            with col3:
                if st.button("3️⃣ 거시경제 수집", use_container_width=True):
                    with st.spinner("한국은행 API 조회 중..."):
                        r = DashboardClient.trigger_fetch_macro()
                    if "error" in r:
                        st.error(r["error"])
                    else:
                        macro = r.get("macro", {})
                        br = macro.get("base_rate") or {}
                        lr = macro.get("loan_rate") or {}
                        st.success(f"✅ 기준금리 {br.get('value','-')}% | 주담대 {lr.get('value','-')}%")
                        st.caption(f"📊 출처: 한국은행 ECOS API | 기준: 예금은행 가중평균금리(신규취급액) | 기준월: {lr.get('date','-')} | ⚠️ 시중은행 실제 금리와 차이 있을 수 있음")

            with col4:
                if st.button("📌 정책 팩트 수집", use_container_width=True):
                    with st.spinner("뉴스 크롤링 + LLM 팩트 추출 중... (1~2분 소요)"):
                        r = DashboardClient.trigger_update_policy()
                    if "error" in r:
                        st.error(r["error"])
                    else:
                        st.success(f"✅ 팩트 {r.get('indexed_facts', 0)}건 ChromaDB 저장 완료")
                        st.session_state.pop("policy_facts", None)  # 캐시 초기화

            with col5:
                if st.button("4️⃣ 리포트 생성", use_container_width=True):
                    with st.spinner("인사이트 리포트 생성 중... (1~3분 소요)"):
                        r = DashboardClient.trigger_generate_report(job_district)
                    if "error" in r:
                        st.error(r["error"])
                    else:
                        st.success(f"✅ 점수 {r.get('score',0)}점 | 실거래 {r.get('tx_count',0)}건")

            st.markdown("---")
            st.markdown("**전체 파이프라인 (Job 1→2→3→4 + Slack)**")
            send_slack = st.checkbox("Slack 전송", value=True)
            if st.button("🚀 파이프라인 실행", type="primary", use_container_width=True):
                with st.spinner("파이프라인 실행 중... (최대 5분 소요)"):
                    r = DashboardClient.trigger_run_pipeline(job_district, send_slack=send_slack)
                if "error" in r:
                    st.error(r["error"])
                else:
                    pipeline = r.get("pipeline", {})
                    j4 = pipeline.get("job4", {})
                    slack_status = pipeline.get("slack", "미전송")
                    st.success(f"✅ 파이프라인 완료 | 점수 {j4.get('score',0)}점 | Slack: {slack_status}")
                    with st.expander("상세 결과"):
                        st.json(pipeline)

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
