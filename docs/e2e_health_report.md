# ✅ E2E 헬스체크 리포트 — Real Estate 탭

**생성일시:** 2026-04-15 21:35:33  
**테스트 대상:** `tests/e2e/test_e2e_real_estate.py`  
**총 소요 시간:** 64.2s  
**결과:** 18 통과 / 0 실패 / 0 스킵 / 18 전체

---

## 요약

| 상태 | 건수 |
|------|------|
| ✅ 통과 | 18 |
| ❌ 실패 | 0 |
| ⏭️ 스킵 | 0 |
| 합계 | 18 |

---

## 실패 없음

모든 테스트가 통과했습니다. 🎉

---

## 통과 테스트

- ✅ `test_real_estate_page_title[chromium]`
- ✅ `test_real_estate_no_exception_on_load[chromium]`
- ✅ `test_apt_four_main_tabs_exist[chromium]`
- ✅ `test_apt_filter_expander_expanded[chromium]`
- ✅ `test_apt_filter_inputs_name_sido_sigungu[chromium]`
- ✅ `test_apt_search_button_in_expander[chromium]`
- ✅ `test_apt_search_shows_result_caption[chromium]`
- ✅ `test_apt_search_subtabs_exist[chromium]`
- ✅ `test_apt_name_search_filters_results[chromium]`
- ✅ `test_apt_dataframe_visible_with_results[chromium]`
- ✅ `test_apt_map_tab_shows_load_button[chromium]`
- ✅ `test_apt_map_no_exception[chromium]`
- ✅ `test_insight_three_subtabs_exist[chromium]`
- ✅ `test_insight_macro_renders[chromium]`
- ✅ `test_insight_news_renders[chromium]`
- ✅ `test_insight_policy_search_button[chromium]`
- ✅ `test_report_archive_renders[chromium]`
- ✅ `test_report_archive_list_or_warning[chromium]`

---

## 자동 수정 컨텍스트

아래 정보는 Claude 자동 수정 루프를 위한 컨텍스트입니다.

**소스 파일:**
- UI: `src/dashboard/views/real_estate.py`
- 테스트: `tests/e2e/test_e2e_real_estate.py`
- 헬퍼: `tests/e2e/conftest.py`

**알려진 Streamlit 셀렉터 매핑:**

| UI 요소 | Playwright 셀렉터 |
|---------|-----------------|
| 검색 버튼 | `get_by_role('button', name='🔍 검색')` — expander 스코핑 필요 |
| 결과 캡션 | `[data-testid='stCaptionContainer']` filter `has_text='건 검색됨'` |
| 예외 박스 | `[data-testid='stException']` |
| 경고 박스 | `[data-testid='stAlertWarning']` |
| info 박스 | `[data-testid='stAlertInfo']` |
| 탭 | `get_by_role('tab').filter(has_text=...)` |
| 데이터프레임 | `[data-testid='stDataFrame']` |

**apt_master 상태 주의:**  
`real_estate.db`가 비어있으면 Tab1이 `st.stop()` 호출 → 서브탭 미표시 (정상 케이스, pytest.skip() 처리됨)
