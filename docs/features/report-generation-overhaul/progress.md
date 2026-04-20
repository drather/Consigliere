# Progress: 부동산 리포트 생성 전면 점검

**Branch:** `feature/report-generation-overhaul`

## Phase 1: Planning
- [x] spec.md 작성
- [x] progress.md 생성
- [x] 피처 브랜치 생성

## Phase 2: Implementation (TDD)

### 2-1. calculator.py — MacroRepository 주담대금리 주입
- [x] 테스트: `test_calculator_with_macro_rate.py`
- [x] 구현: `calculate_budget()` macro_rate 파라미터 추가

### 2-2. service.py — ChromaDB → tx_repo 전환
- [x] 테스트: `test_generate_report_sqlite.py`
- [x] 구현: `generate_report()` tx_repo 쿼리 + 가격 ±10% 필터

### 2-3. service.py — apt_master_repo enrich 수정
- [x] 테스트: `test_enrich_apt_master_repo.py`
- [x] 구현: `_enrich_transactions()` → `apt_master_repo.get_by_name()` 사용

### 2-4. insight_orchestrator.py — LLM 1회 통합
- [x] 테스트: `test_orchestrator_single_llm.py`
- [x] 구현: `_analyze_horea()` 제거, `macro_summary`/`horea_items` 파라미터 추가

### 2-5. report_synthesizer.md 프롬프트 개선
- [x] macro_summary 섹션 추가
- [x] horea_items 섹션 추가
- [x] top_n 기본값 5 반영

## Phase 2.5: SOLID Review
- [x] SRP / OCP / DIP 점검
- [x] Zero Hardcoding 확인
- [x] 에러 처리 점검

## Phase 3: Documentation
- [x] issues.md (SOLID review + 결정사항)
- [ ] result.md
- [ ] history.md 업데이트

## Phase 3.5: 실행 결과 점검 (2026-04-19 Job4 첫 실행)
- [x] Job4 단독 실행 성공
- [x] 주담대금리 2.83% 실데이터 반영 확인
- [x] 점수 변별력 확보 확인 (77.5 / 57.5 / 51.1 / 31.1점)
- [x] LLM 1회 호출 확인 (synthesizer in=2,396 out=1,987)
- [x] 토큰 비용 확인: Job4 1회 = **+1원** (387→388원)
- [x] ISSUE-01: 중복 단지 제거 — _make_dedup_key + _normalize_name
- [x] ISSUE-02: 세대수 미확인 단지 보강 — _lookup_apt_details normalize + ScoringEngine 중립값
- [x] ISSUE-03: 가격상승가능성 전체 10점 — horea_validator LLM + _area_matches + 중립값 50

## Phase 3.6: LLM 할루시네이션 수정 (2026-04-20)
- [x] ISSUE-04: LLM 점수 재계산 — `_format_candidates_for_llm()` 도입, 점수를 텍스트로 pre-format
- [x] ISSUE-05: LLM 가격 단위 오변환 — 가격을 만원 단위(90,000만원)로 표기
- [x] ISSUE-06: nearest_stations dict raw 노출 — name/line 필드 추출 텍스트 변환
- [x] ISSUE-07: phantom 후보 생성 — 후보 수 명시 헤더("총 N개 단지") 추가
- [x] 최종 검증: Job4 재실행 — 3개 단지, 점수/가격/역 정보 모두 정확

## Phase 4: Release
- [x] 단위 테스트 전체 통과 (178 passed)
- [x] result.md 작성 + E2E 면제 기록 (화면 변경 없음)
- [ ] master 머지
