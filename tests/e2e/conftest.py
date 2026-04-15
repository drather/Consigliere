"""
E2E test fixtures — Streamlit 서버 기동/종료 및 Playwright 공통 설정.

실행 방법:
    arch -arm64 .venv/bin/python3.12 -m pytest tests/e2e/ -v

서버 포트: 8502 (기동 중인 8501과 충돌 방지)
"""
import os
import socket
import subprocess
import time

import pytest

TEST_PORT = 8502
BASE_URL = f"http://localhost:{TEST_PORT}"
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PYTHON = os.path.join(PROJECT_ROOT, ".venv", "bin", "python3.12")
MAIN_PY = os.path.join(PROJECT_ROOT, "src", "dashboard", "main.py")

SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


def _wait_for_port(port: int, timeout: int = 40) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("localhost", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.5)
    return False


@pytest.fixture(scope="session")
def streamlit_server():
    """Streamlit 서버를 TEST_PORT로 기동하고 세션 종료 시 정리."""
    proc = subprocess.Popen(
        [
            "arch", "-arm64", PYTHON, "-m", "streamlit", "run", MAIN_PY,
            "--server.port", str(TEST_PORT),
            "--server.headless", "true",
            "--server.runOnSave", "false",
            "--logger.level", "error",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=PROJECT_ROOT,
    )

    if not _wait_for_port(TEST_PORT, timeout=40):
        proc.terminate()
        pytest.fail(f"Streamlit 서버가 {TEST_PORT} 포트에서 기동되지 않았습니다.")

    yield BASE_URL

    proc.terminate()
    proc.wait(timeout=5)


@pytest.fixture(scope="session")
def base_url(streamlit_server):
    """pytest-playwright base_url 오버라이드 — streamlit_server 사용."""
    return streamlit_server


@pytest.fixture
def page(page, streamlit_server):
    """각 테스트용 page fixture — 기본 타임아웃 10초."""
    page.set_default_timeout(10_000)
    yield page


def wait_for_streamlit(page, timeout: int = 8_000) -> None:
    """Streamlit 앱 초기 로딩 대기 (stApp 마운트 확인)."""
    page.wait_for_selector("[data-testid='stApp']", timeout=timeout)


def navigate_to(page, menu_label: str) -> None:
    """사이드바 라디오에서 메뉴 항목 선택."""
    # Streamlit radio label 클릭 (data-testid 기반으로 사이드바 내 한정)
    sidebar = page.locator("[data-testid='stSidebar']")
    sidebar.locator("label").filter(has_text=menu_label.split()[-1]).click()
    page.wait_for_timeout(1_500)  # 페이지 재렌더 대기


def get_main_text(page) -> str:
    """메인 콘텐츠 영역 텍스트 반환 (사이드바 제외).

    Streamlit DOM: stApp > stMain > stMainBlockContainer
    """
    # Streamlit 버전별 메인 컨테이너 testid 순서로 시도
    for selector in [
        "[data-testid='stMainBlockContainer']",
        "[data-testid='stMain']",
        "[data-testid='stAppViewContainer']",
        ".main",
    ]:
        el = page.locator(selector)
        if el.count() > 0:
            return el.first.inner_text(timeout=10_000)
    # 최후 fallback: 전체 body에서 sidebar 제외
    return page.locator("body").inner_text(timeout=10_000)


def get_page_heading(page) -> str:
    """메인 콘텐츠 영역의 첫 번째 h1 텍스트 반환."""
    for selector in [
        "[data-testid='stMainBlockContainer'] h1",
        "[data-testid='stMain'] h1",
        "[data-testid='stAppViewContainer'] h1",
    ]:
        el = page.locator(selector)
        if el.count() > 0:
            return el.first.inner_text(timeout=8_000)
    # fallback: 두 번째 h1 (첫 번째는 사이드바)
    return page.locator("h1").nth(1).inner_text(timeout=8_000)


def take_screenshot(page, name: str) -> None:
    """실패 디버깅용 스크린샷 저장."""
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    page.screenshot(path=path)


# ──────────────────────────────────────────────────────────────────────────────
# 부동산 탭 전용 헬퍼
# ──────────────────────────────────────────────────────────────────────────────

def go_to_real_estate(page, base_url: str) -> None:
    """Real Estate 탭으로 이동하고 h1 렌더링까지 조건 대기.

    blind wait_for_timeout 대신 DOM 조건으로 대기하여 flaky 방지.
    """
    page.goto(base_url)
    wait_for_streamlit(page)
    navigate_to(page, "🏢 Real Estate")
    page.wait_for_selector(
        "[data-testid='stMainBlockContainer'] h1",
        timeout=8_000,
    )


def click_real_estate_tab(page, tab_name: str, wait_ms: int = 800) -> None:
    """Real Estate 페이지 내 탭을 부분 텍스트로 클릭하고 재렌더 대기.

    Args:
        tab_name: 탭 레이블 부분 문자열 (이모지 불필요, 예: "Insight", "아파트 탐색")
        wait_ms:  클릭 후 Streamlit 재렌더 대기 시간 (ms)

    Note:
        4개 주 탭 + Insight 3개 서브탭이 모두 role=tab으로 DOM에 존재한다.
        filter(has_text=...) 부분 매칭이므로 이모지 프리픽스 없이도 동작한다.
    """
    import pytest as _pytest  # noqa: F401

    tab = page.get_by_role("tab").filter(has_text=tab_name).first
    tab.wait_for(state="visible", timeout=5_000)
    tab.click()
    page.wait_for_timeout(wait_ms)


def wait_for_search_results(page, timeout: int = 12_000) -> None:
    """'N건 검색됨' 캡션 또는 empty/warning 상태가 나타날 때까지 대기.

    st.caption("**N건** 검색됨") → Streamlit이 <strong> 래핑.
    filter(has_text=...) 는 자식 텍스트 노드 전체를 검사하므로
    "건 검색됨" 부분 매칭이 동작한다.

    우선순위:
    1. stCaptionContainer 내 "건 검색됨" 텍스트 대기
    2. fallback: stAlertInfo/stAlertWarning (empty state / apt_master 비어있음 / DB 오류)
    """
    try:
        page.locator("[data-testid='stCaptionContainer']").filter(
            has_text="건 검색됨"
        ).first.wait_for(state="visible", timeout=timeout)
    except Exception:
        # apt_master 빈 DB, API 오류, 검색 결과 없음 등 모든 alert 수용
        page.locator(
            "[data-testid='stAlertInfo'], [data-testid='stAlertWarning'], [data-testid='stAlertError']"
        ).first.wait_for(state="visible", timeout=3_000)


def assert_no_streamlit_exception(page, context_name: str = "") -> None:
    """현재 페이지에 stException 박스가 없음을 단언한다.

    실패 시 스크린샷을 저장하고 pytest.fail()로 에러 텍스트를 출력한다.
    """
    import pytest as _pytest

    error_boxes = page.locator("[data-testid='stException']")
    if error_boxes.count() > 0:
        take_screenshot(page, f"exception_{context_name or 'unknown'}")
        _pytest.fail(
            f"Streamlit 예외 발생 ({context_name}):\n{error_boxes.first.inner_text()}"
        )
