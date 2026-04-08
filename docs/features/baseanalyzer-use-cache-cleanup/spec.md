# Spec: BaseAnalyzer use_cache 분기 정리

**Feature:** `baseanalyzer-use-cache-cleanup`
**Branch:** `feature/baseanalyzer-use-cache-cleanup`
**작성일:** 2026-04-08

---

## 목표

`BaseAnalyzer._call_llm()`의 `use_cache` 분기를 제거하고 단일 경로로 통합한다.

## 배경 및 문제

LLM Filter Chain (`core/llm_pipeline.py`) 도입 이후, `PromptCacheFilter`가 프롬프트 frontmatter의 `cache_boundary`를 감지하여 자동으로 Claude 프롬프트 캐싱을 처리한다. 따라서 `_call_llm(use_cache=True)` 분기는 중복이며, 현재 호출처 4곳 모두 `use_cache=False`(기본값)로 사용 중 — 실제로 한 번도 실행된 적 없는 dead code다.

## 변경 범위

| 파일 | 변경 내용 |
|------|-----------|
| `src/modules/career/processors/base.py` | `use_cache` 파라미터 및 분기 제거, 단일 경로(`generate_json`)로 통합 |
| `tests/modules/career/test_base_analyzer.py` | `use_cache` 관련 테스트 케이스 제거 |

## 변경 후 구조

```python
def _call_llm(self, prompt_key, variables, model_class) -> T:
    metadata, prompt = self.prompt_loader.load(prompt_key, variables=variables)
    data = self.llm.generate_json(prompt, metadata=metadata)
    return model_class(**data)
```

- PromptCacheFilter가 `metadata["cache_boundary"]` 존재 여부로 캐싱 자동 처리
- 호출처 코드 변경 불필요 (기본값 사용 중이었으므로)
