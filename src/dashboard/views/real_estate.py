import os
import re
import sys
import streamlit as st
import pandas as pd
from typing import Dict, List

try:
    from streamlit_folium import st_folium
except ImportError:
    st_folium = None  # type: ignore

try:
    from dashboard.api_client import DashboardClient
    from dashboard.components.map_view import render_master_map_view
    from modules.real_estate.geocoder import GeocoderService
except ImportError:
    from src.dashboard.api_client import DashboardClient
    from src.dashboard.components.map_view import render_master_map_view
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


def _render_apt_detail_panel(entry, apt_repo=None, bm_repo=None, tx_limit: int = 50) -> None:
    """선택된 단지의 상세정보 + 실거래가 패널을 렌더링한다.

    Args:
        entry: AptMasterEntry (Transaction-First 마스터) 또는 ApartmentMaster (레거시)
        apt_repo: ApartmentRepository — complex_code로 상세정보 조회 (optional)
        tx_limit: 실거래가 최대 표시 건수
    """
    from modules.real_estate.models import AptMasterEntry

    is_apt_master_entry = isinstance(entry, AptMasterEntry)

    st.markdown("---")
    st.markdown(f"### 📋 {entry.apt_name}")

    # ── 상세정보 (optional) ───────────────────────────────────────────────────
    details = None
    if is_apt_master_entry:
        # AptMasterEntry: complex_code 있으면 apt_details 조회
        if entry.complex_code and apt_repo is not None:
            details = apt_repo.get(entry.complex_code)
        if details is None:
            # 상세정보 없는 단지 — Transaction-First에서는 정상 케이스
            st.info("상세정보 없음 (공동주택 기본정보 API 미수록 단지)")
    else:
        # 레거시: ApartmentMaster 객체 자체가 상세정보
        details = entry

    if details is not None:
        addr = getattr(details, "road_address", "") or getattr(details, "legal_address", "")
        if addr:
            st.caption(f"📍 {addr}")

        approved = getattr(details, "approved_date", "") or ""
        year_disp = approved[:4] if len(approved) >= 4 else "-"

        dc1, dc2, dc3, dc4 = st.columns(4)
        with dc1:
            st.metric("세대수", f"{getattr(details, 'household_count', 0):,}세대")
        with dc2:
            st.metric("동수", f"{getattr(details, 'building_count', 0)}개동")
        with dc3:
            st.metric("준공연도", f"{year_disp}년")
        with dc4:
            top_floor = getattr(details, "top_floor", 0)
            st.metric("최고층수", f"{top_floor}F" if top_floor else "-")

        dc5, dc6, dc7, dc8 = st.columns(4)
        with dc5:
            st.metric("건설사", getattr(details, "constructor", "") or "-")
        with dc6:
            st.metric("시행사", getattr(details, "developer", "") or "-")
        with dc7:
            st.metric("난방방식", getattr(details, "heat_type", "") or "-")
        with dc8:
            elev = getattr(details, "elevator_count", 0)
            st.metric("승강기", f"{elev}대" if elev else "-")

        units = (
            getattr(details, "units_60", 0) + getattr(details, "units_85", 0)
            + getattr(details, "units_135", 0) + getattr(details, "units_136_plus", 0)
        )
        if units > 0:
            st.markdown("**전용면적별 세대 구성**")
            uc1, uc2, uc3, uc4 = st.columns(4)
            with uc1:
                st.metric("60㎡ 이하", f"{getattr(details, 'units_60', 0):,}세대")
            with uc2:
                st.metric("60~85㎡", f"{getattr(details, 'units_85', 0):,}세대")
            with uc3:
                st.metric("85~135㎡", f"{getattr(details, 'units_135', 0):,}세대")
            with uc4:
                st.metric("135㎡ 초과", f"{getattr(details, 'units_136_plus', 0):,}세대")

        total_area = getattr(details, "total_area", 0)
        complex_code = getattr(entry, "complex_code", None) or getattr(details, "complex_code", None)
        st.caption(
            f"단지코드: {complex_code or '-'}  |  지구코드: {entry.district_code}"
            + (f"  |  연면적: {total_area:,.0f}㎡" if total_area else "")
        )

        # 출퇴근 경로 상세 카드
        _road_address = getattr(details, "road_address", "") or ""
        with st.expander("🗺️ 출퇴근 경로 상세", expanded=False):
            try:
                import requests as _req
                commute_resp = _req.get(
                    "http://localhost:8000/dashboard/real-estate/commute",
                    params={
                        "address": _road_address,
                        "apt_name": entry.apt_name or "",
                        "district_code": entry.district_code or "",
                    },
                    timeout=30,
                )
                if commute_resp.status_code == 200:
                    _render_commute_card(commute_resp.json())
                else:
                    st.caption("출퇴근 정보 조회 실패")
            except Exception:
                st.caption("서버 연결 실패 — FastAPI 서버가 실행 중인지 확인하세요")

    # ── 건물 정보 (용적률·건폐율 from building_master) ───────────────────────
    _pnu = getattr(entry, "pnu", None)
    if _pnu and bm_repo is not None:
        try:
            _bm = bm_repo.get_by_mgm_pk(_pnu)
        except Exception:
            _bm = None
        if _bm is not None and (_bm.floor_area_ratio is not None or _bm.building_coverage_ratio is not None):
            st.markdown("#### 🏗️ 건물 정보 (건축물대장)")
            _bc1, _bc2 = st.columns(2)
            with _bc1:
                _far = _bm.floor_area_ratio
                st.metric("용적률", f"{_far:.1f}%" if _far is not None else "-")
            with _bc2:
                _bcr = _bm.building_coverage_ratio
                st.metric("건폐율", f"{_bcr:.1f}%" if _bcr is not None else "-")

    # ── 실거래가 ──────────────────────────────────────────────────────────────
    st.markdown("### 📈 최근 실거래가")

    # 캐시 키: AptMasterEntry이면 id, 아니면 complex_code/district_code 기반
    if is_apt_master_entry and getattr(entry, "id", None) is not None:
        _tx_cache_key = f"tx__master__{entry.id}"
    else:
        complex_code = getattr(entry, "complex_code", None)
        _tx_cache_key = f"tx__{complex_code or entry.district_code}__{entry.apt_name}"

    if _tx_cache_key not in st.session_state:
        with st.spinner("실거래가 조회 중..."):
            raw_df = pd.DataFrame()

            if is_apt_master_entry and getattr(entry, "id", None) is not None:
                # Transaction-First: apt_master_id로 정확 조회 (항상 성공)
                raw_df = DashboardClient.get_real_estate_transactions(
                    apt_master_id=entry.id,
                    limit=tx_limit,
                )
            elif getattr(entry, "complex_code", None):
                # 레거시: complex_code 조회
                raw_df = DashboardClient.get_real_estate_transactions(
                    complex_code=entry.complex_code,
                    limit=tx_limit,
                )

            # fallback: district + fuzzy 이름 매칭 (레거시 호환 / apt_master 미구축 단지)
            if raw_df.empty:
                district_df = DashboardClient.get_real_estate_transactions(
                    district_code=entry.district_code,
                    limit=min(tx_limit * 10, 500),
                )
                if not district_df.empty:
                    master_nm = entry.apt_name.strip().lower()

                    def _fuzzy(tx_name: str) -> bool:
                        tx = tx_name.strip().lower()
                        if tx in master_nm or master_nm in tx:
                            return True
                        shorter = tx if len(tx) <= len(master_nm) else master_nm
                        longer = master_nm if shorter is tx else tx
                        if len(shorter) >= 4:
                            for n in range(4, len(shorter) + 1):
                                if shorter[-n:] in longer:
                                    return True
                        return False

                    raw_df = district_df[district_df["apt_name"].apply(_fuzzy)]

            st.session_state[_tx_cache_key] = raw_df

    tx_df = st.session_state.get(_tx_cache_key, pd.DataFrame())

    col_tx_hd, col_tx_btn = st.columns([3, 1])
    with col_tx_hd:
        if not tx_df.empty:
            st.caption(f"최근 {len(tx_df)}건 (최대 {tx_limit}건, 최신순)")
    with col_tx_btn:
        sigungu = getattr(entry, "sigungu", "") or entry.district_code
        if st.button("📥 실거래가 수집", key="collect_tx_for_apt", use_container_width=True):
            with st.spinner(f"{sigungu} 수집 중..."):
                r = DashboardClient.trigger_fetch_transactions(district_code=entry.district_code)
            if "error" in r:
                st.error(r["error"])
            else:
                st.success(
                    f"✅ {r.get('fetched_count', 0)}건 수집 "
                    f"/ {r.get('saved_count', 0)}건 저장"
                )
                st.session_state.pop(_tx_cache_key, None)
                st.rerun()

    if tx_df.empty:
        st.info("저장된 실거래가가 없습니다. '📥 실거래가 수집' 버튼으로 데이터를 수집하세요.")
    else:
        _render_tx_dataframe(
            tx_df.sort_values("deal_date", ascending=False).head(tx_limit).copy()
        )


