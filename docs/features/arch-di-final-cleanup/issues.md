# Issues: arch-di-final-cleanup

**작성일:** 2026-06-06

---

## 의사결정

### report_repo._path 직접 접근

**상황:** `generate_daily_report`에서 응답 body에 `report_path` 문자열을 구성할 때 `storage_path` 변수가 필요하다. 기존 코드는 `cfg.get("daily_report", {}).get("storage_path", ...)` 로 직접 읽었는데, DI 전환 후에는 이 값이 `DailyReportRepository._path`에만 있다.

**결정:** `report_repo._path`를 직접 참조. `DailyReportRepository`에 public `storage_path` 프로퍼티를 추가하는 것이 더 깔끔하지만, 현재 피처 스코프(DI 전환)를 벗어나는 추가 변경이므로 보류. `_path`는 안정적인 내부 구현이므로 로컬 접근 허용.

---

## 트레이드오프

### DailyReportOrchestrator를 싱글톤으로 등록 시 LLM 클라이언트 공유

`_daily_llm = build_llm_pipeline()`을 모듈 로드 시 1회 실행한다. 이 LLM 클라이언트는 `_supply_analyzer`와 `_daily_report_orchestrator` 양쪽에서 공유된다. 동일 객체를 공유하므로 상태 오염 가능성이 있으나, `BaseLLMClient`는 무상태(stateless) API 래퍼이므로 실질적 문제 없음.
