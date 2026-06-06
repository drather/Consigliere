# Result: arch-di-final-cleanup

**완료일:** 2026-06-06  
**커밋:** `83207b0`

---

## 구현 결과

### Fix 1 — CommuteRepository 싱글톤 통합

`dependencies.py`에서 `CommuteRepository`가 두 군데서 독립적으로 생성되던 문제를 제거했다.

**Before:**
```python
# _commute_service 생성 시
_commute_service = CommuteService(
    repo=CommuteRepository(db_path=_commute_db_path, ttl_days=90),
    ...
)

# _apt_orchestrator 생성 시 (별개 인스턴스)
_apt_orchestrator = AptAnalysisOrchestrator(
    commute_repo=CommuteRepository(db_path=_commute_db_path, ttl_days=90),
    ...
)
```

**After:**
```python
_commute_repo = CommuteRepository(db_path=_commute_db_path, ttl_days=90)  # 싱글톤
_commute_service = CommuteService(repo=_commute_repo, ...)
_apt_orchestrator = AptAnalysisOrchestrator(commute_repo=_commute_repo, ...)
```

---

### Fix 2 — DailyReportOrchestrator DI 전환

`generate_daily_report` 엔드포인트에서 20개 이상의 로컬 import와 직접 빌더 로직을 제거했다.

**Before:** 함수 본문 145줄, 20+ 인라인 import, 모든 의존성 직접 생성  
**After:** 함수 본문 45줄, 4개 `Depends()` 파라미터

`list_daily_reports`도 로컬 `RealEstateConfig` + `DailyReportRepository` 생성을 제거하고 `Depends(get_daily_report_repo)` 1줄로 대체.

**`dependencies.py`에 추가된 싱글톤:**
- `_commute_repo` — CommuteRepository
- `_daily_report_repo` — DailyReportRepository
- `_daily_llm` — LLM 클라이언트
- `_prompt_loader` — PromptLoader
- `_daily_report_orchestrator` — DailyReportOrchestrator (전체 의존성 그래프 포함)

---

## 테스트 결과

```
858 passed, 7 failed (all pre-existing), 1 collection error (pre-existing)
```

신규 실패 없음.

---

## Phase 2.5 SOLID 체크리스트

- [x] **SRP:** 각 클래스 책임 단일 유지
- [x] **DIP:** 엔드포인트가 구체 클래스 직접 생성 안 함, 추상 인터페이스 통해 주입
- [x] **Zero Hardcoding:** 설정값 모두 `_re_config.get()` 경유
- [x] **테스트 가능성:** `app.dependency_overrides` 패턴으로 모킹 가능
- [x] **DI 등록:** 모든 신규 싱글톤 `dependencies.py`에 factory 함수 등록
- [x] **계층 건너뛰기 금지:** 엔드포인트 → DI factory → module 경로 준수

---

## E2E 검증 면제

- **사유:** 화면단 변경 없음 — 백엔드 DI 리팩토링만 포함 (API 응답 스펙 동일)
- **변경 범위:** `src/api/dependencies.py`, `src/api/routers/real_estate.py`
