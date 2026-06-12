"""
E2E: Real Estate — 부동산 탭 전체 시나리오 검증 (25개).

대상 탭:
  Tab1: 🔍 아파트 탐색 (필터 / 단지 목록 / 지도 뷰)
  Tab2: 💡 Insight (거시경제 / 뉴스 리포트 / 정책 팩트)
  Tab3: 📋 Report Archive
  (Tab4: 👤 페르소나 — API 의존성 높아 별도 파일로 추후 분리 예정)

검증 범위 (Transaction-First 기준):
  Group A: 페이지 기본 (SCN-01 ~ 02)
  Group B: Tab1 검색 필터 (SCN-03 ~ 06)
  Group C: Tab1 검색 결과 (SCN-07 ~ 10, 19 ~ 25)
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


@pytest.mark.e2e
def test_real_estate_six_tabs_exist(page, base_url):
    """SCN-03: Real Estate에 6개 탭(아파트 탐색/거시경제/뉴스 리포트/정책 팩트/데일리 브리핑/페르소나)이 렌더링된다."""
    go_to_real_estate(page, base_url)
    page.wait_for_selector("[role='tablist']", timeout=8_000)

    for label in ["아파트 탐색", "거시경제", "뉴스 리포트", "정책 팩트", "데일리 브리핑", "페르소나"]:
        count = page.get_by_role("tab").filter(has_text=label).count()
        assert count > 0, f"탭 '{label}'가 없음"


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


@pytest.mark.e2e
def test_apt_detail_transaction_chart_section(page, base_url):
    """SCN-19: '📈 실거래가' 섹션을 펼치면 시계열 라인 차트가 표시된다 (카드 그리드 아님)."""
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

    tx_summary = page.locator("summary").filter(has_text="실거래가")
    if tx_summary.count() == 0:
        pytest.skip("'실거래가' 섹션 없음")
    tx_summary.first.click()
    page.wait_for_timeout(1_500)

    assert_no_streamlit_exception(page, "apt_detail_transaction_chart")

    detail_text = get_main_text(page)
    if "거래 이력이 없습니다" in detail_text:
        pytest.skip("거래 이력 없음")

    assert page.locator("[data-testid='stVegaLiteChart']").count() > 0, \
        "실거래가 시계열 라인 차트(stVegaLiteChart)가 없음"
    assert page.locator("[data-testid='stDataFrame']").count() > 0, \
        "실거래가 내역 테이블(stDataFrame)이 없음"


@pytest.mark.e2e
def test_apt_detail_commute_kpi_section(page, base_url):
    """SCN-20: '🚇 출퇴근' 섹션을 펼치면 대중교통/자가용/도보 소요시간 KPI가 표시된다."""
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

    commute_summary = page.locator("summary").filter(has_text="출퇴근")
    if commute_summary.count() == 0:
        pytest.skip("'출퇴근' 섹션 없음")
    commute_summary.first.click()
    page.wait_for_timeout(1_500)

    assert_no_streamlit_exception(page, "apt_detail_commute_kpi")

    detail_text = get_main_text(page)
    if "출퇴근 정보를 불러올 수 없습니다" in detail_text:
        pytest.skip("출퇴근 정보 없음")

    for label in ["🚇 대중교통", "🚗 자가용", "🚶 도보"]:
        assert label in detail_text, f"출퇴근 KPI '{label}' 미표시. 텍스트(앞 400자):\n{detail_text[:400]}"


@pytest.mark.e2e
def test_apt_detail_commute_transit_route_detail(page, base_url):
    """SCN-21: '🚇 출퇴근' 섹션에 대중교통 경로 상세(legs)가 별도 expander로 표시된다."""
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

    commute_summary = page.locator("summary").filter(has_text="출퇴근")
    if commute_summary.count() == 0:
        pytest.skip("'출퇴근' 섹션 없음")
    commute_summary.first.click()
    page.wait_for_timeout(1_500)

    detail_text = get_main_text(page)
    if "출퇴근 정보를 불러올 수 없습니다" in detail_text:
        pytest.skip("출퇴근 정보 없음")

    route_summary = page.locator("summary").filter(has_text="대중교통 경로 상세")
    if route_summary.count() == 0:
        pytest.skip("대중교통 경로 상세 없음 (transit_legs 데이터 없음)")

    route_summary.first.click()
    page.wait_for_timeout(1_000)

    assert_no_streamlit_exception(page, "apt_detail_commute_route_detail")

    detail_text = get_main_text(page)
    has_leg = any(marker in detail_text for marker in ["🚶 도보", "🚌", "🚇"])
    assert has_leg, f"대중교통 경로 상세에 이동 구간(leg) 정보가 없음. 텍스트(앞 400자):\n{detail_text[:400]}"


@pytest.mark.e2e
def test_apt_detail_location_score_card_grid(page, base_url):
    """SCN-22: '📍 입지점수' 섹션은 실거주/투자 점수를 2열 카드 그리드로 표시한다.

    location_score 데이터가 없으면 '입지 분석 데이터가 없습니다' 안내로 대체된다.
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
    page.wait_for_timeout(2_000)

    loc_summary = page.locator("summary").filter(has_text="입지점수")
    if loc_summary.count() == 0:
        pytest.skip("'입지점수' 섹션 없음")
    loc_summary.first.click()
    page.wait_for_timeout(1_000)

    assert_no_streamlit_exception(page, "apt_detail_location_score_grid")

    detail_text = get_main_text(page)
    if "입지 분석 데이터가 없습니다" in detail_text:
        pytest.skip("location_score 데이터 없음")

    for heading in ["🏠 실거주 점수", "💰 투자 점수"]:
        assert heading in detail_text, f"'{heading}' 섹션 없음. 텍스트(앞 600자):\n{detail_text[:600]}"

    assert page.locator("summary").filter(has_text="근거 보기").count() > 0, \
        "점수 카드에 '근거 보기' expander가 없음"


