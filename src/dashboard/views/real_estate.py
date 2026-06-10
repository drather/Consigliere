import os
import re
import sys
import streamlit as st
import pandas as pd
from typing import Dict, List, Optional

_API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

try:
    from streamlit_folium import st_folium
except ImportError:
    st_folium = None  # type: ignore

try:
    from dashboard.api_client import DashboardClient
    from dashboard.components.map_view import render_detail_map
    from dashboard.services import (
        get_location_score, get_location_score_as_dict, get_poi_cached,
        count_apt_masters, get_distinct_sidos, get_distinct_sigungus,
        search_apt_masters, get_apt_search_limits, get_apt_details,
        get_building_master_by_pnu,
    )
    from modules.real_estate.geocoder import GeocoderService
except ImportError:
    from src.dashboard.api_client import DashboardClient
    from src.dashboard.components.map_view import render_detail_map
    from src.dashboard.services import (
        get_location_score, get_location_score_as_dict, get_poi_cached,
        count_apt_masters, get_distinct_sidos, get_distinct_sigungus,
        search_apt_masters, get_apt_search_limits, get_apt_details,
        get_building_master_by_pnu,
    )
    from src.modules.real_estate.geocoder import GeocoderService


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



def _render_analysis_report(rdata: dict, complex_code: str = "") -> None:
    """AptAnalysisReport dict를 구조화된 형태로 렌더링."""
    import requests as _req

    # ── 지표 요약 ────────────────────────────────────────────────────────────
    macro = rdata.get("macro_snapshot") or {}
    base_rate = (macro.get("base_rate") or {}).get("value")
    loan_rate = (macro.get("loan_rate") or {}).get("value")

    m1, m2, m3 = st.columns(3)
    with m1:
        jr = rdata.get("jeonse_ratio")
        st.metric("전세가율", f"{jr:.1f}%" if jr else "-")
    with m2:
        st.metric("기준금리", f"{base_rate}%" if base_rate is not None else "-")
    with m3:
        st.metric("주담대금리", f"{loan_rate}%" if loan_rate is not None else "-")

    if rdata.get("supply_risk_summary"):
        st.caption(f"🏗️ 공급리스크: {rdata['supply_risk_summary']}")

    # ── 입지 점수 (저장된 스냅샷 → live fallback) ────────────────────────────
    try:
        loc = rdata.get("location_score") or (get_location_score_as_dict(complex_code) if complex_code else None)
    except Exception:
        loc = rdata.get("location_score")
    if loc:
        st.markdown("#### 📍 입지 점수")
        lc1, lc2 = st.columns(2)
        with lc1:
            st.metric("🏠 실거주 점수", f"{loc.get('residential_total', '-')}점")
            res_items = (loc.get("results") or {}).get("residential") or []
            if res_items:
                with st.expander("항목별 상세"):
                    for item in res_items:
                        st.progress(item["score"] / 100, text=f"{item['label']}  {item['score']}점")
                        for ev in (item.get("evidence") or []):
                            st.caption(f"　　· {ev}")
        with lc2:
            st.metric("💰 투자 점수", f"{loc.get('investment_total', '-')}점")
            inv_items = (loc.get("results") or {}).get("investment") or []
            if inv_items:
                with st.expander("항목별 상세"):
                    for item in inv_items:
                        st.progress(item["score"] / 100, text=f"{item['label']}  {item['score']}점")
                        for ev in (item.get("evidence") or []):
                            st.caption(f"　　· {ev}")
    else:
        lc1, lc2 = st.columns(2)
        with lc1:
            st.info("🏠 실거주 점수\n\n리포트 생성 후 표시됩니다.")
        with lc2:
            st.info("💰 투자 점수\n\n리포트 생성 후 표시됩니다.")

    # ── POI 분석 (실시간 조회) ────────────────────────────────────────────────
    try:
        poi = get_poi_cached(complex_code) if complex_code else None
    except Exception:
        poi = None
    if poi:
        st.markdown("#### 🗺️ POI 분석 (주변 시설)")
        stations = poi.get("subway_stations") or []
        if stations:
            station_text = " | ".join(f"{s['name']} ({s['walk_minutes']}분)" for s in stations[:5])
            st.caption(f"🚇 지하철: {station_text}")
        p1, p2, p3, p4 = st.columns(4)
        with p1:
            st.metric("🏫 학교", f"{poi['schools_count']}개")
        with p2:
            st.metric("📚 학원", f"{poi['academies_count']}개")
        with p3:
            st.metric("🛒 마트", f"{poi['marts_count']}개")
        with p4:
            st.metric("🏪 편의점", f"{poi['convenience_count']}개")
        p5, p6, p7, p8 = st.columns(4)
        with p5:
            st.metric("💊 약국", f"{poi['pharmacy_count']}개")
        with p6:
            st.metric("🏥 의료", f"{poi['medical_count']}개")
        with p7:
            park_m = poi.get("park_nearest_m") or 0
            st.metric("🌳 공원", f"{park_m}m" if park_m else "-")
        with p8:
            st.metric("🍽️ 음식점", f"{poi['restaurant_count']}개")

    # ── 출퇴근 ───────────────────────────────────────────────────────────────
    commute = rdata.get("commute_summary")
    if commute:
        st.markdown("#### 🚗 출퇴근 요약")
        mode_labels = {"transit": "🚌 대중교통", "car": "🚗 자가용", "walking": "🚶 도보"}
        cols = st.columns(len(commute))
        for i, (mode, mins) in enumerate(commute.items()):
            with cols[i]:
                st.metric(mode_labels.get(mode, mode), f"{mins}분")
    else:
        st.caption("출퇴근: 캐시 데이터 없음 (기존 단지 상세 패널에서 조회 가능)")

    # ── 학군 분석 (실시간 조회) ──────────────────────────────────────────────
    if complex_code:
        with st.expander("📚 학군 분석", expanded=False):
            try:
                school_resp = _req.get(
                    f"{_API_BASE}/dashboard/real-estate/school/{complex_code}",
                    timeout=5,
                )
                if school_resp.status_code == 200:
                    sd = school_resp.json()
                    sc1, sc2, sc3, sc4 = st.columns(4)
                    with sc1:
                        st.metric("반경 1km 학교 수", f"{sd.get('nearby_school_count', '-')}개")
                    with sc2:
                        avg_cls = sd.get("avg_students_per_class") or 0
                        st.metric("학급당 평균 학생수", f"{avg_cls:.1f}명" if avg_cls else "-")
                    with sc3:
                        avg_tch = sd.get("avg_students_per_teacher") or 0
                        st.metric("교사 1인당 학생수", f"{avg_tch:.1f}명" if avg_tch else "-")
                    with sc4:
                        st.metric("학군 점수", f"{sd.get('score', '-')}/100")
                    if sd.get("message"):
                        st.caption(sd["message"])
                else:
                    st.caption("학군 정보 없음")
            except Exception:
                st.caption("학군 조회 실패")

    # ── 실거래가 이력 ────────────────────────────────────────────────────────
    price_history = rdata.get("price_history") or []
    if price_history:
        st.markdown("#### 📈 실거래가 이력")
        try:
            df = pd.DataFrame(price_history)
            df["억원"] = df["price"] / 1e8
            df = df.rename(columns={"date": "거래일", "area": "전용면적(㎡)"})
            st.dataframe(
                df[["거래일", "전용면적(㎡)", "억원"]].sort_values("거래일", ascending=False),
                use_container_width=True, hide_index=True
            )
        except Exception:
            for p in price_history[:5]:
                st.caption(f"{p.get('date')} | {p.get('area')}㎡ | {p.get('price', 0)/1e8:.2f}억")

    # ── AI 종합 분석 ─────────────────────────────────────────────────────────
    st.markdown("#### 🤖 AI 종합 분석")
    st.markdown(rdata.get("llm_insight", "분석 결과 없음"))
    st.caption(f"분석일시: {rdata.get('generated_at', '')[:19]}")


