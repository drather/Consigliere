# Project Consigliere: History
**Last Updated:** 2026-03-22

## 2026-03-22: Job1 aiohttp 비동기 전환 + 데이터 라이프사이클
- **Feature (job1-aiohttp-migration):** ThreadPoolExecutor 방식의 OOM/429 문제를 근본 해결. aiohttp + asyncio.Semaphore(2)로 전환, 7일 필터 + 1년 삭제 정책 추가.
- **결과:** 71개 구 999건 수집, OOM·429 없음, 약 3분 30초 완주.
- **변경 파일:** `requirements.txt`, `monitor/service.py`, `models.py`, `repository.py`, `service.py`
- **주요 변경:**
    - `_parse_item_to_transaction` 모듈 레벨 함수 추출 (async 파이프라인 재사용)
    - `models.py` `deal_date_int` 필드 추가 (숫자 범위 필터용)
    - `repository.py` `save_transactions_batch`, `delete_old_transactions` 추가
    - `service.py` `fetch_transactions` async 재구현 + `_async_fetch_all`, `_fetch_one_district` 헬퍼
    - 수집 범위 7일 이내로 제한 (API 신고 지연 특성 반영)

**Last Updated:** 2026-03-18
**Status:** Active

## 2026-03-18: 데이터 파이프라인 분리 및 대시보드 고도화
- **Feature (data-pipeline-dashboard-enhancement):** 실거래가·뉴스·거시경제·리포트 파이프라인을 4개 독립 Job으로 분리하고, 수도권 전체(71개 지구) 자동 수집 및 대시보드 전면 개편.
- **Implementation:**
    - 4개 Job API (`/jobs/real-estate/fetch-transactions|news|macro|generate-report`) 및 파이프라인 엔드포인트 신설.
    - `service.py` Job 메서드 분리: `fetch_transactions()` (수도권 71개 지구 순회), `fetch_news()`, `fetch_macro_data()` (JSON 파일 저장), `generate_report()` (저장 데이터 우선 사용), `run_insight_pipeline()` (Job1~4+Slack).
    - `config.yaml` districts 9→71개 확장 (서울 25구 + 경기 38시군구 + 인천 8구).
    - `repository.py` 필터 확장: apt_name 부분 검색, price_min/price_max 범위, limit 500.
    - `bok_service.py`: BOK 10개월 시계열 조회 (`fetch_macro_history()`).
    - `llm.py`: `generate_json()` 배열(`[...]`) 응답 파싱 버그 수정.
    - `docker-compose.yml`: ChromaDB 볼륨 경로 `/chroma/chroma` → `/data` 수정 (데이터 휘발 버그).
- **Dashboard:**
    - Market Monitor: 시/구 selectbox (71개), 아파트명 검색, 금액 범위 슬라이더↔숫자 입력 동기화, 페이지네이션 (최대 500건).
    - Insight 탭: 거시경제 카드+시계열 차트, 뉴스 리포트, 정책 팩트(ChromaDB 검색).
    - Report Archive: 저장 리포트 목록+상세, mrkdwn→Markdown 변환 렌더링.
- **Automation:** n8n 비활성 워크플로우 삭제 후 4개 스케줄 워크플로우 신규 등록 (05:00 실거래가·뉴스, 05:00 월1회 거시경제, 06:00 리포트+Slack).
- **Verification:** 각 Job 독립 실행 확인, ChromaDB 데이터 영속성 확인, 대시보드 전 탭 E2E 확인.
- **Documentation:** `docs/features/data-pipeline-dashboard-enhancement/` 내 spec, progress, result 완비.

## 2026-03-18: Claude LLM 전환 및 토큰 최적화
- **Feature (claude-migration-token-optimization):** 기본 LLM을 Gemini에서 Claude(`claude-sonnet-4-6`)로 전환, JSON 파싱 버그 2건 수정, 토큰 사용량 최적화.
- **Implementation:**
    - `LLMFactory` 기본값 `"gemini"` → `"claude"` 변경, `.env.example` Claude 설정 추가.
    - `ClaudeClient.generate_json` 버그 수정: `max_tokens` 4096 → 8192, JSON 경계 추출 로직(`find('{')`~`rfind('}'`) 추가.
    - `generate_json(max_tokens=)` 파라미터화로 호출처별 토큰 제어 가능.
    - 토큰 최적화: `MAX_ITERATIONS` 3→2, Validator `max_tokens` 1024, `daily_txs` 15건, `policy_facts` 3건.
- **Verification:** E2E 테스트 성공 — 인사이트 리포트 HTTP 200 (Score 82), Slack 전송 `ok: true` 확인.
- **Documentation:** `docs/features/claude-migration-token-optimization/` 내 spec, progress, result, issues 완비.

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
