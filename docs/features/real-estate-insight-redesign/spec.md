# Spec: 부동산 인사이트 리포트 파이프라인 재설계

**Feature:** `real-estate-insight-redesign`
**Branch:** `feature/real-estate-insight-redesign`
**작성일:** 2026-04-08

---

## 목표

LLM이 필터링·점수계산·리포트를 전부 담당하던 구조를 분리한다.
- **Python 코드**: 예산 계산, 후보 필터링, 가중치 점수 계산
- **LLM**: 뉴스 호재 분석(경량), 최종 리포트 서술(단일 호출)
- **Zero Hardcoding**: 모든 임계값·기준·목적지를 config/persona에서 읽음

---

## 새 파이프라인 흐름

```
1. calculate_budget(persona, macro_policy)
   → BudgetPlan (LTV/DSR 수식, 기존 FinancialCalculator 유지)

2. get_candidates(districts, budget, recent_days)
   → ChromaDB에서 최근 N일 거래 조회 + 예산 이하 필터
   → recent_days: config.yaml report.recent_days

3. apply_preference_rules(candidates, rules)
   → preference_rules.yaml enabled 규칙을 Python 코드로 실행
   → LLM 프롬프트 전달 방식 폐지

4. enrich_with_area_data(candidates, area_intel, workplace_station)
   → area_intel.json join (commute_minutes, stations, school, reconstruction)
   → workplace_station: persona.commute.workplace_station (하드코딩 없음)

5. analyze_horea(news_text, interest_areas)   ← LLM #1 (경량)
   → 뉴스에서 지역별 호재 추출 → {"분당구": {"gtx": true, "items": [...]}}
   → generate_json() 호출, 입력 최소화

6. score_candidates(candidates, persona_weights, horea_data, config)
   → 각 아파트를 5개 기준으로 Python 수식 점수화
   → 기준별 임계값: config.yaml scoring 섹션
   → 가중치: persona.priority_weights

7. select_top_n(scored, n)
   → 상위 N개 선정 (config.yaml report.top_n, 기본 10)

8. generate_report(top_candidates, budget, persona)  ← LLM #2 (단일 호출)
   → 점수·근거 데이터를 받아 서술만 담당
   → Validator/Retry 없음 (코드가 이미 검증 완료)
```

---

## 점수 계산 기준 (Python 코드)

각 기준: 0~100점, 가중치 합산 → 최종 점수

| 기준 | 데이터 소스 | 점수 기준 (config.yaml에서 읽음) |
|------|------------|----------------------------------|
| 출퇴근편의성 | `area_intel.commute_minutes` | thresholds.commute: [20, 35] |
| 환금성 | `household_count` + `nearest_stations` | thresholds.households: [300, 500] |
| 가격상승가능성 | `reconstruction_potential` + `horea_data` | HIGH/MEDIUM/LOW 매핑 |
| 생활편의 | `nearest_stations` 수 + district 레벨 | station_count 기준 |
| 학군 | `school_zone_notes` 키워드 존재 여부 | 키워드 목록: config.yaml |

---

## Zero Hardcoding 변경 사항

| 항목 | 현재 | 변경 |
|------|------|------|
| 직장역 | `commute_minutes_to_samsung` 필드명 | `commute_minutes` + `area_intel.reference_workplace` |
| 출퇴근 임계값 (20분/35분) | `insight_parser.md` 하드코딩 | `config.yaml: scoring.commute_thresholds` |
| 환금성 세대수 기준 | `insight_parser.md` 하드코딩 | `config.yaml: scoring.household_thresholds` |
| 추천 상위 N개 | LLM 임의 결정 | `config.yaml: report.top_n` |
| 최근 N일 | 없음 | `config.yaml: report.recent_days` |
| 학군 키워드 | 없음 | `config.yaml: scoring.school_keywords` |
| `preference_rules` 삼성역 언급 | `preference_rules.yaml:46` | `persona.commute.workplace_station` 참조로 교체 |

---

## 신규/변경 파일 목록

### 신규
| 파일 | 역할 |
|------|------|
| `src/modules/real_estate/candidate_filter.py` | preference_rules Python 실행 엔진 |
| `src/modules/real_estate/scoring.py` | 5개 기준 가중치 점수 계산 |
| `src/modules/real_estate/prompts/horea_analyst.md` | LLM #1: 뉴스 → 호재 JSON |
| `src/modules/real_estate/prompts/report_synthesizer.md` | LLM #2: scored 결과 → 리포트 서술 |

### 변경
| 파일 | 변경 내용 |
|------|-----------|
| `data/static/area_intel.json` | `commute_minutes_to_samsung` → `commute_minutes`, 루트에 `reference_workplace` 추가 |
| `src/modules/real_estate/config.yaml` | `scoring`, `report` 섹션 추가 |
| `src/modules/real_estate/insight_orchestrator.py` | 전면 재작성 (새 파이프라인 오케스트레이션) |
| `src/modules/real_estate/agents/specialized.py` | ContextAnalystAgent, ReportValidator, SynthesizerAgent → 단순화/제거 |
| `src/modules/real_estate/service.py` | `_enrich_transactions()` 필드명 업데이트, per-apt ChromaDB 호출 제거 |
| `src/modules/real_estate/preference_rules.yaml` | 하드코딩 역명 제거 |
| `src/modules/real_estate/prompts/context_analyst.md` | 호재 분석 전용으로 경량화 (horea_analyst.md로 대체) |
| `src/modules/real_estate/prompts/insight_parser.md` | report_synthesizer.md로 대체 |

### 제거
| 파일/클래스 | 이유 |
|------------|------|
| `ReportValidator` (specialized.py) | Python 코드 scoring으로 대체 |
| `ContextAnalystAgent` (specialized.py) | HoreaAnalyst LLM으로 대체 |
| `SynthesizerAgent` (specialized.py) | ReportSynthesizer로 대체 |
| `prompt_optimizer.py`의 complex slimming | scoring.py로 역할 이동 |

---

## LLM 호출 비교

| | 기존 | 변경 후 |
|---|------|---------|
| 호출 수 | 최대 3회 (Context + Synth×2) | **최대 2회** (Horea + Report) |
| Validator/Retry | 있음 | **없음** |
| 필터링 | LLM 프롬프트 | **Python 코드** |
| 점수 계산 | LLM 추정 | **Python 수식** |
| LLM 역할 | 전부 | **호재분석 + 서술만** |
