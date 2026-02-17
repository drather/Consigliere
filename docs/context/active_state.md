# Project Consigliere: Active State
**Last Updated:** 2026-02-16
**Current Active Feature:** `real_estate_news` (docs/features/real_estate_news/)

## 📍 Current Focus
- **Goal:** Implement "Real Estate News Insight Agent".
- **Action:** Scraping Naver News, Summarizing via LLM, and Trend Analysis (RAG).
- **Branch:** `feature/real-estate-news`

## 📋 Task List (News Insight)
- [ ] **Config:** Setup Naver API credentials in `.env`.
- [ ] **Spec:** Define data flow and analysis prompt (`spec.md`).
- [ ] **Client:** Implement Naver News API Client (`src/modules/real_estate/news/client.py`).
- [ ] **Service:** Implement LLM Analysis Logic (Summary & Trend Comparison).
- [ ] **Storage:** Save Report (Markdown) + Embeddings (ChromaDB).

## ✅ Completed Tasks (Recent)
- [x] **Infrastructure:** Dockerized FastAPI Backend
- [x] **Feature:** n8n Workflow Integration
- [x] **Feature:** Real Estate Monitor (MOLIT API Integration)
