# POI Scoring Enhancement — 업종 다양성 + 혐오시설 탐지

**작성일:** 2026-05-10  
**브랜치:** `feature/poi-scoring-enhancement`

---

## 목표

1. **업종 다양성 지수** — `CommercialDimension`을 단순 카운트 기반에서 규모(50%) + 다양성(50%) 복합 점수로 개선
2. **혐오시설 탐지** — 화장장·소각장 등 9개 키워드를 POI 수집에 추가하고 `NuisanceDimension`으로 실거주·투자 양쪽 점수에 반영

---

## 아키텍처

```
[업종 다양성]
config.yaml (diversity_min_count 임계값)
    ↓
CommercialDimension.score()
    volume_score (restaurant + cafe 합계, 기존 로직) × 0.5
  + diversity_score (카테고리 출현 개수 / 6 × 100) × 0.5
    ↓
LocationScorer → 기존 흐름 유지

[혐오시설]
PoiCollector
    ↓ 9개 키워드 개별 API 호출
    nuisance_high_count (고강도 키워드 탐지 수)
    nuisance_mid_count  (중강도 키워드 탐지 수)
    ↓
poi_cache 테이블 (2컬럼 추가 + _migrate())
PoiData (2필드 추가)
    ↓
NuisanceDimension.score()
    high > 0 → 20점 / mid > 0 → 60점 / 없음 → 100점
    ↓
LocationScorer (residential + investment 양쪽 등록)
```

---

## 데이터 모델

### PoiData 신규 필드

```python
nuisance_high_count: int = 0  # 고강도 혐오시설 탐지 키워드 수
nuisance_mid_count:  int = 0  # 중강도 혐오시설 탐지 키워드 수
```

### poi_cache 테이블 신규 컬럼

```sql
ALTER TABLE poi_cache ADD COLUMN nuisance_high_count INTEGER DEFAULT 0;
ALTER TABLE poi_cache ADD COLUMN nuisance_mid_count  INTEGER DEFAULT 0;
```

기존 `_migrate()` 패턴(try/except per column) 동일 적용.

### 혐오시설 쿼리 정의

| 키워드 | 반경 | 강도 | 근거 |
|--------|------|------|------|
| `화장장` | 1000m | HIGH | 기피 강도 최고, 가격 10~20% 디스카운트 실증 |
| `납골당` | 1000m | HIGH | 동일 |
| `자원회수시설` | 1500m | HIGH | 악취·초미세먼지 영향권 |
| `하수처리장` | 1500m | HIGH | 악취 민원 집중 구간 |
| `교도소` | 1000m | HIGH | 심리적 낙인 + 체감 치안 불안 |
| `구치소` | 1000m | HIGH | 동일 |
| `도축장` | 1000m | HIGH | 악취·운반 차량 동선 |
| `장례식장` | 500m | MID | 500m 이내 가격 영향 확인 |
| `변전소` | 300m | MID | 300m 이내 전자파 민원 집중 |

`nuisance_high_count` = HIGH 키워드 중 결과 1개 이상 반환한 키워드 수  
`nuisance_mid_count` = MID 키워드 중 결과 1개 이상 반환한 키워드 수  
(개수 합산이 아닌 탐지 여부 기반)

**제외 키워드:** `공장`(false positive 과다), `발전소`(주거지 인근 없음), `군부대`(이전 호재로 작용)

---

## 점수 계산 로직

### CommercialDimension (수정)

```python
def score(self, candidate: dict) -> int:
    restaurant  = candidate.get("poi_restaurant_count",  0) or 0
    cafe        = candidate.get("poi_cafe_count",        0) or 0
    convenience = candidate.get("poi_convenience_count", 0) or 0
    pharmacy    = candidate.get("poi_pharmacy_count",    0) or 0
    medical     = candidate.get("poi_medical_count",     0) or 0
    mart        = candidate.get("poi_marts_count",       0) or 0

    cfg  = self._config.get("thresholds", {}).get("commercial", {})
    high = cfg.get("high_count",   30)
    mid  = cfg.get("medium_count", 10)

    # 50% 규모 점수 (기존)
    total = restaurant + cafe
    volume_score = 100 if total >= high else (60 if total >= mid else 20)

    # 50% 다양성 점수
    min_c = cfg.get("diversity_min_count", {})
    checks = [
        (restaurant,  min_c.get("restaurant",  3)),
        (cafe,        min_c.get("cafe",        2)),
        (convenience, min_c.get("convenience", 1)),
        (pharmacy,    min_c.get("pharmacy",    1)),
        (medical,     min_c.get("medical",     1)),
        (mart,        min_c.get("mart",        1)),
    ]
    present = sum(1 for count, threshold in checks if count >= threshold)
    diversity_score = round(present / len(checks) * 100)

    return round(volume_score * 0.5 + diversity_score * 0.5)
```

