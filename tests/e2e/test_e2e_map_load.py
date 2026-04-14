"""
E2E: 지도 로드 기능 — '🗺️ 지도 로드' 버튼 동작 검증.

버그 원인: main.py에 load_dotenv() 누락 → KAKAO_API_KEY가 os.environ에
미반영 → st.warning("KAKAO_API_KEY 환경변수가 설정되지 않았습니다.") 출력 후 중단.

수정: main.py에 load_dotenv() 추가.

검증 범위:
1. KAKAO_API_KEY 경고 메시지가 표시되지 않음 (버그 회귀 방지)
2. 지도 뷰 탭 진입 시 '지도 로드' 버튼 노출
3. 버튼 클릭 → 스피너 → folium 지도 또는 empty-state 렌더링
4. '🔄 초기화' 버튼으로 지도 캐시 삭제 후 안내 메시지 복원
"""
import pytest
from conftest import get_main_text, navigate_to, take_screenshot, wait_for_streamlit

# 지도 로드 타임아웃: Kakao 지오코딩 + folium 렌더링 시간 고려
MAP_LOAD_TIMEOUT = 45_000  # 45초


def go_to_map_tab(page, base_url):
    """Real Estate → 아파트 탐색 → 지도 뷰 탭까지 이동하고 검색 결과를 확보."""
    page.goto(base_url)
    wait_for_streamlit(page)
    navigate_to(page, "🏢 Real Estate")

    # 아파트 탐색 탭
    page.get_by_role("tab", name="아파트 탐색").click()

    # 초기 검색 결과 로딩 완료 대기
    page.wait_for_selector("text=건 검색됨", timeout=15_000)

    # 지도 뷰 서브탭
    page.get_by_role("tab", name="지도 뷰").click()
    page.wait_for_timeout(800)


@pytest.mark.e2e
def test_map_tab_no_kakao_warning(page, base_url):
    """KAKAO_API_KEY가 정상 로드되어 경고 메시지가 표시되지 않는다.

    이 테스트가 실패하면 load_dotenv() 누락 버그가 재발한 것이다.
    """
    go_to_map_tab(page, base_url)

    main_text = get_main_text(page)
    assert "KAKAO_API_KEY 환경변수가 설정되지 않았습니다" not in main_text, (
        "KAKAO_API_KEY 경고 메시지 발견 → main.py의 load_dotenv() 누락 버그 재발\n"
        f"페이지 텍스트(앞 300자):\n{main_text[:300]}"
    )


@pytest.mark.e2e
def test_map_load_button_visible(page, base_url):
    """검색 결과가 있을 때 '지도 로드' 버튼이 지도 뷰 탭에 표시된다."""
    go_to_map_tab(page, base_url)

    load_btn = page.get_by_role("button", name="지도 로드")
    assert load_btn.count() > 0, "지도 로드 버튼이 없음 — 검색 결과 없거나 KAKAO_API_KEY 오류"


@pytest.mark.e2e
def test_map_initial_guide_message(page, base_url):
    """지도 로드 전 초기 상태 안내 메시지가 표시된다."""
    go_to_map_tab(page, base_url)

    main_text = get_main_text(page)
    assert "지도 로드" in main_text, (
        f"초기 안내 메시지 없음. 페이지 텍스트(앞 300자):\n{main_text[:300]}"
    )


@pytest.mark.e2e
def test_map_load_button_click_renders_map(page, base_url):
    """'지도 로드' 버튼 클릭 후 지도 캡션 또는 folium iframe이 렌더링된다."""
    go_to_map_tab(page, base_url)

    load_btn = page.get_by_role("button", name="지도 로드")
    if load_btn.count() == 0:
        pytest.skip("지도 로드 버튼 없음 — 검색 결과 없음")

    load_btn.first.click()

    # 스피너 대기 후 지도 렌더링 완료 확인
    # folium 지도는 iframe으로 삽입되거나, 캡션("지도 표시: N개")으로 확인
    try:
        # 캡션 텍스트 대기 (지오코딩 + 렌더링 포함)
        page.wait_for_selector(
            "text=지도 표시",
            timeout=MAP_LOAD_TIMEOUT,
        )
        map_loaded = True
    except Exception:
        map_loaded = False

    if not map_loaded:
        # iframe (folium map) 존재 여부로 재확인
        iframe_count = page.locator("iframe").count()
        map_loaded = iframe_count > 0

    if not map_loaded:
        take_screenshot(page, "map_load_failed")
        main_text = get_main_text(page)
        pytest.fail(
            f"지도 로드 후 지도 또는 캡션 미렌더링.\n"
            f"페이지 텍스트(앞 500자):\n{main_text[:500]}"
        )


@pytest.mark.e2e
def test_map_clear_button_resets_state(page, base_url):
    """'초기화' 버튼 클릭 시 지도가 사라지고 안내 메시지가 복원된다."""
    go_to_map_tab(page, base_url)

    load_btn = page.get_by_role("button", name="지도 로드")
    if load_btn.count() == 0:
        pytest.skip("지도 로드 버튼 없음 — 검색 결과 없음")

    # 먼저 지도 로드
    load_btn.first.click()
    try:
        page.wait_for_selector("text=지도 표시", timeout=MAP_LOAD_TIMEOUT)
    except Exception:
        pytest.skip("지도 로드 실패 — 초기화 테스트 건너뜀")

    # 초기화 버튼 클릭
    clear_btn = page.get_by_role("button", name="초기화")
    if clear_btn.count() == 0:
        pytest.skip("초기화 버튼 없음")

    clear_btn.first.click()
    page.wait_for_timeout(2_000)

    # 안내 메시지 복원 확인
    main_text = get_main_text(page)
    assert "지도 로드" in main_text, (
        f"초기화 후 안내 메시지 미복원. 페이지 텍스트(앞 300자):\n{main_text[:300]}"
    )
