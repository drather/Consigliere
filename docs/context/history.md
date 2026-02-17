# Project Consigliere: History
**Last Updated:** 2026-02-17
**Status:** In Progress

## 2026-02-17: System Dashboard Implementation
- **Feature:** Added Streamlit-based system dashboard (`src/dashboard/main.py`).
- **Domain:** Finance, Real Estate.
- **Architecture:** Shifted to **REST API Integration** pattern for decoupling.
- **Components:**
    - Finance Ledger: Data Grid with monthly summary.
    - Real Estate: Market Monitor (Transaction Table) and News Insights (Markdown Viewer).
- **Tech Stack:** Streamlit, Pandas, Requests, FastAPI.

## 2026-02-16: News Insight Automation
- **Feature:** n8n Workflow Integration
- **Feature:** Real Estate News Insight (Korean Report + RAG)
- **Infrastructure:** Dockerized FastAPI Backend
- **Feature:** n8n News Insight Automation

## 2026-02-15: Initial Setup
- **Infrastructure:** Project structure, Docker, and Git initialized.
- **Core:** LLM Integration (Gemini 2.5 Flash).
- **Module:** Finance Ledger (Markdown-based).
