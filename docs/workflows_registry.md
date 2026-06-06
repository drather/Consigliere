# System Workflows Registry

**Status:** Active
**Last Updated:** 2026-06-06

This registry tracks all automated routines, background tasks, and n8n workflows that the user has explicitly requested the AI to create or manage. The LLM must consult this file to understand the active context of system automations and avoid duplicating work.

## Active Routines

| Routine ID | Area        | Workflow Name                   | Trigger / Schedule | Description                                                    | Status | N8N ID             |
| :--------- | :---------- | :------------------------------ | :----------------- | :------------------------------------------------------------- | :----- | :----------------- |
| `WR-001`   | System      | (Example) Daily Sync            | 08:00 KST          | Test entry for registry initialization.                        | Active | -                  |
| `WR-002`   | Finance     | Finance MVP                     | Manual             | Parses text/SMS into finance backend API                       | Active | `vki9zjZffGuXajT8` |
| `WR-003`   | Real Estate | Real Estate Transaction Monitor | **06:30 KST**      | Fetches and saves real estate transactions via API (Slack 제거) | Active | `fRuluv52mhU17CR4` |
| `WR-004`   | Real Estate | Real Estate News Insight        | 06:00 KST          | News analysis and save only — Slack disabled (Daily Report로 통합) | Active | `KI3Arb7F8lZiqtlK` |
| `WR-007`   | Real Estate | Jeonse & Supply Weekly Collect  | Sunday 05:00 KST   | 전세/공급 데이터 주 1회 자동 수집 (실패 시 Slack)              | Active | `EbHtr48rdQJn1Emn` |
| `WR-NEW`   | System      | Daily Report (08:00 KST)        | 08:00 KST          | 데일리 리포트 생성 + Slack 1회 발송 (모든 인사이트 통합)       | Active | -                  |

## Suspended / Hidden Routines

| Routine ID | Area | Workflow Name | Trigger / Schedule | Description | Status |
| :--------- | :--- | :------------ | :----------------- | :---------- | :----- |
| `WR-005`   | Real Estate | Real Estate Monitor (Slack)              | (비활성)  | Daily Report로 통합됨 | Suspended |
| `WR-006`   | Real Estate | Real Estate Comprehensive Insight Report | (비활성)  | Daily Report로 통합됨 | Suspended |

*(Note: When a user requests a new automation, AI must generate the workflow, deploy it via MCP, and append a new line to the Active Routines table.)*
