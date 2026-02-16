# n8n Integration Result

## 🎯 Overview
Successfully integrated Real Estate Monitor with n8n for automated daily data fetching.
The Python backend exposes an API endpoint, and n8n acts as the scheduler/orchestrator.

## 📡 API Endpoint
### Fetch & Save Transactions
- **URL:** `POST /agent/real_estate/monitor/fetch`
- **Body:**
  ```json
  {
    "district_code": "41135", // Optional (Default: Bundang-gu)
    "year_month": "202602"    // Optional (Default: Current Month)
  }
  ```
- **Response:**
  ```json
  {
    "status": "success",
    "fetched_count": 100,
    "saved_count": 100
  }
  ```

## ⚙️ n8n Workflow
- **File:** `workflows/real_estate_monitor.json`
- **Logic:**
  1. **Schedule Trigger:** Runs daily at 09:00.
  2. **Set Date:** Calculates `YYYYMM` (e.g., `202602`).
  3. **HTTP Request:** Calls the FastAPI endpoint using `host.docker.internal`.

## 🧪 Verification
- **Test:** `tests/test_n8n_integration.py`
- **Result:** Successfully triggered the API via TestClient and saved 100+ transactions to ChromaDB.
