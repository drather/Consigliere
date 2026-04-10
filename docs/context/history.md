# Project Consigliere: History
**Last Updated:** 2026-04-10

## 2026-04-10: 아파트 마스터 데이터 활용 고도화 (1-A + 1-B)
- **BugFix:** `_enrich_transactions()` early return 버그 수정
  - `area_intel={}` 시 마스터 DB 조회 블록이 실행되지 않아 `household_count=0`, `constructor=""` 상태로 전파되던 문제 해결
  - 마스터 조회 로직을 루프 최상단으로 이동 → area_intel 유무와 무관하게 항상 실행
  - `_score_liquidity()` 이제 실제 세대수 기반으로 동작 (기존: 항상 LOW 20점)
- **Feature:** `ApartmentMasterRepository.search()` + `get_distinct_constructors()` 추가
  - 동적 WHERE 조건 조합, 최대 500건 반환
- **Feature:** Streamlit `🏗️ 단지 검색` 탭 추가 (tab5)
  - 아파트명/지구/세대수/건설사/준공연도 복합 필터, 단지 상세 expander
- **Prompt:** `report_synthesizer.md` — 건설사·준공연도 서술 지시 추가
- 신규 테스트 29개 (scoring_liquidity 8 + enrich_constructor 7 + apt_master_search 14), 전체 271 passed

## 2026-04-09: 아파트 마스터 DB 구축 — 실제 API 검증 완료
- **Fix + Data:** 실제 API 키 승인 후 연동 테스트 → 3가지 버그 발견·수정
  - API URL 수정: `AptListService3/getSigunguAptList3` (항상 0건) → `getTotalAptList3`
  - API URL 수정: `AtclService/getAphusBassInfoV4` (500) → `AptBasisInfoServiceV4`
  - 필드 매핑 수정: `hhldCnt`→`hoCnt`, `bdNum`→`kaptDongCnt`, `useAprDay`→`kaptUsedate`
  - `fetch_complex_list`: 전체 목록 in-memory 캐시 후 bjdCode prefix 필터링으로 재설계
  - `build_initial`: `progress.json` 실시간 기록, 재시작 이어받기 지원 추가
  - `scripts/build_apartment_master.py`: 수도권 초기 구축 실행 스크립트 신설
  - 수도권(서울+인천+경기) **9,261개 단지** 실제 수집 완료 (세대수 0건 58개, 99% 완전 데이터)
  - 21 passed (테스트 +1개)

## 2026-04-09: 아파트 마스터 DB 구축 — 설계
- **Feature (apartment-master-db):** 공동주택 공공 API로 수도권 아파트 마스터 정보 수집·저장
  - `ApartmentMasterClient`: 공동주택 단지목록 + 기본정보 2개 공공 API
  - `ApartmentMasterRepository`: SQLite CRUD (geocoder.py 패턴, PK=district_code__apt_name)
  - `ApartmentMasterService`: 전수 구축(build_initial) + 온디맨드 보완(get_or_fetch)
  - `_enrich_transactions()` 확장: household_count, building_count, constructor, approved_date 자동 부착
  - `POST /jobs/real-estate/build-apartment-master` 신규 엔드포인트
  - 신규 테스트 20개, 241 passed

## 2026-04-08: 부동산 인사이트 리포트 E2E 검증 및 버그픽스
- **BugFix (real-estate-insight-redesign):** E2E 파이프라인 검증 중 2건 버그 발견·수정
  - `generate_insight_report()`: 구버전 orchestrator 파라미터(`macro_dict` 등) → `generate_report()` 위임으로 교체
  - `_handle_min_household_count`: `household_count` 미존재 시 전 후보 탈락 → 데이터 없으면 통과
  - 수도권 71개 지구 E2E 파이프라인 완전 동작 확인 (1,536건 수집, Slack 전송)
  - 20 passed (CandidateFilter 7 + ScoringEngine 13)

## 2026-04-08: 부동산 인사이트 리포트 파이프라인 재설계
- **Refactor (real-estate-insight-redesign):** LLM→Python 역할 분리, Zero Hardcoding 완성
  - CandidateFilter: preference_rules를 Python 코드로 실행 (LLM 프롬프트 전달 방식 폐지)
  - ScoringEngine: 5개 기준 가중치 점수 Python 수식으로 계산
  - InsightOrchestrator: 전면 재작성 (LLM 최대 2회, Validator/Retry 제거)
  - commute_minutes_to_samsung → commute_minutes + reference_workplace
  - config.yaml scoring/report 섹션 추가 (임계값 전부 config화)
  - 신규 테스트 20개, 207 passed

