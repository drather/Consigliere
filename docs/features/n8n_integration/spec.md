# n8n Workflow Integration: Specification

## 🎯 Objective
Integrate the Real Estate Monitor feature with n8n to automate daily data fetching.
Instead of running a standalone Python scheduler, n8n will orchestrate the process by calling the Consigliere API.

## 🔑 Key Features
1. **API Exposure:** Expose `TransactionMonitorService` via FastAPI endpoint.
2. **Workflow Automation:** Create an n8n workflow (`workflows/real_estate_monitor.json`).
3. **Dynamic Parameters:** Workflow calculates current `YYYYMM` automatically.

## 🛠️ Architecture
- **Trigger:** n8n Schedule Trigger (Daily at 09:00).
- **Action:** n8n HTTP Request Node -> `POST http://host.docker.internal:8000/agent/real_estate/monitor/fetch`.
- **Backend:** `src/main.py` -> `TransactionMonitorService`.

## 📡 API Design
- **Endpoint:** `POST /agent/real_estate/monitor/fetch`
- **Request Body:**
  ```json
  {
    "district_code": "41135",  // Optional (Defaults to Bundang)
    "year_month": "202602"     // Optional (Defaults to current month)
  }
  ```
- **Response:**
  ```json
  {
    "status": "success",
    "fetched_count": 5,
    "saved_count": 5
  }
  ```
