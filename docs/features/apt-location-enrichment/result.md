# Result

**완료일:** 2026-06-08

## 변경 내용

- `src/modules/real_estate/apt_analysis/orchestrator.py`
  - `loc_repo` → `location_service` DI 전환
  - `_get_location_score()`: 점수 미존재 시 `enrich_and_save()` 자동 계산·저장 + graceful degrade
  - `_build_location_candidate()` 신규: POI 캐시 + 통근(transit) + household_count → candidate dict
- `src/api/dependencies.py` — `_apt_orchestrator`에 `_location_service` 싱글톤 주입
- `tests/modules/real_estate/apt_analysis/test_apt_analysis_orchestrator.py` — 11개 신규/수정 테스트

## 테스트 결과

```
588 passed
```

- 신규 11개 테스트 포함 전체 통과, 신규 회귀 없음

## 검증 방법 (E2E)

- 문정시영(A13820007) POI 캐시 재수집 후 `POST /jobs/apt/analyze` 실제 호출
- 응답에 `location_score: { residential_total: 74, investment_total: 67, results: {...} }` 정상 포함 확인

## E2E 검증 면제

- **사유:** 화면단(Streamlit) 변경 없음 — 백엔드 orchestrator/DI 로직만 포함
- **변경 범위:** `src/modules/real_estate/apt_analysis/orchestrator.py`, `src/api/dependencies.py`
