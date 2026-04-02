# Feature: LLM Filter Chain — Result

**작성일:** 2026-04-02
**작성자:** ValidatorAgent PASS 후 문서화
**상태:** ✅ 구현 완료 / 검증 통과

---

## 구현 완료 파일 목록

### 신규 생성 파일

| 파일 | 역할 |
|------|------|
| `src/core/llm_pipeline.py` | Filter Chain 핵심 구현 (LLMFilter ABC, LLMRequest/LLMResponse dataclass, LLMFilterChain, 4개 Filter, build_llm_pipeline 팩토리) |
| `tests/test_llm_pipeline.py` | 파이프라인 단위/통합 테스트 27개 |

### 수정 파일

| 파일 | 변경 내용 |
|------|-----------|
| `src/core/llm.py` | `BaseLLMClient.generate_json()`에 `metadata: Optional[Dict] = None` 파라미터 추가 |
| `src/modules/career/processors/base.py` | `BaseAnalyzer._call_llm()`에서 `prompt_loader.load()` 반환 metadata를 `llm.generate_json()`에 전달 |
| `src/modules/career/service.py` | `self.llm = LLMClient()` → `self.llm = build_llm_pipeline()` |
| `src/modules/real_estate/service.py` | `self.llm = LLMClient()` → `self.llm = build_llm_pipeline()` |
| `src/modules/real_estate/insight_orchestrator.py` | `llm` 타입 힌트 `LLMClient` → `BaseLLMClient` 완화 |
| `src/prompts/career/job_analyst.md` | frontmatter에 `task_type: extraction`, `cache_boundary: "## 입력 데이터"`, `ttl: 86400` 추가 |
| `src/prompts/career/trend_analyst.md` | frontmatter에 `task_type: extraction`, `cache_boundary: "## 입력 데이터"`, `ttl: 86400` 추가 |
| `src/prompts/career/skill_gap_analyst.md` | frontmatter에 `task_type: analysis`, `cache_boundary: "## 입력 데이터"`, `ttl: 86400` 추가 |
| `src/prompts/career/community_analyst.md` | frontmatter에 `task_type: extraction`, `cache_boundary: "## 입력 데이터"`, `ttl: 86400` 추가 |
| `src/prompts/career/weekly_synthesizer.md` | frontmatter에 `task_type: synthesis`, `cache_boundary: "## 입력 데이터"`, `ttl: 604800` 추가 |
| `src/prompts/career/monthly_synthesizer.md` | frontmatter에 `task_type: synthesis`, `cache_boundary: "## 입력 데이터"`, `ttl: 2592000` 추가 |

---

## 테스트 결과

```
신규 테스트: 27개 (test_llm_pipeline.py)
전체 테스트: 195 passed
Pre-existing failures: 3개 (변화 없음, 본 기능과 무관)
Regression: 0개
```

### 테스트 커버리지 (27개)

| TC 그룹 | 항목 수 | 내용 |
|---------|---------|------|
| U01~U02 | 2 | LLMRequest/LLMResponse 데이터클래스 |
| MR01~MR05 | 5 | ModelRoutingFilter (task_type 라우팅, Gemini no-op) |
| SC01~SC04 | 4 | SemanticCacheFilter (캐시 히트/미스, TTL, 만료) |
| PC01~PC04 | 4 | PromptCacheFilter (static_prompt 분기, Gemini no-op) |
| TL01~TL03 | 3 | TokenLogFilter (로그, session_usage 누적, from_cache 로깅) |
| CH01~CH04 | 4 | LLMFilterChain (순서 보장, 빈 체인, get_last_usage, 인터페이스 준수) |
| INT01~INT05 | 5 | build_llm_pipeline() 통합 테스트 |

---

## 핵심 설계 결정

### 1. Filter Chain 패턴 채택 (Django Middleware 구조)

비즈니스 로직에서 LLM 최적화 관심사(모델 라우팅, 캐싱, 로깅)를 완전 분리하기 위해 Filter Chain 패턴을 채택했다. 각 필터는 `chain.proceed(request)` 호출로 다음 필터로 제어를 넘기는 Django Middleware와 동일한 구조를 따른다.

### 2. 비즈니스 로직 무변경

CareerAgent, RealEstateAgent의 비즈니스 로직 코드는 `self.llm = LLMClient()` → `self.llm = build_llm_pipeline()` 한 줄 교체만으로 전체 최적화 파이프라인을 활성화한다. `BaseAnalyzer._call_llm()`은 metadata 전달 한 줄만 추가되었다.

### 3. 하위 호환성 보장

`LLMFilterChain`이 `BaseLLMClient`를 구현하므로 기존 `self.llm` 할당 지점에서 투명하게 교체된다. 기존 `BaseLLMClient`에 metadata를 전달해도 무시하므로 하위 호환성이 완전히 보장된다.

### 4. Zero Hardcoding

모든 가변값이 환경변수로 override 가능하다:

| 환경변수 | 기본값 | 역할 |
|---------|--------|------|
| `CLAUDE_EXTRACTION_MODEL` | `claude-haiku-4-5` | extraction 태스크 모델 |
| `CLAUDE_ANALYSIS_MODEL` | `claude-sonnet-4-6` | analysis 태스크 모델 |
| `CLAUDE_SYNTHESIS_MODEL` | `claude-sonnet-4-6` | synthesis 태스크 모델 |
| `SEMANTIC_CACHE_TTL_SECONDS` | `86400` | 기본 캐시 TTL |
| `SEMANTIC_CACHE_DIR` | `data/llm_cache/` | 캐시 저장 경로 |
| `LLM_PIPELINE_FILTERS` | 전체 4개 | 활성 필터 목록 (콤마 구분) |

