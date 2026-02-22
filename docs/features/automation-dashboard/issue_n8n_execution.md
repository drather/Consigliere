# Issue: n8n External Workflow Execution Constraint

## Date
2026-02-22

## Context
During the development of the **Automation Dashboard UI**, the initial specification called for a "Run Workflow" button in the Streamlit dashboard. The intent was to allow users to manually trigger any registered n8n workflow by hitting a FastAPI endpoint (`POST /agent/automation/workflow/{id}/run`), which would in turn call the n8n public API.

## Problem Description
When testing the execution of the `Scheduled HTTP Fetch Template` (which only contains a `Schedule Trigger` node), n8n returned a `404 Not Found` or `500 Server Error` indicating that the workflow could not be started.

Detailed investigation revealed a structural limitation in the n8n Public API:
1. **No Generic Execute Endpoint:** The n8n Public API v1 does *not* provide an endpoint to arbitrarily execute a workflow by its ID using standard API Keys. 
2. **Trigger Node Requirement:** To trigger a workflow programmatically from an external source, the workflow *must* start with a **Webhook node**. The execution is then performed by making an HTTP request directly to the Webhook URL, rather than a generic n8n API endpoint.
3. **Internal API:** While the n8n UI uses an internal REST API (`/rest/workflows/{id}/run`) to execute workflows manually, this endpoint relies on internal session cookies and csrf tokens, making it unsuitable for server-to-server API Key authentication.

## Resolution (Pivot)
To avoid breaking the intended event-driven nature of n8n workflows (e.g., forcing Webhooks into pure cron-job templates), the decision was made to **abandon external programmatic execution for non-webhook workflows**.

Instead, the dashboard UI was modified:
- The `Run Workflow` action button was replaced with a `🛠️ Open in n8n Editor` link.
- Clicking the link redirects the user directly to `http://localhost:5678/workflow/{id}`.
- Users can view, test, and manually execute the workflow natively within the n8n interface, which leverages the internal authenticated session.

## Next Steps
If future requirements necessitate programmatic execution of specific tasks from the Consigliere Python backend, those specific workflows *must* be designed with an active **Webhook Node** as their starting point. The FastAPI layer would then need to be configured to store and call those specific Webhook URLs, rather than relying on the generic n8n Public API.
