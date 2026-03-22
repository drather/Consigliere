import re
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from typing import Dict, List

try:
    from dashboard.api_client import DashboardClient
except ImportError:
    from src.dashboard.api_client import DashboardClient


def _mrkdwn_to_md(text: str) -> str:
    """Slack mrkdwn → standard Markdown 변환."""
    # <URL|label> → [label](URL)
    text = re.sub(r'<(https?://[^|>]+)\|([^>]+)>', r'[\2](\1)', text)
    # <URL> → <URL> (bare link, leave as-is for markdown)
    text = re.sub(r'<(https?://[^>]+)>', r'\1', text)
    # *bold* → **bold** (단, **already bold** 는 건드리지 않음)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'**\1**', text)
    # _italic_ → *italic*
    text = re.sub(r'(?<!_)_(?!_)(.+?)(?<!_)_(?!_)', r'*\1*', text)
    # ~strikethrough~ → ~~strikethrough~~
    text = re.sub(r'~(.+?)~', r'~~\1~~', text)
    # • 로 시작하는 줄 → - 목록 (줄바꿈 보장)
    lines = text.split('\n')
    converted = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('•'):
            converted.append(stripped.replace('•', '-', 1))
        else:
            converted.append(line)
    return '\n'.join(converted)


def _render_tx_dataframe(df: pd.DataFrame, code_to_name: Dict[str, str] = None):
    if "price" in df.columns:
        df["거래가(억)"] = (df["price"] / 100_000_000).round(2)
    if code_to_name and "district_code" in df.columns:
        df["구/시"] = df["district_code"].map(lambda c: code_to_name.get(str(c), str(c)))
        display_cols = ["deal_date", "apt_name", "거래가(억)", "floor", "exclusive_area", "build_year", "구/시"]
        col_map = {
            "deal_date": "거래일자",
            "apt_name": "아파트명",
            "exclusive_area": "전용면적(㎡)",
            "floor": "층",
            "build_year": "건축연도",
        }
    else:
        display_cols = ["deal_date", "apt_name", "거래가(억)", "floor", "exclusive_area", "build_year", "district_code"]
        col_map = {
            "deal_date": "거래일자",
            "apt_name": "아파트명",
            "exclusive_area": "전용면적(㎡)",
            "floor": "층",
            "build_year": "건축연도",
            "district_code": "동코드",
        }
    available = [c for c in display_cols if c in df.columns]
    st.dataframe(df[available].rename(columns=col_map), use_container_width=True, hide_index=True)


