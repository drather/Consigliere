# Project Consigliere: Active State
**Last Updated:** 2026-03-30
**Current Active Feature:** LLM Harness Engineering

## 📍 Current Focus
- **Branch:** `feature/llm-harness-engineering`
- **Status:** ✅ 구현 완료, 머지 대기

## 💡 Recent Context
- **completed:** 커뮤니티 트렌드 조사 모듈 + SOLID 리팩토링 (career 모듈 확장)
  - 데이터 소스: Reddit (공개 JSON API), Mastodon (해시태그 타임라인), 클리앙 (cm_app), DCInside
  - LLM 분석: CommunityAnalyzer → CommunityTrendAnalysis
  - Daily Report 🌐 커뮤니티 트렌드 섹션 (개조식·백틱·줄바꿈)
  - SOLID 단기: BaseAnalyzer (Processor LLM 호출 패턴 공통화)
  - SOLID 중기: CollectorFactory (Collector 생성 책임 분리, 제네릭 루프)
  - 101 tests all green, master 머지 완료
- **completed:** 커리어 Daily Report 모듈 (Collector 5종, Processor 3종, Reporter 3종, 테스트 42개)
- **completed:** Job4 부동산 리포트 고도화 + 토큰 최적화
- **completed:** Job1 aiohttp 비동기 전환
- **blocked:** 없음

## 🔜 다음 작업 로드맵

### 1순위 — Job4 LLM 과다 호출 수정
- 부동산 report 생성 시 LLM 호출이 너무 많아 토큰 과다 사용
- 배치 처리 또는 프롬프트 통합으로 호출 횟수 감소

### 2순위 — Career SOLID 장기 개선 (선택)
- Processor Protocol 정의 (ISP/DIP 강화)
- CareerAgent 의존성 주입 패턴 적용

### 3순위 — Career 모듈 고도화
- 수집 소스 확장 (LinkedIn, HackerNews Jobs 등)
- 주간/월간 리포트 커뮤니티 트렌드 섹션 추가

## ✅ Completed Tasks (Recent)
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
