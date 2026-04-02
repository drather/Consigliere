# Feature: LLM Filter Chain

**작성일:** 2026-04-02
**작성자:** PlannerAgent
**상태:** 설계 완료 / 구현 대기

---

## 목표

현재 `CareerAgent`, `InsightOrchestrator`, `BaseAnalyzer` 등 비즈니스 로직 클래스에 LLM 최적화 관심사(모델 라우팅, 응답 캐싱, 토큰 로깅)가 산재해 있다.
이를 **Filter Chain 패턴**으로 분리함으로써 아래 목표를 달성한다:

1. **SRP 강화** — 비즈니스 로직은 `llm.generate_json(prompt, metadata=...)` 호출만 담당한다. 모델 선택, 캐싱, 로깅은 필터가 처리한다.
2. **OCP 준수** — 새 최적화(예: 요청 압축, 비용 예산 가드) 추가 시 기존 코드를 수정하지 않고 필터만 추가한다.
3. **Harness 실 서비스 주입** — LLM Harness Engineering에서 구현한 `TaskType`, `CachedLLMClient`, `PromptLoader.load_with_cache_split()`을 프로덕션 파이프라인에 실제로 연결한다. (active_state.md 1순위 작업)

---

## 구현 범위

### 생성할 파일

| 파일 | 역할 |
|------|------|
| `src/core/llm_pipeline.py` | Filter Chain 핵심 구현 (ABC, 데이터클래스, 4개 Filter, 팩토리) |
| `tests/test_llm_pipeline.py` | 파이프라인 단위/통합 테스트 |

### 수정할 파일

| 파일 | 변경 내용 |
|------|-----------|
| `src/core/llm.py` | `BaseLLMClient.generate_json()`에 `metadata: Optional[Dict] = None` 파라미터 추가 |
| `src/modules/career/processors/base.py` | `BaseAnalyzer._call_llm()`에서 `prompt_loader.load()`가 반환한 `metadata`를 `llm.generate_json()`에 전달 |
| `src/modules/career/service.py` | `self.llm = LLMClient()` → `self.llm = build_llm_pipeline()` |
| `src/modules/real_estate/service.py` | `self.llm = LLMClient()` → `self.llm = build_llm_pipeline()` |
| `src/modules/real_estate/insight_orchestrator.py` | `llm` 타입 힌트 `LLMClient` → `BaseLLMClient` (인터페이스로 완화, 기능 변경 없음) |
| `src/prompts/career/job_analyst.md` | frontmatter에 `task_type: extraction`, `cache_boundary` 추가 |
| `src/prompts/career/trend_analyst.md` | frontmatter에 `task_type: extraction`, `cache_boundary` 추가 |
| `src/prompts/career/skill_gap_analyst.md` | frontmatter에 `task_type: analysis`, `cache_boundary` 추가 |
| `src/prompts/career/community_analyst.md` | frontmatter에 `task_type: extraction`, `cache_boundary` 추가 |
| `src/prompts/career/weekly_synthesizer.md` | frontmatter에 `task_type: synthesis`, `cache_boundary` 추가 |
| `src/prompts/career/monthly_synthesizer.md` | frontmatter에 `task_type: synthesis`, `cache_boundary` 추가 |

### 변경하지 않는 파일

| 파일 | 이유 |
|------|------|
| `src/modules/career/processors/job_analyzer.py` 외 3종 | `BaseAnalyzer`만 소폭 수정하여 서브클래스는 자동 혜택 수령 |
| `src/modules/career/reporters/*.py` | 리포터는 LLM 직접 호출 없음 (Weekly/Monthly는 `BaseAnalyzer` 미사용) — 별도 검토 필요 시 2순위 작업으로 분리 |
| `src/modules/real_estate/agents/specialized.py` | `InsightOrchestrator`에서 주입된 `llm`을 그대로 사용 — 인터페이스 호환으로 자동 동작 |
| `src/core/llm_cache.py` | `SemanticCacheFilter`가 내부에서 `LLMResponseCache`를 사용하는 방식으로 재활용 |

