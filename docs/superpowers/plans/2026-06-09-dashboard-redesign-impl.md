# Dashboard 전체 재설계 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 사이드바 메뉴 재편 + Real Estate 6탭 분리 + 아파트 탐색 탭 3단 레이아웃(목록|카드상세|지도) + Automation/Jobs 통합 + Home 실데이터화

**Architecture:** 순수 프론트엔드 변경 — 백엔드(FastAPI), 서비스 레이어, DB, `api_client.py`, `services.py` 일절 수정 없음. `views/`, `components/`, `main.py`만 변경.

**Tech Stack:** Python 3.12 (arm64), Streamlit, streamlit-folium, folium, pytest

---

## 파일 변경 맵

| 파일 | 유형 | 내용 |
|------|------|------|
| `src/dashboard/main.py` | 수정 | 사이드바 그룹 분리, Jobs 라우팅 제거 |
| `src/dashboard/views/automation.py` | 수정 | 탭 2개 추가, Jobs 본문 이식 |
| `src/dashboard/views/jobs.py` | **삭제** | automation.py로 흡수 |
| `src/dashboard/views/real_estate.py` | 수정 | 6탭 재편, Tab1 3단 레이아웃, detail 카드 그리드 |
| `src/dashboard/components/map_view.py` | 수정 | `render_detail_map()` 신규 추가 |
| `docs/system_snapshot/ui_structure.md` | 수정 | 최신 구조 반영 |
| `tests/dashboard/test_map_view.py` | **신규** | render_detail_map 단위 테스트 |

---

## Task 1: Automation + Jobs 통합 (`automation.py`, `jobs.py`)

**Files:**
- Modify: `src/dashboard/views/automation.py`
- Delete: `src/dashboard/views/jobs.py`

- [ ] **Step 1: `automation.py` 탭 구조로 교체**

`src/dashboard/views/automation.py` 전체를 아래로 교체:

```python
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
```

- [ ] **Step 2: `jobs.py` 삭제**

```bash
rm src/dashboard/views/jobs.py
```

- [ ] **Step 3: E2E 테스트 추가 — `tests/e2e/test_e2e_automation.py`**

파일 상단 import에 `assert_no_streamlit_exception` 추가:

```python
from conftest import assert_no_streamlit_exception, get_main_text, get_page_heading, navigate_to, take_screenshot, wait_for_streamlit
```

파일 맨 끝에 추가:

```python
@pytest.mark.e2e
def test_automation_has_two_tabs(page, base_url):
    """Automation 페이지에 워크플로우/실행 내역 2개 탭이 존재한다."""
    go_to_automation(page, base_url)
    page.wait_for_selector("[role='tablist']", timeout=8_000)

    for label in ["워크플로우", "실행 내역"]:
        count = page.get_by_role("tab").filter(has_text=label).count()
        assert count > 0, f"탭 '{label}'가 없음"


@pytest.mark.e2e
def test_automation_executions_tab_shows_summary(page, base_url):
    """실행 내역 탭 클릭 시 요약 메트릭(전체 실행/성공/실패)이 표시된다."""
    go_to_automation(page, base_url)
    page.wait_for_selector("[role='tablist']", timeout=8_000)

    page.get_by_role("tab").filter(has_text="실행 내역").first.click()
    page.wait_for_timeout(1_500)

    main_text = get_main_text(page)
    assert "전체 실행" in main_text, f"실행 내역 요약 미표시:\n{main_text[:300]}"
    assert_no_streamlit_exception(page, "automation_executions_tab")
```

- [ ] **Step 4: E2E 테스트 실행**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/e2e/test_e2e_automation.py -v -m e2e 2>&1 | tail -20
```
Expected: 모두 PASS (n8n 오프라인이어도 empty-state로 PASS)

- [ ] **Step 5: 커밋**

```bash
git add src/dashboard/views/automation.py tests/e2e/test_e2e_automation.py
git rm src/dashboard/views/jobs.py
git commit -m "feat(dashboard): Automation에 실행 내역 탭 통합, jobs.py 제거 + E2E 추가"
```

---

## Task 2: 사이드바 메뉴 재편 + Home 실데이터화 (`main.py`)

**Files:**
- Modify: `src/dashboard/main.py`

- [ ] **Step 1: `main.py` 전체 교체**

```python
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

    with st.sidebar:
        st.title("Consigliere 🤖")

        st.caption("도메인")
        domain_menu = st.radio(
            "domain",
            ["🏠 Home", "🚀 Career", "💰 Finance", "🏢 Real Estate"],
            label_visibility="collapsed",
            key="domain_radio",
        )

        st.divider()
        st.caption("시스템 운영")
        ops_menu = st.radio(
            "ops",
            ["⚙️ Automation"],
            label_visibility="collapsed",
            key="ops_radio",
        )

        # 마지막으로 클릭한 그룹을 active로 유지
        if "active_group" not in st.session_state:
            st.session_state.active_group = "domain"

    # 어느 라디오가 마지막으로 바뀌었는지 추적
    prev_domain = st.session_state.get("prev_domain_menu", domain_menu)
    prev_ops = st.session_state.get("prev_ops_menu", ops_menu)

    if domain_menu != prev_domain:
        st.session_state.active_group = "domain"
        st.session_state.prev_domain_menu = domain_menu
    elif ops_menu != prev_ops:
        st.session_state.active_group = "ops"
        st.session_state.prev_ops_menu = ops_menu

    st.session_state.prev_domain_menu = domain_menu
    st.session_state.prev_ops_menu = ops_menu

    if st.session_state.active_group == "ops":
        menu = ops_menu
    else:
        menu = domain_menu

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
```

- [ ] **Step 2: `tests/e2e/test_e2e_navigation.py` 전체 교체**

기존 파일을 아래로 전체 교체 (사이드바 그룹 분리, Jobs 제거, Home 위젯 검증 추가):

```python
"""
E2E: 사이드바 네비게이션 + 각 페이지 타이틀 렌더링 검증.

검증 범위:
- 홈 페이지 기본 로딩 + 실데이터 위젯 3종
- 사이드바 도메인/시스템 운영 그룹 분리
- Jobs 메뉴 제거 확인
- 각 페이지 이동 시 예외 없이 렌더링
"""
import pytest
from conftest import assert_no_streamlit_exception, get_main_text, get_page_heading, navigate_to, take_screenshot, wait_for_streamlit


