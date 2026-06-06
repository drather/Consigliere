# Progress: arch-di-final-cleanup

**시작:** 2026-06-06  
**완료:** 2026-06-06

---

## 체크리스트

### Fix 1: CommuteRepository 싱글톤 통합

- [x] `dependencies.py` — `_commute_repo` 모듈 레벨 추출
- [x] `_commute_service`에서 `_commute_repo` 재사용
- [x] `_apt_orchestrator`에서 중복 `CommuteRepository(...)` 제거 → `_commute_repo` 재사용
- [x] `get_commute_repo()` 게터 추가
- [x] 테스트 통과 확인

### Fix 2: DailyReportOrchestrator DI 전환

- [x] `dependencies.py` — Daily Report 섹션 신규 작성
  - [x] `_daily_report_repo` 싱글톤 (DailyReportRepository)
  - [x] `_daily_llm`, `_prompt_loader`, `_root_storage` 싱글톤
  - [x] `_daily_report_orchestrator` 싱글톤 (모든 의존성 주입)
  - [x] `get_daily_report_repo()`, `get_daily_report_orchestrator()` 게터
- [x] `routers/real_estate.py` — `generate_daily_report` 20+ 로컬 import/빌더 제거 → `Depends()`
- [x] `routers/real_estate.py` — `list_daily_reports` 로컬 Config/Repository 생성 제거 → `Depends()`
- [x] 상단 import 블록에 필요한 타입 import 추가
- [x] 테스트 통과 확인 (858 passed)
- [x] 커밋 및 푸시
