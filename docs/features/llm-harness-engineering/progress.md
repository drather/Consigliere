# Progress: LLM Harness Engineering

## Phase 0/1 — Preparation & Planning
- [x] feature/llm-harness-engineering 브랜치 생성
- [x] active_state.md 업데이트
- [x] spec.md 작성
- [x] progress.md 초기화
- [ ] 플랜 커밋

## Phase 2 — Implementation (TDD)

### Improvement 1: Token Observability
- [ ] tests/test_llm_harness.py — Observability 테스트 작성
- [ ] TokenUsage dataclass + __add__ 구현
- [ ] ClaudeClient: _last_usage 저장 + get_last_usage()
- [ ] GeminiClient: usage_metadata 추출 + get_last_usage()
- [ ] BaseLLMClient: get_last_usage() no-op 기본 구현
- [ ] 테스트 통과 확인

### Improvement 2: Career Context Compression
- [ ] src/core/prompt_optimizer.py 신규 생성 (real_estate에서 이전)
- [ ] src/modules/real_estate/prompt_optimizer.py re-export shim으로 교체
- [ ] tests: 압축 테스트 작성
- [ ] JobAnalyzer: postings 30개 제한 + description 200자 트런케이션
- [ ] TrendAnalyzer: repos/stories/articles 각 20개 제한
- [ ] CommunityAnalyzer: 소스당 25개 제한 + body 150자 트런케이션
- [ ] 테스트 통과 확인

### Improvement 3: Model Routing per Agent
- [ ] TaskType enum 추가 (src/core/llm.py)
- [ ] LLMFactory.create(task_type=None) 확장
- [ ] ClaudeClient(model_override=None) 확장
- [ ] tests: Model Routing 테스트 작성
- [ ] career/service.py: 프로세서별 TaskType 할당
- [ ] insight_orchestrator.py: 에이전트별 TaskType 할당
- [ ] 테스트 통과 확인

### Improvement 4: Prompt Caching
- [ ] PromptLoader.load_with_cache_split() 추가
- [ ] ClaudeClient.generate_with_cache() + generate_json_with_cache() 추가
- [ ] BaseAnalyzer._call_llm(use_cache=False) 확장
- [ ] tests: Prompt Caching 테스트 작성
- [ ] Career 프롬프트 .md 파일들에 cache_boundary frontmatter 추가
- [ ] 프로세서에서 use_cache=True 활성화
- [ ] 테스트 통과 확인

### Improvement 5: Semantic/Response Cache
- [ ] src/core/llm_cache.py 신규 생성 (CacheEntry, LLMResponseCache, CachedLLMClient)
- [ ] tests: Semantic Cache 테스트 작성
- [ ] career/service.py: CachedLLMClient 주입
- [ ] real_estate/service.py: CachedLLMClient 주입 (TTL 6h)
- [ ] 테스트 통과 확인

## Phase 2.5 — SOLID Review
- [ ] SRP 체크
- [ ] OCP 체크
- [ ] DIP 체크
- [ ] 회귀 테스트 전체 실행

## Phase 3 — Documentation
- [ ] issues.md 작성
- [ ] result.md 작성
- [ ] history.md 항목 추가
