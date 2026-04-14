"""
E2E: 사이드바 네비게이션 + 각 페이지 타이틀 렌더링 검증.

검증 범위:
- 홈 페이지 기본 로딩
- 사이드바 라디오 메뉴 5종 (Home / Career / Finance / Real Estate / Automation)
- 각 페이지 이동 시 예외 없이 렌더링
"""
import pytest
from conftest import get_main_text, get_page_heading, navigate_to, take_screenshot, wait_for_streamlit


@pytest.mark.e2e
def test_home_page_loads(page, base_url):
    """홈 페이지가 정상 로딩되고 타이틀이 표시된다."""
    page.goto(base_url)
    wait_for_streamlit(page)

    # 사이드바가 DOM에 존재하는지 확인 (viewport 밖이어도 count > 0)
    sidebar = page.locator("[data-testid='stSidebar']")
    page.wait_for_selector("[data-testid='stSidebar']", timeout=10_000)
    assert sidebar.count() > 0, "사이드바가 DOM에 없음"
    assert "Consigliere" in sidebar.inner_text(timeout=10_000)

    # 메인 타이틀 확인
    assert "Consigliere" in get_page_heading(page)


@pytest.mark.e2e
def test_sidebar_has_five_menus(page, base_url):
    """사이드바 라디오에 5개 메뉴가 모두 존재한다."""
    page.goto(base_url)
    wait_for_streamlit(page)

    # inner_text()는 라디오 옵션 일부를 캡처 못할 수 있으므로
    # get_by_role("radio") 또는 label 텍스트로 존재 확인
    page.wait_for_selector("[data-testid='stSidebar']", timeout=10_000)

    expected_menus = ["Home", "Career", "Finance", "Real Estate", "Automation"]
    for menu in expected_menus:
        # label 또는 전체 페이지 내 텍스트로 확인
        found = (
            page.get_by_text(menu, exact=False).count() > 0
        )
        assert found, f"메뉴 '{menu}'가 페이지에 없음"


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

    # 예외 발생 여부 확인 (Streamlit error box)
    error_boxes = page.locator("[data-testid='stException']")
    if error_boxes.count() > 0:
        take_screenshot(page, f"error_{menu.replace(' ', '_')}")
        pytest.fail(f"'{menu}' 페이지에서 예외 발생:\n{error_boxes.first.inner_text()}")

    # 페이지 타이틀 확인
    page_text = get_main_text(page)
    assert expected_title in page_text, (
        f"'{menu}' 이동 후 타이틀 '{expected_title}' 미발견\n"
        f"실제 텍스트(앞 200자): {page_text[:200]}"
    )
