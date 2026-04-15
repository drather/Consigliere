# Progress: 부동산 탭 E2E 시나리오 + 헬스체크 워크플로우

**브랜치:** `feature/e2e-real-estate-scenarios`  
**시작일:** 2026-04-15

---

## Phase 0: Preparation

- [x] `active_state.md` 업데이트
- [x] `feature/e2e-real-estate-scenarios` 브랜치 생성
- [x] `docs/features/e2e_real_estate_scenarios/` 디렉토리 생성

## Phase 1: Planning

- [x] `spec.md` 작성
- [x] `progress.md` 작성
- [ ] 초기 커밋 (spec + progress)

## Phase 2: Implementation

### 2-A. 의존성
- [ ] `requirements.txt`에 `pytest-json-report>=1.5.0` 추가
- [ ] `arch -arm64 .venv/bin/python3.12 -m pip install pytest-json-report`
- [ ] 커밋

### 2-B. conftest.py 헬퍼 추가
- [ ] `go_to_real_estate(page, base_url)` 추가
- [ ] `click_real_estate_tab(page, tab_name, wait_ms)` 추가
- [ ] `wait_for_search_results(page, timeout)` 추가
- [ ] `assert_no_streamlit_exception(page, context_name)` 추가
- [ ] 커밋

### 2-C. test_e2e_real_estate.py 재작성 (18개 시나리오)

#### Group A: 페이지 기본
- [ ] SCN-01 `test_real_estate_page_title`
- [ ] SCN-02 `test_real_estate_no_exception_on_load`

#### Group B: Tab1 — 검색 필터
- [ ] SCN-03 `test_apt_four_main_tabs_exist`
- [ ] SCN-04 `test_apt_filter_expander_expanded`
- [ ] SCN-05 `test_apt_filter_inputs_name_sido_sigungu`
- [ ] SCN-06 `test_apt_search_button_in_expander`

#### Group C: Tab1 — 검색 결과
- [ ] SCN-07 `test_apt_search_shows_result_caption`
- [ ] SCN-08 `test_apt_search_subtabs_exist`
- [ ] SCN-09 `test_apt_name_search_filters_results`
- [ ] SCN-10 `test_apt_dataframe_visible_with_results`

#### Group D: Tab1 — 지도 뷰
- [ ] SCN-11 `test_apt_map_tab_shows_load_button`
- [ ] SCN-12 `test_apt_map_no_exception`

#### Group E: Tab2 — Insight
- [ ] SCN-13 `test_insight_three_subtabs_exist`
- [ ] SCN-14 `test_insight_macro_renders`
- [ ] SCN-15 `test_insight_news_renders`
- [ ] SCN-16 `test_insight_policy_search_button`

#### Group F: Tab3 — Report Archive
- [ ] SCN-17 `test_report_archive_renders`
- [ ] SCN-18 `test_report_archive_list_or_warning`

- [ ] 커밋

### 2-D. e2e_health_check.py 작성
- [ ] `run_pytest()` 함수
- [ ] `parse_report()` 함수
- [ ] `build_markdown()` 함수
- [ ] `main()` 오케스트레이션
- [ ] 커밋

### 2-E. 테스트 실행 및 검증
- [ ] `arch -arm64 .venv/bin/python3.12 -m pytest tests/e2e/test_e2e_real_estate.py -v`
- [ ] 실패 테스트 수정 (있을 경우)
- [ ] 헬스체크 스크립트 실행 확인

## Phase 3: Documentation

- [ ] `result.md` 작성 (최종 결과, 통과 수, 스크린샷)
- [ ] `active_state.md` 완료 상태로 업데이트
- [ ] `history.md`에 요약 추가
- [ ] 최종 커밋
