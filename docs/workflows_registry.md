# System Workflows Registry

**Status:** Active
**Last Updated:** 2026-02-20

This registry tracks all automated routines, background tasks, and n8n workflows that the user has explicitly requested the AI to create or manage. The LLM must consult this file to understand the active context of system automations and avoid duplicating work.

## Active Routines

| Routine ID | Area        | Workflow Name                   | Trigger / Schedule | Description                                                    | Status | N8N ID             |
| :--------- | :---------- | :------------------------------ | :----------------- | :------------------------------------------------------------- | :----- | :----------------- |
| `WR-001`   | System      | (Example) Daily Sync            | 08:00 KST          | Test entry for registry initialization.                        | Active | -                  |
| `WR-002`   | Finance     | Finance MVP                     | Manual             | Parses text/SMS into finance backend API                       | Active | `vki9zjZffGuXajT8` |
| `WR-003`   | Real Estate | Real Estate Transaction Monitor | 09:00 KST          | Fetches and saves real estate transactions via API             | Active | `fRuluv52mhU17CR4` |
| `WR-004`   | Real Estate | Real Estate News Insight        | 06:00 KST          | Analyzes news and sends insights to Slack (Email/SMS disabled) | Active | `KI3Arb7F8lZiqtlK` |
| `WR-005`   | Real Estate | Real Estate Monitor (Slack)     | 08:00 KST          | Fetches daily summary API and sends Slack Block Kit      | Active | -                  |

## Suspended / Hidden Routines

| Routine ID | Area | Workflow Name | Trigger / Schedule | Description | Status |
| :--------- | :--- | :------------ | :----------------- | :---------- | :----- |
| -          | -    | -             | -                  | -           | -      |

*(Note: When a user requests a new automation, AI must generate the workflow, deploy it via MCP, and append a new line to the Active Routines table.)*
