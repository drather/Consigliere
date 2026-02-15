# Real Estate Report: Implementation Result

## 🎯 Overview
The "Real Estate Report" feature enables users to log unstructured property tour notes and search them using natural language queries.
It leverages Gemini AI for metadata extraction and ChromaDB for semantic search.

## 🛠️ Architecture
- **Language Model:** `gemini-2.5-flash` (Structured Output: JSON)
- **Vector Database:** `ChromaDB` (via Docker, port 8001)
- **Framework:** FastAPI (REST API)
- **Module Path:** `src/modules/real_estate/`

## 📡 API Endpoints

### 1. Log Tour Report
- **URL:** `POST /agent/real_estate/report`
- **Body:** `{"text": "Your tour note here..."}`
- **Process:**
  1. **User Input:** Unstructured text describing a property.
  2. **AI Parsing:** Extracts `complex_name`, `price`, `pros`, `cons`, `has_elementary_school`.
  3. **Embedding:** Text is embedded by ChromaDB automatically.
  4. **Storage:** Upserted into `real_estate_reports` collection.
- **Response:** JSON with confirmation and extracted metadata.

### 2. Search Reports
- **URL:** `POST /agent/real_estate/search`
- **Body:** `{"text": "Natural language query..."}`
- **Process:**
  1. **AI Query Generation:** Translates question into `{"query_text": "...", "where": {...}}`.
  2. **Vector Search:** Queries ChromaDB using cosine similarity + metadata filtering (`$and`).
  3. **Formatting:** Returns top N matching reports.

## 🧪 Verification
- **Integration Test:** `tests/test_real_estate.py`
- **Results:**
  - **Latency:** Average < 3 seconds per request.
  - **Accuracy:** Successfully filters by price (`$lte`) and boolean flags (`has_elementary_school`).
  - **Filter Logic:** Verified `$and` operator for complex queries.

## 📂 Key Files
- `src/modules/real_estate/service.py`: Business logic & AI orchestration.
- `src/modules/real_estate/repository.py`: ChromaDB interactions.
- `src/modules/real_estate/models.py`: Pydantic schemas.
- `src/modules/real_estate/prompts/`: `parser.md`, `searcher.md`.
