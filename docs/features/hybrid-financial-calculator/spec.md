# Feature Spec: Hybrid Financial Calculator (Phase 1)

## 1. Goal
비현실적인 자산 산출(단순 역산) 대신, LLM(RAG)이 최신 정책을 찾고 Python 모듈이 부대비용 및 DSR 한도를 적용하여 정확한 가용 예산을 산출하는 **하이브리드 재무 자동화 파이프라인**을 구축합니다.

## 2. Architecture
1. **`PolicySearcher` (LLM/Tool)**: 웹 검색(`duckduckgo-search`) 또는 RAG를 통해 현 시점(2026년 3월 기준)의 '투기과열지구 LTV', 'DSR 규제 단계', '취득세율' 등 동적 정책 지표 확인 (현재 `core/policy_fetcher.py`의 역할 고도화).
2. **`FormulaValidator` (LLM)**: Python이 사용할 세금/수수료 및 DSR 계산 기본 공식을 점검하고 예외 케이스 판단.
3. **`FinancialCalculator` (Python)**:
    - 선공제: `가용 자본금 - (예상 취득세 + 중개수수료)`
    - LTV 한도: `순수 자본금 / (1 - LTV비율)`
    - DSR 한도: `(연소득 * DSR비율) / 연간 원리금 상환액 + 가용 자본금`
    - 최종 한도: `Min(LTV 기반 최대가, DSR 기반 최대가)`
4. **Context Injection**: 산출된 정확한 예산을 프롬프트에 주입하여 LLM이 불필요한 수학 계산을 하지 않도록 강제.

## 3. Data Models (Persona Updates)
- `persona.yaml` 기반으로 입력 데이터 처리.
- 출력은 `BudgetPlan` Pydantic 모델 반환 (`max_price`, `loan_amount`, `tax_estimate`, `reasoning`).

## 4. Acceptance Criteria
- [ ] LLM이 단순히 자본금을 나눈 (예: 15억) 비현실적 예산을 제시하지 않아야 함.
- [ ] DSR 및 가용 현금(부대비용 공제 후) 기준 10억 내외의 현실적 상한선을 도출해야 함.
- [ ] 계산 모듈에 대한 Unit Test(다양한 LTV/DSR 조건) 통과.
