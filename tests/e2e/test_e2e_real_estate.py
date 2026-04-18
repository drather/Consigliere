"""
E2E: Real Estate — 부동산 탭 전체 시나리오 검증 (18개).

대상 탭:
  Tab1: 🔍 아파트 탐색 (필터 / 단지 목록 / 지도 뷰)
  Tab2: 💡 Insight (거시경제 / 뉴스 리포트 / 정책 팩트)
  Tab3: 📋 Report Archive
  (Tab4: 👤 페르소나 — API 의존성 높아 별도 파일로 추후 분리 예정)

검증 범위 (Transaction-First 기준):
  Group A: 페이지 기본 (SCN-01 ~ 02)
  Group B: Tab1 검색 필터 (SCN-03 ~ 06)
  Group C: Tab1 검색 결과 (SCN-07 ~ 10)
  Group D: Tab1 지도 뷰 (SCN-11 ~ 12)
  Group E: Tab2 Insight (SCN-13 ~ 16)
  Group F: Tab3 Report Archive (SCN-17 ~ 18)

주요 변경 사항 (기존 9개 테스트 대비):
  - 검색 버튼: "검색" → "🔍 검색" (이모지 포함)
  - 결과 캡션: st.caption("**N건** 검색됨") → <strong> 래핑 구조
  - 내부 Repository: ApartmentMasterRepository → AptMasterRepository (E2E 레벨 투명)
  - 셀렉터 전략: blind wait_for_timeout → DOM 조건 대기
"""
import pytest
from conftest import (
    assert_no_streamlit_exception,
    click_real_estate_tab,
    get_main_text,
    go_to_real_estate,
    take_screenshot,
    wait_for_search_results,
)


# ══════════════════════════════════════════════════════════════════════════════
# GROUP A: 페이지 기본
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.e2e
def test_real_estate_page_title(page, base_url):
    """SCN-01: Real Estate 페이지 진입 시 h1에 'Real Estate'가 포함된다."""
    go_to_real_estate(page, base_url)
    heading = page.locator("[data-testid='stMainBlockContainer'] h1").first
    assert "Real Estate" in heading.inner_text(timeout=8_000)


@pytest.mark.e2e
def test_real_estate_no_exception_on_load(page, base_url):
    """SCN-02: 페이지 로딩 시 Streamlit stException 박스가 없다.

    ImportError, DB 연결 오류 등이 st.error()로 표면화되는 것을 감지한다.
    """
    go_to_real_estate(page, base_url)
    # 초기 렌더링 완료 대기
    page.wait_for_selector("[data-testid='stMainBlockContainer']", timeout=8_000)
    assert_no_streamlit_exception(page, "initial_load")


# ══════════════════════════════════════════════════════════════════════════════
# GROUP B: Tab1 — 검색 필터
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.e2e
def test_apt_four_main_tabs_exist(page, base_url):
    """SCN-03: 4개 주 탭(아파트 탐색 / Insight / Report Archive / 페르소나)이 렌더링된다."""
    go_to_real_estate(page, base_url)
    page.wait_for_selector("[role='tablist']", timeout=8_000)

    for label in ["아파트 탐색", "Insight", "Report Archive", "페르소나"]:
        count = page.get_by_role("tab").filter(has_text=label).count()
        assert count > 0, f"탭 '{label}'가 없음"


@pytest.mark.e2e
def test_apt_filter_expander_expanded(page, base_url):
    """SCN-04: 🔍 검색 필터 expander가 expanded=True 상태로 렌더링되어 내부 요소가 보인다."""
    go_to_real_estate(page, base_url)
    click_real_estate_tab(page, "아파트 탐색")

    # expander가 열려 있으면 placeholder가 보임
    text_input = page.get_by_placeholder("래미안, 힐스테이트 …")
    assert text_input.is_visible(), "검색 필터 expander가 닫혀 있거나 placeholder가 없음"