---

## 아키텍처 설계

### 전체 흐름

```
비즈니스 로직
  llm.generate_json(prompt, metadata={"task_type": "extraction", "ttl": 86400})
       ↓
[LLMFilterChain] — BaseLLMClient를 구현하는 체인
  Filter 1: ModelRoutingFilter    → metadata["task_type"] 기반 모델 선택
  Filter 2: SemanticCacheFilter   → SHA256(prompt) 기반 파일 캐시 (TTL 제어)
  Filter 3: PromptCacheFilter     → cache_boundary 기반 Claude 프롬프트 캐싱
  Filter 4: TokenLogFilter        → 호출 후 토큰 사용량 구조화 로깅
       ↓
실제 LLM API 호출 (ClaudeClient / GeminiClient)
```

### LLMRequest / LLMResponse (데이터 클래스)

**LLMRequest**

| 필드 | 타입 | 설명 |
|------|------|------|
| `prompt` | `str` | 전체 렌더링된 프롬프트 텍스트 |
| `max_tokens` | `int` | 최대 출력 토큰 수 (기본 8192) |
| `metadata` | `Dict[str, Any]` | 프롬프트 frontmatter에서 추출한 메타데이터 |
| `static_prompt` | `Optional[str]` | cache_boundary 분리 후 정적 부분 (None이면 미분리) |
| `dynamic_prompt` | `Optional[str]` | cache_boundary 분리 후 동적 부분 |

**LLMResponse**

| 필드 | 타입 | 설명 |
|------|------|------|
| `data` | `Dict[str, Any]` | LLM이 반환한 JSON 파싱 결과 |
| `usage` | `TokenUsage` | 이번 호출의 토큰 사용량 |
| `from_cache` | `bool` | SemanticCache hit 여부 |
| `model_used` | `str` | 실제 사용된 모델명 |

### LLMFilter (추상 인터페이스)

```
ABC
  process(request: LLMRequest, chain: LLMFilterChain) -> LLMResponse
```

- `chain.proceed(request)` 를 호출하면 다음 필터로 이동한다.
- 필터는 `request`를 변형하거나, `chain.proceed()` 전/후에 로직을 실행하거나, 조기 반환(캐시 히트)할 수 있다.
- Django middleware의 `get_response(request)` 호출 패턴과 동일한 구조다.

### LLMFilterChain (체인 실행 엔진)

- `filters: List[LLMFilter]` 와 `inner: BaseLLMClient` 를 보유한다.
- `proceed(request: LLMRequest) -> LLMResponse` 메서드: 현재 인덱스의 필터를 호출하고 인덱스를 증가시킨다. 필터가 모두 소진되면 `inner`의 실제 API 호출로 진입한다.
- `LLMFilterChain` 자체도 `BaseLLMClient`를 구현하여 기존 `self.llm` 할당 지점에서 투명하게 교체된다.
  - `generate_json(prompt, max_tokens, metadata)` → `LLMRequest` 생성 후 `proceed()` 호출.
  - `get_last_usage()` → 마지막 `LLMResponse.usage` 반환.

### 구체 Filter 구현체

#### Filter 1: ModelRoutingFilter

**역할:** `metadata["task_type"]` 값을 보고 `request`의 내부 모델 힌트를 설정한다.

| task_type | 선택 모델 (Claude 기준) | 환경변수 |
|-----------|------------------------|----------|
| `extraction` | `CLAUDE_EXTRACTION_MODEL` (기본: `claude-haiku-4-5`) | `CLAUDE_EXTRACTION_MODEL` |
| `analysis` | `CLAUDE_ANALYSIS_MODEL` (기본: `claude-sonnet-4-6`) | `CLAUDE_ANALYSIS_MODEL` |
| `synthesis` | `CLAUDE_SYNTHESIS_MODEL` (기본: `claude-sonnet-4-6`) | `CLAUDE_SYNTHESIS_MODEL` |

