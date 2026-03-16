# Project Consigliere: History
**Last Updated:** 2026-03-16
**Status:** Active

## 2026-03-16: Phase 4 SOLID Refactoring & Scalability
- **Feature (architecture-refactor):** 부동산 모듈의 God Class 해체 및 SOLID 원칙 기반의 확장성 있는 아키텍처로 리팩토링.
- **Implementation:**
    - **Service Decomposition:** `RealEstateAgent`를 `TourService`, `InsightOrchestrator`, `RealEstatePresenter`로 분해.
    - **Dynamic Config:** `config.yaml` 도입으로 한국은행 코드 및 금융 파라미터 하드코딩 제거.
    - **Agent Abstraction:** `BaseAgent` 추상화를 통한 다중 에이전트(Macro, Analyst, Validator) 협업 구조 완성.
    - **Citation Link:** 리포트 내부 팩트 ID를 Slack 클릭 가능 링크(`<URL|[뉴스: 제목]>`)로 변환하는 레이어 추가.
- **Verification:** Red Team Validator(전략 검증관) 루프를 통해 예산 오차(242만원)를 잡아내어 수정 리포트 생성 성공.
- **Documentation:** `docs/features/solid-refactoring/result.md` 성과 보고서 작성 완료.

## 2026-03-12: Comprehensive Real Estate Insight Report & Persona Action Plan
- **Feature (insight-report):** 실거래가, 뉴스, 정책을 통합한 종합 리포트 및 사용자 페르소나 기반 액션 플랜 기능 구현.
- **Implementation:**
    - `RealEstateAgent.generate_insight_report()`: 실거래 데이터 그룹화, 뉴스 분류, LLM 인사이트 추출.
    - **Persona Integration:** `persona.yaml`을 통한 사용자 맞춤형 재무/거주 전략(Action Plan) 및 금융 용어 해설 제공.
    - **News Categorization:** `NewsService` 확장으로 정책 및 지역 개발 소스 정형화.
- **Automation:** n8n 워크플로우(`WR-006`)를 통한 08:30 KST 자동 발송.
- **Documentation:** `doc/features/real-estate-insight-report/` 내 Spec, Progress, Result, Walkthrough 완비.

## 2026-03-10: Real Estate Monitor Enhancement (Slack)
- **Feature (real-estate-monitor):** 고도화된 부동산 실거래가 데일리 요약 기능 구현.
- **Implementation:** 
    - `RealEstateAgent.get_daily_summary` API를 통한 데이터 중복 제거 및 요약 로직 구축.
    - Naver Map 연동 및 Slack Block Kit을 활용한 풍부한 알림 포맷 적용.
    - n8n 스케줄링 워크플로우(`WR-005`) 생성 및 등록.
- **Documentation:** `spec.md`, `result.md` 작성 및 `workflows_registry.md` 업데이트.

## 2026-03-08: Scheduled Slack Reports & Docs Update
- **Feature (real-estate-news):** Automated Daily Real Estate News at 06:00 KST via Slack.
- **Refinement:** Fixed n8n expression syntax (added `=` prefix) and resolved variable field mismatch (`summary` -> `report_content`).
- **Verification:** Successfully triggered E2E workflow; confirmed rich markdown summary delivery to Slack.
- **Documentation:** Updated `README.md`, `sw_architecture.md`, and `infrastructure.md` to reflect the new notification infrastructure.
- **Implementation**: Created `Sender` abstract interface and `SlackSender` implementation.
- **Verification**: Successfully sent trial notifications from local FastAPI to mobile Slack.
- **Infrastructure**: Established Cloudflare Tunnel for local dev; initiated Slack "challenge" verify troubleshooting.

## 2026-03-04: Workflow Verification & Notification Layer
- **Verification**: Confirmed `Real Estate Transaction Monitor` and `Real Estate News Insight` workflows execute successfully in n8n v2.9.4.
- **Implementation**: Appended Gmail (SMTP) and SMS (HTTP Request) notification nodes to core workflows.
- **Documentation**: Created `result.md` and moved verification screenshots to permanent feature directory.

## 2026-03-03: n8n Version Upgrade (v1.72.0 -> v2.9.4)
- **Upgrade**: Successfully finalized database migration and UI upgrade.
- **Optimization**: Reclaimed 3.8GB Docker space and implemented `.dockerignore` to prevent disk exhaustion.
- **Verification**: Passed E2E automation API tests on the upgraded engine.

## 2026-03-02: Workflow Deployment Fix & Containerization
- **Feature (workflow-automation):** 
    - Resolved `400 Bad Request` in n8n deployment by aligning JSON schemas with n8n v1 API requirements (adding `settings`, stripping `style`/`pinData`).
    - Configured `.env` with `N8N_API_KEY` for secure and authorized access to n8n Public API.
    - Updated `AutomationService` and `deploy_workflows.py` to use environment variables and improved error logging.
- **Infrastructure:** 
    - Containerized the Streamlit dashboard as `consigliere_dashboard` to resolve architecture mismatch issues (ARM64 vs x86_64) on Apple Silicon.
    - Fixed internal container networking by using Docker service names (`consigliere_n8n`) for API-n8n communication.

## 2026-02-22: Automation Dashboard & Workflow E2E
- **Feature (workflow-automation):** Completed the E2E integration test for the FastAPI -> n8n pipeline using an API Key.
- **Feature (automation-dashboard):** 
    - Added the `Automation` tab to the Streamlit UI.
    - Integrated `DashboardClient` to fetch workflows.
    - Documented an issue (`docs/features/automation-dashboard/issue_n8n_execution.md`) regarding n8n's structural limitation on external programmatic execution. Pivoted functionality to open workflows in the n8n Visual Editor instead.

## 2026-02-20: Architecture Review & Workflow Automation (Phase 1)
- **Review:** Analyzed Local vs Production architecture, identifying bottlenecks in n8n workflow generation.
- **Process Update:** Updated SOP (`.gemini_instructions.md`) to enforce n8n JSON templates and MCP integrations.
- **Feature (workflow-automation):** 
    - Created `docs/workflows_registry.md` to track active user automations.
    - Initialized `src/n8n/templates/` with `http_fetch_schedule.json`.
    - Created feature branch and spec.

## 2026-02-17: System Dashboard Implementation
- **Feature:** Added Streamlit-based system dashboard (`src/dashboard/main.py`).
- **Domain:** Finance, Real Estate.
- **Architecture:** Shifted to **REST API Integration** pattern for decoupling.
- **Components:**
    - Finance Ledger: Data Grid with monthly summary.
    - Real Estate: Market Monitor (Transaction Table) and News Insights (Markdown Viewer).
- **Tech Stack:** Streamlit, Pandas, Requests, FastAPI.

## 2026-02-16: News Insight Automation
- **Feature:** n8n Workflow Integration
- **Feature:** Real Estate News Insight (Korean Report + RAG)
- **Infrastructure:** Dockerized FastAPI Backend
- **Feature:** n8n News Insight Automation

## 2026-02-15: Initial Setup
- **Infrastructure:** Project structure, Docker, and Git initialized.
- **Core:** LLM Integration (Gemini 2.5 Flash).
- **Module:** Finance Ledger (Markdown-based).
