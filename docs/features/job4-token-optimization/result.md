# Result: Job4 토큰 최적화 & 안정화

**완료일**: 2026-03-29
**브랜치**: master
**테스트**: 59개 전부 통과

---

## 해결된 이슈 요약

| 이슈 | 이전 | 이후 |
|------|------|------|
| LLM 최대 호출 수 | 4회 (ContextAnalyst 1 + Synthesizer 3) | 3회 (ContextAnalyst 1 + Synthesizer 최대 2) |
| Validator Score 고착 | Score 40 → 3회 전부 실패 | 화이트리스트 강제로 Budget 40점 구조적 확보 |
| 파이프라인 중복 실행 | Job1/2/3만 방지 (마커 파일) | 전체 파이프라인 lock (`pipeline_running.lock`) |
| 프롬프트 입력 토큰 | 전체 JSON 직렬화 (수만 토큰) | PTO 일괄 슬림화 (20~30% 감소 추정) |
| 하드코딩 추천 조건 | 아파트 전용 등 코드에 박힘 | `preference_rules.yaml` 선언형 관리 + UI |

---

## 구현 내용

### 1. 예산 화이트리스트 강제 (`service.py`, `insight_parser.md`)

Budget filter 이후 잔여 단지명을 `budget_complex_names`로 추출해 Synthesizer 프롬프트에 명시.
LLM이 화이트리스트 외 단지를 추천할 경우 즉시 기각 규칙 삽입.

### 2. Validator 적응형 스코어카드 (`agents/specialized.py`)

가용 단지 수가 3개 미만인 경우 `required_ranks = min(3, max(1, available_complex_count))`로 동적 조정.
데이터 부족 상황에서 Validator 감점으로 인한 구조적 실패 방지.

### 3. 선호 규칙 체인 (`preference_rules.yaml`, `insight_orchestrator.py`)

하드코딩된 추천 조건을 선언형 YAML 규칙으로 분리.
`enabled: true/false` 토글만으로 규칙 활성화/비활성화 가능.
`_load_preference_rules()` → `{{user_preference_rules}}` 로 프롬프트에 동적 주입.

### 4. 선호 규칙 UI (`api/routers/real_estate.py`, `dashboard/views/real_estate.py`)

- `GET/PUT /dashboard/real-estate/preference-rules` 엔드포인트 추가
- Streamlit 페르소나 탭에 규칙 토글·편집·추가·삭제 UI 추가
- 저장 즉시 다음 Job4 실행에 반영

### 5. SOLID 리팩토링 (`persona_manager.py`, `service.py`, `insight_orchestrator.py`)

| 우선순위 | 내용 |
|---------|------|
| P1 Pipeline Lock | `_pipeline_lock_path()` + try/finally로 동시 실행 차단 |
| P2 SRP | `PersonaManager` + `PreferenceRulesManager` → `persona_manager.py` 분리 |
| P3 DIP | `InsightOrchestrator.__init__` optional 에이전트 주입 파라미터 추가 |
| P4 LSP/Naming | `CodeBasedValidator` → `ReportValidator` + 하위호환 alias |
| P5 Silent Exceptions | 3개 bare except → `logger.warning/debug` 추가 |

### 6. PromptTokenOptimizer (`prompt_optimizer.py`)

| 메서드 | 역할 |
|--------|------|
| `compact_json(data)` | 공백 제거 compact JSON (기본 대비 15~20% 절감) |
| `drop_empty(data)` | None/빈값 키 제거 (0·False 보존) |
| `slim_list(items, fields)` | 필드 필터링 + null 제거 (`tx_data` 적용) |
| `slim_budget(budget_dict)` | 4개 핵심 필드만 유지 |
| `slim_policy_context(policy_context)` | ltv/dsr/standard_year/news_summary만 유지 |
| `truncate(text, max_chars)` | ContextAnalyst 출력 길이 상한 (1500/2000자) |

`InsightOrchestrator.generate_strategy()` 의 모든 직렬화/슬림화 로직이 `PTO.*` 단일 호출로 대체됨.

---

## 테스트

| 테스트 클래스 | 케이스 수 | 내용 |
|-------------|-----------|------|
| TestBudgetCompliance | 5 | 예산 초과/준수/경계 |
| TestScorecardCompleteness | 4 | 1/2/3순위 존재 여부 |
| TestCommuteCitation | 3 | 출퇴근 수치 인용 |
| TestPolicyFactsCitation | 4 | RAG 내용 인용 |
| TestBudgetFilter | 2 | 예산 필터 결과 |
| TestComputeDistrictAverage | 2 | 구 평균 fallback |
| TestEnrichTransactions | 3 | enrichment 로직 |
| TestLoadStoredNews | 3 | 뉴스 파일 로드 |
| TestDeepMerge | 4 | PersonaManager deep merge |
| TestUpdatePersona | 3 | persona.yaml 업데이트·백업 |
| TestAdaptiveScorecardValidator | 7 | available_count 적응형 |
| TestPromptTokenOptimizer | 16 | PTO 메서드 전체 |
| **합계** | **59** | **전부 통과** |

---

## 변경 파일 목록

```
신규
  src/modules/real_estate/persona_manager.py
  src/modules/real_estate/preference_rules.yaml
  src/modules/real_estate/prompt_optimizer.py
  docs/features/job4-token-optimization/result.md

수정
  src/modules/real_estate/service.py
  src/modules/real_estate/insight_orchestrator.py
  src/modules/real_estate/agents/specialized.py
  src/modules/real_estate/prompts/insight_parser.md
  src/modules/real_estate/persona.yaml
  src/api/routers/real_estate.py
  src/dashboard/api_client.py
  src/dashboard/views/real_estate.py
  tests/test_job4_enhancements.py
  docs/features/job4-token-optimization/progress.md
```
