# Real Estate Domain MVP Specification (v1.0)
**Date:** 2026-02-15
**Author:** Consigliere Team

## 1. Overview
This feature allows the user to log and retrieve real estate tour reports (임장 리포트) using natural language.
The system transforms unstructured tour notes into structured data for search and analysis.

## 2. User Stories
### 2.1 Logging a Tour
- **User:** "I just visited [Complex Name]. The price is [Price]. It has [Pros/Cons]. There is an elementary school inside."
- **System:** Parses the input into structured data (Price, Location, Features) and stores it in the vector database for semantic search.

### 2.2 Retrieving Information
- **User:** "Show me complexes under 1 billion won with an elementary school inside."
- **System:** Queries the database using metadata filters (price <= 1000000000 AND has_school=true) and semantic similarity. Returns a summary of matching reports.

## 3. Data Schema (ChromaDB)
We use a **Hybrid Schema** where core fields are metadata for filtering, and the full text is embedded for semantic search.

| Field | Type | Description | Example |
|---|---|---|---|
| `id` | String | Unique ID (Complex Name) | "dandae_e_pyeonhan" |
| `document` | String | Full tour note text | "The hill is steep, but the school is close..." |
| `metadata.price` | Integer | Transaction price | 1000000000 |
| `metadata.complex_name` | String | Name of the complex | "단대오거리 e편한세상" |
| `metadata.has_school` | Boolean | Is there a school inside? | true |
| `metadata.pros` | String | List of pros (comma separated) | "School, Park" |
| `metadata.cons` | String | List of cons (comma separated) | "Hill, Bus" |

## 4. Architecture
- **Storage:** ChromaDB (Local Vector Store)
  - Stores embeddings of tour notes.
  - Stores structured metadata for filtering.
- **AI Model:** Gemini 3 Flash Preview
  - **Extraction:** Extracts structured data from user input.
  - **Query Generation:** Converts user questions into ChromaDB filters.
- **API:**
  - `POST /agent/real_estate/report`: Create/Update report.
  - `GET /agent/real_estate/search`: Semantic search with filters.

## 5. Implementation Plan
1. **Setup ChromaDB:** Add service to `docker-compose.yml`.
2. **Define Models:** Pydantic models for Report and SearchQuery.
3. **Implement Repository:** `ChromaRealEstateRepository`.
4. **Implement Agent:** `RealEstateAgent` with Gemini integration.
5. **Integration Test:** Verify storage and retrieval.