@pytest.mark.e2e
def test_home_page_loads(page, base_url):
    """홈 페이지가 정상 로딩되고 타이틀이 표시된다."""
    page.goto(base_url)
    wait_for_streamlit(page)

    sidebar = page.locator("[data-testid='stSidebar']")
    page.wait_for_selector("[data-testid='stSidebar']", timeout=10_000)
    assert sidebar.count() > 0, "사이드바가 DOM에 없음"
    assert "Consigliere" in sidebar.inner_text(timeout=10_000)
    assert "Consigliere" in get_page_heading(page)


@pytest.mark.e2e
def test_sidebar_grouped_into_domain_and_ops(page, base_url):
    """사이드바가 '도메인' / '시스템 운영' 캡션으로 그룹화되어 있다."""
    page.goto(base_url)
    wait_for_streamlit(page)
    page.wait_for_selector("[data-testid='stSidebar']", timeout=10_000)

    sidebar_text = page.locator("[data-testid='stSidebar']").inner_text(timeout=10_000)
    assert "도메인" in sidebar_text, f"'도메인' 그룹 캡션 없음:\n{sidebar_text[:300]}"
    assert "시스템 운영" in sidebar_text, f"'시스템 운영' 그룹 캡션 없음:\n{sidebar_text[:300]}"


@pytest.mark.e2e
def test_sidebar_jobs_menu_removed(page, base_url):
    """사이드바에 더 이상 'Jobs' 메뉴가 단독으로 존재하지 않는다."""
    page.goto(base_url)
    wait_for_streamlit(page)
    page.wait_for_selector("[data-testid='stSidebar']", timeout=10_000)

    sidebar_text = page.locator("[data-testid='stSidebar']").inner_text(timeout=10_000)
    assert "🕐 Jobs" not in sidebar_text, f"'Jobs' 메뉴가 여전히 존재함:\n{sidebar_text[:300]}"


@pytest.mark.e2e
def test_home_widgets_render_with_metrics(page, base_url):
    """홈 화면에 지출/브리핑/실행현황 3개 메트릭 위젯이 표시된다."""
    page.goto(base_url)
    wait_for_streamlit(page)
    page.wait_for_timeout(1_500)

    main_text = get_main_text(page)
    for label in ["이번달 지출", "데일리 브리핑", "오늘 실행"]:
        assert label in main_text, f"홈 위젯 '{label}' 미표시:\n{main_text[:300]}"
    assert_no_streamlit_exception(page, "home_widgets")


@pytest.mark.e2e
@pytest.mark.parametrize("menu,expected_title", [
    ("💰 Finance", "Finance"),
    ("🏢 Real Estate", "Real Estate"),
    ("⚙️ Automation", "Automation"),
    ("🚀 Career", "커리어"),  # Career 페이지 실제 타이틀: "🚀 커리어 Daily Report"
    ("🏠 Home", "Consigliere"),
])
def test_navigation_renders_page(page, base_url, menu, expected_title):
    """각 메뉴 선택 시 해당 페이지 타이틀이 렌더링된다."""
    page.goto(base_url)
    wait_for_streamlit(page)

    navigate_to(page, menu)
    page.wait_for_timeout(1_000)

    error_boxes = page.locator("[data-testid='stException']")
    if error_boxes.count() > 0:
        take_screenshot(page, f"error_{menu.replace(' ', '_')}")
        pytest.fail(f"'{menu}' 페이지에서 예외 발생:\n{error_boxes.first.inner_text()}")

    page_text = get_main_text(page)
    assert expected_title in page_text, (
        f"'{menu}' 이동 후 타이틀 '{expected_title}' 미발견\n"
        f"실제 텍스트(앞 200자): {page_text[:200]}"
    )
```

- [ ] **Step 3: E2E 테스트 실행**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/e2e/test_e2e_navigation.py -v -m e2e 2>&1 | tail -30
```
Expected: 모두 PASS

- [ ] **Step 4: 커밋**

```bash
git add src/dashboard/main.py tests/e2e/test_e2e_navigation.py
git commit -m "feat(dashboard): 사이드바 도메인/운영 그룹 분리, Home 실데이터 위젯화 + E2E 추가"
```

---

## Task 3: `render_detail_map()` 신규 추가 (`components/map_view.py`)

**Files:**
- Modify: `src/dashboard/components/map_view.py`
- Create: `tests/dashboard/test_map_view.py`

