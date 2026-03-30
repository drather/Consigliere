# Spec: LLM Harness Engineering

## 목표
LLM 호출 주변의 인프라(harness)를 강화하여 토큰 비용 폭증을 방지하고 observability를 확보한다.

## 배경
- Career 모듈 확장으로 1회 실행당 ~25K 토큰 소모 예상
- 현재 token 사용량 추적 없음 (블랙박스)
- 캐싱 없음: 동일 입력 반복 호출 시 매번 과금
- 단일 모델: 단순 JSON 추출에도 Sonnet 사용 중 (비용 낭비)
- Career processors에 token 압축 없음 (real_estate는 있음)

## 5가지 개선 항목

### 1. Token Observability
- LLM 응답에서 `input_tokens`, `output_tokens` 추출 후 구조화 로깅
- `TokenUsage` dataclass + `get_last_usage()` 인터페이스
- 파일: `src/core/llm.py`

### 2. Career Module Context Compression
- `PromptTokenOptimizer`를 `src/core/prompt_optimizer.py`로 이전
- JobAnalyzer: postings 30개 제한, description 200자 트런케이션
- TrendAnalyzer: repos/stories/articles 각 20개 제한
- CommunityAnalyzer: 소스당 25개 제한, body 150자 트런케이션

### 3. Model Routing per Agent
- `TaskType` enum (ANALYSIS, EXTRACTION, SYNTHESIS)
- `LLMFactory.create(task_type)` 확장
- 단순 JSON 추출 → haiku-4-5, 복잡한 추론/리포트 → sonnet-4-6
- env vars: `CLAUDE_ANALYSIS_MODEL`, `CLAUDE_EXTRACTION_MODEL`, `CLAUDE_SYNTHESIS_MODEL`

### 4. Prompt Caching (Claude cache_control)
- 프롬프트를 static(role/guidelines) + dynamic(입력 데이터)으로 분리
- `cache_boundary` frontmatter 키로 분할 지점 지정
- `ClaudeClient.generate_with_cache()`, `generate_json_with_cache()`
- `PromptLoader.load_with_cache_split()` 추가
- `BaseAnalyzer._call_llm(use_cache=False)` 확장

### 5. Semantic/Response Cache
- `LLMResponseCache`: SHA256(prompt) → data/llm_cache/{hash[:2]}/{hash}.json
- `CachedLLMClient`: Decorator 패턴으로 BaseLLMClient 감쌈 (OCP)
- TTL: Career 86400s, RealEstate 21600s (env vars 설정 가능)

## 아키텍처 원칙
- 모든 변경은 **기존 인터페이스 하위 호환** 유지
- **SOLID** 원칙 준수: 각 클래스 단일 책임, Decorator 패턴, 추상에 의존
- **TDD**: 모든 구현 전 테스트 먼저 작성

## 검증 기준
1. `pytest tests/test_llm_harness.py -v` 전부 통과
2. `pytest` 기존 101개 테스트 회귀 없음
3. 로그에서 `[Claude] usage: in=X out=Y cached=Z` 확인
4. `data/llm_cache/` 캐시 파일 생성 확인
5. 동일 프롬프트 2회 호출 시 2번째 cache hit 로그 확인
