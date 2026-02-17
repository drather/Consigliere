# Project Consigliere: Active State
**Last Updated:** 2026-02-16
**Current Active Feature:** `n8n_news_insight` (docs/features/n8n_news_insight/)

## 📍 Current Focus
- **Goal:** Automate "Real Estate News Insight" via n8n.
- **Action:** Expose NewsService as API endpoint and create scheduler workflow.
- **Branch:** `feature/n8n-news-insight`

## 📋 Task List (n8n Integration)
- [ ] **Spec:** Define API and Workflow (`spec.md`).
- [ ] **Backend:** Add `POST /agent/real_estate/news/analyze` to `src/main.py`.
- [ ] **Workflow:** Create `workflows/real_estate_news.json`.
- [ ] **Test:** Verify automated execution.

## ✅ Completed Tasks (Recent)
- [x] **Feature:** Real Estate News Insight (Naver API + RAG)
- [x] **Infrastructure:** Dockerized FastAPI Backend
- [x] **Feature:** n8n Workflow Integration
