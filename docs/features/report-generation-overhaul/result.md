# Result: 부동산 리포트 생성 전면 점검

**Branch:** `feature/report-generation-overhaul`
**완료일:** 2026-04-20
**테스트:** 178 passed, 0 failed

---

## 구현 결과 요약

### 변경 범위

| 파일 | 변경 내용 |
|------|-----------|
| `src/modules/real_estate/service.py` | tx_repo SQLite 전환, dedup normalize, apt_master enrich, news_articles 로드 |
| `src/modules/real_estate/calculator.py` | `mortgage_rate` 파라미터 추가 |
| `src/modules/real_estate/scoring.py` | `data_absent_neutral=50`, `horea_scores` 파라미터 |
| `src/modules/real_estate/insight_orchestrator.py` | horea_validator 단계 추가, `_format_candidates_for_llm()` |
| `src/modules/real_estate/news/service.py` | Job2 기사 JSON 저장 |
| `src/modules/real_estate/config.yaml` | `budget_band_ratio`, `data_absent_neutral`, `reconstruction_score_map.UNKNOWN=50` |
| `src/modules/real_estate/prompts/report_synthesizer.md` | 개조식 형식, horea_assessments 섹션, 절대 규칙 |
| `src/modules/real_estate/prompts/horea_validator.md` | 신규 — 호재 LLM 검증 프롬프트 |

### 신규 테스트 파일

| 파일 | 테스트 수 |
|------|-----------|
| `test_scoring_neutral_defaults.py` | 14 |
| `test_horea_validator.py` | 4 |
| `test_format_candidates_for_llm.py` | 9 |
| `test_service_fixes.py` | 기존 확장 |

---

## Phase 2 — 핵심 변경사항 walkthrough

### 1. ChromaDB → SQLite 전환
`generate_report()`에서 ChromaDB 벡터 검색을 `tx_repo.get_by_district()` + 날짜 필터로 교체. 최근 7일 거래만 대상으로 결정론적 조회.

### 2. 예산 ±10% 필터 (`budget_band_ratio`)
```python
lo, hi = budget_ceiling * (1 - band), budget_ceiling * (1 + band)
candidates = [tx for tx in deduped_txs if lo <= tx.get("price", 0) <= hi]
```
`config.yaml → report.budget_band_ratio: 0.1` 설정으로 하드코딩 제거.

### 3. 주담대금리 예산 반영
`_load_stored_macro(target_date)` → `loan_rate.value` → `calculate_budget(mortgage_rate=mr)`. 2026-04-19 기준 2.83% 실데이터 반영 확인.

### 4. LLM 2회 → 1회 통합
`horea_analyst` LLM 호출 제거. `macro_summary`와 `horea_text`를 Python에서 사전 포맷 후 `report_synthesizer` 단일 LLM 호출로 통합. 토큰 비용 ~50% 절감.

### 5. data_absent_neutral = 50
`household_count=None`, `nearest_stations=None`, `school_zone_notes=None`, `reconstruction_potential=UNKNOWN` 모두 중립값 50으로 처리. 데이터 부재 ≠ 불량 로직.

### 6. `_format_candidates_for_llm()` (LLM 할루시네이션 방지)
scored 후보 목록을 LLM에 raw JSON 대신 아래 형태 텍스트로 전달:
```
총 3개 단지 (이 목록 외 단지는 절대 출력하지 마십시오)

🥇 1위: 송파파크데일1단지 [지역: 송파구] | 총점=87.5
  가격: 90,000만원 | 2026-04-15 | 84.13㎡ | 4층
  출퇴근점수: 100점 | 19분 | 잠실역 (2호선·8호선)
  환금성점수: 100점 (812세대)
  생활편의점수: 100점
  학군점수: 100점
  가격상승가능성점수: 50점
```
raw 필드 노출 없이 모든 점수가 명시되어 LLM이 재계산 불가.

---

## 최종 검증 결과 (2026-04-20 Job4 재실행)

### Python 파이프라인 출력
```
예산 8.7억 ±10% → 5건 (전체 29건)
preference_rules 필터 후: 3건
horea_validator: 뉴스 기사 없음 → 중립값 적용
상위 3개 선정
LLM 호출: synthesizer in=1,918 out=1,561
```

### LLM 출력 검증

| 항목 | 기대값 | 실제값 | 결과 |
|------|--------|--------|------|
| 후보 수 | 3개 | 3개 | ✅ |
| 1위 총점 | 87.5점 | 87.5점 | ✅ |
| 2위 총점 | 75.0점 | 75.0점 | ✅ |
| 3위 총점 | 61.1점 | 61.1점 | ✅ |
| 금강캐스빌 환금성 | 50점 (중립) | 50점 | ✅ |
| 가격상승가능성 (전체) | 50점 (중립) | 50점 | ✅ |
| 가격 표시 | X억 Y천만원 | 9억 0천만원 | ✅ |
| 역 정보 | 잠실역 (2호선·8호선) | 잠실역 (2호선·8호선) | ✅ |
| 이매촌(청구) phantom 4위 | 없음 | 없음 | ✅ |

### 토큰 비용
- Job4 1회 실행: **+1원** (2026-04-19 첫 실행 기준, 387→388원)
- 당월 잔여 예산 여유 충분

---

## E2E 검증 면제

- **사유:** 화면단 변경 없음 — 백엔드 리포트 생성 로직 및 LLM 프롬프트만 변경
- **변경 범위:** `src/modules/real_estate/` 내부, Slack 전송 데이터 포맷
- **Slack 리포트 품질 검증:** Job4 직접 실행 후 blocks 출력 육안 확인으로 대체
