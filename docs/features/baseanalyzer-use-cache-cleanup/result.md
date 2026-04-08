# Result: BaseAnalyzer use_cache 분기 정리

**완료일:** 2026-04-08

## 변경 내용

`src/modules/career/processors/base.py`
- `_call_llm(use_cache=False)` 파라미터 제거
- `if use_cache and hasattr(...)` 분기 제거
- 단일 경로(`prompt_loader.load` → `llm.generate_json`)로 통합

`tests/test_llm_harness.py`
- `TestBaseAnalyzerUseCacheFlag` 클래스 전체 제거 (2개 케이스)

## 검증

- 188 passed (기존 pre-existing 1개 실패 무변화)
- `TestBaseAnalyzer` 6개 케이스 모두 통과

## 효과

- Dead code 제거: `use_cache=True` 경로는 실제로 한 번도 호출된 적 없었음
- PromptCacheFilter가 frontmatter `cache_boundary` 감지 → 자동 캐싱 처리 (단일 경로)
- `base.py` 9줄 → 5줄로 단순화
