# Career SOLID 장기 개선 — Progress

**Feature:** `career-solid-refactor`
**Branch:** `feature/career-solid-refactor`
**Created:** 2026-04-05

---

## Phase 1: Planning ✅

- [x] spec.md 작성
- [x] progress.md 생성
- [x] 브랜치 생성 및 커밋

---

## Phase 2: Implementation (TDD)

### Step 1 — Processor Protocol 정의
- [ ] `src/modules/career/processors/protocols.py` 신규 작성
  - `JobAnalyzerProtocol`
  - `TrendAnalyzerProtocol`
  - `SkillGapAnalyzerProtocol`
  - `CommunityAnalyzerProtocol`
- [ ] `tests/modules/career/test_protocols.py` — Protocol 적합성 테스트 (Red → Green)

### Step 2 — CareerPathResolver 분리
- [ ] `src/modules/career/path_resolver.py` 신규 작성
- [ ] `tests/modules/career/test_path_resolver.py` — 단위 테스트 (Red → Green)
- [ ] `service.py`에서 `_*_path()` 헬퍼 제거, `CareerPathResolver` 위임

### Step 3 — CareerDataStore 분리
- [ ] `src/modules/career/data_store.py` 신규 작성
- [ ] `tests/modules/career/test_data_store.py` — 단위 테스트 (Red → Green)
- [ ] `service.py` `fetch_*()` 내부 캐시 로직을 `CareerDataStore`에 위임

### Step 4 — CareerAgent 의존성 주입 개선
- [ ] `service.py` `__init__` 시그니처 변경 (Protocol 타입 힌트, 기본값 None)
- [ ] `tests/modules/career/test_career_agent_di.py` — Mock 주입 통합 테스트 (Red → Green)

### Step 5 — run_pipeline 중복 제거
- [ ] `generate_report()` / `run_pipeline()` 내부 `_analyze()` 헬퍼 추출
- [ ] 기존 동작과 동일한지 통합 테스트 확인

---

## Phase 2.5: SOLID Review

- [ ] SRP: CareerAgent가 오케스트레이션만 담당하는가
- [ ] OCP: 새 Analyzer 추가 시 CareerAgent 수정 없이 주입 가능한가
- [ ] DIP: CareerAgent가 Protocol에만 의존하는가
- [ ] Zero Hardcoding 확인
- [ ] 전체 테스트 통과: `arch -arm64 .venv/bin/python3.12 -m pytest tests/ -v`

---

## Phase 3: Documentation

- [ ] `issues.md` 작성
- [ ] `result.md` 작성
- [ ] `docs/context/history.md` 업데이트
- [ ] `docs/context/active_state.md` 업데이트

---

## Phase 4: Release

- [ ] master 머지
- [ ] `arch -arm64 .venv/bin/python3.12 -m pytest tests/ -v` Green 확인
- [ ] push
