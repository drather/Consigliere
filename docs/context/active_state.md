# Project Consigliere: Active State
**Last Updated:** 2026-03-16
**Current Active Feature:** `None (Phase 4 SOLID Refactoring Completed)`

## 📍 Current Focus
- **Status:** Architecture Stabilization (Phase 4: SOLID & Scalability)
- **Current Objective:** **부동산 모듈 아키텍처 고도화 및 SOLID 원칙 적용 완료**

## 💡 Recent Context
- **completed:** `RealEstateAgent` God Class 해체 및 `TourService`, `InsightOrchestrator`, `RealEstatePresenter` 분리
- **completed:** `config.yaml` 기반 동적 설정 시스템 도입 (한국은행 코드, 세율 등 하드코딩 제거)
- **completed:** AI 에이전트 추상화 (`BaseAgent`) 및 플러거블 구조 확보
- **completed:** 리포트 내 출처(Citation) 클릭 가능한 Slack 링크 형식으로 자동 변환 로직 구현
- **completed:** Red Team Validator를 통한 예산 정합성 검증 루프 강화 (242만원 오차 발견 및 수정 확인)
- [x] **Maintenance: Update Real Estate Insight Report Schedule** <!-- id: 31 -->
    - Changed cron expression from `30 8 * * *` to `0 7 * * *` (07:00 KST).
    - Redeployed workflow and restarted Docker containers.
- [x] **BugFix: Resolved n8n Workflow Deployment Duplication & Inactivation** <!-- id: 32 -->
    - Fixed `AutomationService` to support workflow updates (PUT) instead of always creating new ones.
    - Added automatic activation logic to the deployment pipeline.
    - Cleaned up duplicate/inactive workflows from n8n environment.
    - Fixed `Header NoneType` bug in `AutomationService`.
## ✅ Completed Tasks (Recent)
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