@pytest.mark.e2e
def test_apt_filter_inputs_name_sido_sigungu(page, base_url):
    """SCN-05: 아파트명 텍스트 입력, 시도 selectbox, 시군구 selectbox가 렌더링된다."""
    go_to_real_estate(page, base_url)
    click_real_estate_tab(page, "아파트 탐색")

    # 아파트명 텍스트 입력
    text_input = page.get_by_placeholder("래미안, 힐스테이트 …")
    assert text_input.is_visible(), "아파트명 검색 입력란이 없음"

    # 시도 selectbox — label 연결 또는 텍스트로 확인
    has_sido = (
        page.get_by_label("시도").count() > 0
        or page.get_by_text("시도").count() > 0
    )
    assert has_sido, "시도 selectbox가 없음"

    # 시군구 selectbox
    has_sigungu = (
        page.get_by_label("시군구").count() > 0
        or page.get_by_text("시군구").count() > 0
    )
    assert has_sigungu, "시군구 selectbox가 없음"


@pytest.mark.e2e
def test_apt_search_button_in_expander(page, base_url):
    """SCN-06: expander 내 '🔍 검색' 버튼이 존재하고 클릭 가능하다.

    주의: Tab2 정책 팩트에도 '🔍 검색' 버튼이 있으므로 expander 범위로 스코핑한다.
    """
    go_to_real_estate(page, base_url)
    click_real_estate_tab(page, "아파트 탐색")

    # expander 내 버튼 스코핑
    expander = page.locator("[data-testid='stExpander']").first
    search_btn = expander.get_by_role("button", name="🔍 검색")

    assert search_btn.count() > 0, "expander 내 '🔍 검색' 버튼이 없음"
    assert search_btn.first.is_enabled(), "'🔍 검색' 버튼이 비활성화 상태임"


