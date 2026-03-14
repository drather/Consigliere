# Project Consigliere: Active State
**Last Updated:** 2026-03-14
**Current Active Feature:** `Architecture Refactoring (Planning)`

## 📍 Current Focus
- **Status:** Planning
- **Current Objective:** **시스템 구조 및 로깅 체계 리팩토링 기획**
  - 라우터 분리, 의존성 주입(DI) 적용, 로깅 중앙화 및 테스트 전략 수립.

## ✅ Completed Tasks (Recent)
- [x] **Feature: Real Estate Insight Report (Advanced)** <!-- id: 27 -->
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
