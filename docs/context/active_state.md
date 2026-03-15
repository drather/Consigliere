# Project Consigliere: Active State
**Last Updated:** 2026-03-15
**Current Active Feature:** `None (All tasks completed)`

## 📍 Current Focus
- **Status:** Maintenance & Stability
- **Current Objective:** **부동산 리포트 자금조달계획 정교화 및 고성능 모델 안정화 완료**

## 💡 Recent Context
- **completed:** 부동산 리포트 자금조달계획 산출 오류(Hallucination) 완벽 교정 및 LTV 역산 제약 조건 강제
- **completed:** 웹 검색 기반 실시간 금융 정책(LTV/DSR) 추출 모듈(`policy_fetcher.py`) 구축
- **completed:** 자가 검증(Self-Reflection) 100회 루프 및 `gemini-3.1-pro-preview` 고성능 모델 연동
- **completed:** 부부 합산 소득 반영 및 생애최초 주택구입 혜택 로직 고도화
- [x] **Maintenance: Update Real Estate Insight Report Schedule** <!-- id: 31 -->
    - Changed cron expression from `30 8 * * *` to `0 7 * * *` (07:00 KST).
    - Redeployed workflow and restarted Docker containers.
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
