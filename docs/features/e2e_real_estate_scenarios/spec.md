# 부동산 탭 E2E 테스트 시나리오 + 헬스체크 워크플로우

**작성일:** 2026-04-15  
**브랜치:** `feature/e2e-real-estate-scenarios`  
**담당:** Claude Code

---

## 1. 배경 및 목표

### 배경

Transaction-First 아파트 마스터 재설계(2026-04-15) 이후 기존 E2E 테스트(`test_e2e_real_estate.py`, 9개)가 다음 이유로 깨질 가능성이 생겼다:

| 변경 사항 | 기존 코드 | 현재 코드 |
|-----------|-----------|-----------|
| 검색 버튼 텍스트 | `"검색"` | `"🔍 검색"` |
| 결과 캡션 렌더링 | `"N건 검색됨"` (plain) | `"**N건** 검색됨"` (markdown bold → `<strong>` 태그) |
| 내부 Repository | `ApartmentMasterRepository` | `AptMasterRepository` |

### 목표

1. **18개 E2E 시나리오**로 부동산 탭 4개 전체를 커버하도록 테스트 전면 재작성
2. **헬퍼 함수 4개** 추가로 flaky timing 문제 해결 (blind `wait_for_timeout` 제거)
3. **헬스체크 워크플로우** (`scripts/e2e_health_check.py`) — 테스트 실행 → 실패 분석 → 마크다운 리포트 자동 생성 (향후 Claude 자동 수정 루프 기반)

---

## 2. 테스트 시나리오 목록

### Group A: 페이지 기본 (2개)

| ID | 함수명 | 검증 내용 |
|----|--------|-----------|
| SCN-01 | `test_real_estate_page_title` | h1에 "Real Estate" 포함 여부 |
| SCN-02 | `test_real_estate_no_exception_on_load` | `stException` 박스 0개 확인 |

### Group B: Tab1 — 검색 필터 (4개)

| ID | 함수명 | 검증 내용 |
|----|--------|-----------|
| SCN-03 | `test_apt_four_main_tabs_exist` | 4개 주 탭 텍스트 확인 |
| SCN-04 | `test_apt_filter_expander_expanded` | placeholder `"래미안, 힐스테이트 …"` visible |
| SCN-05 | `test_apt_filter_inputs_name_sido_sigungu` | 아파트명 text_input + 시도/시군구 selectbox |
| SCN-06 | `test_apt_search_button_in_expander` | expander 내 `"🔍 검색"` 버튼 존재 |

### Group C: Tab1 — 검색 결과 (4개)

| ID | 함수명 | 검증 내용 |
|----|--------|-----------|
| SCN-07 | `test_apt_search_shows_result_caption` | `wait_for_search_results()` 후 "건 검색됨" |
| SCN-08 | `test_apt_search_subtabs_exist` | "단지 목록", "지도 뷰" 서브탭 존재 |
| SCN-09 | `test_apt_name_search_filters_results` | "래미안" 입력 후 검색 → 캡션 갱신 |
| SCN-10 | `test_apt_dataframe_visible_with_results` | `stDataFrame` 또는 empty-state info |

### Group D: Tab1 — 지도 뷰 (2개)

| ID | 함수명 | 검증 내용 |
|----|--------|-----------|
| SCN-11 | `test_apt_map_tab_shows_load_button` | 지도 뷰 탭 → "지도 로드" 버튼 또는 경고/안내 |
| SCN-12 | `test_apt_map_no_exception` | 지도 뷰 탭 `stException` 없음 |

### Group E: Tab2 — Insight (4개)

| ID | 함수명 | 검증 내용 |
|----|--------|-----------|
| SCN-13 | `test_insight_three_subtabs_exist` | "거시경제", "뉴스 리포트", "정책 팩트" 서브탭 |
| SCN-14 | `test_insight_macro_renders` | 기준금리 metric 또는 "불러올 수 없습니다" |
| SCN-15 | `test_insight_news_renders` | 리포트 selectbox 또는 "생성된 뉴스 리포트가 없습니다" |
| SCN-16 | `test_insight_policy_search_button` | `"🔍 검색"` 버튼 count > 0 |

### Group F: Tab3 — Report Archive (2개)

| ID | 함수명 | 검증 내용 |
|----|--------|-----------|
| SCN-17 | `test_report_archive_renders` | "인사이트 리포트" in text + no exception |
| SCN-18 | `test_report_archive_list_or_warning` | 리포트 dataframe 또는 "저장된 인사이트 리포트가 없습니다" |

> **참고:** 페르소나 탭(Tab4)은 API 의존성이 높아 별도 파일(`test_e2e_persona.py`)로 추후 분리 예정.

---

## 3. 신규 헬퍼 함수 설계 (conftest.py)

### `go_to_real_estate(page, base_url)`
- 기존 test 파일 내 동명 함수를 conftest로 이동
- `navigate_to()` + blind timeout 대신 `h1` 렌더링 조건 대기

### `click_real_estate_tab(page, tab_name, wait_ms=800)`
- 탭 이름 부분 매칭으로 클릭 (이모지 프리픽스 불필요)

### `wait_for_search_results(page, timeout=12_000)`
- `stCaptionContainer` 에 "건 검색됨" 조건 대기
- fallback: `stAlertInfo/stAlertWarning` (empty state / apt_master 비어있음)

### `assert_no_streamlit_exception(page, context_name="")`
- `stException` 존재 시 스크린샷 저장 + `pytest.fail()`

---

## 4. 헬스체크 워크플로우 설계

### `scripts/e2e_health_check.py`

```
run_pytest()       → subprocess + --json-report (실시간 출력)
parse_report()     → 실패 목록 + 스크린샷 경로 추출
build_markdown()   → 구조화된 마크다운 보고서
main()             → docs/e2e_health_report.md 저장
```

**실행:**
```bash
arch -arm64 .venv/bin/python3.12 scripts/e2e_health_check.py
```

**출력:** `docs/e2e_health_report.md` — 실패 테스트명·에러·스크린샷 경로·소스 파일 참조

---

## 5. 의존성

- `pytest-json-report>=1.5.0` (신규 설치 필요)
- 기존: `pytest-playwright`, `playwright`, `pytest-base-url`

---

## 6. 주의 사항

1. **`apt_master` empty 케이스:** DB 비어있으면 Tab1이 `st.stop()` → `wait_for_search_results()`가 warning으로 graceful 처리
2. **복수 `🔍 검색` 버튼:** Tab1 필터 expander + Tab2 정책 팩트에 각각 존재 → expander 스코핑
3. **`stCaptionContainer` testid:** Streamlit 1.28+ 기준. 변경 시 fallback `p.stCaption`
