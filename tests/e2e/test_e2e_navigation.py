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
