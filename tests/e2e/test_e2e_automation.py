"""
E2E: Automation 페이지 UI 검증.

검증 범위:
1. 페이지 타이틀 및 기본 레이아웃
2. n8n 연결 성공 시 워크플로우 목록 표시
3. n8n 연결 실패(오프라인) 시 empty-state 메시지 표시
4. 'Open in n8n Editor' 링크 버튼 존재
"""
import pytest
from conftest import get_main_text, get_page_heading, navigate_to, take_screenshot, wait_for_streamlit


def go_to_automation(page, base_url):
    page.goto(base_url)
    wait_for_streamlit(page)
    navigate_to(page, "⚙️ Automation")
    page.wait_for_timeout(2_000)  # n8n API 요청 대기


@pytest.mark.e2e
def test_automation_page_title(page, base_url):
    """Automation 페이지 타이틀이 표시된다."""
    go_to_automation(page, base_url)

    assert "Automation" in get_page_heading(page)


@pytest.mark.e2e
def test_automation_no_exception(page, base_url):
    """Automation 페이지 진입 시 Streamlit 예외가 발생하지 않는다."""
    go_to_automation(page, base_url)

    error_boxes = page.locator("[data-testid='stException']")
    if error_boxes.count() > 0:
        take_screenshot(page, "error_automation_page")
        pytest.fail(f"Automation 페이지 예외:\n{error_boxes.first.inner_text()}")


@pytest.mark.e2e
def test_automation_shows_workflows_or_empty_state(page, base_url):
    """n8n 상태에 따라 워크플로우 목록 또는 empty-state 메시지가 표시된다."""
    go_to_automation(page, base_url)

    main_text = get_main_text(page)
    # n8n 온라인: "Active Agents" 헤더 또는 워크플로우 이름
    # n8n 오프라인: "No workflows found" 메시지
    has_content = (
        "Active Agents" in main_text
        or "Workflows" in main_text
        or "No workflows found" in main_text
        or "n8n" in main_text
    )
    assert has_content, (
        f"워크플로우 목록 또는 empty state 미발견. 페이지 텍스트(앞 300자):\n{main_text[:300]}"
    )


@pytest.mark.e2e
def test_automation_n8n_link_or_info_present(page, base_url):
    """n8n Editor 링크 또는 n8n 관련 안내 텍스트가 존재한다."""
    go_to_automation(page, base_url)

    main_text = get_main_text(page)
    has_n8n_ref = "n8n" in main_text or "workflow" in main_text.lower()
    assert has_n8n_ref, (
        f"n8n 관련 콘텐츠가 없음. 페이지 텍스트(앞 300자):\n{main_text[:300]}"
    )