---

## 아키텍처 다이어그램

```
비즈니스 로직 (CareerAgent / RealEstateAgent)
  llm.generate_json(prompt, metadata={"task_type": "extraction", "ttl": 86400})
       │
       ▼
┌─────────────────────────────────────────────────────────┐
│                    LLMFilterChain                        │
│               (implements BaseLLMClient)                 │
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Filter 1: ModelRoutingFilter                   │    │
│  │  task_type → LLMFactory.create(task_type)       │    │
│  │  extraction→haiku / analysis,synthesis→sonnet   │    │
│  └─────────────────────────┬───────────────────────┘    │
│                            │ chain.proceed(request)      │
│  ┌─────────────────────────▼───────────────────────┐    │
│  │  Filter 2: SemanticCacheFilter                  │    │
│  │  SHA256(prompt) → 파일 캐시 (TTL 제어)           │    │
│  │  캐시 히트 시 즉시 반환 (from_cache=True)         │    │
│  └─────────────────────────┬───────────────────────┘    │
│                            │ cache miss                  │
│  ┌─────────────────────────▼───────────────────────┐    │
│  │  Filter 3: PromptCacheFilter                    │    │
│  │  cache_boundary 기반 static/dynamic 분리         │    │
│  │  ClaudeClient.generate_json_with_cache() 호출   │    │
│  │  Gemini provider → no-op 통과                   │    │
│  └─────────────────────────┬───────────────────────┘    │
│                            │                             │
│  ┌─────────────────────────▼───────────────────────┐    │
│  │  Filter 4: TokenLogFilter                       │    │
│  │  chain.proceed() 후 response.usage 구조화 로깅  │    │
│  │  session_usage 누적 카운터                       │    │
│  └─────────────────────────┬───────────────────────┘    │
│                            │                             │
└────────────────────────────┼────────────────────────────┘
                             │
                             ▼
              실제 LLM API 호출
         (ClaudeClient / GeminiClient)

프롬프트 frontmatter 흐름:
  src/prompts/career/*.md
    │ task_type, cache_boundary, ttl
    ▼
  PromptLoader.load(prompt_key)
    │ returns (metadata, prompt)
    ▼
  BaseAnalyzer._call_llm()
    │ llm.generate_json(prompt, metadata=metadata)
    ▼
  LLMFilterChain (위 파이프라인 진입)
```

---

## 완료 기준 체크리스트

- ✅ `src/core/llm_pipeline.py` 구현 완료
  - ✅ `LLMFilter` ABC 정의
  - ✅ `LLMRequest`, `LLMResponse` dataclass 정의
  - ✅ `LLMFilterChain` 구현 (BaseLLMClient 상속)
  - ✅ `ModelRoutingFilter` 구현
  - ✅ `SemanticCacheFilter` 구현 (`LLMResponseCache` 재활용)
  - ✅ `PromptCacheFilter` 구현
  - ✅ `TokenLogFilter` 구현
  - ✅ `build_llm_pipeline()` 팩토리 함수 구현
- ✅ `src/core/llm.py` — `generate_json()`에 `metadata` 파라미터 추가
- ✅ `src/modules/career/processors/base.py` — metadata를 llm에 전달
- ✅ `src/modules/career/service.py` — `build_llm_pipeline()` 적용
- ✅ `src/modules/real_estate/service.py` — `build_llm_pipeline()` 적용
- ✅ `src/modules/real_estate/insight_orchestrator.py` — 타입 힌트 완화
- ✅ `src/prompts/career/*.md` 6개 — `task_type` + `cache_boundary` + `ttl` frontmatter 추가
- ✅ `tests/test_llm_pipeline.py` — 전체 TC 구현 및 pass
- ✅ 기존 전체 테스트 (`pytest`) regression 없음 (195 passed, 3 pre-existing failures 무변화)
- ✅ `TokenLogFilter` 로그에 `task_type`, `model_used`, `from_cache` 포함 확인
- ✅ `build_llm_pipeline(semantic_cache=False)` 옵션 동작 확인

---

## spec.md 대비 Minor Deviation

| 항목 | spec.md 명세 | 실제 구현 | 영향 |
|------|-------------|-----------|------|
| `weekly_synthesizer.md` cache_boundary | `## 일별 리포트` | `## 입력 데이터` | 해당 섹션 헤더가 파일 내 존재하지 않아 `## 입력 데이터` 섹션 추가 후 사용. 기능 동일. |
| `monthly_synthesizer.md` cache_boundary | `## 주간 리포트` | `## 입력 데이터` | 동일 사유. 기능 동일. |

spec.md는 "헤더가 없는 경우 `## 입력 데이터` 섹션을 추가하거나 적합한 분기점을 확인 후 결정한다"고 명시하고 있어 정책 범위 내 결정이다.

---

## 3-Agent 오케스트레이션

- **PlannerAgent:** spec.md 작성 (설계 완료)
- **CoderAgent:** TDD 순서로 구현 (test → 핵심 구현 → SOLID Review → 서비스 통합 → 프롬프트 추가)
- **ValidatorAgent:** 1회 PASS (재시도 없음)
