# LocationService.enrich_and_save() 리포트 생성 플로우 연결

**작성일:** 2026-06-08
**브랜치:** master (직접 작업, 별도 feature 브랜치 없음)

## 목표

`AptAnalysisOrchestrator.analyze()` 실행 시 단지의 입지 점수(`LocationScore`)가 없으면
POI 캐시 + 통근 데이터로 `LocationService.enrich_and_save()`를 호출해 자동 계산·저장하고,
리포트에 `residential_total`/`investment_total`/항목별 breakdown을 포함한다.

## 배경

- `LocationService.enrich_and_save()`는 구현·테스트 완료 상태였으나 리포트 생성 플로우에서 호출되지 않음
- 로드맵 1순위 과제 (`docs/context/active_state.md` 2026-06-06 시점 기준)

## 변경 내용

수정 파일: `src/modules/real_estate/apt_analysis/orchestrator.py`
1. 생성자 `loc_repo` → `location_service` (LocationService) DI 전환
2. `analyze()`: `commute_summary`를 `location_score` 계산 이전으로 재배치
3. `_get_location_score()`: 점수 미존재 시 `_build_location_candidate()` → `enrich_and_save()` 자동 계산·저장,
   계산 실패 시 로그 후 `location_score=None`으로 graceful degrade (LLM 인사이트는 계속 진행)
4. `_build_location_candidate()` 신규: POI 캐시(`get_poi_cached`) + 통근(transit) + household_count → candidate dict 구성

수정 파일: `src/api/dependencies.py`
- `_apt_orchestrator` 생성 시 `loc_repo=_loc_repo` → `location_service=_location_service` (기존 싱글톤 재사용)

## 아키텍처

```
AptAnalysisOrchestrator.analyze()
  └── _get_location_score(complex_code, apt_entry, commute_summary)
        ├── location_service.get_score(complex_code)  # 캐시 확인
        └── (없으면) location_service.enrich_and_save(complex_code, candidate)
              └── candidate ← _build_location_candidate()
                    ├── poi = location_service.get_poi_cached(complex_code)
                    ├── commute_summary["transit"]
                    └── apt_entry.household_count
```
