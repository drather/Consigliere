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