def _render_commute_card(commute_data: dict):
    """출퇴근 경로 3단 카드 렌더링."""
    transit_min = commute_data.get("transit")
    car_min = commute_data.get("car")
    walking_min = commute_data.get("walking")
    transit_legs = commute_data.get("transit_legs", [])
    car_legs = commute_data.get("car_legs", [])
    walking_legs = commute_data.get("walking_legs", [])
    transit_summary = commute_data.get("transit_summary", "")
    car_summary = commute_data.get("car_summary", "")
    walking_summary = commute_data.get("walking_summary", "")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### 🚌 대중교통")
        if transit_min is not None:
            st.metric("소요시간", f"{transit_min}분")
            if transit_legs:
                for leg in transit_legs:
                    mode = leg.get("mode", "")
                    if mode == "WALK":
                        st.caption(f"🚶 도보 {leg.get('duration_minutes', 0)}분")
                    elif mode == "BUS":
                        st.caption(f"🚌 {leg.get('route', '')}번 버스 ({leg.get('stop_count', 0)}정거장)")
                    elif mode in ("SUBWAY", "RAIL"):
                        st.caption(f"🚇 {leg.get('route', '')} ({leg.get('stop_count', 0)}정거장)")
            elif transit_summary:
                st.caption(transit_summary)
        else:
            st.caption("조회 실패")

    with col2:
        st.markdown("#### 🚗 자가용")
        if car_min is not None:
            st.metric("소요시간", f"{car_min}분")
            if car_legs:
                for leg in car_legs:
                    st.caption(f"🛣️ {leg.get('road_name', '')}")
            elif car_summary:
                st.caption(car_summary)
        else:
            st.caption("조회 실패")

    with col3:
        st.markdown("#### 🚶 도보")
        if walking_min is not None:
            st.metric("소요시간", f"{walking_min}분")
            if walking_legs:
                for leg in walking_legs:
                    st.caption(f"🛤️ {leg.get('road_name', '')}")
            elif walking_summary:
                st.caption(walking_summary)
        else:
            st.caption("조회 실패")