## 2026-04-08: Career 커뮤니티 소스 분류 config화
- **Refactor (career-community-source-config):** `_REDDIT_SOURCES` 등 frozenset 하드코딩 제거, config.yaml category 기반 동적 분류
  - `config.yaml` community_sources 4개 소스에 `category` 필드 추가
  - `config.py` `get_community_source_categories()` 신규 메서드
  - `service.py` frozenset 3개 → `defaultdict` 동적 분류로 교체 (OCP 충족)
  - 179 passed (신규 테스트 2개 포함)

## 2026-04-08: Finance LLM Pipeline 통합
- **Refactor (finance-llm-pipeline):** `FinanceAgent`의 `LLMClient()` → `build_llm_pipeline()` 교체
  - `service.py` import 교체 1줄, `parser.md` frontmatter 추가 (task_type/cache_boundary/ttl)
  - SemanticCache, TokenLog, ModelRouting(extraction→haiku) 혜택 적용
  - 178 passed, pre-existing 1개 실패 무변화

## 2026-04-08: BaseAnalyzer use_cache 분기 정리
- **Cleanup (baseanalyzer-use-cache-cleanup):** `_call_llm(use_cache)` dead code 제거, PromptCacheFilter 단일 경로로 통합
  - `base.py` use_cache 파라미터 및 if 분기 제거 (9줄 → 5줄)
  - `test_llm_harness.py` TestBaseAnalyzerUseCacheFlag 2개 케이스 제거
  - 188 passed, pre-existing 1개 실패 무변화

## 2026-04-06: 시스템 전체 리뷰 및 개선 계획 수립
- **Planning (career-solid-refactor):** Career SOLID 장기 개선 spec/progress 문서 작성 및 master 머지
  - Processor Protocol 4종 (ISP/DIP), CareerPathResolver (SRP), CareerDataStore (SRP), CareerAgent DI 개선
  - 구현 미착수, `docs/features/career_solid_refactor/` 참조
- **시스템 전체 리뷰 — 신규 발견 이슈 및 개선 제안 (로드맵 반영):**
  - Finance LLM Pipeline 미통합: `service.py`가 `LLMClient()` 직접 사용, `build_llm_pipeline()` 교체 필요
  - Career 커뮤니티 소스 분류 하드코딩: `_REDDIT_SOURCES` 등이 service.py에 고정, config.yaml `category` 필드로 이동 필요
  - n8n 워크플로우 실패 피드백 없음: 실행 히스토리 미저장, 실패 알림 부재
  - 부동산 ↔ 커리어 소득 연계 분석 기회: 두 모듈을 연결하는 통합 인사이트 가능
  - Career 스킬갭 트렌드 예측: gap_score 히스토리 활용한 예측/달성 시점 계산 미구현
  - Streamlit 파이프라인 실행 블로킹: 장시간 요청 시 UI 멈춤, Background Task + polling 필요
- **run_pipeline 중복 실행 재확인:** `generate_report()` 호출 후 LLM 분석 3종이 다시 실행됨, SOLID 작업 시 `_analyze()` 헬퍼로 통합 예정

## 2026-04-02: LLM Filter Chain
- **Feature (llm-filter-chain):** LLM 호출 최적화 관심사를 Filter Chain 패턴으로 비즈니스 로직에서 완전 분리
- **신규 파일:** src/core/llm_pipeline.py — LLMFilter ABC, LLMRequest/LLMResponse, LLMFilterChain, 4개 Filter, build_llm_pipeline()
- **4개 Filter:**
  - ModelRoutingFilter: task_type(extraction→haiku, analysis/synthesis→sonnet) 기반 모델 자동 선택
  - SemanticCacheFilter: SHA256(prompt) 파일 캐시, TTL 제어 (metadata["ttl"])
  - PromptCacheFilter: cache_boundary 기반 Claude 프롬프트 캐싱 (static/dynamic 분리)
  - TokenLogFilter: 토큰 사용량 구조화 로깅 + 세션 누적
