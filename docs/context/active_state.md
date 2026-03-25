# Project Consigliere: Active State
**Last Updated:** 2026-03-24
**Current Active Feature:** 없음 (Pipeline Optimization & LLM Robustness 완료)

## 📍 Current Focus
- **Branch:** `master`
- **Status:** ✅ Insight Pipeline 최적화 (Skip logic) 및 LLM 파싱 안정성 강화 완료

## 💡 Recent Context
- **completed:** Job1 aiohttp 비동기 전환 완료
- **completed:** `json-repair` 도입으로 LLM 출력 파싱 안정성 극대화 (Gemini/Claude 공통)
- **completed:** Insight Pipeline (Job 1-3) 중복 실행 방지 로직 구현 (`.done` 및 파일 체크)
- **completed:** 부동산 평가 가중치(`persona.yaml`) 재조정
- **blocked:** 없음

## 🔜 다음 작업 로드맵

### 1순위 — Job4 부동산 전략 리포트 고도화 (진행 예정)
- 현재 리포트 품질 개선 (점수 안정화, 예산 준수, 단지 추천 정확도)
- 페르소나 기반 개인화 강화 (interest_areas 매핑 고도화)
- 거시경제 + 뉴스 + 실거래 데이터 통합 인사이트 품질 향상

### 2순위 — 커리어 Daily Report (신규 모듈)
- 개인화된 커리어 관련 일일 리포트 기능
- 구직 동향, 기술 트렌드, 채용 공고 요약 등 포함 예정
- 설계 필요 (spec 없음)

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