def _render_apt_detail_cards(entry) -> None:
    """3단 레이아웃의 가운데 패널 — KPI + 카드 그리드 expander."""
    from modules.real_estate.models import AptMasterEntry
    import requests as _req

    is_master = isinstance(entry, AptMasterEntry)
    complex_code = getattr(entry, "complex_code", None) or ""

    # ── 단지 헤더 ──────────────────────────────────────────────────────────
    details = None
    if is_master and complex_code:
        details = get_apt_details(complex_code)

    addr = ""
    if details:
        addr = getattr(details, "road_address", "") or getattr(details, "legal_address", "") or ""
        constructor = getattr(details, "constructor", "") or ""
        approved = getattr(details, "approved_date", "") or ""
        year = approved[:4] if len(approved) >= 4 else "-"
        household = getattr(details, "household_count", 0)
        sub_text = f"{entry.sigungu or entry.district_code} · {year}년 준공 · {household:,}세대"
        if constructor:
            sub_text += f" · {constructor}"
    else:
        sub_text = entry.sigungu or entry.district_code

    st.markdown(f"### {entry.apt_name}")
    st.caption(sub_text)
    if addr:
        st.caption(f"📍 {addr}")

    # ── KPI 4개 ────────────────────────────────────────────────────────────
    # 실거래가 최근값
    tx_df = DashboardClient.get_real_estate_transactions(
        apt_master_id=getattr(entry, "id", None),
        complex_code=complex_code or None,
        district_code=entry.district_code,
        limit=1,
    )
    recent_price = "-"
    recent_detail = ""
    if not tx_df.empty:
        row = tx_df.iloc[0]
        price_awk = row.get("price", 0) / 100_000_000
        recent_price = f"{price_awk:.1f}억"
        area = row.get("exclusive_area", 0)
        floor = row.get("floor", 0)
        recent_detail = f"{area:.0f}㎡ · {floor}층"

    # 입지점수
    loc_score = None
    try:
        loc_score = get_location_score(complex_code)
    except Exception:
        pass

    # 출퇴근 (API 호출)
    commute_data = None
    commute_min = "-"
    if addr:
        try:
            resp = _req.get(
                f"{_API_BASE}/dashboard/real-estate/commute",
                params={"address": addr, "apt_name": entry.apt_name, "district_code": entry.district_code},
                timeout=10,
            )
            if resp.status_code == 200:
                commute_data = resp.json()
                transit = commute_data.get("transit_minutes") or commute_data.get("transit")
                if transit:
                    commute_min = f"{transit}분"
        except Exception:
            pass

    kc1, kc2, kc3, kc4 = st.columns(4)
    kc1.metric("최근거래", recent_price, help=recent_detail)
    kc2.metric("입지점수", f"{loc_score.residential_total}점" if loc_score else "-")
    kc3.metric("출퇴근", commute_min)
    kc4.metric("전세가율", "-")  # 전세가율은 별도 API 없으면 "-" 유지

    st.divider()

    # ── 📍 입지점수 (카드 그리드) ───────────────────────────────────────────
    if loc_score:
        label = (f"📍 입지점수 — 실거주 **{loc_score.residential_total}점** "
                 f"/ 투자 **{loc_score.investment_total}점**")
        with st.expander(label, expanded=True):
            results = loc_score.residential_results or []
            for i in range(0, len(results), 2):
                c1, c2 = st.columns(2)
                for col, dr in zip([c1, c2], results[i:i+2]):
                    with col:
                        with st.container(border=True):
                            st.markdown(f"**{dr.label}**")
                            col_score, col_bar = st.columns([1, 3])
                            col_score.metric("", f"{dr.score}점")
                            col_bar.progress(min(dr.score / 100, 1.0))
                            for ev in (getattr(dr, "evidence", None) or []):
                                st.caption(f"　　· {ev}")
    else:
        with st.expander("📍 입지점수", expanded=False):
            st.info("입지 분석 데이터가 없습니다. 심층 분석을 실행하세요.")

    # ── 📈 실거래가 (카드 그리드) ──────────────────────────────────────────
    tx_df_full = DashboardClient.get_real_estate_transactions(
        apt_master_id=getattr(entry, "id", None),
        complex_code=complex_code or None,
        district_code=entry.district_code,
        limit=20,
    )
    tx_label = f"📈 실거래가 — {recent_price}" + (f" · {recent_detail}" if recent_detail else "")
    with st.expander(tx_label, expanded=False):
        if tx_df_full.empty:
            st.info("거래 이력이 없습니다.")
        else:
            rows_data = []
            for _, row in tx_df_full.head(8).iterrows():
                rows_data.append({
                    "date": str(row.get("deal_date", "-"))[:10],
                    "price": f"{row.get('price', 0) / 100_000_000:.1f}억",
                    "area": f"{row.get('exclusive_area', 0):.0f}㎡ · {int(row.get('floor', 0))}층",
                })
            for i in range(0, len(rows_data), 2):
                c1, c2 = st.columns(2)
                for col, r in zip([c1, c2], rows_data[i:i+2]):
                    with col:
                        with st.container(border=True):
                            st.caption(r["date"])
                            st.markdown(f"**{r['price']}**")
                            st.caption(r["area"])

    # ── 🚇 출퇴근 (카드 그리드) ────────────────────────────────────────────
    with st.expander(f"🚇 출퇴근 — {commute_min}", expanded=False):
        if commute_data:
            transit = commute_data.get("transit_minutes") or commute_data.get("transit")
            bus = commute_data.get("bus_minutes") or commute_data.get("bus")
            c1, c2 = st.columns(2)
            with c1:
                with st.container(border=True):
                    st.markdown("**🚇 지하철**")
                    st.metric("", f"{transit}분" if transit else "-")
                    route = commute_data.get("transit_route") or commute_data.get("route", "")
                    if route:
                        st.caption(route)
            with c2:
                with st.container(border=True):
                    st.markdown("**🚌 버스**")
                    st.metric("", f"{bus}분" if bus else "-")
        else:
            st.info("출퇴근 정보를 불러올 수 없습니다.")

    # ── 🤖 AI 인사이트 ────────────────────────────────────────────────────
    # NOTE: list_insight_reports()/get_insight_report()는 날짜 기반 데일리
    # 브리핑(Tab5)용이며 complex_code 필드가 없다. 단지별 심층 분석 결과는
    # GET /dashboard/apt/analysis/{complex_code}/latest 로 조회한다
    # (기존 _render_apt_detail_panel의 "이전 분석 보기" 버튼과 동일 엔드포인트).
    _analysis_complex_code = complex_code or (getattr(details, "complex_code", None) if details else None)
    latest_report = None
    if _analysis_complex_code:
        try:
            resp = _req.get(
                f"{_API_BASE}/dashboard/apt/analysis/{_analysis_complex_code}/latest",
                timeout=10,
            )
            if resp.status_code == 200:
                latest_report = resp.json()
        except Exception:
            pass

    if latest_report:
        insight = latest_report.get("llm_insight", "")
        preview = insight[:80] + "..." if len(insight) > 80 else insight
        with st.expander(f"🤖 AI 인사이트 — {preview}", expanded=False):
            _render_analysis_report(latest_report, _analysis_complex_code)
    else:
        with st.expander("🤖 AI 인사이트", expanded=False):
            if _analysis_complex_code:
                if st.button("🔬 심층 분석 실행", key=f"analyze_card_{_analysis_complex_code}",
                             use_container_width=True):
                    with st.spinner("LLM 분석 중... (최대 2분)"):
                        try:
                            resp = _req.post(
                                f"{_API_BASE}/jobs/apt/analyze",
                                json={"complex_code": _analysis_complex_code, "send_slack": False},
                                timeout=180,
                            )
                            if resp.status_code == 200:
                                rdata = resp.json().get("report", {})
                                _render_analysis_report(rdata, _analysis_complex_code)
                            else:
                                st.error(f"분석 실패: {resp.status_code}")
                        except Exception as e:
                            st.error(f"오류: {e}")
            else:
                st.info("단지코드 없음 — 심층 분석 불가")