### NuisanceDimension (신규)

```python
class NuisanceDimension(BaseDimension):
    @property
    def dimension_id(self) -> str:
        return "nuisance"

    def score(self, candidate: dict) -> int:
        high = candidate.get("poi_nuisance_high_count", 0) or 0
        mid  = candidate.get("poi_nuisance_mid_count",  0) or 0

        cfg = self._config.get("thresholds", {}).get("nuisance", {})
        if high > 0:
            return cfg.get("high_score", 20)
        if mid > 0:
            return cfg.get("mid_score", 60)
        return cfg.get("clean_score", 100)
```

### 점수 예시

| 상황 | high | mid | 점수 |
|------|------|-----|------|
| 혐오시설 없음 | 0 | 0 | **100** |
| 장례식장만 500m 이내 | 0 | 1 | **60** |
| 화장장 1km 이내 | 1 | 0 | **20** |
| 화장장 + 장례식장 | 1 | 1 | **20** (고강도 우선) |
| POI 미수집 | — | — | **50** (data_absent_neutral) |

---

## config.yaml 변경

```yaml
scoring:
  data_absent_neutral: 50

  thresholds:
    commercial:
      high_count: 30
      medium_count: 10
      diversity_min_count:
        restaurant: 3
        cafe: 2
        convenience: 1
        pharmacy: 1
        medical: 1
        mart: 1

    nuisance:
      high_score: 20
      mid_score: 60
      clean_score: 100

  residential_dimensions:
    - {id: transportation, weight: 0.25}
    - {id: education,      weight: 0.20}
    - {id: living_infra,   weight: 0.20}
    - {id: medical,        weight: 0.15}
    - {id: nature,         weight: 0.20}
    - {id: nuisance,       weight: 0.15}   # 신규

  investment_dimensions:
    - {id: price_potential, weight: 0.30}
    - {id: commercial,      weight: 0.25}
    - {id: liquidity,       weight: 0.20}
    - {id: school_premium,  weight: 0.25}
    - {id: nuisance,        weight: 0.20}  # 신규
```

가중치는 LocationScorer가 `sum(weights)`로 자동 정규화하므로 기존 값 변경 불필요.

---

## 변경 파일 목록

| 파일 | 변경 유형 |
|------|-----------|
| `src/modules/real_estate/poi_collector.py` | PoiData 2필드 + 9개 쿼리 + _migrate() + _save/_load_cache |
| `src/modules/real_estate/location/dimensions/commercial.py` | 다양성 로직 추가 |
| `src/modules/real_estate/location/dimensions/nuisance.py` | 신규 생성 |
| `src/modules/real_estate/location/location_scorer.py` | _DIMENSION_REGISTRY에 nuisance 등록 |
| `src/modules/real_estate/config.yaml` | diversity_min_count + nuisance 섹션 + Dimension 등록 |
| `src/modules/real_estate/report_orchestrator.py` | candidate dict에 poi_nuisance_* 필드 매핑 |
| `tests/modules/real_estate/location/test_dimensions.py` | Commercial 5케이스 + Nuisance 5케이스 추가 |
| `tests/modules/real_estate/test_poi_collector.py` | 혐오시설 수집 케이스 추가 |

---

## 테스트 케이스

### CommercialDimension

계산 방식: `round(volume_score × 0.5 + diversity_score × 0.5)`  
`diversity_score = round(present / 6 × 100)`

| 케이스 | restaurant | cafe | 기타 | volume | diversity | **기대값** |
|--------|------------|------|------|--------|-----------|------------|
| 규모 HIGH + 다양성 ALL | 45 | 20 | 전부 임계 충족 | 100 | 100 (6/6) | **100** |
| 규모 HIGH + 다양성 3/6 | 45 | 20 | convenience=5, 나머지 0 | 100 | 50 (3/6) | **75** |
| 규모 LOW + 다양성 ALL | 3 | 2 | 전부 임계 충족 | 20 | 100 (6/6) | **60** |
| 음식점·카페 골목 (2카테고리) | 45 | 20 | 0 | 100 | 33 (2/6) | **67** |
| 경계: restaurant=3 충족, cafe=1 미달, 나머지 0 | 3 | 1 | 0 | 20 | 17 (1/6) | **19** |

### NuisanceDimension

| 케이스 | high | mid | 기대값 |
|--------|------|-----|--------|
| 혐오시설 없음 | 0 | 0 | **100** |
| 중강도만 | 0 | 1 | **60** |
| 고강도 탐지 | 1 | 0 | **20** |
| 고강도+중강도 복합 | 2 | 1 | **20** |
| data absent | — | — | **50** |

### PoiCollector

- 혐오시설 탐지 시 `nuisance_high_count` 정확히 집계
- 혐오시설 없음 시 0으로 저장
- DB 마이그레이션 후 기존 레코드 `nuisance_*` DEFAULT 0 유지
