# n8n News Insight Integration: Specification

## 🎯 Objective
Automate the daily generation of Real Estate News Reports using n8n.

## 📡 API Design
- **Endpoint:** `POST /agent/real_estate/news/analyze`
- **Body:** (Optional)
  ```json
  {
    "keywords": "부동산 정책 아파트 분양" // Override default search keywords
  }
  ```
- **Response:**
  ```json
  {
    "status": "success",
    "report_date": "2026-02-16",
    "report_content": "...markdown content..."
  }
  ```

## ⚙️ Workflow Design
- **Trigger:** Schedule (Every day at 08:00 KST).
- **Action:** HTTP Request to `consigliere_api`.
- **Output:** Returns the generated markdown report (can be connected to Email/Slack later).
