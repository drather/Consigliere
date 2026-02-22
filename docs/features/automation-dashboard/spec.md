# Feature Specification: Automation Dashboard

## 1. Goal
Add a dedicated "Automation" tab to the existing Streamlit dashboard to allow users to view, manage, and manually execute n8n workflows that are integrated with the Consigliere system.

## 2. Background
In the previous feature `workflow-automation`, the API layer (`src/main.py` and `AutomationService`) was successfully integrated with the containerized n8n instance. This provided the backend capability to deploy and activate workflows. However, there is currently no user interface for the user to see which workflows are active or to manually trigger them.

## 3. Product Features
1. **Workflow Listing:** Query `GET /agent/automation/workflows` and display the results in a readable format (e.g., Table or Expandable Cards) on the dashboard.
2. **Workflow Execution:** Provide a UI button to manually trigger a workflow by its ID using `POST /agent/automation/workflow/{workflow_id}/run`.

## 4. Architecture / Integration Points
- **Frontend (`src/dashboard/`):**
  - Modify `main.py` sidebar to include "⚙️ Automation".
  - Create `views/automation.py` for the UI layout.
  - Extend `api_client.py` to communicate with the new FastApi endpoint.
- **Backend (`src/main.py`):**
  - Add the manual run endpoint `POST /agent/automation/workflow/{workflow_id}/run`.

## 5. Scope
- Only implementing listing and manual execution of workflows.
- Dynamic creation or editing of workflow nodes inside the dashboard is out of scope (n8n's native UI handles this).

## 6. Verification
- Manual testing using a browser automation tool (Playwright/Browser Subagent) to interact with the Streamlit UI.
- Verify that clicking "Run" on the UI successfully triggers the workflow in the backend.
