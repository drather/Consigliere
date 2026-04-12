# Result: 아파트 마스터 × Market Monitor 통합 탐색 허브

**Feature:** `apt-master-monitor-integration`
**완료일:** 2026-04-12
**Branch:** `feature/apt-master-monitor-integration`

---

## 구현 요약

Tab1(Market Monitor)과 Tab5(단지 검색)를 **"🔍 아파트 탐색"** 단일 탭으로 통합.

### UX 흐름

```
필터 (시도/시군구/아파트명/세대수/건설사/준공연도)
    ↓ 🔍 검색
단지 목록 (클릭 가능 dataframe)
    ↓ 단지 클릭
상세 정보 카드 (세대수, 동수, 준공연도, 건설사 등 8개 metric)
    + 최근 실거래가 테이블 (최대 50건, 최신순)
    + 📥 실거래가 수집 버튼
    
[지도 뷰 서브탭]
    → 검색 결과 단지 지도 표시 (최대 100개)
    → 마커 클릭 → 팝업(단지 정보 + 최근 실거래가)
```

---

## 변경 파일 목록

| 파일 | 변경 내용 |
|------|-----------|
| `src/dashboard/views/real_estate.py` | Tab1+Tab5 통합, `_render_apt_detail_panel()` 추출, 탭 5→4 |
| `src/modules/real_estate/apartment_master/repository.py` | models 임포트 try/except 추가 |
| `src/modules/real_estate/apartment_master/service.py` | models 임포트 try/except 추가 |
| `src/modules/real_estate/config.yaml` | `apt_search_tx_limit`, `apt_search_map_limit` 추가 |
| `tests/test_real_estate_tab5.py` | 통합 UI 검증 테스트 4개 작성 |
| `tests/conftest.py` | AppTest용 sys.path 설정 |

---

## 테스트 결과

```
tests/test_real_estate_tab5.py::test_tab_count_reduced_to_four    PASSED
tests/test_real_estate_tab5.py::test_apt_search_filter_widgets_exist PASSED
tests/test_real_estate_tab5.py::test_apt_search_subtabs_exist     PASSED
tests/test_real_estate_tab5.py::test_no_module_import_errors_on_load PASSED

tests/test_apt_master_map.py (7개) PASSED

총 11 passed
```

---

## SOLID Review 결과

- **SRP:** `_render_apt_detail_panel(m, tx_limit)` 분리 완료
- **Zero Hardcoding:** `apt_search_tx_limit`(50), `apt_search_map_limit`(100) → `config.yaml` 이관 완료
- **에러 처리:** API 실패 시 `st.error()` + 안내 메시지 (기존 graceful fallback 유지)
