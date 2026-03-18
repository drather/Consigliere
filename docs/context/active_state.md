# Project Consigliere: Active State
**Last Updated:** 2026-03-18
**Current Active Feature:** `Feature: 데이터 파이프라인 분리 및 대시보드 고도화`

## 📍 Current Focus
- **Branch:** `feature/data-pipeline-dashboard-enhancement`
- **Status:** 🟡 기획 완료, 구현 시작 전
- **Current Objective:** 실거래가·뉴스·리포트 데이터 파이프라인 분리 및 대시보드 고도화

## 💡 Recent Context
- **completed:** 기본 LLM Gemini → Claude (`claude-sonnet-4-6`) 전환
- **completed:** `ClaudeClient.generate_json` JSON 파싱 버그 2건 수정 (truncation, 경계 추출)
- **completed:** 토큰 최적화 (MAX_ITERATIONS 2, Validator 1024, 데이터 상한 축소)
- **completed:** 인사이트 리포트 E2E 테스트 성공 (Score 82, Slack 전송 확인)
- **in-progress:** 데이터 파이프라인 분리 및 대시보드 고도화 기획 완료
  - Phase 1: 리포트 저장 레이어 + Report Archive 탭
  - Phase 2: 실거래가 그리드 고도화 (날짜 필터, 50건, 정렬)
  - Phase 3: News Insight 탭 고도화 (정책 팩트, 수집 트리거)
  - Phase 4: 리포트 파이프라인 분리 (저장 데이터 우선 사용)
- [x] **Maintenance: Update Real Estate Insight Report Schedule** <!-- id: 31 -->
    - Changed cron expression from `30 8 * * *` to `0 7 * * *` (07:00 KST).
    - Redeployed workflow and restarted Docker containers.
- [x] **BugFix: Resolved n8n Workflow Deployment Duplication & Inactivation** <!-- id: 32 -->
    - Fixed `AutomationService` to support workflow updates (PUT) instead of always creating new ones.
    - Added automatic activation logic to the deployment pipeline.
    - Cleaned up duplicate/inactive workflows from n8n environment.
    - Fixed `Header NoneType` bug in `AutomationService`.
## ✅ Completed Tasks (Recent)
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
- [x] **Feature: Insight Report Delivery Fix** <!-- id: 28 -->
    - Integrated `insight_report_workflow.json` into deployment script.
    - Added data fallback notes for empty transactions.
- [x] **Feature: Real Estate Daily Summary (Slack)** <!-- id: 26 -->
    - Created daily summary API with data deduplication.
    - Integrated Naver Map links and Slack Block Kit.
    - Deployed n8n template for 08:00 KST schedule.
- [x] **Feature: Scheduled Real Estate News (Slack)** <!-- id: 25 -->
    - Integrated `/notify/slack` with n8n at 06:00 KST schedule.
- [x] **Feature: Workflow Verification & Notifications (Real Estate)** <!-- id: 24 -->
- [x] **Feature: n8n Version Upgrade (v1.72.0 -> v2.9.4)** <!-- id: 23 -->
- [x] **Feature: n8n Workflow Organization**
    - Created `workflows/finance/` and `workflows/real_estate/`
    - Moved existing workflows to their domain folders
    - Updated `docs/workflows_registry.md` with active workflows
- [x] **Feature:** Automation Dashboard UI
- [x] **Feature:** Workflow Automation (MCP-n8n Interface)
- [x] **Feature:** Fix `400 Bad Request` in `scripts/deploy_workflows.py` and successfully deploy the workflows.
