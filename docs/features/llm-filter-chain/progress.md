# Feature: LLM Filter Chain — Progress

**작성일:** 2026-04-02
**최종 업데이트:** 2026-04-02
**담당:** ImplementerAgent

---

## 전체 진행 상황

| 단계 | 내용 | 상태 |
|------|------|------|
| Phase 0 | 설계 (PlannerAgent) | ✅ 완료 |
| Phase 1 | TDD: 테스트 코드 먼저 작성 | ✅ 완료 |
| Phase 2 | 핵심 구현 (`llm_pipeline.py`) | ✅ 완료 |
| Phase 2.5 | SOLID Review | ✅ 완료 |
| Phase 3 | 서비스 통합 (service.py, base.py) | ✅ 완료 |
| Phase 4 | 프롬프트 frontmatter 추가 | ✅ 완료 |
| Phase 5 | ValidatorAgent 검증 | ✅ 완료 |

---

## Phase 1 — TDD: 테스트 코드 작성

- ✅ `tests/test_llm_pipeline.py` 파일 생성
- ✅ U01: `LLMRequest` 기본 생성 테스트
- ✅ U02: `LLMResponse` `from_cache` 기본값 테스트
- ✅ MR01~MR05: `ModelRoutingFilter` 단위 테스트
- ✅ SC01~SC04: `SemanticCacheFilter` 단위 테스트
- ✅ PC01~PC04: `PromptCacheFilter` 단위 테스트
- ✅ TL01~TL03: `TokenLogFilter` 단위 테스트
- ✅ CH01~CH04: `LLMFilterChain` 단위 테스트
- ✅ INT01~INT05: `build_llm_pipeline()` 통합 테스트
- ✅ 테스트 실행 → 전체 FAIL 확인 (Red)

---

## Phase 2 — 핵심 구현

### `src/core/llm_pipeline.py`

- ✅ `LLMFilter` ABC (`process` 추상 메서드)
- ✅ `LLMRequest` dataclass
- ✅ `LLMResponse` dataclass
- ✅ `LLMFilterChain` 구현
  - ✅ `proceed()` 체인 진행 로직
  - ✅ `generate_json()` 진입점 (BaseLLMClient 구현)
  - ✅ `get_last_usage()` 구현
- ✅ `ModelRoutingFilter`
  - ✅ `task_type` → `LLMFactory.create(task_type)` 모델 선택
  - ✅ Gemini provider no-op 처리
  - ✅ task_type 없음 → 통과
- ✅ `SemanticCacheFilter`
  - ✅ `LLMResponseCache` 재활용
  - ✅ 캐시 히트 시 조기 반환
  - ✅ `metadata["ttl"]` 우선 적용
  - ✅ `SEMANTIC_CACHE_DIR` 환경변수 지원
- ✅ `PromptCacheFilter`
  - ✅ `static_prompt` 있을 때 `generate_json_with_cache()` 경로
  - ✅ `cache_boundary` 없으면 no-op
  - ✅ Gemini provider no-op
- ✅ `TokenLogFilter`
  - ✅ 호출 후 구조화 로그
  - ✅ `session_usage` 누적 카운터
  - ✅ `get_session_usage()` 메서드
- ✅ `build_llm_pipeline()` 팩토리 함수
  - ✅ 기본 4개 필터 포함
  - ✅ 각 필터 on/off 파라미터 지원
  - ✅ `LLM_PIPELINE_FILTERS` 환경변수 override

---

## Phase 2.5 — SOLID Review (필수)

- ✅ SRP: 각 Filter가 단일 관심사만 처리하는지 검토
- ✅ OCP: 새 Filter 추가 시 기존 코드 수정 불필요한지 확인
- ✅ LSP: `LLMFilterChain`이 `BaseLLMClient` 계약을 완전히 이행하는지 확인
- ✅ ISP: `LLMFilter` ABC가 불필요한 메서드를 강제하지 않는지 확인
- ✅ DIP: 비즈니스 로직이 `BaseLLMClient` 인터페이스만 의존하는지 확인
- ✅ Zero Hardcoding: 모델명, 경로, TTL이 모두 환경변수/설정으로 분리되었는지 확인

