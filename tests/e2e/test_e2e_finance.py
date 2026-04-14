"""
E2E: Finance 페이지 UI 검증.

검증 범위:
1. 페이지 타이틀 및 기본 레이아웃
2. 날짜 선택기(date_input) 렌더링
3. 데이터 없을 때 warning 메시지 표시
4. 데이터 있을 때 트랜잭션 표 또는 메트릭 표시
"""
import pytest
from conftest import get_main_text, get_page_heading, navigate_to, take_screenshot, wait_for_streamlit


def go_to_finance(page, base_url):
    page.goto(base_url)
    wait_for_streamlit(page)
    navigate_to(page, "💰 Finance")
    page.wait_for_timeout(1_500)


@pytest.mark.e2e
def test_finance_page_title(page, base_url):
    """Finance 페이지 타이틀 'Finance Management'가 표시된다."""
    go_to_finance(page, base_url)

    assert "Finance" in get_page_heading(page)


@pytest.mark.e2e
def test_finance_no_exception(page, base_url):
    """Finance 페이지 진입 시 Streamlit 예외가 발생하지 않는다."""
    go_to_finance(page, base_url)

    error_boxes = page.locator("[data-testid='stException']")
    if error_boxes.count() > 0:
        take_screenshot(page, "error_finance_page")
        pytest.fail(f"Finance 페이지 예외:\n{error_boxes.first.inner_text()}")


@pytest.mark.e2e
def test_finance_date_input_visible(page, base_url):
    """날짜 선택기(Select Month)가 렌더링된다."""
    go_to_finance(page, base_url)

    main_text = get_main_text(page)
    assert "Select Month" in main_text or "Month" in main_text, (
        f"날짜 선택기 레이블 미발견. 페이지 텍스트(앞 200자):\n{main_text[:200]}"
    )


@pytest.mark.e2e
def test_finance_shows_data_or_empty_state(page, base_url):
    """데이터 유무에 따라 거래내역 표 또는 empty-state warning이 표시된다."""
    go_to_finance(page, base_url)

    main_text = get_main_text(page)
    # 데이터 있음: "Transactions" 헤더 또는 "Total Expense"
    # 데이터 없음: "No ledger found"
    has_content = (
        "Transactions" in main_text
        or "Total Expense" in main_text
        or "No ledger found" in main_text
    )
    assert has_content, (
        f"거래내역 표 또는 empty state 미발견. 페이지 텍스트(앞 300자):\n{main_text[:300]}"
    )
