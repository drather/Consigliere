# Location Scoring Redesign — 실거주/투자 이중 점수 체계

**작성일:** 2026-05-09
**브랜치:** `feature/location-scoring-redesign`
**참고 상세 스펙:** `docs/superpowers/specs/2026-05-09-location-scoring-redesign.md`

---

## 목표

기존 단일 종합점수(`ScoringEngine` 5차원)를 **실거주 점수 + 투자 점수** 이중 체계로 전면 재설계한다. 항목 추가가 용이한 유연한 아키텍처를 적용하고, POI 수집 카테고리를 6개 확장하여 상권·입지 분석을 가능하게 한다.

---

## 아키텍처

- `BaseDimension` 추상 클래스 기반 차원 구현체 9개
- `config.yaml` 가중치 정의 (코드 변경 없이 조정 가능)
- `LocationScorer`가 두 점수 계산 + `LocationRepository` SQLite 영속화
- 기존 `ScoringEngine` 제거

---

## 차원 구성

### 실거주 점수 (Residential Score)

| Dimension ID | 클래스 | 가중치 |
|---|---|---|
| `transportation` | TransportationDimension | 0.25 |
| `education` | EducationDimension | 0.20 |
| `living_infra` | LivingInfraDimension | 0.20 |
| `medical` | MedicalDimension | 0.15 |
| `nature` | NatureDimension | 0.20 |

### 투자 점수 (Investment Score)

| Dimension ID | 클래스 | 가중치 |
|---|---|---|
| `price_potential` | PricePotentialDimension | 0.30 |
| `commercial` | CommercialDimension | 0.25 |
| `liquidity` | LiquidityDimension | 0.20 |
| `school_premium` | SchoolPremiumDimension | 0.25 |

---

## 데이터 모델

### PoiData 신규 필드

| 필드 | 쿼리 | 반경 |
|---|---|---|
| `convenience_count` | 편의점 | 500m |
| `pharmacy_count` | 약국 | 500m |
| `medical_count` | 병원 | 1000m |
| `park_nearest_m` | 공원 최근접 거리(m) | 1000m |
| `restaurant_count` | 음식점 | 500m (3페이지) |
| `cafe_count` | 카페 | 500m (3페이지) |

### LocationScore dataclass

```python
@dataclass
class LocationScore:
    complex_code: str
    residential_total: int       # 0-100
    residential_breakdown: dict  # {dimension_id: score}
    investment_total: int        # 0-100
    investment_breakdown: dict
    scored_at: str
```

### location_scores 테이블 (SQLite)

| 컬럼 | 타입 |
|---|---|
| complex_code | TEXT UNIQUE |
| residential_total | INTEGER |
| residential_breakdown | TEXT (JSON) |
| investment_total | INTEGER |
| investment_breakdown | TEXT (JSON) |
| scored_at | TEXT |

---

## 데이터 흐름

- **수집 트리거:** 리포트 생성 시 on-demand + 데일리 Job(`POST /jobs/poi/collect`) 선제 워밍
- **대시보드:** `location_scores` 테이블 읽기 전용 (API 호출 없음)

---

## 파일 구조

```
신규:
  src/modules/real_estate/location/__init__.py
  src/modules/real_estate/location/dimensions/{base,transportation,education,
    living_infra,medical,nature,commercial,price_potential,liquidity,school_premium}.py
  src/modules/real_estate/location/location_scorer.py
  src/modules/real_estate/location/location_repository.py
  tests/modules/real_estate/location/test_dimensions.py
  tests/modules/real_estate/location/test_location_scorer.py

수정:
  src/modules/real_estate/poi_collector.py
  src/modules/real_estate/config.yaml
  src/modules/real_estate/report_orchestrator.py
  src/modules/real_estate/insight_orchestrator.py
  src/api/routers/real_estate.py
  src/dashboard/views/real_estate.py

삭제:
  src/modules/real_estate/scoring.py
  tests/modules/real_estate/test_scoring.py
```
