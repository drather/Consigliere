# Progress: 부동산 인사이트 리포트 파이프라인 재설계

## Phase 1: Spec
- [x] spec.md 작성

## Phase 2: Implementation

### Step 1 — config/data 변경 (기반 작업)
- [ ] `config.yaml`: scoring, report 섹션 추가
- [ ] `area_intel.json`: `commute_minutes_to_samsung` → `commute_minutes` + `reference_workplace`
- [ ] `preference_rules.yaml`: 하드코딩 역명 제거

### Step 2 — Python 엔진 구현 (TDD)
- [ ] `candidate_filter.py` 테스트 작성 → 구현
- [ ] `scoring.py` 테스트 작성 → 구현

### Step 3 — LLM 프롬프트 작성
- [ ] `prompts/horea_analyst.md` (뉴스 → 호재 JSON, 경량)
- [ ] `prompts/report_synthesizer.md` (scored 결과 → 리포트 서술)

### Step 4 — 오케스트레이터 재작성
- [ ] `insight_orchestrator.py` 전면 재작성
- [ ] `agents/specialized.py` 정리 (불필요 에이전트 제거)
- [ ] `service.py` `_enrich_transactions()` 필드명 업데이트

### Step 5 — 통합 테스트
- [ ] 전체 파이프라인 단위 테스트
- [ ] 기존 테스트 회귀 확인

## Phase 2.5: SOLID Review
- [ ] SRP/OCP/DIP 체크
- [ ] Zero Hardcoding 체크

## Phase 3: Documentation
- [ ] issues.md
- [ ] result.md
- [ ] history.md 업데이트

## Phase 4: Release
- [ ] master 머지 + push
