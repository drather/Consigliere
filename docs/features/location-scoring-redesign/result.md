# Location Scoring Redesign — Result

**완료일:** 2026-05-09
**브랜치:** `feature/location-scoring-redesign`

---

## 구현 결과

### 신규 파일

| 파일 | 역할 |
|------|------|
| `src/modules/real_estate/location/dimensions/base.py` | BaseDimension 추상 클래스 |
| `src/modules/real_estate/location/dimensions/transportation.py` | 교통 접근성 차원 |
| `src/modules/real_estate/location/dimensions/education.py` | 교육 환경 차원 |
| `src/modules/real_estate/location/dimensions/living_infra.py` | 생활 인프라 차원 |
| `src/modules/real_estate/location/dimensions/medical.py` | 의료 접근성 차원 |
| `src/modules/real_estate/location/dimensions/nature.py` | 자연 환경 차원 |
| `src/modules/real_estate/location/dimensions/commercial.py` | 상권 활성도 차원 |
| `src/modules/real_estate/location/dimensions/price_potential.py` | 가격 상승 잠재력 차원 |
| `src/modules/real_estate/location/dimensions/liquidity.py` | 거래 유동성 차원 |
| `src/modules/real_estate/location/dimensions/school_premium.py` | 학군 프리미엄 차원 |
| `src/modules/real_estate/location/location_scorer.py` | LocationScorer + LocationScore |
| `src/modules/real_estate/location/location_repository.py` | SQLite 영속화 |
| `tests/modules/real_estate/location/test_dimensions.py` | Dimension 단위 테스트 25개 |
| `tests/modules/real_estate/location/test_location_scorer.py` | Scorer 통합 테스트 8개 |
| `tests/modules/real_estate/test_poi_collector.py` | POI Collector 테스트 7개 |

### 수정 파일

| 파일 | 변경 내용 |
|------|----------|
| `src/modules/real_estate/poi_collector.py` | 6개 신규 카테고리 + DB 마이그레이션 |
| `src/modules/real_estate/config.yaml` | scoring 섹션 전면 재작성 |
| `src/modules/real_estate/report_orchestrator.py` | LocationScorer로 교체 + POI 필드 매핑 |
| `src/modules/real_estate/insight_orchestrator.py` | LocationScorer로 교체 |
| `src/api/routers/real_estate.py` | POST /jobs/poi/collect 추가 |
| `src/dashboard/views/real_estate.py` | 실거주/투자 2-score 카드 추가 |

### 삭제 파일

- `src/modules/real_estate/scoring.py` (ScoringEngine)
- `tests/modules/real_estate/test_scoring.py`
- `tests/modules/real_estate/test_scoring_liquidity.py`
- `tests/modules/real_estate/test_scoring_neutral_defaults.py`

---

## 테스트 결과

```
649 passed, 11 failed (all pre-existing)
```

- **location/ 테스트:** 33개 PASS (dimensions 25 + scorer 8)
- **poi_collector 테스트:** 7개 PASS
- **school 테스트:** 45개 PASS (test_scoring_engine 1개 제거)
- **pre-existing 실패:** career, dashboard_ui, n8n_news, news_insight, insight_report, tab5 (본 작업과 무관)

---

## 아키텍처 개요

```
config.yaml (scoring 섹션)
    ↓ 가중치/임계값 주입
LocationScorer
    ├── _DIMENSION_REGISTRY (9개 차원)
    ├── residential_dimensions × 5 → residential_total (0-100)
    └── investment_dimensions × 4 → investment_total (0-100)
                                          ↓
                                   LocationRepository (location_scores 테이블)
                                          ↓
                                   Dashboard 2-score 카드 (읽기 전용)
```

---

## 데일리 POI Job

```
POST /jobs/poi/collect?limit=10
  → apt_master에서 POI 미수집 or 만료 단지 선택
  → PoiCollector.collect() × limit
  → poi_cache 적재
  → {"collected": N, "requested": 10}
```

---

## E2E 검증 면제

- **사유:** 대시보드 점수 카드는 신규 추가이나, `location_scores` 테이블에 데이터가 없으면 "리포트 생성 후 표시됩니다" 안내 메시지가 표시됨 — E2E 환경에서 리포트 생성 없이는 유효한 점수가 없어 UI 검증 불가
- **변경 범위:** `src/modules/real_estate/location/`, `src/modules/real_estate/poi_collector.py`, `src/modules/real_estate/report_orchestrator.py`, `src/modules/real_estate/insight_orchestrator.py`, `src/api/routers/real_estate.py`, `src/dashboard/views/real_estate.py`
- **백엔드 단위 테스트:** 649 PASS (완료)