- **비즈니스 로직 변경:** CareerAgent, RealEstateAgent의 `self.llm = LLMClient()` → `build_llm_pipeline()` 한 줄 교체만 필요. BaseAnalyzer._call_llm()에 metadata 전달 추가.
- **프롬프트 frontmatter:** career 6개 파일에 task_type, cache_boundary, ttl 추가
- **Zero Hardcoding:** TTL/모델명/캐시경로 모두 환경변수(SEMANTIC_CACHE_TTL_SECONDS 등)로 override 가능
- **테스트:** 신규 27개 (전체 195 passed, 3 pre-existing failures 무변화)
- **3-Agent 오케스트레이션:** PlannerAgent→CoderAgent→ValidatorAgent 1회 PASS

## 2026-04-01: 부동산 실거래가 지도 시각화
- **Feature (real-estate-map-view):** 실거래가 데이터를 folium 지도 위에 아파트별 마커로 시각화, 클릭 시 거래 이력 최신순 팝업 표시
- **지오코딩:** 카카오 Local API (keyword 검색) + SQLite 캐시 (`data/geocode_cache.db`) — 동일 아파트 반복 호출 방지
- **UI:** Streamlit tab1에 서브탭 추가 ("📋 거래 목록" / "🗺️ 지도 뷰"), 기존 필터 공유
- **SOLID:** GeocoderProtocol (DIP), cache_path config.yaml 관리 (Zero Hardcoding)
- **테스트:** 신규 11개 (test_geocoder 7개 + test_map_view 4개), 모두 통과
- **신규 파일:** geocoder.py, components/map_view.py
- **3-Agent 오케스트레이션 첫 적용:** PlannerAgent→CoderAgent→ValidatorAgent(1차 FAIL→피드백→2차 PASS)

## 2026-03-30: LLM Harness Engineering
- **Feature (llm-harness-engineering):** LLM 호출 주변 harness 인프라 5종 TDD 구현
- **Token Observability:** `TokenUsage` dataclass, `get_last_usage()`, 구조화 로그 `[Claude] usage: in=X out=Y cached=Z`
- **Career Context Compression:** `PromptTokenOptimizer` core 이전, 포스팅 30개/소스 20-25개 제한, 텍스트 트런케이션 150-200자
- **Model Routing:** `TaskType` enum (ANALYSIS/EXTRACTION/SYNTHESIS), `LLMFactory.create(task_type)`, 기본값 EXTRACTION→haiku
- **Prompt Caching:** `load_with_cache_split()`, `generate_with_cache()`, `BaseAnalyzer._call_llm(use_cache=True)` opt-in
- **Semantic Cache:** `LLMResponseCache` (SHA256→파일), `CachedLLMClient` (Decorator 패턴), TTL 설정 가능
- **테스트:** 신규 51개 (전체 230 passed, 5 pre-existing 실패)

## 2026-03-28: 커뮤니티 트렌드 조사 모듈 + SOLID 리팩토링
- **Feature (community-trend-collector):** 커리어 Daily Report에 개발자 커뮤니티 여론·트렌드 섹션 추가.
- **수집 소스:** Reddit (공개 JSON API, 7개 subreddit), Mastodon (fosstodon.org/hachyderm.io/mastodon.social, 7개 해시태그), 클리앙 (cm_app 개발한당), DCInside (프로그래밍 갤러리)
- **분석:** CommunityAnalyzer (LLM) → CommunityTrendAnalysis (hot_topics, key_opinions, emerging_concerns, community_summary)
- **리포트:** Daily Report에 🌐 커뮤니티 트렌드 섹션 추가. 개조식·백틱·줄바꿈 렌더링
- **이슈 해결:**
  - Twitter 대안 탐색: Nitter(종료) → twscrape(Cloudflare 차단) → Twitter API v2 Free(402 CreditsDepleted) → Mastodon 해시태그 타임라인 API(✅)
  - SSL: macOS Python `SSLCertVerificationError` → `BaseCollector.make_connector()` certifi 공통화 (10개 Collector)
  - 클리앙 URL: cm_programmers(404) → cm_app(✅)
- **SOLID 리팩토링:**
  - `processors/base.py` BaseAnalyzer: Processor 4개 LLM 호출 패턴 공통화 (DRY/SRP)
  - `collectors/factory.py` CollectorFactory: Collector 생성 책임 분리 (OCP/DIP). `fetch_community()` 제네릭 루프 전환
- **테스트:** 101 tests all green (기존 42개 + 신규 59개)
- **변경 파일:** collectors/{reddit,mastodon,clien,dcinside,factory}.py, processors/{base,community_analyzer}.py, service.py, daily_reporter.py, models.py, config.yaml, prompts/career/community_analyst.md

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
