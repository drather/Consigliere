# Project Consigliere: Active State
**Last Updated:** 2026-03-28
**Current Active Feature:** 커뮤니티 트렌드 조사 모듈 개발

## 📍 Current Focus
- **Branch:** `feature/community-trend-collector`
- **Status:** 🔧 Phase 2 (Collector TDD 진행 중)

## 💡 Recent Context
- **in_progress:** 커뮤니티 트렌드 조사 모듈 개발 (career 모듈 확장)
  - 데이터 소스: Reddit (asyncpraw), Twitter/Nitter 스크래핑, 클리앙, 디씨인사이드
  - LLM 분석: CommunityAnalyzer → CommunityTrendAnalysis
  - Daily Report에 🌐 커뮤니티 트렌드 섹션 추가
  - 수집 실패(Nitter 불안정 등) 시 ⚠️ 경고 표기
- **completed:** 커리어 Daily Report 모듈 (Collector 5종, Processor 3종, Reporter 3종, 테스트 42개)
- **completed:** Job4 부동산 리포트 고도화 + 토큰 최적화
- **completed:** Job1 aiohttp 비동기 전환
- **blocked:** 없음

## 🔜 다음 작업 로드맵

### 현재 — 커뮤니티 트렌드 조사 모듈 (feature/community-trend-collector)
- Phase 1: 모델 TDD ← 완료
- Phase 2: Collector TDD (4개) ← 진행 중
- Phase 3: CommunityAnalyzer TDD
- Phase 4: DailyReporter 커뮤니티 섹션 추가
- Phase 5: CareerAgent 통합

### 다음 — Job4 LLM 호출 최적화
- 부동산 리포트 LLM 호출 과다 문제 수정 (배치 처리, 프롬프트 통합)

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
