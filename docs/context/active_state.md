# Project Consigliere: Active State
**Last Updated:** 2026-04-09
**Current Active Feature:** `apartment-master-db` — 아파트 마스터 DB 구축

## 현재 포커스
- **Branch:** `feature/apartment-master-db`
- **Status:** 🔄 Phase 1 (Spec 작성 중)

## 최근 컨텍스트
- **completed:** LLM Filter Chain (Filter Chain 패턴으로 LLM 최적화 관심사 분리)
  - src/core/llm_pipeline.py — LLMFilter ABC, LLMRequest/LLMResponse, LLMFilterChain, 4개 Filter, build_llm_pipeline()
  - ModelRoutingFilter: task_type 기반 모델 자동 선택 (extraction→haiku, analysis/synthesis→sonnet)
  - SemanticCacheFilter: SHA256(prompt) 파일 캐시, TTL 제어
  - PromptCacheFilter: cache_boundary 기반 Claude 프롬프트 캐싱
  - TokenLogFilter: 토큰 사용량 구조화 로깅 + 세션 누적
  - career 6개 프롬프트 frontmatter (task_type, cache_boundary, ttl) 추가
  - 신규 테스트 27개, 전체 195 passed, 3-Agent 오케스트레이션 1회 PASS
- **completed:** LLM Harness Engineering (Token Observability, Context Compression, Model Routing, Prompt Caching, Semantic Cache)
  - TokenUsage dataclass + get_last_usage() — 전 LLM 호출 토큰 추적
  - Career processors 입력 압축: 포스팅 30개, 소스당 20-25개, 텍스트 150-200자
  - TaskType enum + LLMFactory.create(task_type) — EXTRACTION→haiku, ANALYSIS→sonnet
  - PromptLoader.load_with_cache_split() + ClaudeClient.generate_with_cache()
  - LLMResponseCache + CachedLLMClient (Decorator 패턴)
  - 신규 테스트 51개, 전체 230 passed, master 머지 및 push 완료
- **completed:** 커뮤니티 트렌드 조사 모듈 + SOLID 리팩토링 (career 모듈 확장)
  - 데이터 소스: Reddit (공개 JSON API), Mastodon (해시태그 타임라인), 클리앙 (cm_app), DCInside
  - LLM 분석: CommunityAnalyzer → CommunityTrendAnalysis
  - Daily Report 커뮤니티 트렌드 섹션 (개조식·백틱·줄바꿈)
  - SOLID 단기: BaseAnalyzer (Processor LLM 호출 패턴 공통화)
  - SOLID 중기: CollectorFactory (Collector 생성 책임 분리, 제네릭 루프)
  - 101 tests all green, master 머지 완료
- **completed:** 커리어 Daily Report 모듈 (Collector 5종, Processor 3종, Reporter 3종, 테스트 42개)
- **completed:** Job4 부동산 리포트 고도화 + 토큰 최적화
- **completed:** Job1 aiohttp 비동기 전환
- **blocked:** 없음

## 다음 작업 로드맵

### 1순위 — 부동산 아파트 마스터 정보 구축 (Data Enrichment)
- **목표:** 실거래가 외에 아파트 단지의 물리적/법적 정보를 통합하여 분석 품질 고도화
- **주요 데이터:** 용적률, 건폐율, 세대수, 준공일(사용승인일), 시공사 등
- **데이터 소스:**
  - 국토교통부 건축물대장 API (용적률, 건폐율, 면적)
  - K-apt(공동주택관리정보시스템) API (세대수, 난방방식, 준공일)
- **구현 계획:** `models.py` 확장, `MasterDataService` 신설, `area_intel.json` 자동화 연동

### 2순위 — Career SOLID 장기 개선
- Processor Protocol 정의 (ISP/DIP 강화)
- CareerAgent 의존성 주입 패턴 적용
- 상세: `docs/features/career_solid_refactor/spec.md`

### 3순위 — Finance LLM Pipeline 통합 (빠른 개선)
- **문제:** `finance/service.py`가 `LLMClient()` 직접 생성 → SemanticCache, TokenLog 혜택 없음
- **개선:** `build_llm_pipeline()` 교체 (1시간 수정, 다른 모듈과 동일 패턴)

### 4순위 — Career 커뮤니티 소스 분류 config화
- **문제:** `service.py`의 `_REDDIT_SOURCES`, `_KOREAN_SOURCES` 등이 하드코딩 → 새 소스 추가 시 service.py 수정 필요
- **개선:** `config.yaml` 소스 정의에 `category` 필드 추가 → service.py 무수정 확장

