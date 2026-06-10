# Progress

- [x] `_build_orchestrator()` 테스트 헬퍼: `loc_repo` mock → `location_service` mock 전환
- [x] `_make_fake_location_score()` 헬퍼 추가
- [x] `TestAptAnalysisOrchestratorLocationScoring` 4개 신규 테스트
  - [x] 점수 미존재 시 계산+저장
  - [x] 점수 존재 시 스킵
  - [x] candidate에 POI/commute 필드 포함 검증
  - [x] 계산 실패 시 graceful degrade (`location_score=None`, LLM은 계속 호출)
- [x] `orchestrator.py` 구현 (`_get_location_score`, `_build_location_candidate`, DI 전환)
- [x] `dependencies.py` DI 배선 (`_location_service` 싱글톤 주입)
- [x] 테스트 11개 신규/수정, 전체 588 passed
- [x] 문정시영(A13820007) POI 캐시 재수집 (수동, `POST /jobs/poi/collect` 우회)
- [x] E2E 검증: 실제 API 호출로 residential=74/investment=67 점수 생성 확인
- [x] `docs/context/active_state.md` 업데이트
