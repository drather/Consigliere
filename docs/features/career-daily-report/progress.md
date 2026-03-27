# Progress: 커리어 Daily Report

**Branch:** `feature/career-daily-report`
**Started:** 2026-03-25

---

## Phase 0: Preparation ✅
- [x] `docs/context/active_state.md` 업데이트
- [x] 브랜치 생성: `feature/career-daily-report`
- [x] `docs/features/career-daily-report/` 디렉토리 생성

## Phase 1: Planning ✅
- [x] `spec.md` 작성
- [x] `progress.md` 작성 (이 파일)
- [x] 기획 커밋

## Phase 2: Implementation ✅

### 2-1. Foundation (데이터 모델 + 설정) ✅
- [x] `src/modules/career/models.py` — Pydantic 모델
- [x] `src/modules/career/config.py` + `config.yaml`
- [x] `src/modules/career/persona.yaml`

### 2-2. Collectors (수집 계층) ✅
- [x] `collectors/base.py` — BaseCollector
- [x] `collectors/github_trending.py` — BeautifulSoup 스크래핑
- [x] `collectors/hacker_news.py` — Firebase REST API (aiohttp)
- [x] `collectors/devto.py` — dev.to 공개 API
- [x] `collectors/wanted.py` — Wanted XHR API
- [x] `collectors/jumpit.py` — 점핏 내부 API

### 2-3. Processors (LLM 분석 계층) ✅
- [x] `src/prompts/career/job_analyst.md`
- [x] `src/prompts/career/trend_analyst.md`
- [x] `src/prompts/career/skill_gap_analyst.md`
- [x] `src/prompts/career/weekly_synthesizer.md`
- [x] `src/prompts/career/monthly_synthesizer.md`
- [x] `processors/job_analyzer.py`
- [x] `processors/trend_analyzer.py`
- [x] `processors/skill_gap_analyzer.py`
- [x] `history/tracker.py`

### 2-4. Reporters (리포트 생성 계층) ✅
- [x] `reporters/daily_reporter.py` — Markdown 일별 리포트
- [x] `reporters/weekly_reporter.py` — LLM 기반 주간 리포트
- [x] `reporters/monthly_reporter.py` — LLM 기반 월간 리포트
- [x] `presenter.py` — Markdown → Slack Block Kit

### 2-5. Service Facade ✅
- [x] `service.py` — CareerAgent (fetch_jobs, fetch_trends, generate_report, run_pipeline, generate_weekly_report, generate_monthly_report)

## Phase 3: Dashboard & API ✅

### 3-1. API ✅
- [x] `src/api/routers/career.py` — 전체 엔드포인트
- [x] `src/api/dependencies.py` — CareerAgent 등록
- [x] `src/main.py` — 라우터 등록

### 3-2. Dashboard ✅
- [x] `src/dashboard/views/career.py` — Career Streamlit 페이지 (4탭)
- [x] `src/dashboard/main.py` — Career 메뉴 추가

### 3-3. n8n 워크플로우 ✅
- [x] `workflows/career/career_daily_report.json`
- [x] `workflows/career/career_weekly_report.json`
- [x] `workflows/career/career_monthly_report.json`

## Phase 2.5: SOLID Review
- [ ] SRP/OCP/DIP 체크리스트 검토
- [ ] Zero Hardcoding 확인
- [ ] 에러 처리 확인

## Phase 4: Documentation & Review
- [ ] `issues.md` 작성
- [ ] `result.md` 작성
- [ ] `docs/context/history.md` 업데이트

## Phase 5: Release
- [ ] master 머지
- [ ] 전체 테스트 통과
- [ ] git push
