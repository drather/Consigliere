# Progress: LLM Harness Engineering

## Phase 0/1 — Preparation & Planning
- [x] feature/llm-harness-engineering 브랜치 생성
- [x] active_state.md 업데이트
- [x] spec.md 작성
- [x] progress.md 초기화
- [x] 플랜 커밋

## Phase 2 — Implementation (TDD)

### Improvement 1: Token Observability ✅
- [x] tests/test_llm_harness.py — Observability 테스트 작성
- [x] TokenUsage dataclass + __add__ 구현
- [x] ClaudeClient: _last_usage 저장 + get_last_usage()
- [x] GeminiClient: usage_metadata 추출 + get_last_usage()
- [x] BaseLLMClient: get_last_usage() no-op 기본 구현
- [x] 테스트 통과 (11개)

### Improvement 2: Career Context Compression ✅
- [x] src/core/prompt_optimizer.py 신규 생성 (real_estate에서 이전)
- [x] src/modules/real_estate/prompt_optimizer.py re-export shim으로 교체
- [x] tests: 압축 테스트 작성
- [x] JobAnalyzer: postings 30개 제한
- [x] TrendAnalyzer: repos/stories/articles 각 20개 제한 + repo description 200자 트런케이션
- [x] CommunityAnalyzer: 소스당 25개 제한 + selftext/text 150자 트런케이션
- [x] 테스트 통과 (12개)

### Improvement 3: Model Routing per Agent ✅
- [x] TaskType enum 추가 (src/core/llm.py)
- [x] LLMFactory.create(task_type=None) 확장
- [x] ClaudeClient(model_override=None) 확장
- [x] tests: Model Routing 테스트 작성 + 통과 (7개)

### Improvement 4: Prompt Caching ✅
- [x] PromptLoader.load_with_cache_split() 추가
- [x] ClaudeClient.generate_with_cache() + generate_json_with_cache() 추가
- [x] BaseAnalyzer._call_llm(use_cache=False) 확장
- [x] tests: Prompt Caching 테스트 작성 + 통과 (8개)

### Improvement 5: Semantic/Response Cache ✅
- [x] src/core/llm_cache.py 신규 생성 (CacheEntry, LLMResponseCache, CachedLLMClient)
- [x] tests: Semantic Cache 테스트 작성 + 통과 (13개)

## Phase 2.5 — SOLID Review
- [x] SRP: TokenUsage(데이터), LLMResponseCache(I/O), CachedLLMClient(캐싱) 단일 책임
- [x] OCP: CachedLLMClient는 ClaudeClient 미수정으로 감쌈. 압축은 각 프로세서에서만
- [x] DIP: CachedLLMClient는 BaseLLMClient 인터페이스에만 의존
- [x] 회귀 테스트: 230 passed (5 pre-existing 실패 — API 크레딧, async 설정, 네트워크 관련)

## Phase 3 — Documentation
- [x] issues.md 작성
- [x] result.md 작성
- [x] history.md 항목 추가
