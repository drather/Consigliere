# Progress: 부동산 리포트 생성 전면 점검

**Branch:** `feature/report-generation-overhaul`

## Phase 1: Planning
- [x] spec.md 작성
- [x] progress.md 생성
- [x] 피처 브랜치 생성

## Phase 2: Implementation (TDD)

### 2-1. calculator.py — MacroRepository 주담대금리 주입
- [ ] 테스트: `test_calculator_with_macro_rate.py`
- [ ] 구현: `calculate_budget()` macro_rate 파라미터 추가

### 2-2. service.py — ChromaDB → tx_repo 전환
- [ ] 테스트: `test_generate_report_sqlite.py`
- [ ] 구현: `generate_report()` tx_repo 쿼리 + 가격 ±10% 필터

### 2-3. service.py — apt_master_repo enrich 수정
- [ ] 테스트: `test_enrich_apt_master_repo.py`
- [ ] 구현: `_enrich_transactions()` → `apt_master_repo.get_by_name()` 사용

### 2-4. insight_orchestrator.py — LLM 1회 통합
- [ ] 테스트: `test_orchestrator_single_llm.py`
- [ ] 구현: `_analyze_horea()` 제거, `macro_summary`/`horea_items` 파라미터 추가

### 2-5. report_synthesizer.md 프롬프트 개선
- [ ] macro_summary 섹션 추가
- [ ] horea_items 섹션 추가
- [ ] top_n 기본값 5 반영

## Phase 2.5: SOLID Review
- [ ] SRP / OCP / DIP 점검
- [ ] Zero Hardcoding 확인
- [ ] 에러 처리 점검

## Phase 3: Documentation
- [ ] issues.md
- [ ] result.md
- [ ] history.md 업데이트

## Phase 4: Release
- [ ] 단위 테스트 전체 통과
- [ ] result.md E2E 면제 기록 (화면 변경 없음)
- [ ] master 머지