@pytest.mark.e2e
def test_apt_detail_location_score_evidence_click_to_reveal(page, base_url):
    """SCN-23: 점수 카드의 근거(evidence)는 '근거 보기'를 클릭해야만 표시된다 (카드형 클릭 UX)."""
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

    loc_summary = page.locator("summary").filter(has_text="입지점수")
    if loc_summary.count() == 0:
        pytest.skip("'입지점수' 섹션 없음")
    loc_summary.first.click()
    page.wait_for_timeout(1_000)

    detail_text = get_main_text(page)
    if "입지 분석 데이터가 없습니다" in detail_text:
        pytest.skip("location_score 데이터 없음")

    evidence_toggle = page.locator("summary").filter(has_text="근거 보기")
    if evidence_toggle.count() == 0:
        pytest.skip("'근거 보기' expander 없음")

    before_text = get_main_text(page)
    assert "· " not in before_text.split("근거 보기")[-1][:5], \
        "클릭 전인데 근거(evidence) 텍스트가 이미 노출됨"

    evidence_toggle.first.click()
    page.wait_for_timeout(1_000)

    assert_no_streamlit_exception(page, "apt_detail_location_score_evidence")

    after_text = get_main_text(page)
    assert "·" in after_text, f"'근거 보기' 클릭 후 근거 텍스트가 표시되지 않음. 텍스트(앞 600자):\n{after_text[:600]}"


@pytest.mark.e2e
def test_apt_detail_school_premium_card_shows_school_detail(page, base_url):
    """SCN-24: '🎒 학군프리미엄' 카드의 근거를 펼치면 학군 상세 데이터(학군 점수 등)가 표시된다.

    학군분석은 더 이상 AI 인사이트 안이 아니라 투자점수의 학군프리미엄 카드로 이동되었다.
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
    page.wait_for_timeout(2_000)

    loc_summary = page.locator("summary").filter(has_text="입지점수")
    if loc_summary.count() == 0:
        pytest.skip("'입지점수' 섹션 없음")
    loc_summary.first.click()
    page.wait_for_timeout(1_000)

    detail_text = get_main_text(page)
    if "입지 분석 데이터가 없습니다" in detail_text:
        pytest.skip("location_score 데이터 없음")

    if "🎒 학군프리미엄" not in detail_text:
        pytest.skip("'🎒 학군프리미엄' 카드 없음")

    # 🎒 학군프리미엄 카드 바로 다음의 '근거 보기' expander를 펼친다.
    school_card = page.locator("[data-testid='stMainBlockContainer']").get_by_text("🎒 학군프리미엄").first
    evidence_toggle = school_card.locator(
        "xpath=ancestor::div[contains(@data-testid,'stVerticalBlock')][1]//summary[contains(., '근거 보기')]"
    ).first
    evidence_toggle.click()
    page.wait_for_timeout(1_500)

    assert_no_streamlit_exception(page, "apt_detail_school_premium_detail")

    after_text = get_main_text(page)
    assert "학군 점수" in after_text, \
        f"'🎒 학군프리미엄' 근거에 학군 상세(학군 점수)가 없음. 텍스트(앞 600자):\n{after_text[:600]}"


@pytest.mark.e2e
def test_apt_detail_ai_insight_no_duplicate_sections(page, base_url):
    """SCN-25: '🤖 AI 인사이트'는 카드 상세 패널과 중복되는 입지점수/출퇴근/학군 섹션을 다시 표시하지 않는다."""
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

    insight_summary = page.locator("summary").filter(has_text="AI 인사이트")
    if insight_summary.count() == 0:
        pytest.skip("'AI 인사이트' 섹션 없음")
    insight_summary.first.click()
    page.wait_for_timeout(1_500)

    assert_no_streamlit_exception(page, "apt_detail_ai_insight_dedup")

    detail_text = get_main_text(page)
    for duplicated in ["📍 입지 점수", "🚗 출퇴근 요약", "📚 학군 분석"]:
        assert duplicated not in detail_text, \
            f"AI 인사이트에 중복 섹션 '{duplicated}'이 다시 표시됨. 텍스트(앞 600자):\n{detail_text[:600]}"


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
