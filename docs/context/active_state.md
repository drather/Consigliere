# Project Consigliere: Active State
**Last Updated:** 2026-02-17
**Current Active Feature:** `System Dashboard`

## 📍 Current Focus
- **Status:** In Progress
- **Feature:** `workflow-automation` (Phase 1/3)
- **Active Task:** Implementing MCP integration basics.
- **Next:** Implement explicit MCP tools via FastAPI to hit n8n APIs.

## 📝 Lesson Learned (2026-02-18)
- **Infrastructure:** The project runs on a **Docker Compose** architecture (`api`, `n8n`, `chromadb`).
- **Critical Mistake:** Attempted to run `run_server.py` locally, causing port conflicts (8000) and data path issues.
- **Resolution:** Established `docs/architecture.md` and mandated `docker-compose up -d` for backend services.
- **Environment:** Always check `docker-compose ps` before assuming backend state.

## ✅ Completed Tasks (Recent)
- [x] **Feature:** System Dashboard (Monitoring Only)
    - Finance Ledger Grid View (Read-Only)
    - Real Estate News & Market Monitor
- [x] **Infrastructure:** Documented System Architecture (`docs/architecture.md`)
- [x] **Fix:** Resolved `numpy` ARM64 compatibility issues.
- [x] **Infrastructure:** Dockerized FastAPI Backend & n8n Workflow Integration
