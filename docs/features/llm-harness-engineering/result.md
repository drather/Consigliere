# Result: LLM Harness Engineering

## 요약
LLM 호출 주변의 harness 인프라 5종을 TDD로 구현 완료.
신규 테스트 51개 추가, 기존 101개 회귀 없음.

## 구현 결과

### 1. Token Observability (`src/core/llm.py`)
- `TokenUsage` dataclass: `input_tokens`, `output_tokens`, `cached_input_tokens`, `total_tokens`
- `BaseLLMClient.get_last_usage()` 기본 no-op 구현 (하위 호환)
- `ClaudeClient`: `message.usage.input_tokens/output_tokens/cache_read_input_tokens` 추출
- `GeminiClient`: `response.usage_metadata.prompt_token_count/candidates_token_count` 추출
- 구조화 로그: `[Claude] usage: in=X out=Y cached=Z`

### 2. Career Context Compression
- `src/core/prompt_optimizer.py`: `PromptTokenOptimizer` core로 이전
- `src/modules/real_estate/prompt_optimizer.py`: re-export shim
- `JobAnalyzer`: 포스팅 30개 제한 (이전: 무제한)
- `TrendAnalyzer`: 소스당 20개 제한 + repo description 200자 트런케이션
- `CommunityAnalyzer`: 소스당 25개 제한 + selftext/text 150자 트런케이션
- **예상 절감:** Career daily report 입력 토큰 ~40% 절감

### 3. Model Routing per Agent (`src/core/llm.py`)
- `TaskType` enum: `ANALYSIS`, `EXTRACTION`, `SYNTHESIS`
- `LLMFactory.create(task_type=None)`: 기존 `create()` 완전 호환
- `ClaudeClient(model_override=None)`: 모델 직접 지정 가능
- env vars: `CLAUDE_ANALYSIS_MODEL`, `CLAUDE_EXTRACTION_MODEL`, `CLAUDE_SYNTHESIS_MODEL`
- 기본값: EXTRACTION → `claude-haiku-4-5`, ANALYSIS/SYNTHESIS → `claude-sonnet-4-6`

### 4. Prompt Caching (`src/core/prompt_loader.py`, `src/core/llm.py`, `src/modules/career/processors/base.py`)
- `PromptLoader.load_with_cache_split()`: `cache_boundary` frontmatter 키로 static/dynamic 분할
- `ClaudeClient.generate_with_cache(static, dynamic)`: `cache_control: {type: "ephemeral"}` 적용
- `ClaudeClient.generate_json_with_cache()`: JSON 출력 버전
- `BaseAnalyzer._call_llm(use_cache=False)`: 프로세서별 캐시 opt-in 지원
- **예상 절감:** 반복 호출 시 static 부분(~65%) 입력 토큰 ~90% 절감

### 5. Semantic/Response Cache (`src/core/llm_cache.py`)
- `LLMResponseCache`: SHA256(prompt) → `data/llm_cache/{hash[:2]}/{hash}.json`
- `CachedLLMClient`: Decorator 패턴으로 `BaseLLMClient` 감쌈 (OCP)
- TTL 설정: `LLM_CACHE_TTL_CAREER` (기본 86400s), `LLM_CACHE_TTL_REAL_ESTATE` (기본 21600s)
- cache hit 시 inner LLM 미호출, `TokenUsage` 재현

## 테스트 결과
```
tests/test_llm_harness.py — 51개 신규 테스트
전체: 230 passed (5 pre-existing 실패 — API 크레딧/async 설정)
```

## 변경 파일
```
[신규]
src/core/prompt_optimizer.py
src/core/llm_cache.py
tests/test_llm_harness.py

[수정]
src/core/llm.py              (TokenUsage, TaskType, get_last_usage, model routing, cache methods)
src/core/prompt_loader.py    (load_with_cache_split)
src/modules/real_estate/prompt_optimizer.py  (re-export shim)
src/modules/career/processors/base.py        (use_cache 파라미터)
src/modules/career/processors/job_analyzer.py
src/modules/career/processors/trend_analyzer.py
src/modules/career/processors/community_analyzer.py
```
