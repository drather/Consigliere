# Feature List

**Last Updated:** 2026-03-31

현재 구현 완료된 기능 목록. 각 기능의 진입점 파일과 상태를 기록한다.

---

## Real Estate (부동산)

| 기능 | 진입점 | 상태 |
|------|--------|------|
| 실거래가 수집 (수도권 71개 지구, aiohttp) | `src/modules/real_estate/monitor/service.py` | ✅ 운영 중 |
| 뉴스 분석 및 리포트 생성 | `src/modules/real_estate/news/` | ✅ 운영 중 |
| 거시경제 데이터 수집 (BOK 10개월 시계열) | `src/modules/real_estate/` | ✅ 운영 중 |
| 종합 인사이트 리포트 + 페르소나 액션 플랜 | `src/modules/real_estate/service.py` → `run_insight_pipeline()` | ✅ 운영 중 |
| Slack 자동 발송 (매일 07:00 KST) | n8n 워크플로우, `docs/workflows_registry.md` | ✅ 운영 중 |

---

## Career (커리어)

| 기능 | 진입점 | 상태 |
|------|--------|------|
| Job 포스팅 수집 (Wanted, Jumpit, DevTo, HackerNews, GitHub Trending) | `src/modules/career/collectors/` | ✅ 운영 중 |
| 커뮤니티 트렌드 수집 (Reddit, Mastodon, Clien, DCInside) | `src/modules/career/collectors/` | ✅ 운영 중 |
| LLM 분석 (JobAnalyzer, TrendAnalyzer, SkillGapAnalyzer, CommunityAnalyzer) | `src/modules/career/processors/` | ✅ 운영 중 |
| Daily / Weekly / Monthly 리포트 생성 | `src/modules/career/reporters/` | ✅ 운영 중 |
| Slack 자동 발송 (n8n) | `docs/workflows_registry.md` | ✅ 운영 중 |

---

## Finance (가계부)

| 기능 | 진입점 | 상태 |
|------|--------|------|
| Markdown 기반 가계부 CRUD | `src/modules/finance/markdown_ledger.py` | ✅ 운영 중 |
| 월별 요약 조회 | `src/modules/finance/service.py` | ✅ 운영 중 |

---

## Infrastructure / Core

| 기능 | 진입점 | 상태 |
|------|--------|------|
| LLM Client Factory (Claude/Gemini 전환) | `src/core/llm.py` | ✅ 운영 중 |
| **LLM Harness: Token Observability** | `src/core/llm.py` → `get_last_usage()`, `TokenUsage` | ✅ 구현 완료 |
| **LLM Harness: Model Routing** | `src/core/llm.py` → `TaskType`, `LLMFactory.create(task_type)` | ✅ 구현 완료 |
| **LLM Harness: Prompt Caching** | `src/core/prompt_loader.py` → `load_with_cache_split()` | ✅ 구현 완료 |
| **LLM Harness: Semantic Cache** | `src/core/llm.py` → `CachedLLMClient`, `LLMResponseCache` | ✅ 구현 완료 |
| **LLM Harness: Career 입력 압축** | `src/core/` → `PromptTokenOptimizer` | ✅ 구현 완료 |
| Slack Sender | `src/core/notify/slack.py` | ✅ 운영 중 |
| n8n 워크플로우 배포 | `scripts/deploy_workflows.py` | ✅ 운영 중 |
| Streamlit 대시보드 | `src/dashboard/` | ✅ 운영 중 |

---

## ⚠️ 미주입 / 진행 중

| 항목 | 내용 | 우선순위 |
|------|------|---------|
| LLM Harness 서비스 주입 | career/service.py, insight_orchestrator.py에 TaskType + CachedLLMClient 실제 적용 | **1순위** |
| 프롬프트 cache_boundary 설정 | 프롬프트 파일에 `cache_boundary` frontmatter 추가 | **1순위** |
| Career SOLID 장기 개선 | Processor Protocol 정의, CareerAgent 의존성 주입 | 2순위 |
| Career 수집 소스 확장 | LinkedIn, HackerNews Jobs 등 | 3순위 |
