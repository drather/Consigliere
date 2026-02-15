# 📜 Project History: 2026-02-15 Gemini 3 Integration & MVP

## 2026-02-15: Gemini 3 AI Integration
- **Decision:** Integrated Gemini 3 Flash Preview for advanced natural language understanding.
- **Action:** Created `LLMClient` in `src/core/llm.py` and connected it to `FinanceAgent`.
- **Implementation:** Replaced Mock logic with real AI parsing using `src/prompts/finance/parser.md`.
- **Result:** Successfully parsed complex Korean/English SMS and updated the ledger.

## 2026-02-15: Refactoring - Repository Pattern
- **Action:** Decoupled storage from logic using `LedgerRepository`.
- **Status:** Completed.

## 2026-02-15: n8n & API Connectivity
- **Action:** Established dynamic URL connectivity using environment variables.
- **Status:** 200 OK verified.
