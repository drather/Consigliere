# System Dashboard Progress
**Feature:** `feature/system_dashboard`
**Status:** In Progress

## Phase 1: Setup & Initialization
- [x] **Dependency Management:** Add `streamlit`, `pandas` to `requirements.txt`.
- [x] **Core Structure:** Create `src/dashboard/main.py` entry point.
- [x] **UI Framework:** Implement sidebar navigation and page routing.

## Phase 2: Finance Module (`/finance`)
- [x] **Service Layer:** Implement `FinanceService.get_monthly_ledger(year, month)` to return DataFrame.
- [x] **UI Implementation:** Create `src/dashboard/pages/finance.py`.
- [x] **Data Grid:** Use `st.data_editor` for editable transaction list.
- [x] **CRUD Operations:** Implement `save_changes` callback to update Markdown files. (Partial: API Ready, UI Placeholder)
- [x] **Visuals:** Add simple bar chart for category breakdown.

## Phase 3: Real Estate Module (`/real_estate`)
- [x] **Monitor Service:** Implement `MonitorService.get_transactions(filters)` to return DataFrame.
- [x] **UI Implementation:** Create `src/dashboard/pages/real_estate.py`.
- [x] **Monitor Tab:** Display transaction table with filters.
- [x] **News Service:** Implement `NewsService.get_daily_report(date)` to return Markdown content.
- [x] **News Tab:** Render Markdown report with search functionality.

## Phase 4: Integration & Polish
- [x] **Error Handling:** Graceful messages for missing data or API errors.
- [x] **Caching:** Use `@st.cache_data` for expensive data loading.
- [x] **Docker:** Add Streamlit run command to `Dockerfile` or `docker-compose.yml`. (Skipped: Not requested yet, but local run works)
- [x] **Documentation:** Update `README.md` with instructions to run the dashboard.