def show_real_estate():
    st.title("🏢 Real Estate Insights")

    tab1, tab2, tab3 = st.tabs(["📊 Market Monitor", "💡 Insight", "📋 Report Archive"])

    # ──────────────────────────────────────────────────────────
    # TAB 1: Market Monitor
    # ──────────────────────────────────────────────────────────
    with tab1:
        st.subheader("실거래가 조회")

        # 수집 영역
        with st.expander("📥 실거래가 수집", expanded=False):
            c1, c2, c3 = st.columns([2, 2, 1])
            with c1:
                if not st.session_state.get("districts"):
                    st.session_state.districts = DashboardClient.get_districts()
                _collect_options = {d["name"]: d["code"] for d in st.session_state.get("districts", [])}
                _collect_names = ["수도권 전체"] + list(_collect_options.keys())
                _collect_sel = st.selectbox("수집 시/구 (기본: 수도권 전체)", _collect_names, index=0, key="collect_district_name")
                collect_district = _collect_options.get(_collect_sel) if _collect_sel != "수도권 전체" else None
            with c2:
                collect_ym = st.text_input("년월 YYYYMM (빈값=현재월)", value="", key="collect_ym")
            with c3:
                st.write("")
                st.write("")
                collect_btn = st.button("📥 수집", use_container_width=True, key="collect_tx_btn")

            if collect_btn:
                msg = f"{_collect_sel} 수집 중..." if collect_district else "수도권 전체 수집 중... (수분 소요)"
                with st.spinner(msg):
                    r = DashboardClient.trigger_fetch_transactions(
                        collect_district if collect_district else None,
                        collect_ym if collect_ym else None
                    )
                if "error" in r:
                    st.error(r["error"])
                else:
                    st.success(f"✅ {r.get('district_count', 1)}개 지구 | 수집 {r.get('fetched_count', 0)}건 / 저장 {r.get('saved_count', 0)}건")
                    st.session_state.pop("tx_df", None)

        # 시/구 목록 캐싱 (빈 결과는 캐싱하지 않고 재시도)
        if not st.session_state.get("districts"):
            st.session_state.districts = DashboardClient.get_districts()
        district_options = {d["name"]: d["code"] for d in st.session_state.get("districts", [])}
        district_names = ["전체"] + list(district_options.keys())

        # 금액 슬라이더-입력 동기화 초기화
        for k, v in [("_pmin", 0), ("_pmax", 200)]:
            if k not in st.session_state:
                st.session_state[k] = v

        def _sync_slider():
            st.session_state._pmin, st.session_state._pmax = st.session_state._price_slider

        def _sync_from_min():
            st.session_state._pmin = min(st.session_state._pmin_input, st.session_state._pmax)

        def _sync_from_max():
            st.session_state._pmax = max(st.session_state._pmax_input, st.session_state._pmin)

        # 필터 영역
        with st.expander("🔍 조회 필터", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                selected_name = st.selectbox("시/구 선택", district_names, index=0, key="filter_district_name")
                district_code = district_options.get(selected_name) if selected_name != "전체" else None
            with col2:
                apt_name_filter = st.text_input("아파트명 (부분 검색)", value="", placeholder="예: 래미안")

            col3, col4, col5 = st.columns(3)
            with col3:
                date_from_val = st.date_input("시작일", value=date.today() - timedelta(days=90), format="YYYY-MM-DD")
            with col4:
                date_to_val = st.date_input("종료일", value=date.today(), format="YYYY-MM-DD")
            with col5:
                page_size = st.selectbox("페이지당 건수", [10, 20, 30, 50], index=1)

            # 금액 필터: 입력값 ↔ 슬라이더 양방향 동기화
            st.caption("거래금액 범위 (억원) — 직접 입력하거나 슬라이더로 조정")
            ci1, ci2, ci3 = st.columns([1, 4, 1])
            with ci1:
                st.number_input("최소", 0, 200, value=st.session_state._pmin,
                                key="_pmin_input", on_change=_sync_from_min, step=1, label_visibility="visible")
            with ci2:
                st.slider("", 0, 200, value=(st.session_state._pmin, st.session_state._pmax),
                          key="_price_slider", on_change=_sync_slider, format="%d억",
                          label_visibility="collapsed")
            with ci3:
                st.number_input("최대", 0, 200, value=st.session_state._pmax,
                                key="_pmax_input", on_change=_sync_from_max, step=1, label_visibility="visible")

            price_min_krw = st.session_state._pmin * 100_000_000 if st.session_state._pmin > 0 else None
            price_max_krw = st.session_state._pmax * 100_000_000 if st.session_state._pmax < 200 else None

        filter_btn = st.button("🔎 필터 적용", type="primary")

        if "tx_df" not in st.session_state:
            with st.spinner("최신 실거래가 로딩 중..."):
                st.session_state.tx_df = DashboardClient.get_real_estate_transactions(limit=500)
            st.session_state.tx_page = 0

        if filter_btn:
            with st.spinner("조회 중..."):
                st.session_state.tx_df = DashboardClient.get_real_estate_transactions(
                    district_code=district_code,
                    apt_name=apt_name_filter if apt_name_filter else None,
                    date_from=date_from_val.strftime("%Y-%m-%d"),
                    date_to=date_to_val.strftime("%Y-%m-%d"),
                    price_min=price_min_krw,
                    price_max=price_max_krw,
                    limit=500,
                )
            st.session_state.tx_page = 0

        df = st.session_state.tx_df
        if df.empty:
            st.info("조회 결과가 없습니다. 위 '📥 실거래가 수집'을 먼저 실행하세요.")
        else:
            total = len(df)
            total_pages = max(1, -(-total // page_size))  # ceiling division
            page = st.session_state.get("tx_page", 0)
            page = max(0, min(page, total_pages - 1))

            code_to_name = {d["code"]: d["name"] for d in st.session_state.get("districts", [])}
            page_df = df.iloc[page * page_size: (page + 1) * page_size]
            _render_tx_dataframe(page_df.copy(), code_to_name)

            # 페이지 네비게이션
            nav1, nav2, nav3 = st.columns([1, 3, 1])
            with nav1:
                if st.button("◀ 이전", disabled=(page == 0), use_container_width=True):
                    st.session_state.tx_page = page - 1
                    st.rerun()
            with nav2:
                st.markdown(
                    f"<div style='text-align:center;padding-top:6px'>총 <b>{total}건</b> · {page+1} / {total_pages} 페이지</div>",
                    unsafe_allow_html=True
                )
            with nav3:
                if st.button("다음 ▶", disabled=(page >= total_pages - 1), use_container_width=True):
                    st.session_state.tx_page = page + 1
                    st.rerun()

    # ──────────────────────────────────────────────────────────
    # TAB 2: Insight (서브탭 3개)
    # ──────────────────────────────────────────────────────────
    with tab2:
        news_tab0, news_tab1, news_tab2 = st.tabs(["📈 거시경제", "📰 뉴스 리포트", "📌 정책 팩트"])

        # ── 거시경제 ──────────────────────────────────────────
        with news_tab0:
            st.subheader("거시경제 지표")

            if "macro_history" not in st.session_state:
                with st.spinner("한국은행 지표 로딩 중..."):
                    st.session_state.macro_history = DashboardClient.get_macro_history()

            history = st.session_state.macro_history
            base_series = history.get("base_rate", [])
            loan_series = history.get("loan_rate", [])

            # 최신값 요약 카드
            if base_series or loan_series:
                latest_base = base_series[-1] if base_series else {}
                latest_loan = loan_series[-1] if loan_series else {}
                prev_base = base_series[-2] if len(base_series) >= 2 else latest_base
                prev_loan = loan_series[-2] if len(loan_series) >= 2 else latest_loan

                c1, c2, c3 = st.columns(3)
                with c1:
                    delta_b = round(latest_base.get("value", 0) - prev_base.get("value", 0), 2)
                    st.metric(
                        "🏦 한국은행 기준금리",
                        f"{latest_base.get('value', '-')}%",
                        delta=f"{delta_b:+.2f}%p" if delta_b != 0 else "변동 없음",
                        help=f"기준월: {latest_base.get('date', '-')} | 출처: 한국은행 ECOS"
                    )
                with c2:
                    delta_l = round(latest_loan.get("value", 0) - prev_loan.get("value", 0), 2)
                    st.metric(
                        "🏠 주택담보대출 금리",
                        f"{latest_loan.get('value', '-')}%",
                        delta=f"{delta_l:+.2f}%p" if delta_l != 0 else "변동 없음",
                        help=f"기준월: {latest_loan.get('date', '-')} | 예금은행 가중평균(신규취급액) | ⚠️ 시중은행 실제 금리와 다를 수 있음"
                    )
                with c3:
                    st.caption("📊 데이터 출처")
                    st.caption("한국은행 ECOS Open API")
                    st.caption(f"기준: 예금은행 가중평균금리 (신규취급액, 월별)")
                    st.caption("⚠️ 시중은행 광고 금리와 차이 있음")

                st.markdown("---")

                # 시계열 차트
                if base_series and loan_series:
                    # 두 시리즈를 같은 날짜 기준으로 DataFrame 생성
                    base_map = {r["date"]: r["value"] for r in base_series}
                    loan_map = {r["date"]: r["value"] for r in loan_series}
                    all_dates = sorted(set(base_map) | set(loan_map))

                    chart_df = pd.DataFrame({
                        "기준금리(%)": [base_map.get(d) for d in all_dates],
                        "주담대금리(%)": [loan_map.get(d) for d in all_dates],
                    }, index=all_dates)

                    st.markdown("**금리 추이 (최근 10개월)**")
                    st.line_chart(chart_df, height=280)
                    st.caption("기준금리: 한국은행 722Y001 / 주담대금리: 예금은행 가중평균 121Y002")
                elif base_series:
                    df_b = pd.DataFrame({"기준금리(%)": [r["value"] for r in base_series]},
                                        index=[r["date"] for r in base_series])
                    st.line_chart(df_b, height=280)

            else:
                st.info("거시경제 데이터를 불러올 수 없습니다.")
                st.caption("BOK API 응답 없음 — 네트워크 확인 또는 '📋 Report Archive' 탭에서 거시경제 수집을 실행하세요.")

            if st.button("🔄 새로고침", key="macro_refresh"):
                st.session_state.pop("macro_history", None)
                st.rerun()

        # ── 뉴스 리포트 ──
        with news_tab1:
            st.subheader("일별 뉴스 분석 리포트")

            # 수집 버튼
            with st.expander("📥 뉴스 수집", expanded=False):
                st.caption("오늘 날짜 기준으로 부동산 뉴스를 수집·분석해 마크다운 리포트를 저장합니다. (30초~1분 소요)")
                if st.button("📥 뉴스 수집 실행", key="fetch_news_btn"):
                    with st.spinner("뉴스 수집 및 LLM 분석 중..."):
                        r = DashboardClient.trigger_fetch_news()
                    if "error" in r:
                        st.error(r["error"])
                    else:
                        st.success(f"✅ {r.get('report_date', '')} 뉴스 리포트 생성 완료")
                        st.rerun()

            st.markdown("---")

            report_files = DashboardClient.list_news_reports()
            if not report_files:
                st.warning("생성된 뉴스 리포트가 없습니다. 위 '📥 뉴스 수집'을 먼저 실행하세요.")
            else:
                selected_file = st.selectbox("리포트 날짜 선택", report_files)
                if selected_file:
                    with st.spinner("리포트 로딩 중..."):
                        content = DashboardClient.get_news_content(selected_file)
                    st.markdown("---")
                    st.markdown(content)

        # ── 정책 팩트 ──
        with news_tab2:
            st.subheader("정책·개발 팩트 검색")

            # 수집 버튼
            with st.expander("📥 정책 팩트 수집", expanded=False):
                st.caption("뉴스를 크롤링해 확정된 정책·개발 사실(Hard Facts)을 LLM으로 추출하고 ChromaDB에 저장합니다. (1~2분 소요)")
                if st.button("📥 정책 팩트 수집 실행", key="fetch_policy_btn"):
                    with st.spinner("크롤링 및 팩트 추출 중..."):
                        r = DashboardClient.trigger_update_policy()
                    if "error" in r:
                        st.error(r["error"])
                    else:
                        st.success(f"✅ 팩트 {r.get('indexed_facts', 0)}건 저장 완료")
                        st.session_state.pop("policy_facts", None)
                        st.rerun()

            st.markdown("---")

            col_q, col_n, col_btn = st.columns([3, 1, 1])
            with col_q:
                policy_query = st.text_input("검색어", value="부동산 정책 공급 개발", label_visibility="collapsed")
            with col_n:
                n_results = st.selectbox("건수", [5, 10, 20], label_visibility="collapsed")
            with col_btn:
                policy_search_btn = st.button("🔍 검색", key="policy_search", use_container_width=True)

            if "policy_facts" not in st.session_state:
                st.session_state.policy_facts = DashboardClient.search_policy_facts("부동산 정책 공급 개발", 10)

            if policy_search_btn:
                with st.spinner("ChromaDB 검색 중..."):
                    st.session_state.policy_facts = DashboardClient.search_policy_facts(policy_query, n_results)

            facts = st.session_state.policy_facts
            if not facts:
                st.warning("저장된 정책 팩트가 없습니다.")
                st.info("위 '📥 정책 팩트 수집'을 먼저 실행하세요.")
            else:
                st.success(f"**{len(facts)}건** 검색됨")
                for fact in facts:
                    meta = fact.get("metadata", {})
                    title = meta.get("short_title") or meta.get("title") or fact.get("id", "")
                    fact_date = meta.get("date", "")
                    category = meta.get("category", "")
                    label = f"📌 [{fact_date}] [{category}] {title}" if fact_date else f"📌 [{category}] {title}"
                    with st.expander(label, expanded=False):
                        st.caption(f"출처: {meta.get('source', '-')}")
                        st.markdown(fact.get("content", ""))

    # ──────────────────────────────────────────────────────────
    # TAB 3: Report Archive
    # ──────────────────────────────────────────────────────────
    with tab3:
        st.subheader("인사이트 리포트")

        # 리포트 생성 영역
        with st.expander("⚙️ 리포트 생성", expanded=False):
            rc1, rc2 = st.columns(2)
            with rc1:
                if not st.session_state.get("districts"):
                    st.session_state.districts = DashboardClient.get_districts()
                _report_options = {"페르소나 관심 지역 전체 (강남·서초·분당·송파)": None}
                _report_options.update({d["name"]: d["code"] for d in st.session_state.get("districts", [])})
                _report_names = list(_report_options.keys())
                _report_sel = st.selectbox("수집 지역", _report_names, index=0, key="report_district_select")
                report_district = _report_options.get(_report_sel)

            st.caption("거시경제 지표를 먼저 수집한 뒤 리포트를 생성하면 저장된 데이터를 활용합니다.")
            mc1, mc2, mc3 = st.columns(3)

            with mc1:
                if st.button("📈 거시경제 수집", use_container_width=True):
                    with st.spinner("한국은행 API 조회 중..."):
                        r = DashboardClient.trigger_fetch_macro()
                    if "error" in r:
                        st.error(r["error"])
                    else:
                        macro = r.get("macro", {})
                        br = (macro.get("base_rate") or {})
                        lr = (macro.get("loan_rate") or {})
                        st.success(f"✅ 기준금리 {br.get('value', '-')}% | 주담대 {lr.get('value', '-')}%")
                        st.caption(f"출처: 한국은행 ECOS | 예금은행 가중평균금리(신규취급액) | 기준월: {lr.get('date', '-')} | ⚠️ 시중은행 실제 금리와 차이 있음")

            with mc2:
                if st.button("📊 리포트 생성", use_container_width=True):
                    with st.spinner("인사이트 리포트 생성 중... (1~3분 소요)"):
                        r = DashboardClient.trigger_generate_report(report_district)
                    if "error" in r:
                        st.error(r["error"])
                    else:
                        st.success(f"✅ 점수 {r.get('score', 0)}점 | 실거래 {r.get('tx_count', 0)}건")
                        st.rerun()

            with mc3:
                send_slack = st.checkbox("Slack 전송", value=True, key="pipeline_slack")
                if st.button("🚀 전체 파이프라인", use_container_width=True, type="primary"):
                    with st.spinner("파이프라인 실행 중... (최대 5분 소요)"):
                        r = DashboardClient.trigger_run_pipeline(report_district, send_slack=send_slack)
                    if "error" in r:
                        st.error(r["error"])
                    else:
                        pipeline = r.get("pipeline", {})
                        j4 = pipeline.get("job4", {})
                        st.success(f"✅ 완료 | 점수 {j4.get('score', 0)}점 | Slack: {pipeline.get('slack', '미전송')}")
                        with st.expander("상세 결과"):
                            st.json(pipeline)
                        st.rerun()

        st.markdown("---")

        # 리포트 목록
        reports = DashboardClient.list_insight_reports()
        if not reports:
            st.warning("저장된 인사이트 리포트가 없습니다.")
            st.info("위 '⚙️ 리포트 생성'을 실행하면 자동으로 저장됩니다.")
        else:
            df_reports = pd.DataFrame(reports)
            df_reports["score_label"] = df_reports["score"].apply(
                lambda s: f"{'🟢' if s >= 80 else '🟡' if s >= 60 else '🔴'} {s}점"
            )
            st.dataframe(
                df_reports[["date", "score_label", "tx_count", "created_at"]].rename(columns={
                    "date": "날짜", "score_label": "검증 점수", "tx_count": "실거래 건수", "created_at": "생성 시각"
                }),
                use_container_width=True,
                hide_index=True,
            )

            st.markdown("---")

            filenames = [r["filename"] for r in reports]
            labels = [f"{r['date']} (Score {r['score']})" for r in reports]
            selected_idx = st.selectbox("리포트 선택", range(len(labels)), format_func=lambda i: labels[i])

            if st.button("📄 리포트 보기"):
                with st.spinner("로딩 중..."):
                    report = DashboardClient.get_insight_report(filenames[selected_idx])
                if not report:
                    st.error("리포트를 불러올 수 없습니다.")
                else:
                    st.markdown(f"### 📋 {report.get('date')} 인사이트 리포트")
                    st.caption(f"검증 점수: {report.get('score')}점 | 실거래 건수: {report.get('tx_count')}건 | 생성: {report.get('created_at', '')[:19]}")
                    st.markdown("---")
                    for block in report.get("blocks", []):
                        btype = block.get("type")
                        if btype == "header":
                            st.markdown(f"## {block.get('text', {}).get('text', '')}")
                        elif btype == "section":
                            raw_text = block.get("text", {}).get("text", "")
                            st.markdown(_mrkdwn_to_md(raw_text))
                        elif btype == "context":
                            for elem in block.get("elements", []):
                                st.caption(_mrkdwn_to_md(elem.get("text", "")))
                        elif btype == "divider":
                            st.markdown("---")
