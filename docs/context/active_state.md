# Project Consigliere: Active State
**Last Updated:** 2026-03-25
**Current Active Feature:** 커리어 Daily Report 신규 모듈 구현

## 📍 Current Focus
- **Branch:** `feature/career-daily-report`
- **Status:** 🔧 Phase 1 (기획문서 작성 중)

## 💡 Recent Context
- **in_progress:** 커리어 Daily Report 모듈 신규 개발
  - 데이터 소스: GitHub Trending, Hacker News, Dev.to, Wanted, 점핏
  - 리포트: 일별(.md) + 주간(매주 금) + 월간(매월 말일) 자동 생성
  - 딜리버리: 매일 09:00 Slack 자동 발송 (n8n 크론)
  - 대시보드: Streamlit Career 메뉴 추가 (페르소나 편집 + 리포트 뷰어)
- **completed:** Job1 aiohttp 비동기 전환 완료
- **completed:** `json-repair` 도입으로 LLM 출력 파싱 안정성 극대화
- **completed:** Insight Pipeline (Job 1-3) 중복 실행 방지 로직 구현
- **blocked:** 없음

## 🔜 다음 작업 로드맵

### 현재 — 커리어 Daily Report (feature/career-daily-report)
- Phase 1: 기획문서 (spec.md, progress.md) 작성 ← 지금
- Phase 2: 데이터 수집기 구현 (5개 collector)
- Phase 3: LLM 처리기 + 리포트 생성기
- Phase 4: 대시보드 Career 메뉴
- Phase 5: API + n8n 워크플로우 (일별/주간/월간)

### 다음 — Job4 부동산 전략 리포트 고도화
- 현재 리포트 품질 개선 (점수 안정화, 예산 준수, 단지 추천 정확도)

## ✅ Completed Tasks (Recent)
- [x] **Maintenance: Insight Pipeline Optimization & LLM Robustness** <!-- id: 35 -->
    - Added state-aware execution to `RealEstateAgent.run_insight_pipeline` to skip already completed jobs.
    - Integrated `json-repair` for resilient JSON parsing from LLM outputs.
    - Refactored `llm.py` to use `_parse_json_robust` utility.
    - Adjusted persona priority weights for more balanced evaluation.
- [x] **Feature: 데이터 파라이플라인 aiohttp 전환** <!-- id: 34 -->
    - Job1 aiohttp 비동기 전환 완료 및 master 머지.
- [x] **Maintenance: Update Real Estate Insight Report Schedule** <!-- id: 31 -->
    - Changed cron expression from `30 8 * * *` to `0 7 * * *` (07:00 KST).
    - Redeployed workflow and restarted Docker containers.
- [x] **BugFix: Resolved n8n Workflow Deployment Duplication & Inactivation** <!-- id: 32 -->
    - Fixed `AutomationService` to support workflow updates (PUT) instead of always creating new ones.
    - Added automatic activation logic to the deployment pipeline.
    - Cleaned up duplicate/inactive workflows from n8n environment.
    - Fixed `Header NoneType` bug in `AutomationService`.
- [x] **Maintenance: Gemini Model Update** <!-- id: 33 -->
    - Updated default Gemini model to `gemini-3.1-flash-lite-preview`.
    - Refactored `GeminiClient` to support `GEMINI_MODEL` environment variable.
    - Updated `.env` and `.env.example` with the new model configuration.
- [x] **Feature: Funding Plan Logic Correction & Logic Guard** <!-- id: 29 -->
    - Implemented LTV-back-calculation constraint to prevent simple budget summation.
    - Added 100-iteration self-reflection loop with scoring and feedback.
    - Integrated `duckduckgo-search` for real-time LTV/DSR policy context.
- [x] **Feature: Spousal Income & First-time Buyer Logic** <!-- id: 30 -->
    - Added `is_first_time_buyer` and `spouse_income` handling in `persona.yaml`.
    - Enforced conservative budget selection between LTV and DSR limits.
    - Corrected date logic for 2026 context.
    - Expanded data collection to 9+ metropolitan districts (10+ txs).
    - Integrated 2026 Financial Policy (Stress DSR Phase 3) check.
    - Resolved Slack Block Kit formatting issues (`invalid_blocks_format`).