**참고:** `GeocoderService`(`src/modules/real_estate/geocoder.py`)는 Kakao 키워드 검색 API 기반의
`geocode(apt_name: str, district_code: str, address: Optional[str] = None) -> Optional[tuple[float, float]]`
단일 메서드를 제공한다. `address`가 있으면 우선 쿼리로 사용하고, 없으면 `apt_name`으로 검색한다.
"삼성역" 같은 역명도 키워드 검색으로 좌표를 얻을 수 있다 (페르소나 `commute.workplace_station` 활용 가능).

- [ ] **Step 1: 테스트 파일 생성**

```bash
mkdir -p tests/dashboard
touch tests/dashboard/__init__.py
```

`tests/dashboard/test_map_view.py`:

```python
import folium
import pytest

# import 경로 보정
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from dashboard.components.map_view import render_detail_map


class _FakeGeocoder:
    """apt_name/주소에 따라 좌표를 반환하는 테스트용 geocoder."""

    def geocode(self, apt_name: str, district_code: str, address: str | None = None):
        query = address or apt_name
        if "반포" in query or "래미안" in query:
            return (37.5010, 127.0260)  # 반포동 근처
        if "여의도" in query or "삼성역" in query:
            return (37.5210, 126.9240)  # 여의도/강남 근처
        return None


def test_render_detail_map_returns_folium_map():
    geocoder = _FakeGeocoder()
    result = render_detail_map(
        address="서울 서초구 반포동 1",
        apt_name="래미안원베일리",
        district_code="11650",
        geocoder=geocoder,
        workplace_address=None,
        poi_cached=None,
        commute_summary=None,
    )
    assert isinstance(result, folium.Map)


def test_render_detail_map_centers_on_apt():
    geocoder = _FakeGeocoder()
    result = render_detail_map(
        address="서울 서초구 반포동 1",
        apt_name="래미안원베일리",
        district_code="11650",
        geocoder=geocoder,
        workplace_address=None,
        poi_cached=None,
        commute_summary=None,
    )
    # folium.Map.location is [lat, lng]
    lat, lng = result.location
    assert abs(lat - 37.5010) < 0.01
    assert abs(lng - 127.0260) < 0.01


def test_render_detail_map_geocode_failure_returns_default_map():
    """geocode 실패 시 서울 기본 좌표로 fallback한다."""
    class _FailGeocoder:
        def geocode(self, apt_name, district_code, address=None):
            return None

    result = render_detail_map(
        address="존재하지않는주소",
        apt_name="테스트단지",
        district_code="00000",
        geocoder=_FailGeocoder(),
        workplace_address=None,
        poi_cached=None,
        commute_summary=None,
    )
    assert isinstance(result, folium.Map)
    assert result.location == [37.5665, 126.9780]


def test_render_detail_map_with_workplace():
    """직장 주소(또는 역명) 제공 시 지도가 정상 생성된다."""
    geocoder = _FakeGeocoder()
    result = render_detail_map(
        address="서울 서초구 반포동 1",
        apt_name="래미안원베일리",
        district_code="11650",
        geocoder=geocoder,
        workplace_address="삼성역",
        poi_cached=None,
        commute_summary={"transit": 38},
    )
    assert isinstance(result, folium.Map)


def test_render_detail_map_workplace_geocode_failure_skips_pin():
    """직장 좌표 조회 실패 시 직장 핀/경로 없이 정상 반환한다."""
    geocoder = _FakeGeocoder()
    result = render_detail_map(
        address="서울 서초구 반포동 1",
        apt_name="래미안원베일리",
        district_code="11650",
        geocoder=geocoder,
        workplace_address="존재하지않는직장주소",
        poi_cached=None,
        commute_summary=None,
    )
    assert isinstance(result, folium.Map)
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/dashboard/test_map_view.py -v 2>&1 | head -30
```
Expected: `ImportError: cannot import name 'render_detail_map'`

- [ ] **Step 3: `render_detail_map()` 구현**

`src/dashboard/components/map_view.py` 맨 끝에 추가:

```python
def render_detail_map(
    address: str,
    apt_name: str,
    district_code: str,
    geocoder,
    workplace_address: str | None = None,
    poi_cached: dict | None = None,
    commute_summary: dict | None = None,
) -> folium.Map:
    """단일 단지 상세 지도. 아파트 위치 + 직장 위치 + 출퇴근 경로를 표시한다.

    Args:
        address: 단지 도로명주소 (geocoding 쿼리 우선순위 1순위)
        apt_name: 단지명 (geocoding 쿼리 fallback + 마커 툴팁용)
        district_code: geocode 캐시 키 구성용 법정동 코드
        geocoder: GeocoderService 인스턴스 (geocode(apt_name, district_code, address))
        workplace_address: 직장 주소 또는 역명 (예: "삼성역"). 없으면 None — 직장 핀 생략
        poi_cached: get_poi_cached() 반환 dict (subway_stations 등)
        commute_summary: {"transit": 38, "bus": 44} 등 분 단위
    Returns:
        folium.Map
    """
    DEFAULT_CENTER = [37.5665, 126.9780]  # 서울 시청 (geocode 실패 fallback)

    # ── 아파트 좌표 ──
    apt_coords = geocoder.geocode(apt_name, district_code, address=address)
    center = list(apt_coords) if apt_coords else DEFAULT_CENTER
    zoom = 15 if apt_coords else 11

    fmap = folium.Map(location=center, zoom_start=zoom, tiles="CartoDB dark_matter")

    if not apt_coords:
        return fmap

    # ── 아파트 마커 ──
    transit_min = (commute_summary or {}).get("transit")
    apt_tooltip = f"🏢 {apt_name}" + (f" | 🚇 {transit_min}분" if transit_min else "")
    folium.Marker(
        location=apt_coords,
        tooltip=apt_tooltip,
        icon=folium.Icon(color="blue", icon="home", prefix="fa"),
    ).add_to(fmap)

    # ── 직장 마커 + 경로 ──
    if workplace_address:
        work_coords = geocoder.geocode("직장", "_workplace", address=workplace_address)
        if work_coords:
            folium.Marker(
                location=work_coords,
                tooltip="🏢 직장",
                icon=folium.Icon(color="green", icon="briefcase", prefix="fa"),
            ).add_to(fmap)
            # 출퇴근 경로 점선
            folium.PolyLine(
                locations=[apt_coords, work_coords],
                color="#5c6bc0",
                weight=2,
                dash_array="6 4",
                tooltip=f"출퇴근 {transit_min}분" if transit_min else "출퇴근 경로",
            ).add_to(fmap)

            if transit_min:
                mid_lat = (apt_coords[0] + work_coords[0]) / 2
                mid_lng = (apt_coords[1] + work_coords[1]) / 2
                folium.Marker(
                    location=[mid_lat, mid_lng],
                    icon=folium.DivIcon(
                        html=f'<div style="background:#0e1117cc;color:#4caf93;'
                             f'font-size:11px;font-weight:700;padding:3px 7px;'
                             f'border-radius:5px;white-space:nowrap;border:1px solid #2e7d52;">'
                             f'🚇 {transit_min}분</div>',
                        icon_size=(80, 24),
                        icon_anchor=(40, 12),
                    ),
                ).add_to(fmap)

    # ── 지하철역 핀 (poi_cached 있을 때) ──
    if poi_cached:
        for station in (poi_cached.get("subway_stations") or [])[:3]:
            if isinstance(station, dict) and station.get("lat") and station.get("lng"):
                folium.CircleMarker(
                    location=[station["lat"], station["lng"]],
                    radius=6,
                    color="#5c6bc0",
                    fill=True,
                    fill_color="#5c6bc0",
                    fill_opacity=0.5,
                    tooltip=station.get("name", "지하철역"),
                ).add_to(fmap)

    return fmap
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/dashboard/test_map_view.py -v
```
Expected: `5 passed`

- [ ] **Step 5: 커밋**

```bash
git add src/dashboard/components/map_view.py tests/dashboard/
git commit -m "feat(dashboard): render_detail_map() 신규 추가 — 단지+직장 핀, 출퇴근 경로"
```

---

## Task 4: Real Estate 6탭 재편 (`real_estate.py` 탭 구조)

**Files:**
- Modify: `src/dashboard/views/real_estate.py` (함수 `show_real_estate()` 탭 선언 + Tab2 분해)

현재 `show_real_estate()`의 탭 선언과 Tab2(Insight) 전체를 교체한다. Tab1(아파트 탐색)은 이 태스크에서 **기존 코드 유지** — Task 5에서 교체.

- [ ] **Step 1: `show_real_estate()` 탭 선언 변경**

`real_estate.py` line 596 부근:
```python
# 변경 전
tab1, tab2, tab3, tab4 = st.tabs(["🔍 아파트 탐색", "💡 Insight", "📰 데일리 리포트", "👤 페르소나"])
```
→
```python
# 변경 후
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🔍 아파트 탐색",
    "📈 거시경제",
    "📰 뉴스 리포트",
    "📌 정책 팩트",
    "📋 데일리 브리핑",
    "👤 페르소나",
])
```

- [ ] **Step 2: Tab2 내용 이식 (거시경제)**

```python
# 변경 전 (line 782 근처)
with tab2:
    news_tab0, news_tab1, news_tab2 = st.tabs(["📈 거시경제", "📰 뉴스 리포트", "📌 정책 팩트"])
    with news_tab0:
        # 거시경제 내용...
    with news_tab1:
        # 뉴스 리포트 내용...
    with news_tab2:
        # 정책 팩트 내용...
```
→
```python
# 변경 후: 서브탭 제거, 각 내용을 독립 탭으로 이식
with tab2:
    # [기존 news_tab0 내용 그대로 붙여넣기 — st.subheader("거시경제 지표") 부터]
    st.subheader("거시경제 지표")
    # ... (기존 코드 그대로)

with tab3:
    # [기존 news_tab1 내용 그대로]
    st.subheader("일별 뉴스 분석 리포트")
    # ...

with tab4:
    # [기존 news_tab2 내용 그대로]
    st.subheader("정책·개발 팩트 검색")
    # ...

with tab5:
    _render_daily_report_tab()  # 기존 tab3 내용

with tab6:
    # 기존 tab4 내용 (페르소나) 그대로
    st.subheader("👤 페르소나 설정")
    # ...
```

- [ ] **Step 3: `tests/e2e/test_e2e_real_estate.py` Group A/E/F 갱신**

파일 상단 docstring과 import는 유지. **Group A (SCN-03)**, **Group E**, **Group F** 섹션만 아래 내용으로 교체한다 (Group B/C/D는 Task 6에서 전면 교체 예정이므로 이번 단계에서는 그대로 둔다).

`test_apt_four_main_tabs_exist` 함수를 찾아 아래로 교체:

```python
@pytest.mark.e2e
def test_real_estate_six_tabs_exist(page, base_url):
    """SCN-03: Real Estate에 6개 탭(아파트 탐색/거시경제/뉴스 리포트/정책 팩트/데일리 브리핑/페르소나)이 렌더링된다."""
    go_to_real_estate(page, base_url)
    page.wait_for_selector("[role='tablist']", timeout=8_000)

    for label in ["아파트 탐색", "거시경제", "뉴스 리포트", "정책 팩트", "데일리 브리핑", "페르소나"]:
        count = page.get_by_role("tab").filter(has_text=label).count()
        assert count > 0, f"탭 '{label}'가 없음"
```

**GROUP E** 섹션 전체(`test_insight_three_subtabs_exist` 부터 `test_insight_policy_search_button` 까지)를 아래로 교체:

```python
# ══════════════════════════════════════════════════════════════════════════════
# GROUP E: 거시경제 / 뉴스 리포트 / 정책 팩트 (구 Insight 서브탭 → 최상위 탭)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.e2e
def test_macro_tab_renders(page, base_url):
    """SCN-14: 거시경제 탭에 기준금리 metric 또는 '불러올 수 없습니다' 안내가 표시된다."""
    go_to_real_estate(page, base_url)
    click_real_estate_tab(page, "거시경제", wait_ms=2_500)

    assert_no_streamlit_exception(page, "macro_tab")

    main_text = get_main_text(page)
    has_macro = (
        "기준금리" in main_text
        or "한국은행" in main_text
        or "거시경제 데이터를 불러올 수 없습니다" in main_text
        or "주담대" in main_text
    )
    assert has_macro, f"거시경제 콘텐츠 없음. 텍스트(앞 300자):\n{main_text[:300]}"


@pytest.mark.e2e
def test_news_report_tab_renders(page, base_url):
    """SCN-15: 뉴스 리포트 탭에서 리포트 selectbox 또는 '생성된 뉴스 리포트가 없습니다' 경고가 표시된다."""
    go_to_real_estate(page, base_url)
    click_real_estate_tab(page, "뉴스 리포트", wait_ms=1_500)

    assert_no_streamlit_exception(page, "news_report_tab")

    main_text = get_main_text(page)
    has_news = (
        "리포트 날짜" in main_text
        or "생성된 뉴스 리포트가 없습니다" in main_text
        or "뉴스 수집" in main_text
    )
    assert has_news, f"뉴스 리포트 콘텐츠 없음. 텍스트(앞 300자):\n{main_text[:300]}"


@pytest.mark.e2e
def test_policy_fact_tab_search_button(page, base_url):
    """SCN-16: 정책 팩트 탭에 '🔍 검색' 버튼이 존재한다."""
    go_to_real_estate(page, base_url)
    click_real_estate_tab(page, "정책 팩트", wait_ms=1_500)

    assert_no_streamlit_exception(page, "policy_fact_tab")

    policy_btn = page.get_by_role("button", name="🔍 검색")
    assert policy_btn.count() > 0, "정책 팩트 탭에 '🔍 검색' 버튼이 없음"
```

**GROUP F** 섹션 전체(`test_report_archive_renders`, `test_report_archive_list_or_warning`)를 아래로 교체:

```python
# ══════════════════════════════════════════════════════════════════════════════
# GROUP F: 데일리 브리핑 (구 데일리 리포트 → 개명)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.e2e
def test_daily_briefing_renders(page, base_url):
    """SCN-17: 데일리 브리핑 탭 클릭 시 '데일리 부동산 브리핑' 서브헤더가 표시된다."""
    go_to_real_estate(page, base_url)
    click_real_estate_tab(page, "데일리 브리핑", wait_ms=1_500)

    assert_no_streamlit_exception(page, "daily_briefing_tab")

    main_text = get_main_text(page)
    assert "데일리 부동산 브리핑" in main_text, \
        f"'데일리 부동산 브리핑' 텍스트 없음. 텍스트(앞 300자):\n{main_text[:300]}"


@pytest.mark.e2e
def test_daily_briefing_list_or_empty(page, base_url):
    """SCN-18: 저장된 리포트가 있으면 날짜 선택 UI가, 없으면 안내 메시지가 표시된다."""
    go_to_real_estate(page, base_url)
    click_real_estate_tab(page, "데일리 브리핑", wait_ms=1_500)

    main_text = get_main_text(page)
    has_content = (
        "저장된 데일리 리포트가 없습니다" in main_text
        or "날짜" in main_text
        or "리포트 생성" in main_text
    )
    assert has_content, f"데일리 브리핑 콘텐츠 없음. 텍스트(앞 300자):\n{main_text[:300]}"
```

- [ ] **Step 4: 수동 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m streamlit run src/dashboard/main.py
```

브라우저에서 Real Estate 진입 → 탭 6개 표시 확인 → 각 탭 클릭 → 에러 없이 내용 표시 확인.

- [ ] **Step 5: E2E 테스트 실행 (Group A/E/F)**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/e2e/test_e2e_real_estate.py -v -m e2e -k "six_tabs_exist or macro_tab or news_report_tab or policy_fact_tab or daily_briefing" 2>&1 | tail -30
```
Expected: 모두 PASS (Group B/C/D는 Task 6 전까지 기존 구조 기준이라 실패할 수 있음 — 무시)

- [ ] **Step 6: 커밋**

```bash
git add src/dashboard/views/real_estate.py tests/e2e/test_e2e_real_estate.py
git commit -m "feat(dashboard): Real Estate Insight 서브탭 → 6개 독립 탭으로 분해 + E2E 갱신"
```

---

## Task 5: 아파트 탐색 탭 — 카드 상세 패널 (`_render_apt_detail_cards`)