def show_real_estate():
    st.title("🏢 Real Estate Insights")

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🔍 아파트 탐색",
        "📈 거시경제",
        "📰 뉴스 리포트",
        "📌 정책 팩트",
        "📋 데일리 브리핑",
        "👤 페르소나",
    ])

    # ──────────────────────────────────────────────────────────
    # TAB 1: 아파트 탐색 (마스터 필터 → 목록 → 상세 + 실거래가 + 지도)
    # ──────────────────────────────────────────────────────────
    with tab1:
        try:
            _tx_limit, _map_limit = get_apt_search_limits()

            _apt_master_empty = count_apt_masters() == 0
            if _apt_master_empty:
                st.warning(
                    "⚠️ apt_master 테이블이 비어 있습니다. 마이그레이션 스크립트를 먼저 실행하세요.\n\n"
                    "```bash\narch -arm64 .venv/bin/python3.12 scripts/migrate_to_transaction_first.py\n```"
                )

            # ── 상단 검색바 ──────────────────────────────────────────────
            sb1, sb2, sb3, sb4 = st.columns([3, 1.5, 1.5, 1])
            with sb1:
                search_name = st.text_input(
                    "검색", placeholder="🔍 아파트명 검색...",
                    label_visibility="collapsed", key="master_search_name"
                )
            with sb2:
                sido_opts = ["전체"] + get_distinct_sidos()
                selected_sido = st.selectbox("시도", sido_opts,
                    label_visibility="collapsed", key="master_sido")
                sido_filter = "" if selected_sido == "전체" else selected_sido
            with sb3:
                sigungu_opts = ["전체"] + get_distinct_sigungus(sido_filter)
                selected_sigungu = st.selectbox("시군구", sigungu_opts,
                    label_visibility="collapsed", key="master_sigungu")
                sigungu_filter = "" if selected_sigungu == "전체" else selected_sigungu
            with sb4:
                search_btn = st.button("검색", key="master_search_btn", use_container_width=True)

            if not _apt_master_empty:
                # ── 검색 실행 ────────────────────────────────────────────────
                if search_btn or "master_results" not in st.session_state:
                    with st.spinner("검색 중..."):
                        st.session_state.master_results = search_apt_masters(
                            apt_name=search_name, sido=sido_filter, sigungu=sigungu_filter,
                        )
                    st.session_state.pop("selected_apt_idx", None)

                results = st.session_state.get("master_results", [])

                # ── 3단 분할 ─────────────────────────────────────────────────
                col_list, col_detail, col_map = st.columns([1.2, 1.6, 1.8])

                # ── 왼쪽: 단지 목록 ──────────────────────────────────────────
                with col_list:
                    st.caption(f"**{len(results)}건** 검색됨")
                    _row_limit = 100
                    for _i, _m in enumerate(results[:_row_limit]):
                        _is_sel = st.session_state.get("selected_apt_idx") == _i
                        last_tx = _m.last_traded[:10] if _m.last_traded else "-"
                        btn_label = (
                            f"{'▶ ' if _is_sel else ''}{_m.apt_name}\n"
                            f"{_m.sigungu or _m.district_code} · {last_tx}"
                        )
                        if st.button(
                            btn_label,
                            key=f"apt_row_{_i}",
                            use_container_width=True,
                            type="primary" if _is_sel else "secondary",
                        ):
                            st.session_state.selected_apt_idx = _i
                            st.rerun()

                    if len(results) > _row_limit:
                        st.caption(f"상위 {_row_limit}건 표시 — 필터를 좁혀 검색하세요.")

                # ── 가운데: 상세 카드 ─────────────────────────────────────────
                with col_detail:
                    _sel_idx = st.session_state.get("selected_apt_idx")
                    if _sel_idx is not None and _sel_idx < len(results):
                        _render_apt_detail_cards(results[_sel_idx])
                    else:
                        st.info("왼쪽 목록에서 단지를 선택하세요.")

                # ── 오른쪽: 지도 ─────────────────────────────────────────────
                with col_map:
                    _sel_idx = st.session_state.get("selected_apt_idx")
                    if _sel_idx is not None and _sel_idx < len(results):
                        _entry = results[_sel_idx]
                        _kakao_key = os.environ.get("KAKAO_API_KEY", "")

                        if not _kakao_key:
                            st.warning("KAKAO_API_KEY 환경변수가 설정되지 않았습니다.")
                        elif st_folium is None:
                            st.warning("streamlit-folium 패키지가 설치되지 않았습니다.")
                        else:
                            # 지도 모드 선택
                            map_mode = st.radio(
                                "지도 레이어",
                                ["📍 위치", "🏙 POI"],
                                horizontal=True,
                                key="detail_map_mode",
                                label_visibility="collapsed",
                            )

                            _details = get_apt_details(_entry.complex_code) if _entry.complex_code else None
                            _addr = ""
                            if _details:
                                _addr = getattr(_details, "road_address", "") or getattr(_details, "legal_address", "") or ""

                            _poi = None
                            if map_mode == "🏙 POI" and _entry.complex_code:
                                try:
                                    _poi = get_poi_cached(_entry.complex_code)
                                except Exception:
                                    pass

                            # 페르소나 직장 위치 (역명 또는 주소)
                            _persona = st.session_state.get("persona") or {}
                            _workplace = (_persona.get("commute") or {}).get("workplace_station") or None

                            # 출퇴근 요약
                            _commute_sum = st.session_state.get(f"commute_{_entry.district_code}_{_entry.apt_name}")

                            _geocoder = GeocoderService(api_key=_kakao_key)
                            _cache_key = f"detail_map_{_entry.district_code}_{_entry.apt_name}_{map_mode}"

                            if _cache_key not in st.session_state:
                                with st.spinner("지도 로딩 중..."):
                                    st.session_state[_cache_key] = render_detail_map(
                                        address=_addr,
                                        apt_name=_entry.apt_name,
                                        district_code=_entry.district_code,
                                        geocoder=_geocoder,
                                        workplace_address=_workplace,
                                        poi_cached=_poi if map_mode == "🏙 POI" else None,
                                        commute_summary=_commute_sum,
                                    )

                            st_folium(
                                st.session_state[_cache_key],
                                use_container_width=True,
                                height=500,
                                key=f"detail_folium_{_entry.district_code}_{_entry.apt_name}_{map_mode}",
                                returned_objects=[],
                            )
                    else:
                        st.info("단지를 선택하면 위치가 표시됩니다.")

        except Exception as _e:
            st.error(f"마스터 DB 조회 오류: {_e}")
            st.info("DB 경로 또는 API 서버 상태를 확인하세요.")

    # ──────────────────────────────────────────────────────────
    # TAB 2: 거시경제
    # ──────────────────────────────────────────────────────────
    with tab2:
        st.subheader("거시경제 지표")

        if "macro_latest" not in st.session_state:
            with st.spinner("한국은행 지표 로딩 중..."):
                st.session_state.macro_latest = DashboardClient.get_macro_latest(domain="real_estate")

        items = st.session_state.macro_latest

        if not items:
            st.info("거시경제 데이터를 불러올 수 없습니다.")
            st.caption("수집 Job을 먼저 실행하거나 '📈 거시경제' 탭의 새로고침 버튼을 사용하세요.")
        else:
            from collections import defaultdict
            by_category: dict = defaultdict(list)
            for item in items:
                by_category[item.get("category", "기타")].append(item)

            cat_tabs = st.tabs([f"📊 {cat}" for cat in by_category])
            for cat_tab, (cat_name, cat_items) in zip(cat_tabs, by_category.items()):
                with cat_tab:
                    cols = st.columns(min(len(cat_items), 3))
                    for col, item in zip(cols, cat_items):
                        with col:
                            unit = item["unit"]
                            val = item["value"]
                            if unit == "지수":
                                disp = f"{val:,.3f}".rstrip("0").rstrip(".")
                            elif unit == "십억원":
                                disp = f"{val / 1_000:,.0f}조원"
                            else:
                                disp = f"{val}{unit}"
                            st.metric(
                                label=item["name"],
                                value=disp,
                                help=f"기준기간: {item['period']} | 수집: {item['collected_at'][:10]}",
                            )

                    st.markdown("---")

                    first = cat_items[0]
                    chart_data = DashboardClient.get_macro_indicator_history(
                        indicator_id=first["id"], months=24
                    )
                    records = chart_data.get("records", [])
                    if records:
                        chart_df = pd.DataFrame(records).set_index("period")
                        st.markdown(f"**{first['name']} 추이 (최근 24개월)**")
                        st.line_chart(chart_df["value"], height=250)
                        st.caption(f"출처: 한국은행 ECOS | 단위: {first['unit']}")

        if st.button("🔄 새로고침", key="macro_refresh"):
            st.session_state.pop("macro_latest", None)
            st.rerun()

    # ──────────────────────────────────────────────────────────
    # TAB 3: 뉴스 리포트
    # ──────────────────────────────────────────────────────────
    with tab3:
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

    # ──────────────────────────────────────────────────────────
    # TAB 4: 정책 팩트
    # ──────────────────────────────────────────────────────────
    with tab4:
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
    # TAB 5: 데일리 브리핑
    # ──────────────────────────────────────────────────────────
    with tab5:
        _render_daily_report_tab()

    # ──────────────────────────────────────────────────────────
    # TAB 6: 페르소나 편집
    # ──────────────────────────────────────────────────────────
    with tab6:
        st.subheader("👤 페르소나 설정")
        st.caption("여기서 수정한 값은 다음 부동산 리포트 생성 시 즉시 반영됩니다.")

        col_reload, _ = st.columns([1, 4])
        with col_reload:
            if st.button("🔄 새로고침", key="persona_reload"):
                st.session_state.pop("persona", None)

        if not st.session_state.get("persona"):
            with st.spinner("페르소나 로딩 중..."):
                st.session_state.persona = DashboardClient.get_persona()

        p = st.session_state.get("persona", {})
        if not p:
            st.error("페르소나를 불러올 수 없습니다. API 서버 상태를 확인하세요.")
        else:
            user = p.get("user", {})
            assets = user.get("assets", {})
            income = user.get("income", {})
            plans = user.get("plans", {})
            commute = p.get("commute", {})
            apt_pref = p.get("apartment_preferences", {})
            pw = p.get("priority_weights", {
                "commute": 40, "liquidity": 20, "school": 15,
                "living_convenience": 15, "price_potential": 10,
            })

            # ── 자산 / 소득 ──────────────────────────────────
            st.markdown("#### 💰 자산 & 소득")
            col1, col2 = st.columns(2)
            with col1:
                asset_self = st.number_input(
                    "본인 자산 (만원)", value=int(assets.get("self", 0) / 10000),
                    step=100, min_value=0, key="p_asset_self"
                )
                asset_partner = st.number_input(
                    "파트너 자산 (만원)", value=int(assets.get("partner", 0) / 10000),
                    step=100, min_value=0, key="p_asset_partner"
                )
                asset_total = (asset_self + asset_partner) * 10000
                st.metric("합산 자산", f"{asset_total / 1e8:.2f}억원")
            with col2:
                income_self = st.number_input(
                    "본인 연소득 (만원)", value=int(income.get("self", 0) / 10000),
                    step=100, min_value=0, key="p_income_self"
                )
                income_partner = st.number_input(
                    "파트너 연소득 (만원)", value=int(income.get("partner", 0) / 10000),
                    step=100, min_value=0, key="p_income_partner"
                )
                income_total = (income_self + income_partner) * 10000
                st.metric("합산 연소득", f"{income_total / 1e8:.2f}억원")

            st.markdown("---")

            # ── 선호 기준 가중치 ────────────────────────────────
            st.markdown("#### ⚖️ 선호 기준 가중치")
            st.caption("각 항목의 중요도를 설정하세요. 리포트에서 가중치가 높은 항목을 더 상세히 분석합니다.")

            WEIGHT_LABELS = {
                "commute": "⚡ 출퇴근 편의성",
                "liquidity": "💰 환금성 (역세권·거래량)",
                "school": "🎒 학군",
                "living_convenience": "🛍️ 생활편의 (마트·병원·편의시설)",
                "price_potential": "📈 가격상승 가능성 (GTX·재건축)",
            }

            w_commute = st.slider(
                WEIGHT_LABELS["commute"], 0, 10,
                value=int(pw.get("commute", 40) / 10), key="pw_commute"
            )
            w_liquidity = st.slider(
                WEIGHT_LABELS["liquidity"], 0, 10,
                value=int(pw.get("liquidity", 20) / 10), key="pw_liquidity"
            )
            w_school = st.slider(
                WEIGHT_LABELS["school"], 0, 10,
                value=int(pw.get("school", 15) / 10), key="pw_school"
            )
            w_living = st.slider(
                WEIGHT_LABELS["living_convenience"], 0, 10,
                value=int(pw.get("living_convenience", 15) / 10), key="pw_living"
            )
            w_price = st.slider(
                WEIGHT_LABELS["price_potential"], 0, 10,
                value=int(pw.get("price_potential", 10) / 10), key="pw_price"
            )

            raw_total = w_commute + w_liquidity + w_school + w_living + w_price
            if raw_total > 0:
                norm = lambda v: round(v / raw_total * 100)
                pct_commute = norm(w_commute)
                pct_liquidity = norm(w_liquidity)
                pct_school = norm(w_school)
                pct_living = norm(w_living)
                pct_price = norm(w_price)
                ranked_weights = sorted(
                    [(WEIGHT_LABELS[k], v) for k, v in [
                        ("commute", pct_commute), ("liquidity", pct_liquidity),
                        ("school", pct_school), ("living_convenience", pct_living),
                        ("price_potential", pct_price),
                    ]],
                    key=lambda x: x[1], reverse=True
                )
                st.markdown("**📊 정규화된 가중치 (리포트 반영 비율):**")
                bar_cols = st.columns(5)
                for i, (label, pct) in enumerate(ranked_weights):
                    with bar_cols[i]:
                        st.metric(label.split(" ", 1)[-1][:6], f"{pct}%")
            else:
                st.warning("최소 하나 이상의 항목에 가중치를 설정하세요.")
                pct_commute = pct_liquidity = pct_school = pct_living = pct_price = 20

            st.markdown("---")

            # ── 관심 지역 ──────────────────────────────────────
            st.markdown("#### 🗺️ 관심 지역")
            if not st.session_state.get("districts"):
                st.session_state.districts = DashboardClient.get_districts()
            all_district_names = [d["name"] for d in st.session_state.get("districts", [])]
            current_areas = user.get("interest_areas", [])
            selected_areas = st.multiselect(
                "관심 지역 선택 (최대 6개)",
                options=all_district_names,
                default=[a for a in current_areas if a in all_district_names],
                max_selections=6,
                key="p_interest_areas"
            )

            st.markdown("---")

            # ── 매수 계획 / 출퇴근 ─────────────────────────────
            st.markdown("#### 🏠 매수 계획 & 출퇴근")
            col3, col4 = st.columns(2)
            with col3:
                is_first_time = st.checkbox(
                    "생애최초 주택구입자",
                    value=plans.get("is_first_time_buyer", True),
                    key="p_first_time"
                )
                wedding_plan = st.text_input(
                    "결혼 계획",
                    value=plans.get("wedding", ""),
                    key="p_wedding"
                )
            with col4:
                max_commute = st.slider(
                    "최대 출퇴근 시간 (분)",
                    min_value=20, max_value=90,
                    value=commute.get("max_door_to_door_minutes", 50),
                    step=5, key="p_max_commute"
                )
                min_area = st.number_input(
                    "최소 전용면적 (㎡)",
                    value=apt_pref.get("min_exclusive_area_sqm", 59),
                    min_value=20, max_value=200, step=1, key="p_min_area"
                )

            st.markdown("---")

            # ── 저장 버튼 ──────────────────────────────────────
            if st.button("💾 페르소나 저장", type="primary", use_container_width=True):
                updates = {
                    "user": {
                        "assets": {
                            "self": asset_self * 10000,
                            "partner": asset_partner * 10000,
                            "total": asset_total,
                        },
                        "income": {
                            "self": income_self * 10000,
                            "partner": income_partner * 10000,
                            "total": income_total,
                        },
                        "interest_areas": selected_areas,
                        "plans": {
                            "is_first_time_buyer": is_first_time,
                            "wedding": wedding_plan,
                        },
                    },
                    "commute": {
                        "max_door_to_door_minutes": max_commute,
                    },
                    "apartment_preferences": {
                        "min_exclusive_area_sqm": min_area,
                    },
                    "priority_weights": {
                        "commute": pct_commute,
                        "liquidity": pct_liquidity,
                        "school": pct_school,
                        "living_convenience": pct_living,
                        "price_potential": pct_price,
                    },
                }
                with st.spinner("저장 중..."):
                    result = DashboardClient.update_persona(updates)

                if "error" in result:
                    st.error(f"❌ 저장 실패: {result['error']}")
                else:
                    st.success("✅ 페르소나 저장 완료. 다음 리포트 생성 시 반영됩니다.")
                    st.session_state.persona = result.get("persona", {})
                    st.rerun()

            st.markdown("---")

            # ── 추천 필터 규칙 ─────────────────────────────────
            st.markdown("#### 🔧 추천 필터 규칙")
            st.caption(
                "활성화(ON)된 규칙만 리포트 생성 시 LLM에 전달됩니다. "
                "조건 문장을 직접 편집하거나, 새 규칙을 추가/삭제할 수 있습니다."
            )

            col_rules_reload, _ = st.columns([1, 5])
            with col_rules_reload:
                if st.button("🔄 새로고침", key="rules_reload"):
                    st.session_state.pop("preference_rules", None)

            if "preference_rules" not in st.session_state:
                with st.spinner("규칙 로딩 중..."):
                    st.session_state.preference_rules = DashboardClient.get_preference_rules()

            rules = st.session_state.get("preference_rules", [])

            # 기존 규칙 목록
            for i, rule in enumerate(rules):
                col_toggle, col_del = st.columns([11, 1])
                with col_toggle:
                    st.toggle(
                        f"**{rule.get('description', rule.get('id', f'규칙 {i+1}'))}**",
                        value=rule.get("enabled", True),
                        key=f"rule_enabled_{i}",
                    )
                with col_del:
                    if st.button("🗑️", key=f"rule_del_{i}", help="이 규칙 삭제"):
                        st.session_state.preference_rules = [r for j, r in enumerate(rules) if j != i]
                        st.rerun()

                with st.expander(f"📝 조건 편집  `{rule.get('id', '')}`", expanded=False):
                    st.text_input("설명", value=rule.get("description", ""), key=f"rule_desc_{i}")
                    st.text_area(
                        "LLM에 전달되는 조건 문장",
                        value=rule.get("constraint", "").strip(),
                        key=f"rule_constraint_{i}",
                        height=90,
                    )

            # 새 규칙 추가
            with st.expander("➕ 새 규칙 추가", expanded=False):
                new_id = st.text_input("규칙 ID (영문, 예: no_old_buildings)", key="new_rule_id")
                new_desc = st.text_input("설명 (한 줄)", key="new_rule_desc")
                new_constraint = st.text_area(
                    "LLM에 전달할 조건 문장",
                    key="new_rule_constraint",
                    height=90,
                    placeholder="예: 준공 후 30년 이상 된 단지는 추천하지 마십시오.",
                )
                if st.button("➕ 목록에 추가", key="add_rule_btn"):
                    if new_id and new_desc and new_constraint:
                        st.session_state.preference_rules = rules + [{
                            "id": new_id,
                            "enabled": True,
                            "description": new_desc,
                            "constraint": new_constraint.strip(),
                        }]
                        st.success(f"규칙 '{new_desc}' 추가됨. 저장 버튼을 눌러 반영하세요.")
                        st.rerun()
                    else:
                        st.warning("ID, 설명, 조건 문장을 모두 입력하세요.")

            # 필터 규칙 저장
            if st.button("💾 필터 규칙 저장", key="save_rules_btn", use_container_width=True):
                current_rules = st.session_state.get("preference_rules", [])
                updated_rules = [
                    {
                        "id": r.get("id", f"rule_{i}"),
                        "enabled": st.session_state.get(f"rule_enabled_{i}", r.get("enabled", True)),
                        "description": st.session_state.get(f"rule_desc_{i}", r.get("description", "")).strip(),
                        "constraint": st.session_state.get(f"rule_constraint_{i}", r.get("constraint", "")).strip(),
                    }
                    for i, r in enumerate(current_rules)
                ]
                with st.spinner("저장 중..."):
                    result = DashboardClient.update_preference_rules(updated_rules)
                if "error" in result:
                    st.error(f"❌ 저장 실패: {result['error']}")
                else:
                    st.success(f"✅ {len(updated_rules)}개 규칙 저장 완료. 다음 리포트 생성 시 반영됩니다.")
                    st.session_state.preference_rules = result.get("rules", updated_rules)
                    st.rerun()