# ══════════════════════════════════════════════════════════════════════════════
# GROUP C: Tab1 — 검색 결과
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.e2e
def test_apt_search_shows_result_caption(page, base_url):
    """SCN-07: 페이지 진입 후 자동 검색이 실행되어 'N건 검색됨' 캡션이 나타난다.

    Tab1은 세션 최초 진입 시 master_results가 없으면 자동 검색을 수행한다.
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
def test_apt_search_subtabs_exist(page, base_url):
    """SCN-08: 검색 결과 영역에 '📋 단지 목록' / '🗺️ 지도 뷰' 서브탭이 존재한다.

    초기 자동 검색 완료 후 서브탭을 확인한다.
    apt_master가 비어 있어 st.stop()된 경우에는 서브탭이 없으므로 skip.
    """
    go_to_real_estate(page, base_url)
    click_real_estate_tab(page, "아파트 탐색")
    wait_for_search_results(page, timeout=15_000)

    main_text = get_main_text(page)
    if "apt_master 테이블이 비어 있습니다" in main_text:
        pytest.skip("apt_master DB 비어있음 — 서브탭 미표시 (정상 케이스)")

    assert page.get_by_role("tab").filter(has_text="단지 목록").count() > 0, "'단지 목록' 서브탭 없음"
    assert page.get_by_role("tab").filter(has_text="지도 뷰").count() > 0, "'지도 뷰' 서브탭 없음"


@pytest.mark.e2e
def test_apt_name_search_filters_results(page, base_url):
    """SCN-09: 아파트명에 '래미안' 입력 후 검색 버튼 클릭 시 결과 캡션이 표시된다."""
    go_to_real_estate(page, base_url)
    click_real_estate_tab(page, "아파트 탐색")

    # 초기 검색 완료 대기
    wait_for_search_results(page, timeout=15_000)

    main_text = get_main_text(page)
    if "apt_master 테이블이 비어 있습니다" in main_text:
        pytest.skip("apt_master DB 비어있음 — 필터 테스트 불가")

    # 검색어 입력 (Tab으로 포커스 이동하여 Streamlit state 커밋)
    text_input = page.get_by_placeholder("래미안, 힐스테이트 …")
    text_input.click()
    text_input.fill("래미안")
    text_input.press("Tab")

    # expander 내 검색 버튼 클릭
    expander = page.locator("[data-testid='stExpander']").first
    expander.get_by_role("button", name="🔍 검색").first.click()

    # 결과 캡션 재등장 대기
    wait_for_search_results(page, timeout=12_000)

    result_text = get_main_text(page)
    has_result = (
        "건 검색됨" in result_text
        or "검색 결과가 없습니다" in result_text
    )
    assert has_result, f"'래미안' 검색 후 결과 없음. 텍스트(앞 300자):\n{result_text[:300]}"


@pytest.mark.e2e
def test_apt_dataframe_visible_with_results(page, base_url):
    """SCN-10: 검색 결과가 있을 때 단지 목록 dataframe이 렌더링된다.

    결과가 없으면 empty-state info 박스가 표시되는 것을 확인한다.
    """
    go_to_real_estate(page, base_url)
    click_real_estate_tab(page, "아파트 탐색")
    wait_for_search_results(page, timeout=15_000)

    main_text = get_main_text(page)
    if "apt_master 테이블이 비어 있습니다" in main_text:
        pytest.skip("apt_master DB 비어있음 — dataframe 미표시 (정상 케이스)")

    has_content = (
        page.locator("[data-testid='stDataFrame']").count() > 0
        or page.locator("[data-testid='stAlertInfo']").filter(has_text="검색 결과가 없습니다").count() > 0
    )
    assert has_content, "단지 목록 dataframe 또는 empty-state info가 없음"


# ══════════════════════════════════════════════════════════════════════════════
# GROUP D: Tab1 — 지도 뷰
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.e2e
def test_apt_map_tab_shows_load_button(page, base_url):
    """SCN-11: 지도 뷰 서브탭 클릭 시 '지도 로드' 버튼 또는 상태 메시지가 표시된다.

    유효한 3가지 상태:
      1. 검색 결과 있음 + KAKAO_API_KEY 설정 → "🗺️ 지도 로드" 버튼
      2. 검색 결과 있음 + 키 없음 → KAKAO_API_KEY 경고
      3. 검색 결과 없음 → "검색 결과가 없습니다" info
    """
    go_to_real_estate(page, base_url)
    click_real_estate_tab(page, "아파트 탐색")
    wait_for_search_results(page, timeout=15_000)

    main_text = get_main_text(page)
    if "apt_master 테이블이 비어 있습니다" in main_text:
        pytest.skip("apt_master DB 비어있음 — 지도 뷰 탭 미표시")

    click_real_estate_tab(page, "지도 뷰", wait_ms=1_000)

    map_text = get_main_text(page)
    has_map_content = (
        "지도 로드" in map_text
        or "KAKAO_API_KEY" in map_text
        or "검색 결과가 없습니다" in map_text
        or "지도 로드 버튼" in map_text
    )
    assert has_map_content, f"지도 뷰 탭 예상 콘텐츠 없음. 텍스트(앞 300자):\n{map_text[:300]}"


@pytest.mark.e2e
def test_apt_map_no_exception(page, base_url):
    """SCN-12: 지도 뷰 탭에서 Streamlit 예외가 발생하지 않는다."""
    go_to_real_estate(page, base_url)
    click_real_estate_tab(page, "아파트 탐색")
    wait_for_search_results(page, timeout=15_000)

    main_text = get_main_text(page)
    if "apt_master 테이블이 비어 있습니다" in main_text:
        pytest.skip("apt_master DB 비어있음 — 지도 뷰 탭 미표시")

    click_real_estate_tab(page, "지도 뷰", wait_ms=1_000)
    assert_no_streamlit_exception(page, "map_view_tab")


# ══════════════════════════════════════════════════════════════════════════════
# GROUP E: Tab2 — Insight
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.e2e
def test_insight_three_subtabs_exist(page, base_url):
    """SCN-13: Insight 탭에 3개 서브탭(거시경제 / 뉴스 리포트 / 정책 팩트)이 존재한다."""
    go_to_real_estate(page, base_url)
    click_real_estate_tab(page, "Insight")

    for label in ["거시경제", "뉴스 리포트", "정책 팩트"]:
        assert page.get_by_role("tab").filter(has_text=label).count() > 0, \
            f"Insight 서브탭 '{label}'가 없음"


@pytest.mark.e2e
def test_insight_macro_renders(page, base_url):
    """SCN-14: 거시경제 서브탭에 기준금리 metric 또는 '불러올 수 없습니다' 안내가 표시된다."""
    go_to_real_estate(page, base_url)
    click_real_estate_tab(page, "Insight")
    click_real_estate_tab(page, "거시경제", wait_ms=2_500)

    assert_no_streamlit_exception(page, "insight_macro_tab")

    main_text = get_main_text(page)
    has_macro = (
        "기준금리" in main_text
        or "한국은행" in main_text
        or "거시경제 데이터를 불러올 수 없습니다" in main_text
        or "주담대" in main_text
    )
    assert has_macro, f"거시경제 콘텐츠 없음. 텍스트(앞 300자):\n{main_text[:300]}"


@pytest.mark.e2e
def test_insight_news_renders(page, base_url):
    """SCN-15: 뉴스 리포트 서브탭에서 리포트 selectbox 또는 '생성된 뉴스 리포트가 없습니다' 경고가 표시된다."""
    go_to_real_estate(page, base_url)
    click_real_estate_tab(page, "Insight")
    click_real_estate_tab(page, "뉴스 리포트", wait_ms=1_500)

    assert_no_streamlit_exception(page, "insight_news_tab")

    main_text = get_main_text(page)
    has_news = (
        "리포트 날짜" in main_text
        or "생성된 뉴스 리포트가 없습니다" in main_text
        or "뉴스 수집" in main_text
    )
    assert has_news, f"뉴스 리포트 콘텐츠 없음. 텍스트(앞 300자):\n{main_text[:300]}"


@pytest.mark.e2e
def test_insight_policy_search_button(page, base_url):
    """SCN-16: 정책 팩트 서브탭에 '🔍 검색' 버튼이 존재한다."""
    go_to_real_estate(page, base_url)
    click_real_estate_tab(page, "Insight")
    click_real_estate_tab(page, "정책 팩트", wait_ms=1_500)

    assert_no_streamlit_exception(page, "insight_policy_tab")

    # 정책 팩트 탭의 🔍 검색 버튼 (key='policy_search')
    policy_btn = page.get_by_role("button", name="🔍 검색")
    assert policy_btn.count() > 0, "정책 팩트 탭에 '🔍 검색' 버튼이 없음"


# ══════════════════════════════════════════════════════════════════════════════
# GROUP F: Tab3 — Report Archive
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.e2e
def test_report_archive_renders(page, base_url):
    """SCN-17: Report Archive 탭 클릭 시 '인사이트 리포트' 서브헤더가 표시된다."""
    go_to_real_estate(page, base_url)
    click_real_estate_tab(page, "Report Archive", wait_ms=1_500)

    assert_no_streamlit_exception(page, "report_archive_tab")

    main_text = get_main_text(page)
    assert "인사이트 리포트" in main_text, \
        f"'인사이트 리포트' 텍스트 없음. 텍스트(앞 300자):\n{main_text[:300]}"


@pytest.mark.e2e
def test_report_archive_list_or_warning(page, base_url):
    """SCN-18: 저장된 리포트가 있으면 dataframe이, 없으면 경고 메시지가 표시된다."""
    go_to_real_estate(page, base_url)
    click_real_estate_tab(page, "Report Archive", wait_ms=1_500)

    main_text = get_main_text(page)
    has_content = (
        "저장된 인사이트 리포트가 없습니다" in main_text
        or "날짜" in main_text
        or "검증 점수" in main_text
        or "리포트 생성" in main_text
    )
    assert has_content, f"Report Archive 콘텐츠 없음. 텍스트(앞 300자):\n{main_text[:300]}"