- `task_type`이 없으면 기존 `inner` 클라이언트의 기본 모델을 그대로 사용한다.
- `LLMFactory.create(task_type)`를 내부에서 호출하여 적절한 `ClaudeClient(model_override=…)`를 생성하고, 이후 필터에 교체된 클라이언트를 전달한다.
- Gemini provider의 경우 task_type을 무시하고 통과한다 (Gemini는 단일 모델).

#### Filter 2: SemanticCacheFilter

**역할:** SHA256(prompt) 기반 파일 캐시. 기존 `LLMResponseCache` / `CachedLLMClient`를 내부에서 재활용한다.

- `metadata["ttl"]` 값이 있으면 해당 TTL 사용, 없으면 기본값 (`SEMANTIC_CACHE_TTL_SECONDS`, 기본 86400초).
- 캐시 히트 시 `chain.proceed()`를 호출하지 않고 즉시 `LLMResponse(from_cache=True, ...)`를 반환한다.
- 캐시 미스 시 `chain.proceed(request)` 결과를 `LLMResponseCache.put()`으로 저장 후 반환.
- `data/llm_cache/` 경로 사용 — Zero Hardcoding을 위해 `SEMANTIC_CACHE_DIR` 환경변수로 override 가능.

#### Filter 3: PromptCacheFilter

**역할:** `cache_boundary`가 있는 프롬프트를 정적/동적으로 분리하고 Claude 프롬프트 캐싱(`cache_control: ephemeral`)을 적용한다.

- `request.static_prompt`가 이미 분리되어 있으면 `ClaudeClient.generate_json_with_cache(static, dynamic)` 경로를 사용한다.
- `request.static_prompt`가 None이고 `metadata["cache_boundary"]`가 있으면 `PromptLoader.load_with_cache_split()` 결과를 사용한다.
- LLM provider가 Gemini인 경우 (`request.metadata["provider"] != "claude"`) 이 필터는 통과(no-op)한다.
- `cache_boundary`가 없는 프롬프트는 일반 `generate_json()` 경로로 폴백한다.

#### Filter 4: TokenLogFilter

**역할:** LLM 호출 전후로 토큰 사용량을 구조화 로깅한다.

- `chain.proceed(request)` 호출 후 `response.usage`를 읽어 `logger.info("[TokenLog] task_type={} model={} in={} out={} cached={} from_cache={}")` 형태로 기록한다.
- 누적 세션 토큰 합산을 위한 in-memory 카운터(`session_usage: TokenUsage`)를 보유하며, `get_session_usage() -> TokenUsage` 메서드를 제공한다.
- 비즈니스 로직에 영향을 주지 않으며 response를 그대로 반환한다.

### build_llm_pipeline() 팩토리 함수

```python
# 시그니처 (설계)
def build_llm_pipeline(
    token_log: bool = True,
    semantic_cache: bool = True,
    prompt_cache: bool = True,
    model_routing: bool = True,
) -> LLMFilterChain:
```

- 환경변수 `LLM_PIPELINE_FILTERS` (콤마 구분)로 활성 필터를 override할 수 있다.
- 기본 필터 순서: `ModelRoutingFilter → SemanticCacheFilter → PromptCacheFilter → TokenLogFilter`.
- `inner` 클라이언트는 `LLMFactory.create()` (task_type=None, 기본 모델)로 생성한다. ModelRoutingFilter가 task_type 별로 별도 client를 생성하여 실제 API 호출 시 교체한다.
- 반환 타입은 `LLMFilterChain`이며 `BaseLLMClient`를 구현하므로 기존 `self.llm` 할당과 완전 호환된다.

---

## 프롬프트 frontmatter 설계

career 모듈 6개 프롬프트에 아래 frontmatter 키를 추가한다.

