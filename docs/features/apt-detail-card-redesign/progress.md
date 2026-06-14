# Progress: 아파트 상세 카드 UI/UX 5건 개선

## Phase 1: Spec
- [x] spec.md 작성 (소급 작성, 2026-06-12)

## Phase 2: Implementation

### Issue 1 — 출퇴근 경로(transit_legs) 상세 expander 추가
- [x] `_render_commute_kpis()`에 "🚇 대중교통 경로 상세" expander 추가
- [x] `commute_summary.transit_legs`를 도보/버스/지하철 단계별로 렌더링

### Issue 2 — AI 인사이트 중복 섹션 제거
- [x] `_render_analysis_report()`에서 입지점수/출퇴근/학군 중복 표시 제거
  (이미 `📍 입지점수` 카드 패널에서 표시되는 정보)

### Issue 3 — 입지점수 카드 + 클릭형 근거 expander
- [x] `residential_results`/`investment_results`를 2열 카드 그리드로 표시
- [x] `DimensionResult.evidence`를 기본 collapsed `근거 보기` expander로 전환

### Issue 4 — 실거래가 차트 검증
- [x] `st.line_chart` + `st.dataframe` 렌더링 코드 검토 → 코드상 정상 확인
- [x] worktree(8502)에서 정상 동작 확인 (당시 8501은 mount mismatch로 미반영)
- [x] master 머지 후 8501에서 재검증 완료 (Vega 시각화 + dataframe 정상 렌더링)

### Issue 5 — 학군분석 재배치
- [x] `_render_school_detail()` 신규 함수 추가 (라이브 API `/dashboard/real-estate/school/{complex_code}`)
- [x] `🎒 학군프리미엄` 카드의 `근거 보기` 안에 학군 상세 통합
- [x] AI 인사이트의 `📚 학군 분석` 섹션 제거

### E2E 테스트
- [x] `tests/e2e/test_e2e_real_estate.py`에 SCN-21~25 추가
  - SCN-21: 출퇴근 환승 경로 상세
  - SCN-22: 입지점수 카드 그리드
  - SCN-23: 입지점수 evidence 클릭형 노출
  - SCN-24: 학군프리미엄 카드 내 학군 상세
  - SCN-25: AI 인사이트 중복 섹션 없음

### 부수 작업
- [x] `docs/guidelines/sop.md` Phase 2 step 6 — "재기동 필요 시 진단만 하지 말고 직접 재기동" + worktree 마운트 예외 조항 명문화

## Phase 2.5: SOLID Review
- [x] SRP: `_render_commute_kpis`/`_render_location_score`/`_render_school_detail`/`_render_analysis_report` 각각 단일 표시 책임으로 분리
- [x] DIP: View 계층은 `AptAnalysisReport`/`LocationScore` 데이터 구조 및 기존 dashboard API 클라이언트에만 의존, 신규 서비스/리포지토리 의존성 추가 없음
- [x] Zero Hardcoding: 신규 표시 로직에 하드코딩된 임계값/문자열 상수 없음 (기존 데이터 구조 그대로 사용)
- [x] OCP: `transit_legs` mode별 아이콘 매핑은 dict 기반으로 신규 모드 추가 시 코드 분기 추가 없이 확장 가능

## Phase 3: Documentation
- [x] `result.md` 작성 (구현결과/Playwright 검증/E2E/회귀결과)
- [x] `docs/context/active_state.md` 업데이트 (2026-06-12 항목 추가)
- [x] `docs/context/history.md` 업데이트 (2026-06-12 항목 추가)
- [x] `spec.md`/`progress.md`/`issues.md` 소급 작성 (SOP 문서 체계 정리)

## Phase 4: Release
- [x] worktree(`worktree-dashboard-redesign`)에서 구현 + 커밋 (`559b121` 외)
- [x] `master`로 머지 (`4d2405d`, active_state.md/history.md 충돌 수동 해결)
- [x] 회귀 테스트: 8 failed / 895 passed / 1 error (머지 전 worktree 베이스라인 10 failed/887 passed/1 error 대비 개선, 신규 실패 없음)
- [x] `docker restart consigliere_dashboard` → 8501에 머지 결과 반영
- [x] Playwright MCP로 8501에서 5개 이슈 전체 재검증 (apt "한국", A40381801)
- [x] worktree 삭제 (`git worktree remove --force` + `git branch -d worktree-dashboard-redesign`)
- [x] SOP 문서 체계 정리 커밋 + `git push origin master`
