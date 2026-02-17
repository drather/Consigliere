# Real Estate News Insight: Specification

## 🎯 Objective
Automate the collection and analysis of real estate news to identify market trends and policy shifts.
By comparing daily news with historical data (RAG), the system provides insights like "Policy Stance Changed" or "Supply Concerns Rising".

## 🔑 Key Features
1. **News Collection:** Fetch latest news via Naver Open API.
2. **AI Analysis (Gemini):**
   - **Summarization:** Condense 20+ articles into key topics.
   - **Trend Comparison:** Compare today's news with last week's embedded reports (RAG).
3. **Daily Report:** Generate a Markdown report (`YYYY-MM-DD_News.md`).
4. **Knowledge Base:** Store insights in ChromaDB for future reference.

## 🛠️ Architecture
- **Module:** `src/modules/real_estate/news/`
- **Components:**
  - `client.py`: Naver News API Client.
  - `service.py`: Orchestrates Fetch -> RAG -> LLM -> Save.
  - `prompts/news_analyst.md`: Prompt for summarization and trend analysis.
- **Data Source:** Naver Search API (`/v1/search/news.json`)

## 📝 Data Flow
1. **Fetch:** Get 20 news items (Title, Link, Description).
2. **Context Retrieval:** Query ChromaDB for "Real Estate Policy Trend" (Last 7 days).
3. **LLM Process:**
   - Input: Today's News + Historical Context.
   - Output: JSON (Summary, Keywords, Trend_Change_Flag, Insight).
4. **Save:**
   - **File:** `data/real_estate/news/{date}.md`
   - **DB:** Upsert Insight text to ChromaDB.

## ⚠️ Configuration
- `NAVER_CLIENT_ID` & `NAVER_CLIENT_SECRET` required in `.env`.
