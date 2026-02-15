# Finance Ledger MVP Result
**Status:** Completed
**Verification Date:** 2026-02-15

## 1. How to Use
Use the n8n Workflow **"Finance MVP (Manual Test)"** to simulate an SMS trigger.
- **Input:** "Taxi cost 8,500 won."
- **Output:**
  - n8n Response: `200 OK`
  - Ledger File (`data/Finance/Ledger_YYYY_MM.md`): New transaction added.

## 2. API Reference
### POST /agent/finance/add_transaction
Add a new expense transaction.

**Request:**
```json
{
  "text": "Taxi cost 8,500 won."
}
```

**Response:**
```json
{
  "response": "✅ Transaction Saved via Gemini.\n- Added: Taxi (8,500 KRW) [Transport]\n- Monthly Total: 8,500 KRW (1 transactions)"
}
```

## 3. Screenshots (Logs)
- **FastAPI Server Log:**
  `INFO: 127.0.0.1:52278 - "POST /agent/finance/add_transaction HTTP/1.1" 200 OK`
- **Markdown File Content:**
  `| 2026-02-15 | Transport | Taxi | 8,500 |`
