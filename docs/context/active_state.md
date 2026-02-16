# Project Consigliere: Active State
**Last Updated:** 2026-02-16
**Current Active Feature:** `n8n_integration` (docs/features/n8n_integration/)

## 📍 Current Focus
- Completed "Real Estate Monitor" (API Client & Service).
- **Starting:** Integrating Real Estate Monitor with **n8n Workflow**.
- **Goal:** Expose Monitor as API endpoint and create n8n scheduler.

## 📋 Task List (n8n Integration)
- [ ] Feature Specification (`docs/features/n8n_integration/spec.md`)
- [ ] **Backend:** Expose `TransactionMonitorService` via FastAPI (`src/main.py`).
- [ ] **Workflow:** Design n8n workflow (`workflows/real_estate_monitor.json`).
- [ ] **Test:** Verify n8n -> FastAPI communication (using curl as proxy).

## ✅ Completed Tasks (Recent)
- [x] **Feature:** Real Estate Monitor (MOLIT API Integration)
- [x] **Refactoring:** Modular Architecture
- [x] **Feature:** Real Estate Report (ChromaDB)