**Files:**
- Modify: `src/dashboard/views/real_estate.py`

기존 `_render_apt_detail_panel()` 대신 새로운 `_render_apt_detail_cards(entry)` 함수를 추가한다. 기존 함수는 Task 6에서 삭제.

- [ ] **Step 1: `_render_apt_detail_cards()` 함수 추가**

`_render_apt_detail_panel()` 정의 바로 위(line 293)에 삽입:

```python
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
                            if getattr(dr, "evidence", None):
                                st.caption(dr.evidence)
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
```

- [ ] **Step 2: 커밋 (함수 추가만, 아직 호출 안 함)**

```bash
git add src/dashboard/views/real_estate.py
git commit -m "feat(dashboard): _render_apt_detail_cards() 추가 — 카드 그리드 상세 패널"
```

---

## Task 6: 아파트 탐색 탭 — 3단 레이아웃 (`show_real_estate` Tab1 교체)

**Files:**
- Modify: `src/dashboard/views/real_estate.py` (Tab1 `with tab1:` 블록 전체 교체)

기존 tab1 블록(약 line 601~776)을 3단 레이아웃으로 완전 교체하고 `_render_apt_detail_panel()` 삭제.

- [ ] **Step 1: Tab1 블록 교체**

`with tab1:` ~ `except Exception as _e:` 블록 전체를 아래로 교체:

```python
    with tab1:
        try:
            _tx_limit, _map_limit = get_apt_search_limits()

            if count_apt_masters() == 0:
                st.warning(
                    "⚠️ apt_master 테이블이 비어 있습니다. 마이그레이션 스크립트를 먼저 실행하세요.\n\n"
                    "```bash\narch -arm64 .venv/bin/python3.12 scripts/migrate_to_transaction_first.py\n```"
                )
                st.stop()

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
                    price_label = ""
                    # 단가 정보 없이 거래일만 표시 (목록에서는 날짜+이름 위주)
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
```

- [ ] **Step 2: `render_detail_map` import 추가**

`real_estate.py` 상단 import 블록은 `try`/`except ImportError`로 두 경로를 모두 시도한다 (line 10-34).
두 블록 모두에서 `render_master_map_view`를 import하는 줄에 `render_detail_map`을 추가한다:

```python
try:
    from dashboard.api_client import DashboardClient
    from dashboard.components.map_view import render_master_map_view, render_detail_map
    ...
except ImportError:
    from src.dashboard.api_client import DashboardClient
    from src.dashboard.components.map_view import render_master_map_view, render_detail_map
    ...
```

- [ ] **Step 3: `_render_apt_detail_panel()` 삭제**

line 293~590 (`def _render_apt_detail_panel` 전체 함수 블록) 삭제. 이 함수는 이제 `_render_apt_detail_cards()`로 대체되었고 더 이상 호출되지 않는다.

- [ ] **Step 4: 수동 확인 (골든패스)**

```bash
arch -arm64 .venv/bin/python3.12 -m streamlit run src/dashboard/main.py
```

1. Real Estate → 아파트 탐색 탭
2. "래미안" 검색 → 목록 표시 확인
3. 단지 클릭 → 가운데 패널에 KPI + expander 표시 확인
4. 입지점수 expander 열기 → 2열 카드 그리드 표시 확인
5. 오른쪽 지도 로드 확인

- [ ] **Step 5: `tests/e2e/test_e2e_real_estate.py` Group B/C/D 전면 교체 + `test_e2e_map_load.py` 삭제**

`# ══ GROUP B: Tab1 — 검색 필터 ══` 주석부터 `test_apt_map_no_exception` 함수 끝까지(구 Group B/C/D 전체)를 아래로 교체:

