# Feature Spec: Workflow Verification & Notification Layer

## Overview
This feature focuses on validating the existing real estate workflows in the upgraded n8n v2 environment and implementing a reliable notification layer to deliver results to the user via Gmail and SMS.

## Goals
1. **Verification**: Confirm that the "Real Estate Transaction Monitor" and "Real Estate News Scraping" workflows execute correctly and store data as expected.
2. **Notification Layer**: Design and implement a system to send report summaries via:
   - **Gmail** (using n8n Gmail node or SMTP)
   - **SMS** (using n8n Twilio/Infobip node or a custom script)
3. **Integration**: Ensure the core server can trigger these notifications upon successful workflow completion or on demand.

## Proposed Architecture

### Workflow Execution
- Use n8n v2 to trigger the existing JSON workflows.
- Monitor the n8n execution log and ChromaDB for data persistence.

### Notification Layer (n8n Side)
- Add a "Notification" sub-workflow or reusable nodes.
- **Gmail Node**: Authorized via OAuth2 or App Password.
- **SMS/Message Node**: Explore Twilio or Kakaotalk (if possible via API).

### Data Flow
1. n8n triggers data collection (Real Estate).
2. Data is processed/summarized by LLM (FastAPI).
3. Resulting summary is sent back to n8n to be dispatched via the Notification Layer.

## Verification Plan
1. Manual trigger of workflows via n8n UI.
2. Check `consigliere_api` logs for successful RAG/LLM processing.
3. Verify receipt of Gmail/SMS notifications.
