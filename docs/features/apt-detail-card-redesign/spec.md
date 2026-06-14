# Spec: 아파트 상세 카드 UI/UX 5건 개선

**Feature:** `apt-detail-card-redesign`
**Branch:** `worktree-dashboard-redesign` (머지 완료, 삭제됨)
**작성일:** 2026-06-12
**참조:** `docs/master_plan.md` §2 (Client App: Streamlit 대시보드)

---

## 배경

`docs/guidelines/architecture.md`의 레이어드 아키텍처상 `dashboard/views/real_estate.py`는 표시 계층(View)으로,
`AptAnalysisReport` / `LocationScore` 데이터를 그대로 렌더링한다. 사용자가 Playwright MCP로
`localhost:8501` 아파트 탐색 탭의 상세 카드 패널을 직접 점검하면서, 데이터는 정상이지만
표시 방식에 5가지 가독성/중복 문제가 있음을 확인했다.

---

## 목표

`_render_apt_detail_cards()` 및 관련 렌더 함수의 화면 구조를 정리한다. 데이터 모델/API는 변경하지 않고
**표시 계층만** 재구성한다.

1. **출퇴근 경로 노출** — `commute_summary.transit_legs`를 활용해 대중교통 환승 경로(도보/버스/지하철)를
   상세 expander로 노출
2. **중복 제거** — `📍 입지점수` 카드 패널에 이미 표시되는 정보(입지점수/출퇴근/학군)를
   `🤖 AI 인사이트`(`_render_analysis_report`)에서 다시 렌더링하지 않음
3. **카드+클릭형 근거** — `LocationScore.residential_results`/`investment_results`(각 6/5개 dimension)를
   2열 카드 그리드로 표시하고, `evidence` 리스트는 기본 collapsed `근거 보기` expander 안에만 노출
4. **실거래가 차트 검증** — `st.line_chart` + `st.dataframe` 렌더링이 정상 동작하는지 확인
   (코드 문제인지 배포/캐싱 문제인지 진단)
5. **학군분석 재배치** — `📚 학군 분석`(AI 인사이트 내, `/dashboard/real-estate/school/{complex_code}` 라이브 조회)을
   투자점수의 `🎒 학군프리미엄` 카드의 `근거 보기` 안으로 이동

---

## 데이터 모델 (변경 없음, 참조용)

- `LocationScore` (`src/modules/real_estate/location/location_scorer.py`)
  - `residential_total`, `residential_results: list[DimensionResult]` (6개: 🚇교통/🏫교육환경/🛒생활인프라/🏥의료/🌳자연환경/⚠️혐오시설)
  - `investment_total`, `investment_results: list[DimensionResult]` (5개: 📈가격상승가능성/🛍️상업활성도/💧환금성/🎒학군프리미엄/⚠️혐오시설)
  - `DimensionResult.{label, score, evidence: list[str]}`
- `AptAnalysisReport.commute_summary` (`src/modules/real_estate/apt_analysis/models.py`)
  - `{"transit": int, "car": int, "walking": int, "transit_legs": [{"mode": "WALK"|"BUS"|"SUBWAY"|"RAIL", "duration_minutes": int, "route": str, "stop_count": int}]}`
- `/dashboard/real-estate/school/{complex_code}` (라이브 API)
  - `{"complex_code", "school_kind", "nearby_school_count", "avg_students_per_class", "avg_students_per_teacher", "score", "collected_at", "message"}`

---

## 영향 범위

- `src/dashboard/views/real_estate.py`만 수정 (View 계층, 신규 함수 2개 추가)
- API/Repository/Service 계층 변경 없음 → DI 등록/계층 규칙 영향 없음
- 화면 변경 → E2E 시나리오 추가 필수 (SOP Phase 2 step 5)
