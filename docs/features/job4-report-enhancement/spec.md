# Feature Spec: Job4 부동산 전략 리포트 고도화

## 1. 개요

현재 Job4는 동작하지만 리포트 품질에 다음 문제가 있다:
- **예산 초과 추천**: `CodeBasedValidator`가 규칙 기반으로 동작해 LLM이 예산 초과 단지를 우회 추천하는 경우가 있음
- **스코어카드 근거 부실**: `area_intel.json`에 없는 단지는 enriched 필드가 없어 스코어카드가 "N/A" 또는 기본값으로 채워짐
- **뉴스-실거래-거시경제 분리**: 세 데이터 소스가 있으나 통합 인사이트로 엮이지 않음 (Job2 뉴스가 Job4 리포트에 반영 안 됨)
- **페르소나 고정**: `persona.yaml`이 정적 파일이라 상황 변화(자산 변동, 관심 지역 변경) 반영 불가

---

## 2. 목표 (Definition of Done)

| 항목 | 현재 | 목표 |
|------|------|------|
| 예산 준수율 | ~70% (LLM 우회) | 100% (구조적 강제) |
| 스코어카드 데이터 커버리지 | ~40% (area_intel 단지만) | ~80% 이상 |
| 뉴스 반영 | 미반영 | Job2 뉴스 요약 → 리포트 Section 4에 포함 |
| 페르소나 갱신 | 수동 | Slack 명령 or API로 동적 수정 가능 |
| Validator 점수 | 불안정 (0 or 65 or 92) | 연속 점수 + 항목별 피드백 |

---

## 3. 작업 범위 (5개 Phase)

### Phase 1: 예산 준수 구조적 강제
**목적:** LLM 생성 전에 예산 이하 단지만 필터링하여 프롬프트에 전달

- `service.py::generate_report()` — `daily_txs` 리스트를 `budget_plan.final_max_price` 기준으로 사전 필터링
- `insight_orchestrator.py` — `base_variables`에 `filtered_tx_count` 추가, 프롬프트에 "이 리스트 외 단지 추천 금지" 강화
- `CodeBasedValidator` — score 로직 세분화: PASS(95), WARN(75), FAIL(50) 3단계로 변경

### Phase 2: 스코어카드 커버리지 개선
**목적:** `area_intel.json`에 없는 단지도 스코어카드 작성 가능하도록

- `area_intel.json` 확장: 현재 강남/서초/송파 중심 → persona.interest_areas 기준 구 추가
- `_enrich_transactions()` — fallback 로직 개선: 구 단위 기본값 → 동 단위 평균으로 보강
- 신규 단지가 area_intel에 없을 때 "데이터 미확보" 대신 ChromaDB policy 검색으로 보완

### Phase 3: 뉴스 통합 (Job2 → Job4 연결)
**목적:** Job2에서 저장한 뉴스 리포트를 Job4가 읽어 리포트에 포함

- `news/service.py::generate_daily_report()` 반환값 또는 저장 파일 구조 확인
- `service.py::generate_report()` — 당일 뉴스 마크다운 파일 로드 후 `news_summary` 변수로 orchestrator에 전달
- `insight_parser.md` — Section 4 "📰 오늘의 부동산 뉴스 요약" 추가 (policy_facts + 뉴스 통합)
- `context_analyst.md` — 뉴스 데이터 입력 섹션 추가

### Phase 4: Validator 점수 안정화
**목적:** 현재 이진(PASS/FAIL) 구조를 연속 점수로 교체

- `CodeBasedValidator.run()` — 예산 초과 외 추가 체크 항목:
  - 스코어카드 3개 단지 모두 존재하는지
  - `commute_minutes_to_samsung` 필드 실제 인용 여부
  - policy_facts 인용 여부
- 각 항목 가중치로 연속 점수 산출
- 점수 75 미만 시 `validator_feedback`에 항목별 피드백 포함 → SynthesizerAgent 재시도

### Phase 5: 페르소나 동적 갱신 (선택)
**목적:** `persona.yaml`을 API/Slack으로 수정 가능하게

- `POST /agent/real_estate/persona` 엔드포인트 추가 (필드 부분 수정)
- n8n Slack 워크플로우: `/부동산 페르소나 업데이트 자산=9억 관심지역=마포구` 명령 처리
- 변경 이력 `data/real_estate/persona_history/` 에 백업

---

## 4. 데이터 플로우 (변경 후)

```
Job1: 실거래 수집 (aiohttp) → ChromaDB
Job2: 뉴스 수집 → data/real_estate/news/{date}_news.md  ← 신규 연결
Job3: 거시경제 → data/real_estate/macro/{date}_macro.json
Job4: 리포트 생성
  ├─ ChromaDB 조회 → budget 필터링 (Phase 1)
  ├─ _enrich_transactions() 개선 (Phase 2)
  ├─ 뉴스 파일 로드 (Phase 3)
  ├─ ContextAnalystAgent (거시+실거래+뉴스 통합)
  ├─ SynthesizerAgent → Slack Block Kit JSON
  └─ CodeBasedValidator (Phase 4: 연속 점수)
       └─ score < 75 → 피드백 주입 후 Synthesizer 재시도 (최대 3회)
```

---

## 5. 영향 범위

| 파일 | 변경 여부 |
|------|----------|
| `service.py` | 수정 (Phase 1, 3) |
| `insight_orchestrator.py` | 수정 (Phase 1, 4) |
| `agents/specialized.py` | 수정 (Phase 4) |
| `prompts/insight_parser.md` | 수정 (Phase 3) |
| `prompts/context_analyst.md` | 수정 (Phase 3) |
| `data/static/area_intel.json` | 확장 (Phase 2) |
| `news/service.py` | 반환값 확인 (Phase 3, 읽기만) |
| `routers/real_estate.py` | 수정 (Phase 5, 선택) |

---

## 6. 구현 순서

Phase 1 → Phase 3 → Phase 4 → Phase 2 → Phase 5(선택)

Phase 1이 가장 임팩트 크고 구현 단순. Phase 3은 뉴스 파일 구조 확인 후 착수.

---

## 7. 제외 범위

- Job1/Job2/Job3 로직 자체 변경 없음
- ChromaDB 스키마 변경 없음
- Slack Block Kit 레이아웃 대규모 변경 없음 (Section 추가만)
