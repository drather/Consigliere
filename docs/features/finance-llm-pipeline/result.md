# Result: Finance LLM Pipeline 통합

**완료일:** 2026-04-08

## 변경 내용

`src/modules/finance/service.py`
- `from core.llm import LLMClient` → `from core.llm_pipeline import build_llm_pipeline`
- `self.llm = LLMClient()` → `self.llm = build_llm_pipeline()`

`src/modules/finance/prompts/parser.md`
- frontmatter 교체: `task_type: extraction`, `cache_boundary: "# Input"`, `ttl: 3600`

## 검증

- 178 passed (pre-existing 1개 실패 무변화)
- `test_finance.py` 통과

## 효과

- SemanticCache: 동일 거래 텍스트 재입력 시 1시간 캐시 활용
- TokenLog: 토큰 사용량 구조화 로깅 활성화
- ModelRouting: extraction task → haiku 자동 라우팅 (비용 절감)
- Career, RealEstate와 동일한 LLM 호출 패턴 통일
