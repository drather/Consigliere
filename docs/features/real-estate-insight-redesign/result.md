# Result: 부동산 인사이트 리포트 파이프라인 재설계

**완료일:** 2026-04-08

## 변경 요약

### LLM 호출 구조 변경
| | 기존 | 변경 후 |
|---|------|---------|
| 호출 수 | 최대 3회 (Context + Synth×2) | **최대 2회** (Horea + Report) |
| Validator/Retry | 있음 | **제거** |
| 필터링 | LLM 프롬프트 | **Python CandidateFilter** |
| 점수 계산 | LLM 추정 | **Python ScoringEngine** |

### 신규 파일
- `src/modules/real_estate/candidate_filter.py` — preference_rules Python 실행 엔진
- `src/modules/real_estate/scoring.py` — 5개 기준 가중치 점수 계산
- `src/modules/real_estate/prompts/horea_analyst.md` — LLM #1 (뉴스 → 호재 JSON)
- `src/modules/real_estate/prompts/report_synthesizer.md` — LLM #2 (서술 전담)

### Zero Hardcoding
- `commute_minutes_to_samsung` → `commute_minutes` (area_intel.json + 코드 전체)
- `area_intel.json` 루트에 `reference_workplace` 추가
- 출퇴근·세대수 임계값 → `config.yaml scoring` 섹션
- 추천 상위 N개·최근 N일 → `config.yaml report` 섹션
- preference_rules 역명 하드코딩 제거

### 제거된 클래스
- `ContextAnalystAgent` → `InsightOrchestrator._analyze_horea()`로 대체
- `SynthesizerAgent` → `InsightOrchestrator._synthesize_report()`로 대체
- `ReportValidator` → `ScoringEngine`(Python 코드)으로 대체

## 검증
- 신규 테스트 20개 (CandidateFilter 7개 + ScoringEngine 13개)
- 207 passed, 0 failed

## 버그픽스 (2026-04-08 E2E 검증 중 발견)

### BUG-1: generate_insight_report() 구버전 orchestrator 파라미터
- **증상:** `GET /agent/real_estate/insight_report` → `InsightOrchestrator.generate_strategy() got an unexpected keyword argument 'macro_dict'`
- **원인:** 리팩토링 후 `InsightOrchestrator.generate_strategy()` 시그니처가 변경됐으나, `service.py`의 `generate_insight_report()` 메서드가 구버전 파라미터(`macro_dict`, `daily_txs`, `policy_context` 등)로 호출하던 코드를 그대로 유지
- **수정:** `generate_insight_report()` → `generate_report()`에 위임하도록 전면 교체 (중복 로직 제거, SRP 충족)

### BUG-2: min_household_count 규칙이 household_count 미존재 데이터를 전부 탈락
- **증상:** `⚠️ 조건에 맞는 추천 단지가 없습니다.` — 국토부 API가 세대수를 제공하지 않아 ChromaDB에 `household_count` 미저장
- **원인:** `_handle_min_household_count`에서 `c.get("household_count", 0) >= 500` → 기본값 0이므로 전 후보 탈락
- **수정:** `household_count`가 None 또는 0인 경우(=데이터 미확인) 통과시키도록 수정

## E2E 파이프라인 검증 (2026-04-08)
- 수도권 71개 지구 1,536건 수집 / 1,521건 저장
- 예산 8.74억 이하 47건 → 59㎡ 필터 12건 → 상위 10개 LLM 서술
- Slack 전송 완료 (`sent`)
