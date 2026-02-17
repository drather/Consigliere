# System Dashboard Progress
**Feature:** `feature/system_dashboard`
**Status:** In Progress

## Phase 1: Setup & Initialization
- [ ] **Dependency Management:** Add `streamlit`, `pandas` to `requirements.txt`.
- [ ] **Core Structure:** Create `src/dashboard/main.py` entry point.
- [ ] **UI Framework:** Implement sidebar navigation and page routing.

## Phase 2: Finance Module (`/finance`)
- [ ] **Service Layer:** Implement `FinanceService.get_monthly_ledger(year, month)` to return DataFrame.
- [ ] **UI Implementation:** Create `src/dashboard/pages/finance.py`.
- [ ] **Data Grid:** Use `st.data_editor` for editable transaction list.
- [ ] **CRUD Operations:** Implement `save_changes` callback to update Markdown files.
- [ ] **Visuals:** Add simple bar chart for category breakdown.

## Phase 3: Real Estate Module (`/real_estate`)
- [ ] **Monitor Service:** Implement `MonitorService.get_transactions(filters)` to return DataFrame.
- [ ] **UI Implementation:** Create `src/dashboard/pages/real_estate.py`.
- [ ] **Monitor Tab:** Display transaction table with filters.
- [ ] **News Service:** Implement `NewsService.get_daily_report(date)` to return Markdown content.
- [ ] **News Tab:** Render Markdown report with search functionality.

## Phase 4: Integration & Polish
- [ ] **Error Handling:** Graceful messages for missing data or API errors.
- [ ] **Caching:** Use `@st.cache_data` for expensive data loading.
- [ ] **Docker:** Add Streamlit run command to `Dockerfile` or `docker-compose.yml`.
- [ ] **Documentation:** Update `README.md` with instructions to run the dashboard.
