# Project Consigliere: Active State
**Last Updated:** 2026-03-02
**Current Active Feature:** `n8n Workflow Automation`

## 📍 Current Focus
- **Status:** Completed
- **Feature:** `n8n-upgrade-v2`
- **Next:** Extending RAG capabilities for real estate or implementing "Manual Trigger/Activate" UI in the dashboard.

## 📝 Lesson Learned (2026-02-25)
- **n8n Workflow Deployment:** We attempted to deploy existing workflows programmatically via the n8n API (`POST /workflows`). The API returned a `400 Bad Request`. Further investigation is needed to correctly format the workflow JSON payload for programmatic deployment (e.g., checking if `nodes` and `connections` are wrapped correctly, or if `name` is sufficient).
- **Organization:** Moved loose `.json` files into `workflows/finance/` and `workflows/real_estate/` to keep the project clean. Updated `workflows_registry.md`.

## ✅ Completed Tasks (Recent)
- [x] **Feature: n8n Workflow Organization**
    - Created `workflows/finance/` and `workflows/real_estate/`
    - Moved existing workflows to their domain folders
    - Updated `docs/workflows_registry.md` with active workflows
- [x] **Feature:** Automation Dashboard UI
- [x] **Feature:** Workflow Automation (MCP-n8n Interface)
- [x] **Feature:** Fix `400 Bad Request` in `scripts/deploy_workflows.py` and successfully deploy the workflows.
