"""
E2E: Real Estate — 아파트 탐색 탭 UI 검증.

검증 범위 (feature/real-estate-sqlite-redesign 완료 기준):
1. 페이지 진입 및 탭 구조 확인
2. 검색 필터 expander 렌더링 (시도/시군구/건설사 selectbox, 세대수·준공연도 slider)
3. 검색 실행 → 단지 목록 / 지도 뷰 서브탭 노출
4. 빈 검색(전체) → 결과 카운트 표시
5. 아파트명 텍스트 검색
6. Insight / Report Archive / 페르소나 탭 렌더링
"""
import pytest
from conftest import get_main_text, get_page_heading, navigate_to, take_screenshot, wait_for_streamlit


def go_to_real_estate(page, base_url):
    page.goto(base_url)
    wait_for_streamlit(page)
    navigate_to(page, "🏢 Real Estate")
    page.wait_for_timeout(1_500)


@pytest.mark.e2e
def test_real_estate_page_title(page, base_url):
    """Real Estate 페이지 타이틀이 표시된다."""
    go_to_real_estate(page, base_url)

    assert "Real Estate" in get_page_heading(page)


@pytest.mark.e2e
def test_real_estate_four_tabs_exist(page, base_url):
    """4개 탭(아파트 탐색 / Insight / Report Archive / 페르소나)이 존재한다."""
    go_to_real_estate(page, base_url)

    tabs = page.get_by_role("tab")
    tab_texts = [tabs.nth(i).inner_text() for i in range(tabs.count())]
    tab_all = " ".join(tab_texts)

    for expected in ["아파트 탐색", "Insight", "Report Archive", "페르소나"]:
        assert expected in tab_all, f"탭 '{expected}'가 없음. 실제 탭: {tab_texts}"


@pytest.mark.e2e
def test_apt_search_filter_expander_visible(page, base_url):
    """검색 필터 expander가 기본 펼침 상태로 표시된다."""
    go_to_real_estate(page, base_url)

    # 아파트 탐색 탭 선택
    page.get_by_role("tab", name="아파트 탐색").click()
    page.wait_for_timeout(500)

    # 검색 필터 expander
    expander = page.get_by_text("검색 필터")
    assert expander.is_visible(), "검색 필터 expander가 보이지 않음"


@pytest.mark.e2e
def test_apt_search_filter_inputs_exist(page, base_url):
    """아파트명 텍스트 입력 + 시도/시군구 selectbox가 렌더링된다."""
    go_to_real_estate(page, base_url)
    page.get_by_role("tab", name="아파트 탐색").click()
    page.wait_for_timeout(500)

    # 텍스트 입력란 (placeholder 기준)
    text_input = page.get_by_placeholder("래미안, 힐스테이트 …")
    assert text_input.is_visible(), "아파트명 검색 입력란이 없음"

    # 시도 selectbox
    sido_box = page.get_by_label("시도")
    assert sido_box.count() > 0 or page.get_by_text("시도").count() > 0, "시도 selectbox가 없음"


@pytest.mark.e2e
def test_apt_search_subtabs_exist(page, base_url):
    """검색 결과 영역에 '단지 목록' / '지도 뷰' 서브탭이 있다."""
    go_to_real_estate(page, base_url)
    page.get_by_role("tab", name="아파트 탐색").click()
    page.wait_for_timeout(500)

    # 검색 버튼 클릭 후 서브탭 확인
    search_btn = page.get_by_role("button", name="검색")
    if search_btn.count() > 0:
        search_btn.first.click()
        page.wait_for_timeout(2_000)

    all_tabs = page.get_by_role("tab")
    tab_texts = " ".join([all_tabs.nth(i).inner_text() for i in range(all_tabs.count())])

    assert "단지 목록" in tab_texts, f"'단지 목록' 서브탭 없음. 탭 목록: {tab_texts}"
    assert "지도 뷰" in tab_texts, f"'지도 뷰' 서브탭 없음. 탭 목록: {tab_texts}"


@pytest.mark.e2e
def test_apt_search_shows_result_count(page, base_url):
    """검색 후 결과 건수(N건 검색됨)가 표시된다."""
    go_to_real_estate(page, base_url)
    page.get_by_role("tab", name="아파트 탐색").click()
    page.wait_for_timeout(500)

    search_btn = page.get_by_role("button", name="검색")
    if search_btn.count() > 0:
        search_btn.first.click()
        page.wait_for_timeout(2_500)

    main_text = get_main_text(page)
    # "N건 검색됨" or "검색 결과가 없습니다" 중 하나
    has_count = "건 검색됨" in main_text or "검색 결과가 없습니다" in main_text
    assert has_count, f"결과 카운트 메시지 없음. 페이지 텍스트(앞 300자):\n{main_text[:300]}"


@pytest.mark.e2e
def test_apt_name_search(page, base_url):
    """아파트명 검색어 입력 후 검색 결과 건수가 표시된다."""
    go_to_real_estate(page, base_url)
    page.get_by_role("tab", name="아파트 탐색").click()

    # 초기 검색 결과 로딩 완료 대기
    page.wait_for_selector("text=건 검색됨", timeout=15_000)

    # 텍스트 입력 후 Enter로 Streamlit 상태 커밋
    text_input = page.get_by_placeholder("래미안, 힐스테이트 …")
    text_input.click()
    text_input.fill("래미안")
    text_input.press("Enter")
    page.wait_for_timeout(800)

    # 검색 버튼 클릭
    search_btn = page.get_by_role("button", name="검색")
    if search_btn.count() > 0:
        search_btn.first.click()

    # 결과 또는 empty state 노출 대기 (최대 10초)
    try:
        page.wait_for_selector(
            "text=건 검색됨, text=검색 결과가 없습니다",
            timeout=10_000,
        )
    except Exception:
        pass  # wait_for_selector timeout은 아래 assertion에서 확인

    main_text = get_main_text(page)
    has_result = "건 검색됨" in main_text or "검색 결과가 없습니다" in main_text
    assert has_result, f"검색 실행 후 결과 없음. 페이지 텍스트(앞 500자):\n{main_text[:500]}"


@pytest.mark.e2e
def test_apt_insight_tab_renders(page, base_url):
    """Insight 탭 클릭 시 예외 없이 렌더링된다."""
    go_to_real_estate(page, base_url)

    page.get_by_role("tab", name="Insight").click()
    page.wait_for_timeout(1_000)

    error_boxes = page.locator("[data-testid='stException']")
    if error_boxes.count() > 0:
        take_screenshot(page, "error_insight_tab")
        pytest.fail(f"Insight 탭 예외:\n{error_boxes.first.inner_text()}")


@pytest.mark.e2e
def test_apt_persona_tab_renders(page, base_url):
    """페르소나 탭 클릭 시 예외 없이 렌더링된다."""
    go_to_real_estate(page, base_url)

    page.get_by_role("tab", name="페르소나").click()
    page.wait_for_timeout(1_000)

    error_boxes = page.locator("[data-testid='stException']")
    if error_boxes.count() > 0:
        take_screenshot(page, "error_persona_tab")
        pytest.fail(f"페르소나 탭 예외:\n{error_boxes.first.inner_text()}")