### 5순위 — n8n 워크플로우 실행 결과 피드백 루프
- **문제:** 워크플로우 실패 시 알림 없음, 실행 히스토리 미저장, 장애 원인 분석 불가
- **개선 방향:**
  - n8n `GET /executions?workflowId=...` 폴링 또는 Error Workflow → Slack 실패 알림
  - AutomationService에 `get_execution_history()` 추가
  - **에러 리포트 파일 생성:** 워크플로우 실패 시 구조화된 에러 리포트를 `logs/n8n_errors/` 에 저장
    - 포함 내용: 워크플로우명, 실행ID, 실패 노드, 에러 메시지, 스택트레이스, 발생 시각
    - 파일명: `error_{workflow_id}_{timestamp}.json` 형식
    - 관리자가 언제든 로그 디렉토리에서 이력 확인 가능

### 6순위 — Career 스킬갭 트렌드 예측
- **방향:** 히스토리(`tracker.py`)를 활용한 gap_score 추이 분석 + 목표 달성 예상 시점 계산
- **구현:** 주간 리포트에 "4주 추이 / 예상 달성 주차" 섹션 추가

### 7순위 — Streamlit 파이프라인 실행 비동기화
- **문제:** `run-pipeline` 등 장시간 요청 시 대시보드 UI 블로킹
- **개선:** FastAPI Background Task + 상태 polling 엔드포인트 → 진행상황 실시간 표시

### ~~7순위 — BaseAnalyzer use_cache 분기 정리~~ ✅ 완료 (2026-04-08)
### ~~8순위 — 부동산 리포트 파이프라인 재설계~~ ✅ 완료 (2026-04-08)
- LLM→Python 역할 분리, Zero Hardcoding, Validator/Retry 제거
- CandidateFilter + ScoringEngine + 2 LLM 프롬프트

## 완료 작업 이력 (최근)
- [x] **Feature: LLM Filter Chain** (2026-04-02)
    - LLMFilterChain (FilterChain 패턴, BaseLLMClient 구현)
    - 4개 Filter: ModelRouting, SemanticCache, PromptCache, TokenLog
    - career 서비스 + real_estate 서비스 build_llm_pipeline() 적용
    - 신규 테스트 27개, 전체 195 passed, ValidatorAgent 1회 PASS
- [x] **Feature: 부동산 실거래가 지도 시각화** (2026-04-01)
    - folium 지도, 카카오 API 지오코딩, SQLite 캐시, Streamlit 서브탭
    - GeocoderProtocol (DIP), 신규 11개 테스트, 3-Agent 오케스트레이션 첫 적용
- [x] **Feature: LLM Harness Engineering** (2026-03-30) <!-- id: 37 -->
    - TokenUsage, get_last_usage(), 구조화 로깅
    - Career processors 입력 압축 (30/20/25개 제한, 텍스트 트런케이션)
    - TaskType enum + LLMFactory model routing
    - PromptLoader.load_with_cache_split() + ClaudeClient.generate_with_cache()
    - LLMResponseCache + CachedLLMClient (Decorator)
    - 신규 테스트 51개, 전체 230 passed, master 머지 완료
- [x] **Feature: 커뮤니티 트렌드 조사 모듈 + SOLID 리팩토링** (2026-03-28) <!-- id: 36 -->
    - Reddit/Mastodon/Clien/DCInside Collector, CommunityAnalyzer, Daily Report 커뮤니티 섹션
    - Twitter 대안 탐색: Nitter→twscrape→API v2(402)→Mastodon(✅, 68개/회)
    - SSL 공통화: BaseCollector.make_connector() → 10개 Collector 적용
    - SOLID: BaseAnalyzer (processors/base.py) + CollectorFactory (collectors/factory.py)
    - 101 tests all green, master 머지 완료
- [x] **Feature: 커리어 Daily Report 모듈** (2026-03-26) <!-- id: 35 -->
    - Job 포스팅 수집/분석, 스킬갭 분석, 일별/주별/월별 리포트, 42 tests green
- [x] **Maintenance: Insight Pipeline Optimization & LLM Robustness** <!-- id: 34 -->
    - Added state-aware execution to `RealEstateAgent.run_insight_pipeline`.
    - Integrated `json-repair` for resilient JSON parsing from LLM outputs.
- [x] **Feature: 데이터 파이프라인 aiohttp 전환** <!-- id: 33 -->
    - Job1 aiohttp 비동기 전환 완료 및 master 머지.
- [x] **Maintenance: Update Real Estate Insight Report Schedule** <!-- id: 31 -->
    - Changed cron expression from `30 8 * * *` to `0 7 * * *` (07:00 KST).
- [x] **BugFix: n8n Workflow Deployment Duplication & Inactivation** <!-- id: 32 -->
    - Fixed `AutomationService` to support workflow updates (PUT).
    - Added automatic activation logic to the deployment pipeline.
- [x] **Feature: Funding Plan Logic Correction & Logic Guard** <!-- id: 29 -->
    - LTV-back-calculation constraint, 100-iteration self-reflection loop.
- [x] **Feature: Spousal Income & First-time Buyer Logic** <!-- id: 30 -->
    - `is_first_time_buyer` and `spouse_income` handling in `persona.yaml`.