| 프롬프트 파일 | task_type | cache_boundary 기준 | ttl |
|--------------|-----------|---------------------|-----|
| `job_analyst.md` | `extraction` | `## 입력 데이터` | 86400 |
| `trend_analyst.md` | `extraction` | `## 입력 데이터` | 86400 |
| `skill_gap_analyst.md` | `analysis` | `## 입력 데이터` | 86400 |
| `community_analyst.md` | `extraction` | `## 입력 데이터` | 86400 |
| `weekly_synthesizer.md` | `synthesis` | `## 일별 리포트` | 604800 |
| `monthly_synthesizer.md` | `synthesis` | `## 주간 리포트` | 2592000 |

- `cache_boundary`는 각 프롬프트 파일에서 동적 데이터가 시작되는 헤더로 지정한다.
- 헤더가 없는 경우 `## 입력 데이터` 섹션을 추가하거나 적합한 분기점을 확인 후 결정한다.

---

## BaseAnalyzer._call_llm() 변경 설계

현재:
```
_, prompt = self.prompt_loader.load(prompt_key, variables=variables)
data = self.llm.generate_json(prompt)
```

변경 후:
```
metadata, prompt = self.prompt_loader.load(prompt_key, variables=variables)
data = self.llm.generate_json(prompt, metadata=metadata)
```

- `use_cache=True` 경로는 PromptCacheFilter가 담당하므로 `BaseAnalyzer`의 `use_cache` 분기를 제거하고 단일 경로로 단순화할 수 있다. (단, 기존 동작 유지를 위해 1단계에서는 분기를 유지하고 2단계에서 정리)
- `self.llm`이 `LLMFilterChain`이면 `metadata`를 내부에서 해석하고, 기존 `BaseLLMClient`이면 `metadata`를 무시하므로 하위 호환성이 보장된다.

---

## 테스트 계획

**테스트 파일:** `tests/test_llm_pipeline.py`

### 단위 테스트 — LLMRequest / LLMResponse

| TC ID | 테스트 케이스 | 검증 내용 |
|-------|-------------|-----------|
| U01 | `LLMRequest` 기본 생성 | `metadata` 기본값이 빈 dict, `static_prompt` None |
| U02 | `LLMResponse` `from_cache` 기본값 | `False` |

### 단위 테스트 — ModelRoutingFilter

| TC ID | 테스트 케이스 | 검증 내용 |
|-------|-------------|-----------|
| MR01 | `task_type=extraction` | haiku 계열 모델 선택 (mock LLMFactory) |
| MR02 | `task_type=analysis` | sonnet 계열 모델 선택 |
| MR03 | `task_type=synthesis` | sonnet 계열 모델 선택 |
| MR04 | `task_type` 없음 | 기본 inner client 그대로 사용 |
| MR05 | provider=gemini | task_type 무시, 통과 |

### 단위 테스트 — SemanticCacheFilter

| TC ID | 테스트 케이스 | 검증 내용 |
|-------|-------------|-----------|
| SC01 | 캐시 미스 → `chain.proceed()` 호출 | `LLMResponseCache.put()` 호출 확인 |
| SC02 | 캐시 히트 → `chain.proceed()` 미호출 | `response.from_cache == True` |
| SC03 | `metadata["ttl"]` 적용 | 지정 TTL로 `cache.get()` 호출 확인 |
| SC04 | TTL 만료 항목 → 미스 처리 | `chain.proceed()` 재호출 |

### 단위 테스트 — PromptCacheFilter

| TC ID | 테스트 케이스 | 검증 내용 |
|-------|-------------|-----------|
| PC01 | `static_prompt` 있음, Claude provider | `generate_json_with_cache()` 호출 |
| PC02 | `static_prompt` None, `cache_boundary` 없음 | 일반 `generate_json()` 호출 (no-op) |
| PC03 | Gemini provider | 필터 통과 (no-op) |
| PC04 | `static_prompt` 있음, `dynamic_prompt` 빈 문자열 | 정상 동작 (dynamic_prompt="" 처리) |

### 단위 테스트 — TokenLogFilter

| TC ID | 테스트 케이스 | 검증 내용 |
|-------|-------------|-----------|
| TL01 | 호출 후 logger.info 호출 확인 | `caplog`로 로그 메시지 검증 |
| TL02 | `session_usage` 누적 | 2회 호출 후 합산값 확인 |
| TL03 | `from_cache=True` 시에도 로그 기록 | `from_cache` 필드가 로그에 포함 |

