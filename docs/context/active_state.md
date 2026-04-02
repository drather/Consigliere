# Project Consigliere: Active State
**Last Updated:** 2026-04-02
**Current Active Feature:** 없음 (다음 작업 대기 중)

## 현재 포커스
- **Branch:** `master`
- **Status:** ✅ llm-filter-chain 완료

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

### 1순위 — Career SOLID 장기 개선
- Processor Protocol 정의 (ISP/DIP 강화)
- CareerAgent 의존성 주입 패턴 적용

### 2순위 — Career 모듈 고도화
- 수집 소스 확장 (LinkedIn, HackerNews Jobs 등)
- 주간/월간 리포트 커뮤니티 트렌드 섹션 추가

### 3순위 — BaseAnalyzer use_cache 분기 정리 (2단계)
- `_call_llm(use_cache=True)` 경로 제거, PromptCacheFilter 단일 경로로 통합

### 4순위 — 부동산 리포트 Validator/Retry 패턴 개선
- **문제:** ReportValidator(코드 기반, 토큰 없음)의 score가 항상 15/100 → retry loop에서 SynthesizerAgent가 매번 2회 호출 → 토큰 ~50% 낭비
- **원인 분석:**
  - Budget compliance 0/40: LLM이 화이트리스트 무시하고 예산 초과 단지 추천
  - Scorecard 0/25: 추천 단지 1개 (최소 3개 필요)
  - commute_minutes 미인용 0/20, policy_facts 미인용 0/15
- **선택지:**
  - A (빠른): retry 제거 → 1회 실행, validator는 경고 전용으로 강등
  - B (근본): Synthesizer 프롬프트 개선으로 score ≥ 75 달성 → retry 자연 소멸
  - C (원복): ContextAnalyst + Synthesizer 2-call만 유지, validator 완전 제거

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
