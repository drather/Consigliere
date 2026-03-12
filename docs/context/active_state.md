# Project Consigliere: Active State
**Last Updated:** 2026-03-10
**Current Active Feature:** `Real Estate Monitor Enhancement (Done)`

## 📍 Current Focus
- **Status:** Done
- **Current Objective:** **부동산 종합 인사이트 리포트** 구축 <!-- id: 27 -->
    - 실거래가, 부동산 정책, 지역 개발 소식을 카테고리별로 통합 및 요약하여 제공.

## ✅ Completed Tasks (Recent)
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
