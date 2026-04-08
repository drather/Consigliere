# Progress: 부동산 인사이트 리포트 파이프라인 재설계

## Phase 1: Spec
- [x] spec.md 작성

## Phase 2: Implementation

### Step 1 — config/data 변경 (기반 작업)
- [x] `config.yaml`: scoring, report 섹션 추가
- [x] `area_intel.json`: `commute_minutes_to_samsung` → `commute_minutes` + `reference_workplace`
- [x] `preference_rules.yaml`: 하드코딩 역명 제거 + YAML parse 오류 수정 (description 따옴표)

### Step 2 — Python 엔진 구현 (TDD)
- [x] `candidate_filter.py` 테스트 작성 → 구현
- [x] `scoring.py` 테스트 작성 → 구현

### Step 3 — LLM 프롬프트 작성
- [x] `prompts/horea_analyst.md` (뉴스 → 호재 JSON, 경량)
- [x] `prompts/report_synthesizer.md` (scored 결과 → 리포트 서술)

### Step 4 — 오케스트레이터 재작성
- [x] `insight_orchestrator.py` 전면 재작성
- [x] `agents/specialized.py` 정리 (불필요 에이전트 제거)
- [x] `service.py` `_enrich_transactions()` 필드명 업데이트

### Step 5 — 통합 테스트
- [x] 전체 파이프라인 단위 테스트 (20개 신규)
- [x] 기존 테스트 회귀 확인 (207 passed)
- [x] Docker 실행 검증: `{"success": true, "tx_count": 47}`

## Phase 2.5: SOLID Review
- [x] SRP: CandidateFilter/ScoringEngine 단일 책임 분리
- [x] OCP: preference_rules.yaml YAML 기반 → 코드 수정 없이 규칙 추가/제거
- [x] DIP: InsightOrchestrator는 LLMFilterChain 인터페이스에만 의존
- [x] Zero Hardcoding: 임계값 전부 config.yaml, 역명 제거

## Phase 3: Documentation
- [x] result.md 작성
- [x] history.md 업데이트

## Phase 4: Release
- [x] master 커밋 완료 (15dde18)
- [x] preference_rules.yaml YAML bugfix 커밋
