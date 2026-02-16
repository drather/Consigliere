# 📜 Project History (Recent)
For full history, see `docs/context/archive/`.

## 2026-02-15: Project Management & Quality Control
- **Protocol:** Adopted Troubleshooting Log (`docs/troubleshooting.md`) to capture lessons learned.
- **Workflow:** Initialized Git repository and established Gitflow (Feature Branch -> Merge).
- **Action:** Committed initial codebase (Finance MVP) to `master`.

## 2026-02-15: Gemini 3 AI Integration & MVP Success
- **Action:** Successfully integrated `gemini-2.5-flash` to parse transaction text and real estate notes, significantly improving latency.
- **Verification:** End-to-End test passed (Text -> AI -> Ledger Update).

## 2026-02-16: Real Estate MVP & Architectural Refactoring
- **Feature:** Implemented Real Estate Reporting MVP using ChromaDB (Vector Search) and Gemini 2.5.
- **Refactor:** Migrated codebase to a **Domain-Driven Modular Architecture** (`src/modules/finance`, `src/modules/real_estate`).
- **Structure:** Centralized tests in `tests/` and common assets in `src/common/`.
- **Infrastructure:** Validated Docker Compose setup for n8n and ChromaDB.

## 2026-02-16: Real Estate Monitor (API Integration)
- **Feature:** Implemented `RealEstateTransaction` monitor using MOLIT Open API.
- **Data:** Successfully fetched and parsed 100+ live transaction records (XML -> Pydantic).
- **Storage:** Integrated with ChromaDB for semantic search of transaction history.
- **Issue Resolved:** Fixed `401 Unauthorized` by supporting Hex-formatted Service Keys.

## 2026-02-16: n8n Integration & Automation
- **Feature:** Exposed `RealEstateMonitor` via FastAPI endpoint (`/agent/real_estate/monitor/fetch`).
- **Workflow:** Created n8n workflow for daily scheduling of real estate data collection.
- **Verification:** Successfully triggered API via n8n-compatible request and saved transactions.