# ──────────────────────────────────────────────────────────
# 데일리 리포트 탭 렌더러
# ──────────────────────────────────────────────────────────

def _render_daily_report_tab():
    """데일리 리포트 탭 — 날짜 선택 + 리포트 본문 렌더링."""
    st.subheader("📰 데일리 부동산 브리핑")

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 오늘 리포트 생성", use_container_width=True):
            with st.spinner("리포트 생성 중... (2~5분 소요)"):
                r = DashboardClient.trigger_generate_daily_report(days=3, top_k=5)
                if "error" in r:
                    st.error(f"❌ 오류: {r['error']}")
                elif r.get("status") in ("success", "exists"):
                    st.success(
                        f"✅ {r.get('date')} | Slack {'전송됨' if r.get('slack_sent') else '전송 안됨'}"
                    )
                    st.session_state.pop("daily_report_dates", None)
                    st.rerun()
                else:
                    st.error(f"생성 실패: {r}")

    dates = DashboardClient.list_daily_reports()

    if not dates:
        st.info("저장된 데일리 리포트가 없습니다. '오늘 리포트 생성' 버튼을 눌러주세요.")
        return

    with col1:
        selected_date = st.selectbox("날짜 선택", options=dates, index=0, key="daily_report_date_select")

    if selected_date:
        with st.spinner("리포트 로딩 중..."):
            resp = DashboardClient.get_daily_report(selected_date)
            markdown = resp.get("markdown", "")
        if markdown:
            st.markdown(markdown, unsafe_allow_html=True)
        else:
            st.warning("리포트 내용이 비어있습니다.")
