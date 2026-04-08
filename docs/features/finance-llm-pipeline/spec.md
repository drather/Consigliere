# Spec: Finance LLM Pipeline 통합

**Feature:** `finance-llm-pipeline`
**Branch:** `feature/finance-llm-pipeline`
**작성일:** 2026-04-08

---

## 목표

`FinanceAgent`가 `LLMClient()` 직접 생성 대신 `build_llm_pipeline()`을 사용하도록 교체한다.
Career, RealEstate 모듈과 동일한 LLM 호출 패턴을 갖춰 SemanticCache, TokenLog, ModelRouting 혜택을 받는다.

## 변경 범위

| 파일 | 변경 내용 |
|------|-----------|
| `src/modules/finance/service.py` | `LLMClient()` → `build_llm_pipeline()` 교체, import 정리 |
| `src/modules/finance/prompts/parser.md` | frontmatter에 `task_type`, `cache_boundary`, `ttl` 추가 |
| `tests/test_finance_ai.py` | pipeline mock 대응 테스트 확인/수정 |

## 변경 후 구조

```python
# service.py
from core.llm_pipeline import build_llm_pipeline

class FinanceAgent:
    def __init__(self, ...):
        ...
        self.llm = build_llm_pipeline()
```

```yaml
# parser.md frontmatter
task_type: extraction
cache_boundary: "# Input"
ttl: 3600
```

## 설계 결정

- `task_type: extraction` — 비정형 텍스트 → 구조화 JSON 추출 작업
- `cache_boundary: "# Input"` — Context/Instructions는 정적, Input 이하만 동적
- `ttl: 3600` — 동일 거래 텍스트 재입력 시 1시간 캐시 활용
