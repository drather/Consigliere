# System Workflows Registry

**Status:** Active
**Last Updated:** 2026-02-20

This registry tracks all automated routines, background tasks, and n8n workflows that the user has explicitly requested the AI to create or manage. The LLM must consult this file to understand the active context of system automations and avoid duplicating work.

## Active Routines

| Routine ID | Area | Workflow Name | Trigger / Schedule | Description | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `WR-001` | System | (Example) Daily Sync | 08:00 KST | Test entry for registry initialization. | Active |

## Suspended / Hidden Routines

| Routine ID | Area | Workflow Name | Trigger / Schedule | Description | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| - | - | - | - | - | - |

*(Note: When a user requests a new automation, AI must generate the workflow, deploy it via MCP, and append a new line to the Active Routines table.)*
