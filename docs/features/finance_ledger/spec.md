# Finance Ledger MVP Specification (v1.0)
**Date:** 2026-02-15
**Status:** Completed

## 1. Overview
This feature enables the user to record daily expenses (Ledger) using natural language via SMS or chat.
The system automatically parses unstructured text into structured financial transactions and updates a Markdown-based ledger file.

## 2. User Stories
### 2.1 Logging Expenses
- **User:** "Just paid 12,000 won for Lunch at Kimbap Heaven"
- **System:** Extracts date (Today), Amount (12,000), Category (Food), Item (Kimbap Heaven Lunch).
- **Outcome:** Appends a new row to `Finance/Ledger_YYYY_MM.md` and updates the monthly total.

## 3. Data Schema (Markdown Table)
The data is stored in a structured Markdown table within daily files.

| Date | Category | Item | Amount |
|---|---|---|---|
| YYYY-MM-DD | String | String | Integer |

**File Path:** `data/Finance/Ledger_{YYYY}_{MM}.md`

## 4. Architecture
- **Input:** n8n Workflow (HTTP Trigger)
- **Parser:** Gemini 3 Flash Preview (via `LLMClient`)
- **Storage:** Local Filesystem (via `MarkdownLedgerRepository`)
- **API:** `POST /agent/finance/add_transaction`

## 5. Implementation Details
- **Repository Pattern:** Decoupled storage logic from business logic.
- **Prompt Engineering:** Use `src/prompts/finance/parser.md` for structured extraction.
- **Environment Agnostic:** Dynamic URL configuration via `API_BASE_URL`.