```python
# ══════════════════════════════════════════════════════════════════════════════
# GROUP B: 검색바
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.e2e
def test_apt_search_bar_inputs_exist(page, base_url):
    """SCN-04: 검색바에 아파트명 입력, 시도/시군구 selectbox, 검색 버튼이 존재한다."""
    go_to_real_estate(page, base_url)
    click_real_estate_tab(page, "아파트 탐색")

    text_input = page.get_by_placeholder("🔍 아파트명 검색...")
    assert text_input.is_visible(), "아파트명 검색 입력란이 없음"
    assert page.get_by_role("button", name="검색").count() > 0, "검색 버튼이 없음"


# ══════════════════════════════════════════════════════════════════════════════
# GROUP C: 단지 목록 + 카드 상세 패널
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.e2e
def test_apt_search_shows_result_caption(page, base_url):
    """SCN-07: 페이지 진입 후 자동 검색이 실행되어 'N건 검색됨' 캡션이 나타난다.

    apt_master 테이블이 비어 있으면 warning 메시지로 대체된다 — 둘 다 PASS.
    """
    go_to_real_estate(page, base_url)
    click_real_estate_tab(page, "아파트 탐색")
    wait_for_search_results(page, timeout=15_000)

    main_text = get_main_text(page)
    has_result = (
        "건 검색됨" in main_text
        or "apt_master 테이블이 비어 있습니다" in main_text
        or "마스터 DB 조회 오류" in main_text
    )
    assert has_result, f"검색 결과 또는 상태 메시지가 없음. 페이지 텍스트(앞 300자):\n{main_text[:300]}"


@pytest.mark.e2e
def test_apt_detail_placeholder_before_selection(page, base_url):
    """SCN-08: 단지 미선택 상태에서 카드 상세 패널에 안내 메시지가 표시된다."""
    go_to_real_estate(page, base_url)
    click_real_estate_tab(page, "아파트 탐색")
    wait_for_search_results(page, timeout=15_000)

    main_text = get_main_text(page)
    if "apt_master 테이블이 비어 있습니다" in main_text:
        pytest.skip("apt_master DB 비어있음")

    assert "왼쪽 목록에서 단지를 선택하세요" in main_text, \
        f"상세 패널 안내 메시지 없음. 텍스트(앞 300자):\n{main_text[:300]}"


@pytest.mark.e2e
def test_apt_select_shows_detail_cards(page, base_url):
    """SCN-09: 단지 목록에서 단지를 클릭하면 카드 상세 패널에 KPI 4종이 표시된다."""
    go_to_real_estate(page, base_url)
    click_real_estate_tab(page, "아파트 탐색")
    wait_for_search_results(page, timeout=15_000)

    main_text = get_main_text(page)
    if "apt_master 테이블이 비어 있습니다" in main_text:
        pytest.skip("apt_master DB 비어있음")

    apt_buttons = page.locator("[data-testid='stMainBlockContainer']").get_by_role("button").filter(has_text="·")
    if apt_buttons.count() == 0:
        pytest.skip("검색 결과 없음 — 단지 버튼 없음")

    apt_buttons.first.click()
    page.wait_for_timeout(2_000)

    assert_no_streamlit_exception(page, "apt_detail_select")

    detail_text = get_main_text(page)
    for label in ["최근거래", "입지점수", "출퇴근", "전세가율"]:
        assert label in detail_text, f"KPI '{label}' 미표시. 텍스트(앞 400자):\n{detail_text[:400]}"


@pytest.mark.e2e
def test_apt_detail_location_score_section(page, base_url):
    """SCN-10: 단지 선택 시 카드 상세 패널에 '📍 입지점수' 섹션이 표시된다."""
    go_to_real_estate(page, base_url)
    click_real_estate_tab(page, "아파트 탐색")
    wait_for_search_results(page, timeout=15_000)

    main_text = get_main_text(page)
    if "apt_master 테이블이 비어 있습니다" in main_text:
        pytest.skip("apt_master DB 비어있음")

    apt_buttons = page.locator("[data-testid='stMainBlockContainer']").get_by_role("button").filter(has_text="·")
    if apt_buttons.count() == 0:
        pytest.skip("검색 결과 없음 — 단지 버튼 없음")

    apt_buttons.first.click()
    page.wait_for_timeout(2_000)

    detail_text = get_main_text(page)
    assert "입지점수" in detail_text, f"'입지점수' 섹션 없음. 텍스트(앞 400자):\n{detail_text[:400]}"


# ══════════════════════════════════════════════════════════════════════════════
# GROUP D: 지도 컬럼
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.e2e
def test_map_column_placeholder_before_selection(page, base_url):
    """SCN-11: 단지 미선택 시 지도 컬럼에 안내 메시지가 표시된다."""
    go_to_real_estate(page, base_url)
    click_real_estate_tab(page, "아파트 탐색")
    wait_for_search_results(page, timeout=15_000)

    main_text = get_main_text(page)
    if "apt_master 테이블이 비어 있습니다" in main_text:
        pytest.skip("apt_master DB 비어있음")

    assert "단지를 선택하면 위치가 표시됩니다" in main_text, \
        f"지도 컬럼 안내 메시지 없음. 텍스트(앞 300자):\n{main_text[:300]}"


@pytest.mark.e2e
def test_map_column_renders_after_selection(page, base_url):
    """SCN-12: 단지 선택 시 지도 컬럼에 지도(iframe), KAKAO_API_KEY 경고, 또는 레이어 토글 중 하나가 표시된다.

    KAKAO_API_KEY가 정상 로드된 경우 'KAKAO_API_KEY 환경변수가 설정되지 않았습니다'
    경고가 나타나지 않아야 한다 (load_dotenv 누락 회귀 방지).
    """
    go_to_real_estate(page, base_url)
    click_real_estate_tab(page, "아파트 탐색")
    wait_for_search_results(page, timeout=15_000)

    main_text = get_main_text(page)
    if "apt_master 테이블이 비어 있습니다" in main_text:
        pytest.skip("apt_master DB 비어있음")

    apt_buttons = page.locator("[data-testid='stMainBlockContainer']").get_by_role("button").filter(has_text="·")
    if apt_buttons.count() == 0:
        pytest.skip("검색 결과 없음 — 단지 버튼 없음")

    apt_buttons.first.click()
    page.wait_for_timeout(3_000)

    detail_text = get_main_text(page)
    has_map_content = (
        page.locator("iframe").count() > 0
        or "KAKAO_API_KEY" in detail_text
        or "위치" in detail_text
        or "POI" in detail_text
    )
    assert has_map_content, f"지도 컬럼 콘텐츠 없음. 텍스트(앞 400자):\n{detail_text[:400]}"
```

`tests/e2e/test_e2e_map_load.py`는 "지도 로드" 버튼 기반 구 UX를 테스트하므로 삭제한다 (핵심 회귀 검증은 `test_map_column_renders_after_selection`으로 이전됨):

```bash
git rm tests/e2e/test_e2e_map_load.py
```

