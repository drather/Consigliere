# n8n News Insight Result

## 🎯 Overview
Successfully implemented and automated the **Real Estate News Insight Agent**.
It fetches news daily, analyzes trends using Gemini (RAG), and generates a Korean markdown report with source links.

## 📡 API Endpoint
- **URL:** `POST /agent/real_estate/news/analyze`
- **Body:** `{"keywords": "..."}` (Optional)
- **Response:**
  ```json
  {
    "status": "success",
    "report_date": "2026-02-16",
    "report_content": "# 📰 Real Estate News Report..."
  }
  ```

## 📝 Report Format
The generated report includes:
1. **Key Topics:** Top 5 keywords.
2. **Daily Summary:** 3-sentence summary in Korean.
3. **Trend Insight:** Comparison with previous reports (RAG).
4. **References:** List of top 10 source articles with links.

## ⚙️ n8n Workflow
- **File:** `workflows/real_estate_news.json`
- **Schedule:** Daily at 08:00 KST.
- **Action:** Triggers Python backend to scrape, analyze, and save news.

## 🧪 Verification
- **Test:** `tests/test_n8n_news.py` verified the API end-to-end flow.
- **Output:** Verified Korean output and reference links.
