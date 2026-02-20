# Feature Spec: Workflow Automation (n8n Integration via MCP)

## 1. Goal
Improve the LLM's ability to seamlessly generate and deploy n8n workflows based on user requests, closing the gap between chat instructions and background automation.

## 2. Background
Currently, the LLM attempts to generate complex n8n JSON from scratch, which is prone to errors, hallucinations, and lacks structural consistency. The system also lacks a straightforward method for the LLM to programmatically push these workflow updates into the running n8n container.

## 3. Architecture & Requirements
1.  **Workflow Template Library (`src/n8n/templates/`)**
    *   Store "Golden" JSON templates representing common automation patterns (e.g., Scheduled API Fetching, HTTP Webhook Receivers).
    *   The LLM will use these as base schemas rather than raw generation.
2.  **MCP Integration (`src/modules/automation/`)**
    *   Create a new automation service/module.
    *   Expose specific Python functions to the LLM (Gemini) that interact with the n8n REST API.
    *   Capabilities: `deploy_workflow`, `list_workflows`, `activate_workflow`.
3.  **Runtime Registry (`docs/workflows_registry.md`)**
    *   A system log tracking active routines specifically requested by the user, providing the LLM context of currently executing background tasks.
4.  **SOP & Instructions Update (`.gemini_instructions.md`)**
    *   Add explicit instructions guiding the LLM to utilize the templates and MCP tools when requested to create automations.

## 4. Data Models (Examples)
*   **Workflow Template:** Standard n8n JSON exports.
*   **Registry Entry:** Markdown table row indicating `Task Name | Status | Schedule/Trigger | Description`.

## 5. Scope
*   Phase 1: Setup registries, instructions, and template directories. Create 1-2 base templates.
*   Phase 2: Implement FastAPI MCP routes to interact with the n8n container API.
*   Phase 3: Test LLM generation using the new system.