def show_real_estate():
    st.title("🏢 Real Estate Insights")

    tab1, tab2, tab3, tab4 = st.tabs(["🔍 아파트 탐색", "💡 Insight", "📋 Report Archive", "👤 페르소나"])

    # ──────────────────────────────────────────────────────────
    # TAB 1: 아파트 탐색 (마스터 필터 → 목록 → 상세 + 실거래가 + 지도)
    # ──────────────────────────────────────────────────────────
    with tab1:
        try:
            try:
                from modules.real_estate.apt_master_repository import AptMasterRepository
                from modules.real_estate.apartment_repository import ApartmentRepository
                from modules.real_estate.building_master.building_master_repository import BuildingMasterRepository
                from modules.real_estate.config import RealEstateConfig
            except ImportError:
                from src.modules.real_estate.apt_master_repository import AptMasterRepository
                from src.modules.real_estate.apartment_repository import ApartmentRepository
                from src.modules.real_estate.building_master.building_master_repository import BuildingMasterRepository
                from src.modules.real_estate.config import RealEstateConfig

            _cfg = RealEstateConfig()
            _re_db_path = _cfg.get("real_estate_db_path", "data/real_estate.db")
            _tx_limit = int(_cfg.get("apt_search_tx_limit", 50))
            _map_limit = int(_cfg.get("apt_search_map_limit", 100))
            _repo = AptMasterRepository(db_path=_re_db_path)
            _apt_detail_repo = ApartmentRepository(db_path=_re_db_path)
            _bm_repo = BuildingMasterRepository(db_path=_re_db_path)

            # apt_master 테이블이 비어 있으면 안내
            if _repo.count() == 0:
                st.warning(
                    "⚠️ apt_master 테이블이 비어 있습니다. "
                    "먼저 마이그레이션 스크립트를 실행하세요:\n\n"
                    "```bash\n"
                    "arch -arm64 .venv/bin/python3.12 scripts/migrate_to_transaction_first.py\n"
                    "```"
                )
                st.stop()

            # ── 필터 섹션 (AptMasterEntry 기준: apt_name / sido / sigungu) ──
            with st.expander("🔍 검색 필터", expanded=True):
                col_f1, col_f2, col_f3 = st.columns(3)
                with col_f1:
                    search_name = st.text_input(
                        "아파트명 (부분검색)", placeholder="래미안, 힐스테이트 …",
                        key="master_search_name"
                    )
                with col_f2:
                    sido_opts = ["전체"] + _repo.get_distinct_sidos()
                    selected_sido = st.selectbox("시도", sido_opts, key="master_sido")
                    sido_filter = "" if selected_sido == "전체" else selected_sido
                with col_f3:
                    sigungu_opts = ["전체"] + _repo.get_distinct_sigungus(sido_filter)
                    selected_sigungu = st.selectbox("시군구", sigungu_opts, key="master_sigungu")
                    sigungu_filter = "" if selected_sigungu == "전체" else selected_sigungu

                col_btn, col_note = st.columns([1, 3])
                with col_btn:
                    search_btn = st.button("🔍 검색", key="master_search_btn", use_container_width=True)
                with col_note:
                    st.caption("💡 세대수·건설사·준공연도 필터는 단지 선택 후 상세정보 패널에서 확인")

            # ── 검색 실행 ────────────────────────────────────────────────
            if search_btn or "master_results" not in st.session_state:
                with st.spinner("검색 중..."):
                    st.session_state.master_results = _repo.search(
                        apt_name=search_name,
                        sido=sido_filter,
                        sigungu=sigungu_filter,
                    )
                st.session_state.pop("selected_apt_idx", None)  # 새 검색 시 선택 초기화

            results = st.session_state.get("master_results", [])

            list_tab, map_tab = st.tabs(["📋 단지 목록", "🗺️ 지도 뷰"])

            # ── 📋 단지 목록 탭 ──────────────────────────────────────────
            with list_tab:
                st.caption(
                    f"**{len(results)}건** 검색됨 (최대 500건) "
                    "— 아파트명을 클릭하면 실거래가를 확인할 수 있습니다."
                )

                if not results:
                    st.info("검색 결과가 없습니다. 필터를 조정해 보세요.")
                else:
                    _code_to_name = {
                        d["code"]: d["name"]
                        for d in st.session_state.get("districts", [])
                    }

                    # ── 테이블 헤더 ────────────────────────────────────────
                    _hc = st.columns([4, 2, 1, 2, 2, 1])
                    for _col, _lbl in zip(_hc, ["아파트명", "시군구", "거래건수", "최근거래", "첫거래", "상세"]):
                        _col.markdown(f"**{_lbl}**")
                    st.divider()

                    # ── 행 목록 (아파트명 버튼 클릭으로 선택) ──────────────
                    _row_limit = 100
                    for _i, _m in enumerate(results[:_row_limit]):
                        _is_sel = st.session_state.get("selected_apt_idx") == _i
                        _rc = st.columns([4, 2, 1, 2, 2, 1])
                        with _rc[0]:
                            if st.button(
                                _m.apt_name,
                                key=f"apt_row_{_i}",
                                use_container_width=True,
                                type="primary" if _is_sel else "secondary",
                            ):
                                st.session_state.selected_apt_idx = _i
                        _sigungu = _m.sigungu or _code_to_name.get(_m.district_code, _m.district_code)
                        _rc[1].caption(_sigungu)
                        _rc[2].caption(str(_m.tx_count))
                        _rc[3].caption(_m.last_traded or "-")
                        _rc[4].caption(_m.first_traded or "-")
                        _rc[5].caption("✅" if _m.complex_code else "—")

                    if len(results) > _row_limit:
                        st.caption(f"상위 {_row_limit}건 표시 중 — 더 보려면 필터를 좁혀 검색하세요.")

                    # ── 단지 선택 시: 상세 정보 + 실거래가 ────────────────
                    _sel_idx = st.session_state.get("selected_apt_idx")
                    if _sel_idx is not None and _sel_idx < len(results):
                        _render_apt_detail_panel(
                            results[_sel_idx],
                            apt_repo=_apt_detail_repo,
                            bm_repo=_bm_repo,
                            tx_limit=_tx_limit,
                        )

            # ── 🗺️ 지도 뷰 탭 ───────────────────────────────────────────
            with map_tab:
                if not results:
                    st.info("검색 결과가 없습니다. 필터를 조정 후 검색하세요.")
                else:
                    _kakao_key = os.environ.get("KAKAO_API_KEY", "")
                    if not _kakao_key:
                        st.warning("KAKAO_API_KEY 환경변수가 설정되지 않았습니다.")
                    elif st_folium is None:
                        st.warning("streamlit-folium 패키지가 설치되지 않았습니다.")
                    else:
                        _map_cache_key = str(hash(tuple(sorted(
                            f"{m.district_code}__{m.apt_name}" for m in results
                        ))))

                        col_load, col_clear = st.columns([2, 1])
                        with col_load:
                            load_map_btn = st.button(
                                "🗺️ 지도 로드", key="master_map_load_btn",
                                use_container_width=True
                            )
                        with col_clear:
                            if st.button("🔄 초기화", key="master_map_clear_btn",
                                         use_container_width=True):
                                for _k in ("master_cached_fmap", "master_tx_df",
                                           "master_map_cache_key"):
                                    st.session_state.pop(_k, None)
                                st.rerun()

                        _cache_hit = (
                            st.session_state.get("master_map_cache_key") == _map_cache_key
                            and "master_cached_fmap" in st.session_state
                        )

                        if load_map_btn or _cache_hit:
                            if not _cache_hit:
                                _district_codes = list({m.district_code for m in results})
                                _apt_names = {m.apt_name for m in results}
                                with st.spinner("실거래가 이력 조회 중..."):
                                    _map_tx_df = DashboardClient.get_transactions_by_district_codes(
                                        _district_codes, apt_names=_apt_names
                                    )
                                with st.spinner(
                                    "지도 렌더링 중... (첫 로드 시 시간이 걸릴 수 있습니다)"
                                ):
                                    _geocoder = GeocoderService(api_key=_kakao_key)
                                    _fmap = render_master_map_view(
                                        results[:_map_limit], _map_tx_df, _geocoder
                                    )
                                st.session_state.master_cached_fmap = _fmap
                                st.session_state.master_tx_df = _map_tx_df
                                st.session_state.master_map_cache_key = _map_cache_key

                            _fmap = st.session_state.master_cached_fmap
                            _map_tx_df = st.session_state.get("master_tx_df", pd.DataFrame())
                            _tx_count = len(_map_tx_df) if not _map_tx_df.empty else 0
                            st.caption(
                                f"전체 검색: {len(results)}개  |  "
                                f"지도 표시: {min(len(results), _map_limit)}개 (성능 최적화)  |  "
                                f"거래 이력: {_tx_count}건  |  "
                                "파란 마커=거래있음, 회색 마커=거래없음"
                            )
                            st_folium(_fmap, use_container_width=True, height=620,
                                      key="master_map", returned_objects=[])
                        else:
                            st.info(
                                "'🗺️ 지도 로드' 버튼을 눌러 단지 위치와 "
                                "실거래가 이력을 확인하세요."
                            )

        except Exception as _e:
            st.error(f"마스터 DB 조회 오류: {_e}")
            st.info("DB 경로 또는 API 서버 상태를 확인하세요.")

    # ──────────────────────────────────────────────────────────
    # TAB 2: Insight (서브탭 3개)
    # ──────────────────────────────────────────────────────────
    with tab2:
        news_tab0, news_tab1, news_tab2 = st.tabs(["📈 거시경제", "📰 뉴스 리포트", "📌 정책 팩트"])

        # ── 거시경제 ──────────────────────────────────────────
        with news_tab0:
            st.subheader("거시경제 지표")

            if "macro_latest" not in st.session_state:
                with st.spinner("한국은행 지표 로딩 중..."):
                    st.session_state.macro_latest = DashboardClient.get_macro_latest(domain="real_estate")

            items = st.session_state.macro_latest

            if not items:
                st.info("거시경제 데이터를 불러올 수 없습니다.")
                st.caption("수집 Job을 먼저 실행하거나 '📋 Report Archive' 탭에서 거시경제 수집을 실행하세요.")
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
    # ──────────────────────────────────────────────────────────
    # TAB 3: Report Archive (전문 컨설턴트 리포트)
    # ──────────────────────────────────────────────────────────
    with tab3:
        st.subheader("📋 부동산 전략 리포트 아카이브")

        # 리포트 생성 버튼
        with st.expander("⚙️ 리포트 생성", expanded=False):
            st.caption("오늘 날짜 기준 전문 컨설턴트 리포트를 생성합니다. (2~5분 소요)")
            if st.button("📊 전문 리포트 생성", type="primary", use_container_width=True, key="gen_pro_report"):
                with st.spinner("POI 수집 + 실거래가 추세 + LLM 분석 중..."):
                    r = DashboardClient.trigger_generate_professional_report()
                if "error" in r:
                    st.error(f"❌ 오류: {r['error']}")
                else:
                    st.success(f"✅ {r.get('date', '')} 리포트 생성 완료 ({r.get('candidates_count', 0)}개 단지 분석)")
                    st.session_state.pop("pro_report_dates", None)
                    st.rerun()

        st.markdown("---")

        # 날짜 목록 로드
        if "pro_report_dates" not in st.session_state:
            st.session_state.pro_report_dates = DashboardClient.list_professional_reports()

        dates = st.session_state.get("pro_report_dates", [])

        if not dates:
            st.warning("저장된 전문 리포트가 없습니다.")
            st.info("위 '⚙️ 리포트 생성'을 실행하거나 매일 07:00 자동 생성을 기다리세요.")
        else:
            selected_date = st.selectbox("날짜 선택", dates, key="pro_report_date_select")

            _cache_key = f"pro_report__{selected_date}"
            if st.button("📄 리포트 보기", key="view_pro_report"):
                with st.spinner("리포트 로딩 중..."):
                    st.session_state[_cache_key] = DashboardClient.get_professional_report(selected_date)

            report = st.session_state.get(_cache_key)
            if report is not None:
                if not report:
                    st.error("리포트를 불러올 수 없습니다.")
                else:
                    st.markdown("---")

                    # Executive Summary
                    budget_str = f"{report.get('budget_available', 0) / 1_0000_0000:.1f}억"
                    st.markdown(f"### 💰 구매 가능 예산: {budget_str}")
                    st.caption(report.get("macro_summary", ""))

                    candidates_summary = report.get("candidates_summary", [])
                    if candidates_summary:
                        st.markdown("**🏆 추천 Top 3**")
                        for c in candidates_summary[:3]:
                            st.markdown(f"- **{c['apt_name']}** — {c.get('total_score', 0):.0f}점")

                    st.markdown("---")

                    # 단지별 상세 (expander)
                    location_map = {a["apt_name"]: a["text"] for a in report.get("location_analyses", [])}
                    school_map = {a["apt_name"]: a["text"] for a in report.get("school_analyses", [])}

                    for c in candidates_summary[:5]:
                        name = c.get("apt_name", "알 수 없는 단지")
                        with st.expander(f"📋 {name} — {c.get('total_score', 0):.0f}점"):
                            scores = c.get("scores", {})
                            sc1, sc2, sc3, sc4, sc5 = st.columns(5)
                            with sc1:
                                st.metric("출퇴근", f"{scores.get('commute', '-')}점")
                            with sc2:
                                st.metric("환금성", f"{scores.get('liquidity', '-')}점")
                            with sc3:
                                st.metric("생활편의", f"{scores.get('living_convenience', '-')}점")
                            with sc4:
                                st.metric("학군", f"{scores.get('school', '-')}점")
                            with sc5:
                                st.metric("투자잠재력", f"{scores.get('price_potential', '-')}점")

                            if location_map.get(name):
                                st.markdown("**📍 입지**")
                                st.write(location_map[name])
                            if school_map.get(name):
                                st.markdown("**🏫 학군**")
                                st.write(school_map[name])

                    st.markdown("---")

                    # 투자 전략
                    strategy = report.get("strategy", {})
                    if strategy:
                        st.markdown("### 🎯 투자 전략 및 액션 플랜")
                        if strategy.get("strategy"):
                            st.info(f"**전략:** {strategy['strategy']}")
                        col_s, col_m = st.columns(2)
                        with col_s:
                            st.markdown("**단기(3개월)**")
                            st.write(strategy.get("action_short", "-"))
                        with col_m:
                            st.markdown("**중기(1년)**")
                            st.write(strategy.get("action_mid", "-"))
                        if strategy.get("risks"):
                            st.markdown("**⚠️ 리스크 요인**")
                            for r in strategy["risks"]:
                                st.markdown(f"- {r}")

                    st.markdown("---")

                    # 전체 마크다운 리포트
                    with st.expander("📄 전체 리포트 (Markdown)", expanded=False):
                        st.markdown(report.get("markdown", ""))

    # ──────────────────────────────────────────────────────────
    # TAB 4: 페르소나 편집
    # ──────────────────────────────────────────────────────────
    with tab4:
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