### 단위 테스트 — LLMFilterChain

| TC ID | 테스트 케이스 | 검증 내용 |
|-------|-------------|-----------|
| CH01 | 필터 순서 보장 | 실행 순서 기록 후 순서 검증 |
| CH02 | 필터 없는 체인 | `inner.generate_json()` 직접 호출 |
| CH03 | `get_last_usage()` | 마지막 `LLMResponse.usage` 반환 |
| CH04 | `BaseLLMClient` 인터페이스 준수 | `isinstance(chain, BaseLLMClient)` True |

### 통합 테스트 — build_llm_pipeline()

| TC ID | 테스트 케이스 | 검증 내용 |
|-------|-------------|-----------|
| INT01 | 기본 파이프라인 생성 | 4개 필터 모두 포함 |
| INT02 | `model_routing=False` | ModelRoutingFilter 제외 |
| INT03 | `semantic_cache=False` | SemanticCacheFilter 제외 |
| INT04 | mock inner로 end-to-end 호출 | `metadata={"task_type": "extraction"}` 전달 시 정상 응답 |
| INT05 | CareerAgent와 통합 (mock llm) | `self.llm = build_llm_pipeline()` 후 `generate_json` 호출 성공 |

---

## 완료 기준

- [ ] `src/core/llm_pipeline.py` 구현 완료
  - [ ] `LLMFilter` ABC 정의
  - [ ] `LLMRequest`, `LLMResponse` dataclass 정의
  - [ ] `LLMFilterChain` 구현 (BaseLLMClient 상속)
  - [ ] `ModelRoutingFilter` 구현
  - [ ] `SemanticCacheFilter` 구현 (`LLMResponseCache` 재활용)
  - [ ] `PromptCacheFilter` 구현
  - [ ] `TokenLogFilter` 구현
  - [ ] `build_llm_pipeline()` 팩토리 함수 구현
- [ ] `src/core/llm.py` — `generate_json()`에 `metadata` 파라미터 추가
- [ ] `src/modules/career/processors/base.py` — metadata를 llm에 전달
- [ ] `src/modules/career/service.py` — `build_llm_pipeline()` 적용
- [ ] `src/modules/real_estate/service.py` — `build_llm_pipeline()` 적용
- [ ] `src/modules/real_estate/insight_orchestrator.py` — 타입 힌트 완화
- [ ] `src/prompts/career/*.md` 6개 — `task_type` + `cache_boundary` + `ttl` frontmatter 추가
- [ ] `tests/test_llm_pipeline.py` — 전체 TC 구현 및 pass
- [ ] 기존 전체 테스트 (`pytest`) 230개 이상 통과 (regression 없음)
- [ ] `TokenLogFilter` 로그에 `task_type`, `model_used`, `from_cache` 포함 확인
- [ ] `build_llm_pipeline(semantic_cache=False)` 옵션 동작 확인

---

## 위험 요소 및 대응

| 위험 | 대응 |
|------|------|
| `InsightOrchestrator.__init__(llm: LLMClient)` 타입 힌트 — 파이프라인 주입 시 타입 에러 가능 | 힌트를 `BaseLLMClient`로 완화. 런타임에는 문제 없음 |
| `BaseAnalyzer._call_llm(use_cache=True)` 경로 — PromptCacheFilter와 중복 | 1단계에서는 기존 분기 유지, 2단계(SOLID 장기)에서 단일 경로로 정리 |
| `WeeklyReporter`, `MonthlyReporter`가 `llm`을 직접 사용하는지 여부 | 코드 확인 결과 두 리포터도 `BaseAnalyzer` 상속 확인 필요. 미상속 시 별도 수정 필요 |
| `LLMFilterChain`이 ModelRoutingFilter로 client를 교체할 때 thread-safety 문제 | 필터 내부에서 새 client 인스턴스를 생성하여 request 스코프 내에서만 사용 |
