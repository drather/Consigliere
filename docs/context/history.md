# Project Consigliere: History
**Last Updated:** 2026-03-04
**Status:** Completed

## 2026-03-04: Workflow Verification & Notification Layer
- **Verification**: Confirmed `Real Estate Transaction Monitor` and `Real Estate News Insight` workflows execute successfully in n8n v2.9.4.
- **Implementation**: Appended Gmail (SMTP) and SMS (HTTP Request) notification nodes to core workflows.
- **Documentation**: Created `result.md` and moved verification screenshots to permanent feature directory.

## 2026-03-03: n8n Version Upgrade (v1.72.0 -> v2.9.4)
- **Upgrade**: Successfully finalized database migration and UI upgrade.
- **Optimization**: Reclaimed 3.8GB Docker space and implemented `.dockerignore` to prevent disk exhaustion.
- **Verification**: Passed E2E automation API tests on the upgraded engine.

## 2026-03-02: Workflow Deployment Fix & Containerization
- **Feature (workflow-automation):** 
    - Resolved `400 Bad Request` in n8n deployment by aligning JSON schemas with n8n v1 API requirements (adding `settings`, stripping `style`/`pinData`).
    - Configured `.env` with `N8N_API_KEY` for secure and authorized access to n8n Public API.
    - Updated `AutomationService` and `deploy_workflows.py` to use environment variables and improved error logging.
- **Infrastructure:** 
    - Containerized the Streamlit dashboard as `consigliere_dashboard` to resolve architecture mismatch issues (ARM64 vs x86_64) on Apple Silicon.
    - Fixed internal container networking by using Docker service names (`consigliere_n8n`) for API-n8n communication.

## 2026-02-22: Automation Dashboard & Workflow E2E
- **Feature (workflow-automation):** Completed the E2E integration test for the FastAPI -> n8n pipeline using an API Key.
- **Feature (automation-dashboard):** 
    - Added the `Automation` tab to the Streamlit UI.
    - Integrated `DashboardClient` to fetch workflows.
    - Documented an issue (`docs/features/automation-dashboard/issue_n8n_execution.md`) regarding n8n's structural limitation on external programmatic execution. Pivoted functionality to open workflows in the n8n Visual Editor instead.

## 2026-02-20: Architecture Review & Workflow Automation (Phase 1)
- **Review:** Analyzed Local vs Production architecture, identifying bottlenecks in n8n workflow generation.
- **Process Update:** Updated SOP (`.gemini_instructions.md`) to enforce n8n JSON templates and MCP integrations.
- **Feature (workflow-automation):** 
    - Created `docs/workflows_registry.md` to track active user automations.
    - Initialized `src/n8n/templates/` with `http_fetch_schedule.json`.
    - Created feature branch and spec.

## 2026-02-17: System Dashboard Implementation
- **Feature:** Added Streamlit-based system dashboard (`src/dashboard/main.py`).
- **Domain:** Finance, Real Estate.
- **Architecture:** Shifted to **REST API Integration** pattern for decoupling.
- **Components:**
    - Finance Ledger: Data Grid with monthly summary.
    - Real Estate: Market Monitor (Transaction Table) and News Insights (Markdown Viewer).
- **Tech Stack:** Streamlit, Pandas, Requests, FastAPI.

## 2026-02-16: News Insight Automation
- **Feature:** n8n Workflow Integration
- **Feature:** Real Estate News Insight (Korean Report + RAG)
- **Infrastructure:** Dockerized FastAPI Backend
- **Feature:** n8n News Insight Automation

## 2026-02-15: Initial Setup
- **Infrastructure:** Project structure, Docker, and Git initialized.
- **Core:** LLM Integration (Gemini 2.5 Flash).
- **Module:** Finance Ledger (Markdown-based).
