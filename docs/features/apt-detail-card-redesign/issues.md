# Issues: 아파트 상세 카드 UI/UX 5건 개선

## 1. Issue 4 (실거래가 차트) — 코드 문제 아닌 worktree 마운트 불일치

- **증상**: worktree 환경에서 8501(메인 `consigliere_dashboard` 컨테이너)에 접속 시
  실거래가 `st.line_chart`/`st.dataframe`이 렌더링되지 않는 것처럼 보임.
- **원인 진단**: `consigliere_dashboard` 컨테이너는 메인 레포 `./src`를 마운트하고 있어
  worktree(`.claude/worktrees/dashboard-redesign`)의 변경사항이 반영되지 않음
  ([[feedback_worktree_live_preview]] 참조).
- **확인**: worktree 코드를 로컬 streamlit(8502)으로 직접 구동 → 차트 정상 렌더링 확인.
  → 코드 문제가 아니라 **검증 환경(마운트) 문제**임을 확정.
- **해결**: master 머지 후 `docker restart consigliere_dashboard` → 8501에서도 정상 렌더링 재확인.
- **재발 방지**: `docs/guidelines/sop.md` Phase 2 step 6에 "재기동 필요 시 진단만 하지 말고 직접 재기동" +
  worktree 마운트 예외 조항을 명문화함.

## 2. 머지 충돌 — active_state.md / history.md

- **상황**: 작업 중 master에 `c67ef2a`(전세가율/공급리스크 None 버그 수정, 2026-06-11)가
  먼저 머지되어 `docs/context/active_state.md`/`history.md`의 "최근 완료" 섹션과
  "Last Updated" 필드가 동시에 변경됨 → worktree 머지 시 두 파일 모두 충돌.
- **해결**: 두 항목을 모두 보존하되 최신순으로 재배치
  (2026-06-12 apt-detail-card-redesign → 2026-06-11 jeonse/supply-risk fix → 2026-06-10 LLM 로컬화 순),
  "Last Updated"는 2026-06-12로 통일, 머지 대기 중이던 표현("머지 대기"/"머지 필요")을
  완료형으로 수정.
- **트레이드오프**: 두 작업이 같은 컨텍스트 문서를 동시에 수정하는 구조상,
  병렬 작업 시 이런 충돌은 반복될 수 있음 — 별도 작업 단위로 분리된 "최근 완료" 섹션을
  유지하는 현재 방식이 충돌 해결을 단순하게 만들어 줌(섹션 단위 append이므로 의미 충돌 없음).

## 3. 미해결 관찰 — 학군 데이터 불일치 (범위 외)

- **증상**: `🎒 학군프리미엄` 카드의 evidence는 "학교: 8개"로 표시되나,
  `_render_school_detail()`의 라이브 API(`/dashboard/real-estate/school/{complex_code}`)는
  "반경 1km 학교 수: 0개"를 반환 (apt "한국", A40381801 기준).
- **추정 원인**: evidence의 "학교: 8개"는 `LocationScorer`가 학군프리미엄 점수 계산 시 사용한
  POI 캐시 데이터 기준이고, `_render_school_detail()`의 라이브 API는 별도의
  학교 통계 데이터소스(반경 1km 기준)를 조회 — 두 데이터소스의 집계 기준(반경/카테고리)이 다를 가능성.
- **결정**: 이번 작업은 **표시 계층 재구성**(Issue 5: 학군분석을 학군프리미엄 카드로 이동)에
  한정. 데이터 불일치 자체는 별도 조사 작업으로 분리 — `docs/context/active_state.md`의
  "최근 완료 (2026-06-12)" 섹션에 후속 관찰사항으로 기록됨.