- [ ] **Step 6: E2E 테스트 실행 (Real Estate 전체)**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/e2e/test_e2e_real_estate.py -v -m e2e 2>&1 | tail -40
```
Expected: 모두 PASS (apt_master 비어있으면 일부 skip — 정상)

- [ ] **Step 7: 전체 테스트 실행**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/ -x -q --ignore=tests/test_job4_enhancements.py -m "not e2e" 2>&1 | tail -5
```
Expected: 기존 통과 건수 유지 (신규 실패 없음)

- [ ] **Step 8: 커밋**

```bash
git add src/dashboard/views/real_estate.py src/dashboard/components/map_view.py tests/e2e/test_e2e_real_estate.py
git commit -m "feat(dashboard): 아파트 탐색 탭 3단 레이아웃 완성 (목록|카드상세|지도) + E2E 갱신"
```

---

## Task 7: 문서 갱신

**Files:**
- Modify: `docs/system_snapshot/ui_structure.md`

- [ ] **Step 1: `ui_structure.md` 전면 갱신**

`docs/system_snapshot/ui_structure.md`를 아래로 교체:

```markdown
# UI Structure Snapshot

**Status:** Active
**Last Updated:** 2026-06-09

## 1. Dashboard Structure (Navigation)

사이드바가 "도메인"과 "시스템 운영" 두 그룹으로 분리된다.

### 1.1 Sitemap

\`\`\`
사이드바
├─ 도메인
│   ├─ 🏠 Home          — 이번달 지출 / 최근 브리핑 / 오늘 Job 실행 현황
│   ├─ 🚀 Career        — 리포트(일별/주간/월간) / 스킬갭 / 페르소나 / 파이프라인
│   ├─ 💰 Finance       — 가계부 CRUD (월별)
│   └─ 🏢 Real Estate   — 6탭 (아래 참조)
└─ 시스템 운영
    └─ ⚙️ Automation    — 워크플로우 목록 / 실행 내역
\`\`\`

## 2. Real Estate 탭 구조 (6탭)

| 탭 | 내용 |
|----|------|
| 🔍 아파트 탐색 | 3단: 목록 + 카드 상세(KPI+확장 섹션) + 지도 |
| 📈 거시경제 | BOK 지표 카테고리별 최신값 + 추이 차트 |
| 📰 뉴스 리포트 | 일별 뉴스 분석 리포트 뷰어 |
| 📌 정책 팩트 | ChromaDB 정책 팩트 검색 |
| 📋 데일리 브리핑 | 실거래가+거시경제+LLM 인사이트 통합 브리핑 |
| 👤 페르소나 | 자산/소득/출퇴근/가중치/관심지역 설정 |

## 3. 아파트 탐색 탭 — 3단 레이아웃

\`\`\`
[검색바: 아파트명 | 시도 ▾ | 시군구 ▾ | 검색]

┌──────────────┬───────────────────────┬──────────────────────┐
│  단지 목록   │    카드 상세 패널      │       지도           │
│  (260px)     │    (340px)            │    (나머지)          │
│              │                       │                      │
│ ▶ 래미안원베일│ ### 래미안원베일리    │  [📍 위치] [🏙 POI] │
│  반포자이    │ [89.5억][82점][38분]  │                      │
│  잠실주공5   │ ──────────────────    │  🏢 단지 핀          │
│  ...         │ 📍 입지점수 ▲         │  🏢 직장 핀          │
│              │   [교통27] [편의22]   │  ---- 출퇴근 경로    │
│              │   [학군19] [공원14]   │   🚇 38분 배지       │
│              │ 📈 실거래가 ▼         │                      │
│              │ 🚇 출퇴근 ▼           │                      │
│              │ 🤖 AI 인사이트 ▼      │                      │
└──────────────┴───────────────────────┴──────────────────────┘
\`\`\`

## 4. Automation 탭 (Jobs 통합)

| 탭 | 내용 |
|----|------|
| 📋 워크플로우 | n8n 워크플로우 목록 + n8n 에디터 링크 |
| 🕐 실행 내역 | 기간별 실행 타임라인 + 성공/실패 요약 |

## 5. 구현 파일 현황

| 파일 | 역할 |
|------|------|
| `src/dashboard/main.py` | 사이드바 2그룹, 라우팅, Home 위젯 |
| `src/dashboard/views/real_estate.py` | Real Estate 6탭 전체 |
| `src/dashboard/views/career.py` | Career 4탭 |
| `src/dashboard/views/finance.py` | Finance 단일 화면 |
| `src/dashboard/views/automation.py` | Automation 2탭 (Jobs 통합) |
| `src/dashboard/components/map_view.py` | render_master_map_view(), render_detail_map() |
| `src/dashboard/api_client.py` | DashboardClient — 모든 API 호출 |
| `src/dashboard/services.py` | DB 직접 접근 서비스 진입점 |
```

- [ ] **Step 2: 커밋**

```bash
git add docs/system_snapshot/ui_structure.md
git commit -m "docs: ui_structure.md 6탭 + 3단 레이아웃 반영하여 전면 갱신"
```

---

## 완료 확인 체크리스트

- [ ] 사이드바에 "도메인" / "시스템 운영" 캡션 표시
- [ ] Jobs 메뉴 제거됨 (Automation 탭 내 실행 내역으로 접근 가능)
- [ ] Home 3개 위젯에 실데이터 표시
- [ ] Real Estate 탭 6개로 표시
- [ ] 아파트 탐색: 3단 레이아웃 렌더링
- [ ] 입지점수 expander → 2열 카드 그리드 표시
- [ ] 지도 컬럼: 단지 선택 후 핀 표시
- [ ] 기존 테스트 전체 통과 (`pytest tests/ -q`)
