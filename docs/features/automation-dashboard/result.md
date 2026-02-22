# Result: Automation Dashboard Feature

## 1. Overview
The Automation Dashboard feature provides a native UI integrated into the Streamlit `Consigliere Dashboard` allowing users to view and manage background n8n automation workflows. 

## 2. Changes Made
- Added a new `GET /agent/automation/workflows` consumer in the `api_client.py`.
- Designed `src/dashboard/views/automation.py` containing Expandable Workflow Cards.
- Routed the new page inside `src/dashboard/main.py`.

## 3. Constraint Pivot: Manual Workflow Execution
Initially, the specification stated that the dashboard should contain a "Run Workflow" button to trigger arbitrary workflows. 

However, during integration testing, the following **Core Limitation of n8n** was encountered:
- A `500 Internal Server Error` -> `404 Not Found` occurred when trying to trigger the `Scheduled HTTP Fetch Template` by its ID using standard n8n API logic. 
- n8n strictly disallows external APIs from manually executing workflows unless they explicitly define a **Webhook Node** or a **Manual Trigger** node with an execution session. 
- You cannot generically force-run a "Scheduled" or event-based trigger from outside.

### 4. Resolution
To maintain a high-quality user experience without breaking n8n's event mechanics, the `Run Workflow` action was swapped for a `🛠️ Open in n8n Editor` direct link button. This enables users to see the workflows in Consigliere and seamlessly jump to the n8n Visual Canvas (`localhost:5678/workflow/{id}`) to test or modify parameters directly in the IDE.

## 5. Verification
- Confirmed the dashboard renders successfully with the new `numpy` and `streamlit` binaries built for Apple Silicon arm64.
- Confirmed the Browser subagent could parse and navigate the workflow cards.
