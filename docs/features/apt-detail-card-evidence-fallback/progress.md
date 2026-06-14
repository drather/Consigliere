# Progress: 입지점수 카드 "근거 보기" 빈 항목 표시 수정

## Phase 1: Spec
- [x] spec.md 작성 (배경/원인/목표/범위, 2026-06-14)

## Phase 2: Implementation (TDD)
- [x] 실패하는 테스트 작성: `tests/test_real_estate_evidence_fallback.py`
  - `test_empty_evidence_shows_fallback_caption`
  - `test_non_empty_evidence_still_renders_normally`
- [x] Red 확인: `1 failed, 1 passed` (fallback 캡션 미구현으로 실패)
- [x] `_render_score_dimension_grid()` 수정 (`src/dashboard/views/real_estate.py:193`)
  - evidence가 비어있고 학군프리미엄이 아닌 경우 "데이터 없음 (POI 캐시 미수집)" 캡션 표시
  - 학군프리미엄은 기존과 동일하게 `_render_school_detail()` 항상 호출
- [x] Green 확인: `2 passed`

## Phase 2.5: SOLID Review
- [x] SRP: fallback 표시 로직은 기존 `_render_score_dimension_grid()`의 단일 책임(카드별 근거 표시) 내에서 분기 추가, 신규 함수/클래스 불필요
- [x] DIP: View 계층 수정만, 신규 서비스/리포지토리 의존성 없음
- [x] Zero Hardcoding: fallback 문자열 1개("데이터 없음 (POI 캐시 미수집)")는 UI 표시 텍스트로, 데이터 모델/설정값과 무관 — 하드코딩 회피 대상 아님
- [x] OCP: 기존 evidence 순회 로직 변경 없이 `elif not evidence` 분기만 추가 — 신규 dimension 추가 시 코드 변경 불필요

## Phase 3: Verification
- [x] Playwright MCP — "문정시영"(A13820007, 버그 재현 단지): 5개 카드(🚇교통/🏫교육환경/🛒생활인프라/🏥의료/🌳자연환경)에
      "데이터 없음 (POI 캐시 미수집)" 표시 확인, 🎒학군프리미엄은 `_render_school_detail()` 정상 표시
- [x] Playwright MCP — "한국"(A40381801, 회귀 확인 단지): 11개 카드 전부 기존 evidence 내용 그대로 정상 렌더링 (회귀 없음)
- [x] `docker restart consigliere_dashboard` → 8501에 변경사항 반영 확인

## Phase 4: Documentation & Release
- [x] 전체 회귀 테스트: `8 failed, 897 passed, 1 error` (머지 전 baseline `8 failed/895 passed/1 error`와 동일 실패 집합, 신규 테스트 2건 추가로 passed +2, 신규 실패 없음)
- [x] `result.md` 작성
- [x] `docs/context/active_state.md` / `docs/context/history.md` 업데이트 (2026-06-14 항목 추가)
- [x] 커밋 + `git push origin master`