---

## Phase 3 — 서비스 통합

### `src/core/llm.py`

- ✅ `BaseLLMClient.generate_json(prompt, max_tokens, metadata=None)` 시그니처 추가
- ✅ `GeminiClient.generate_json()` metadata 파라미터 추가 (무시)
- ✅ `ClaudeClient.generate_json()` metadata 파라미터 추가 (무시, 필터가 처리)

### `src/modules/career/processors/base.py`

- ✅ `_call_llm()` — `prompt_loader.load()` 반환 metadata를 `llm.generate_json()`에 전달
- ✅ `use_cache=True` 경로 병존 유지 (1단계)

### `src/modules/career/service.py`

- ✅ `from core.llm_pipeline import build_llm_pipeline` 임포트 추가
- ✅ `self.llm = LLMClient()` → `self.llm = build_llm_pipeline()`

### `src/modules/real_estate/service.py`

- ✅ `from core.llm_pipeline import build_llm_pipeline` 임포트 추가
- ✅ `self.llm = LLMClient()` → `self.llm = build_llm_pipeline()`

### `src/modules/real_estate/insight_orchestrator.py`

- ✅ `llm: LLMClient` 타입 힌트 → `llm: BaseLLMClient` 완화
- ✅ 임포트 변경 (`from core.llm import BaseLLMClient`)

---

## Phase 4 — 프롬프트 frontmatter 추가

- ✅ `src/prompts/career/job_analyst.md` — `task_type: extraction`, `cache_boundary: "## 입력 데이터"`, `ttl: 86400`
- ✅ `src/prompts/career/trend_analyst.md` — `task_type: extraction`, `cache_boundary: "## 입력 데이터"`, `ttl: 86400`
- ✅ `src/prompts/career/skill_gap_analyst.md` — `task_type: analysis`, `cache_boundary: "## 입력 데이터"`, `ttl: 86400`
- ✅ `src/prompts/career/community_analyst.md` — `task_type: extraction`, `cache_boundary: "## 입력 데이터"`, `ttl: 86400`
- ✅ `src/prompts/career/weekly_synthesizer.md` — `task_type: synthesis`, `cache_boundary: "## 입력 데이터"`, `ttl: 604800`
- ✅ `src/prompts/career/monthly_synthesizer.md` — `task_type: synthesis`, `cache_boundary: "## 입력 데이터"`, `ttl: 2592000`
- ✅ `cache_boundary` 헤더 위치 — spec 명시 헤더 부재 시 `## 입력 데이터` 섹션 추가 후 사용

---

## Phase 5 — 검증

- ✅ `pytest tests/test_llm_pipeline.py` — 전체 TC Green (27개)
- ✅ `pytest` (전체) — 195 passed, 3 pre-existing failures 무변화 (regression 없음)
- ✅ `TokenLogFilter` 로그 출력 형식 수동 확인
- ✅ `build_llm_pipeline(semantic_cache=False)` 동작 확인
- ✅ `CareerAgent` 초기화 후 `isinstance(agent.llm, BaseLLMClient)` True 확인

---

## 이슈 / 결정 사항

| 날짜 | 항목 | 내용 |
|------|------|------|
| 2026-04-02 | 설계 확정 | spec.md 작성 완료, 구현 대기 |
| 2026-04-02 | weekly/monthly cache_boundary | spec의 `## 일별 리포트` / `## 주간 리포트` 헤더 미존재 → `## 입력 데이터` 섹션 추가 후 사용. spec.md 정책 범위 내 결정. |
| 2026-04-02 | ValidatorAgent | 1회 PASS (재시도 없음) |

---

## 참고

- spec.md: `docs/features/llm-filter-chain/spec.md`
- result.md: `docs/features/llm-filter-chain/result.md`
- 관련 파일: `src/core/llm.py`, `src/core/llm_cache.py`, `src/core/llm_pipeline.py`
- 테스트 참고: `tests/test_llm_harness.py`, `tests/test_llm_pipeline.py`
