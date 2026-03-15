# Software Development Guidelines

## 1. Core Principles
- **Documentation-Driven:** 모든 기술 문서(Spec, Progress, Result 등)는 **한글(Korean)**로 작성합니다. No code without a spec. No merge without a result doc.
- **Modular Architecture:** All domain logic resides in `src/modules/{domain}/`.
- **Environment Agnostic:** Code must run in Local/Docker/Prod environments.

## 2. LLM Model Usage
- Use `gemini-2.5-flash` in `src/core/llm.py` and all prompt frontmatter by default, unless otherwise specified by the environment (e.g., Claude).

## 3. Workflow Automation (n8n & MCP)
When the user requests a new automated background task:
1. **Never write raw n8n JSON from scratch.** It leads to broken schemas.
2. **Use Templates:** Look for base configurations in `src/workflows/` or `src/n8n/templates/`. Modify ONLY specific fields (Endpoint URLs, Cron Schedules, Credentials).
3. **Use MCP Tools:** Use programmatic tools (like `deploy_workflows.py`) to push JSON into the live container.
4. **Update Registry:** Append the new routine to `docs/workflows_registry.md`.
