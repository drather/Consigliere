# POI Scoring Enhancement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** CommercialDimension에 업종 다양성(규모 50% + 다양성 50%) 추가, 혐오시설 9개 키워드 POI 수집 + NuisanceDimension으로 실거주·투자 점수에 반영.

**Architecture:** PoiCollector에 9개 혐오시설 쿼리를 추가해 `nuisance_high_count / nuisance_mid_count`를 poi_cache에 저장하고, NuisanceDimension이 이 값을 읽어 100/60/20 점수를 반환. CommercialDimension은 기존 volume 로직 50% + 카테고리 존재 여부 기반 diversity 50%로 변경.

**Tech Stack:** Python, SQLite (poi_cache), Kakao Local API, pytest, PyYAML

---

## 파일 구조

| 파일 | 변경 유형 | 책임 |
|------|-----------|------|
| `src/modules/real_estate/location/dimensions/commercial.py` | 수정 | volume + diversity 복합 점수 |
| `src/modules/real_estate/location/dimensions/nuisance.py` | **신규** | 혐오시설 점수 (HIGH/MID/CLEAN) |
| `src/modules/real_estate/location/location_scorer.py` | 수정 | nuisance 레지스트리 등록 |
| `src/modules/real_estate/config.yaml` | 수정 | diversity_min_count, nuisance 임계값, dimension 목록 |
| `src/modules/real_estate/poi_collector.py` | 수정 | PoiData 2필드, 9개 쿼리, DB 마이그레이션 |
| `src/modules/real_estate/report_orchestrator.py` | 수정 | _enrich_with_poi nuisance 필드 매핑 |
| `tests/modules/real_estate/location/test_dimensions.py` | 수정 | Commercial 테스트 업데이트 + Nuisance 5케이스 |
| `tests/modules/real_estate/test_poi_collector.py` | 수정 | 혐오시설 수집 케이스, TTL 테스트 수정 |

---

## Task 1: CommercialDimension — 업종 다양성 로직

**Files:**
- Modify: `src/modules/real_estate/location/dimensions/commercial.py`
- Test: `tests/modules/real_estate/location/test_dimensions.py`

- [ ] **Step 1: 기존 CommercialDimension 테스트 3개를 새 기대값으로 업데이트**

새 공식: `round(volume_score × 0.5 + diversity_score × 0.5)`
- `volume_score`: restaurant+cafe 합계 기반 (100/60/20)
- `diversity_score`: 기본 `diversity_min_count` = {restaurant:3, cafe:2, 나머지:1}

기존 3개 테스트를 아래 값으로 수정 (`tests/modules/real_estate/location/test_dimensions.py`):

```python
# ── CommercialDimension ──────────────────────────────────────
def test_commercial_high():
    cfg = {"high_count": 30, "medium_count": 10, "data_absent_neutral": 50}
    dim = CommercialDimension(cfg)
    c = {"poi_restaurant_count": 25, "poi_cafe_count": 10}
    # volume: 35>=30 → 100; diversity: restaurant(25>=3✅) cafe(10>=2✅) others(0) → 2/6*100=33
    # round(100*0.5 + 33*0.5) = round(66.5) = 67
    assert dim.score(c) == 67

def test_commercial_medium():
    cfg = {"high_count": 30, "medium_count": 10, "data_absent_neutral": 50}
    dim = CommercialDimension(cfg)
    c = {"poi_restaurant_count": 8, "poi_cafe_count": 5}
    # volume: 13>=10 → 60; diversity: restaurant(8>=3✅) cafe(5>=2✅) → 2/6*100=33
    # round(60*0.5 + 33*0.5) = round(46.5) = 47
    assert dim.score(c) == 47

def test_commercial_low():
    cfg = {"high_count": 30, "medium_count": 10, "data_absent_neutral": 50}
    dim = CommercialDimension(cfg)
    c = {"poi_restaurant_count": 3, "poi_cafe_count": 2}
    # volume: 5<10 → 20; diversity: restaurant(3>=3✅) cafe(2>=2✅) → 2/6*100=33
    # round(20*0.5 + 33*0.5) = round(26.5) = 27
    assert dim.score(c) == 27
```

- [ ] **Step 2: 신규 다양성 테스트 케이스 추가** (기존 3개 아래에 이어서)

```python
def test_commercial_high_volume_all_diversity():
    cfg = {
        "high_count": 30, "medium_count": 10, "data_absent_neutral": 50,
        "diversity_min_count": {"restaurant": 3, "cafe": 2, "convenience": 1,
                                "pharmacy": 1, "medical": 1, "mart": 1},
    }
    dim = CommercialDimension(cfg)
    c = {
        "poi_restaurant_count": 45, "poi_cafe_count": 20,
        "poi_convenience_count": 5, "poi_pharmacy_count": 3,
        "poi_medical_count": 3, "poi_marts_count": 1,
    }
    # volume: 65>=30 → 100; diversity: 6/6 → 100
    assert dim.score(c) == 100

def test_commercial_high_volume_3_diversity():
    cfg = {
        "high_count": 30, "medium_count": 10, "data_absent_neutral": 50,
        "diversity_min_count": {"restaurant": 3, "cafe": 2, "convenience": 1,
                                "pharmacy": 1, "medical": 1, "mart": 1},
    }
    dim = CommercialDimension(cfg)
    c = {
        "poi_restaurant_count": 45, "poi_cafe_count": 20,
        "poi_convenience_count": 5,
        "poi_pharmacy_count": 0, "poi_medical_count": 0, "poi_marts_count": 0,
    }
    # volume: 65>=30 → 100; diversity: 3/6 → 50
    # round(100*0.5 + 50*0.5) = 75
    assert dim.score(c) == 75

def test_commercial_low_volume_all_diversity():
    cfg = {
        "high_count": 30, "medium_count": 10, "data_absent_neutral": 50,
        "diversity_min_count": {"restaurant": 3, "cafe": 2, "convenience": 1,
                                "pharmacy": 1, "medical": 1, "mart": 1},
    }
    dim = CommercialDimension(cfg)
    c = {
        "poi_restaurant_count": 3, "poi_cafe_count": 2,
        "poi_convenience_count": 1, "poi_pharmacy_count": 1,
        "poi_medical_count": 1, "poi_marts_count": 1,
    }
    # volume: 5<10 → 20; diversity: 6/6 → 100
    # round(20*0.5 + 100*0.5) = 60
    assert dim.score(c) == 60

def test_commercial_single_category_dominant():
    cfg = {"high_count": 30, "medium_count": 10, "data_absent_neutral": 50}
    dim = CommercialDimension(cfg)
    c = {"poi_restaurant_count": 45, "poi_cafe_count": 20}
    # volume: 65>=30 → 100; diversity: restaurant(✅) cafe(✅) others(0) → 2/6=33
    # round(100*0.5 + 33*0.5) = 67
    assert dim.score(c) == 67

def test_commercial_diversity_boundary():
    cfg = {"high_count": 30, "medium_count": 10, "data_absent_neutral": 50}
    dim = CommercialDimension(cfg)
    c = {"poi_restaurant_count": 3, "poi_cafe_count": 1}
    # restaurant(3>=3✅) cafe(1<2❌) → 1/6=17
    # volume: 4<10 → 20; round(20*0.5 + 17*0.5) = round(18.5) = 19
    assert dim.score(c) == 19
```

- [ ] **Step 3: 테스트 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/location/test_dimensions.py -k "commercial" -v
```

Expected: 기존 3개 FAIL (wrong expected values), 신규 5개 FAIL (function not implemented yet)

- [ ] **Step 4: CommercialDimension 구현**

`src/modules/real_estate/location/dimensions/commercial.py` 전체 교체:

```python
from modules.real_estate.location.dimensions.base import BaseDimension


class CommercialDimension(BaseDimension):
    @property
    def dimension_id(self) -> str:
        return "commercial"

    def score(self, candidate: dict) -> int:
        restaurant  = candidate.get("poi_restaurant_count",  0) or 0
        cafe        = candidate.get("poi_cafe_count",        0) or 0
        convenience = candidate.get("poi_convenience_count", 0) or 0
        pharmacy    = candidate.get("poi_pharmacy_count",    0) or 0
        medical     = candidate.get("poi_medical_count",     0) or 0
        mart        = candidate.get("poi_marts_count",       0) or 0

        cfg  = self._config
        high = cfg.get("high_count",   30)
        mid  = cfg.get("medium_count", 10)

        total = restaurant + cafe
        volume_score = 100 if total >= high else (60 if total >= mid else 20)

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

- [ ] **Step 5: 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/location/test_dimensions.py -k "commercial" -v
```

Expected: 8개 PASS

- [ ] **Step 6: 커밋**

```bash
git add src/modules/real_estate/location/dimensions/commercial.py \
        tests/modules/real_estate/location/test_dimensions.py
git commit -m "feat(commercial): 업종 다양성 지수 — volume 50% + diversity 50%"
```

---

## Task 2: NuisanceDimension — 신규 파일

**Files:**
- Create: `src/modules/real_estate/location/dimensions/nuisance.py`
- Test: `tests/modules/real_estate/location/test_dimensions.py`

- [ ] **Step 1: NuisanceDimension 테스트 추가**

`tests/modules/real_estate/location/test_dimensions.py` 맨 아래에 추가:

```python
from modules.real_estate.location.dimensions.nuisance import NuisanceDimension

_NUISANCE_CFG = {"high_score": 20, "mid_score": 60, "clean_score": 100, "data_absent_neutral": 50}

# ── NuisanceDimension ────────────────────────────────────────
def test_nuisance_clean():
    dim = NuisanceDimension(_NUISANCE_CFG)
    assert dim.score({"poi_nuisance_high_count": 0, "poi_nuisance_mid_count": 0}) == 100

def test_nuisance_mid_only():
    dim = NuisanceDimension(_NUISANCE_CFG)
    assert dim.score({"poi_nuisance_high_count": 0, "poi_nuisance_mid_count": 1}) == 60

def test_nuisance_high():
    dim = NuisanceDimension(_NUISANCE_CFG)
    assert dim.score({"poi_nuisance_high_count": 1, "poi_nuisance_mid_count": 0}) == 20

def test_nuisance_high_dominates_mid():
    dim = NuisanceDimension(_NUISANCE_CFG)
    assert dim.score({"poi_nuisance_high_count": 2, "poi_nuisance_mid_count": 1}) == 20

def test_nuisance_absent_data_returns_neutral():
    # 필드 자체가 없으면 geocoding 실패 = 미수집 → neutral
    dim = NuisanceDimension(_NUISANCE_CFG)
    assert dim.score({}) == 50
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/location/test_dimensions.py -k "nuisance" -v
```

Expected: 5개 FAIL with "cannot import name 'NuisanceDimension'"

- [ ] **Step 3: NuisanceDimension 구현**

`src/modules/real_estate/location/dimensions/nuisance.py` 신규 생성:

```python
from modules.real_estate.location.dimensions.base import BaseDimension


class NuisanceDimension(BaseDimension):
    @property
    def dimension_id(self) -> str:
        return "nuisance"

    def score(self, candidate: dict) -> int:
        if "poi_nuisance_high_count" not in candidate:
            return self._config.get("data_absent_neutral", 50)

        high = candidate.get("poi_nuisance_high_count") or 0
        mid  = candidate.get("poi_nuisance_mid_count")  or 0

        cfg = self._config
        if high > 0:
            return cfg.get("high_score", 20)
        if mid > 0:
            return cfg.get("mid_score", 60)
        return cfg.get("clean_score", 100)
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/location/test_dimensions.py -k "nuisance" -v
```

Expected: 5개 PASS

- [ ] **Step 5: 커밋**

```bash
git add src/modules/real_estate/location/dimensions/nuisance.py \
        tests/modules/real_estate/location/test_dimensions.py
git commit -m "feat(nuisance): NuisanceDimension — 혐오시설 점수 HIGH/MID/CLEAN"
```

---

## Task 3: LocationScorer 레지스트리 + config.yaml

**Files:**
- Modify: `src/modules/real_estate/location/location_scorer.py`
- Modify: `src/modules/real_estate/config.yaml`

- [ ] **Step 1: location_scorer.py — NuisanceDimension import + 레지스트리 등록**

`src/modules/real_estate/location/location_scorer.py`:

imports 맨 아래에 추가:
```python
from modules.real_estate.location.dimensions.nuisance import NuisanceDimension
```

`_DIMENSION_REGISTRY` dict에 추가:
```python
_DIMENSION_REGISTRY: Dict[str, type] = {
    "transportation":  TransportationDimension,
    "education":       EducationDimension,
    "living_infra":    LivingInfraDimension,
    "medical":         MedicalDimension,
    "nature":          NatureDimension,
    "commercial":      CommercialDimension,
    "price_potential": PricePotentialDimension,
    "liquidity":       LiquidityDimension,
    "school_premium":  SchoolPremiumDimension,
    "nuisance":        NuisanceDimension,   # 신규
}
```

- [ ] **Step 2: config.yaml 업데이트**

`src/modules/real_estate/config.yaml`의 `scoring:` 섹션 전체 교체:

```yaml
scoring:
  data_absent_neutral: 50
  residential_dimensions:
    - id: transportation
      weight: 0.25
    - id: education
      weight: 0.20
    - id: living_infra
      weight: 0.20
    - id: medical
      weight: 0.15
    - id: nature
      weight: 0.20
    - id: nuisance
      weight: 0.15
  investment_dimensions:
    - id: price_potential
      weight: 0.30
    - id: commercial
      weight: 0.25
    - id: liquidity
      weight: 0.20
    - id: school_premium
      weight: 0.25
    - id: nuisance
      weight: 0.20
  thresholds:
    transportation:
      subway_close_min: 5
      commute_high_min: 20
      commute_medium_min: 35
    living_infra:
      high_count: 5
      medium_count: 2
    medical:
      high_count: 3
      medium_count: 1
    nature:
      close_m: 300
      medium_m: 800
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
    liquidity:
      high_households: 500
      medium_households: 300
    school_premium: {}
    price_potential:
      recon_age_years: 30
      recon_far_max: 200
      recon_score_map:
        HIGH: 100
        MEDIUM: 60
        LOW: 20
        COMPLETED: 50
        UNKNOWN: 50
```

- [ ] **Step 3: LocationScorer 통합 테스트 실행**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/location/ -v
```

Expected: 전체 PASS (nuisance 관련 scorer 테스트는 candidate에 nuisance 필드 없음 → neutral 50으로 처리)

- [ ] **Step 4: 커밋**

```bash
git add src/modules/real_estate/location/location_scorer.py \
        src/modules/real_estate/config.yaml
git commit -m "feat(scorer): NuisanceDimension 레지스트리 등록 + config.yaml 업데이트"
```

---

## Task 4: PoiCollector — 혐오시설 수집

**Files:**
- Modify: `src/modules/real_estate/poi_collector.py`
- Test: `tests/modules/real_estate/test_poi_collector.py`

- [ ] **Step 1: 혐오시설 수집 테스트 추가**

`tests/modules/real_estate/test_poi_collector.py` 맨 아래에 추가:

```python
def test_poi_data_has_nuisance_fields():
    poi = PoiData(complex_code="X001")
    assert hasattr(poi, "nuisance_high_count")
    assert hasattr(poi, "nuisance_mid_count")
    assert poi.nuisance_high_count == 0
    assert poi.nuisance_mid_count == 0


def test_nuisance_high_detected(db_path):
    collector = PoiCollector(api_key="test_key", db_path=db_path)
    # 화장장 탐지 → nuisance_high_count=1, mid=0
    crematorium_result = _make_kakao_response([_make_place("서울시립승화원", 800)])
    empty = _make_kakao_response([])

    # 총 20번 API 호출:
    # 기존 11 (지하철역, 초등학교, 중학교, 학원x1page, 마트, 편의점, 약국, 병원, 공원, 음식점x1page, 카페x1page)
    # + 9 혐오시설 (화장장, 납골당, 자원회수시설, 하수처리장, 교도소, 구치소, 도축장, 장례식장, 변전소)
    responses = [empty] * 11 + [crematorium_result] + [empty] * 8

    with patch("requests.get") as mock_get:
        mock_get.side_effect = [MagicMock(status_code=200, json=lambda r=r: r) for r in responses]
        result = collector.collect("NUISANCE_TEST", 37.5, 127.0)

    assert result.nuisance_high_count == 1
    assert result.nuisance_mid_count == 0


def test_nuisance_clean(db_path):
    collector = PoiCollector(api_key="test_key", db_path=db_path)
    empty = _make_kakao_response([])
    responses = [empty] * 20  # 11 기존 + 9 혐오시설 = 모두 empty

    with patch("requests.get") as mock_get:
        mock_get.side_effect = [MagicMock(status_code=200, json=lambda r=r: r) for r in responses]
        result = collector.collect("CLEAN_TEST", 37.5, 127.0)

    assert result.nuisance_high_count == 0
    assert result.nuisance_mid_count == 0


def test_migrate_adds_nuisance_columns():
    _OLD_DDL = """
    CREATE TABLE IF NOT EXISTS poi_cache (
        complex_code TEXT PRIMARY KEY, lat REAL, lng REAL,
        subway_stations TEXT, schools_count INTEGER, academies_count INTEGER,
        marts_count INTEGER, convenience_count INTEGER DEFAULT 0,
        pharmacy_count INTEGER DEFAULT 0, medical_count INTEGER DEFAULT 0,
        park_nearest_m INTEGER DEFAULT 0, restaurant_count INTEGER DEFAULT 0,
        cafe_count INTEGER DEFAULT 0, collected_at TEXT
    );
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        with sqlite3.connect(db_path) as conn:
            conn.executescript(_OLD_DDL)
        PoiCollector(api_key="dummy", db_path=db_path)
        with sqlite3.connect(db_path) as conn:
            cols = {row[1] for row in conn.execute("PRAGMA table_info(poi_cache)")}
        assert "nuisance_high_count" in cols
        assert "nuisance_mid_count" in cols
    finally:
        os.unlink(db_path)
```

- [ ] **Step 2: 기존 TTL 테스트 수정**

`test_collect_refreshes_after_ttl` 에서 14컬럼 INSERT를 named-column으로 교체:

```python
def test_collect_refreshes_after_ttl(self, collector, db_path):
    old_date = (datetime.now() - timedelta(days=40)).strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(db_path)
    conn.execute(
        """INSERT INTO poi_cache
           (complex_code, lat, lng, subway_stations,
            schools_count, academies_count, marts_count,
            convenience_count, pharmacy_count, medical_count,
            park_nearest_m, restaurant_count, cafe_count,
            nuisance_high_count, nuisance_mid_count, collected_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        ("OLD_CODE", 37.0, 127.0, "[]", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, old_date),
    )
    conn.commit()
    conn.close()

    empty = _make_kakao_response([])
    with patch("requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: empty)
        collector.collect("OLD_CODE", 37.0, 127.0)
        assert mock_get.call_count > 0
```

- [ ] **Step 3: 기존 test_collect_returns_poi_data 수정**

9개 혐오시설 응답(empty) 추가:

```python
def test_collect_returns_poi_data(self, collector):
    # ... 기존 mock 변수들 ...
    responses = [
        _make_kakao_response(mock_stations),
        _make_kakao_response(mock_elem),
        _make_kakao_response(mock_middle),
        {"documents": mock_academies, "meta": {"total_count": 15, "is_end": True}},
        _make_kakao_response(mock_marts),
        _make_kakao_response(mock_convenience),
        _make_kakao_response(mock_pharmacies),
        _make_kakao_response(mock_medical),
        _make_kakao_response(mock_parks),
        {"documents": mock_restaurants, "meta": {"total_count": 10, "is_end": True}},
        {"documents": mock_cafes, "meta": {"total_count": 5, "is_end": True}},
        # 9개 혐오시설 쿼리 (모두 empty)
        _make_kakao_response([]),  # 화장장
        _make_kakao_response([]),  # 납골당
        _make_kakao_response([]),  # 자원회수시설
        _make_kakao_response([]),  # 하수처리장
        _make_kakao_response([]),  # 교도소
        _make_kakao_response([]),  # 구치소
        _make_kakao_response([]),  # 도축장
        _make_kakao_response([]),  # 장례식장
        _make_kakao_response([]),  # 변전소
    ]
    # ... 기존 assert들 + 추가:
    assert result.nuisance_high_count == 0
    assert result.nuisance_mid_count == 0
```

- [ ] **Step 4: 테스트 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_poi_collector.py -v
```

Expected: nuisance 관련 테스트 FAIL (field not found)

- [ ] **Step 5: PoiData 필드 추가**

`src/modules/real_estate/poi_collector.py` — `PoiData` dataclass에 추가:

```python
@dataclass
class PoiData:
    complex_code: str = ""
    subway_stations: List[Dict] = field(default_factory=list)
    schools_count: int = 0
    academies_count: int = 0
    marts_count: int = 0
    convenience_count: int = 0
    pharmacy_count: int = 0
    medical_count: int = 0
    park_nearest_m: int = 0
    restaurant_count: int = 0
    cafe_count: int = 0
    nuisance_high_count: int = 0   # 신규: 고강도 혐오시설 탐지 키워드 수
    nuisance_mid_count: int = 0    # 신규: 중강도 혐오시설 탐지 키워드 수
    collected_at: str = ""
    # ... 기존 properties 유지 ...
```

- [ ] **Step 6: _DDL + _migrate() 업데이트**

`poi_collector.py`의 `_migrate()` 메서드에 두 줄 추가:

```python
def _migrate(self) -> None:
    new_cols = [
        ("convenience_count", "INTEGER DEFAULT 0"),
        ("pharmacy_count",    "INTEGER DEFAULT 0"),
        ("medical_count",     "INTEGER DEFAULT 0"),
        ("park_nearest_m",    "INTEGER DEFAULT 0"),
        ("restaurant_count",  "INTEGER DEFAULT 0"),
        ("cafe_count",        "INTEGER DEFAULT 0"),
        ("nuisance_high_count", "INTEGER DEFAULT 0"),  # 신규
        ("nuisance_mid_count",  "INTEGER DEFAULT 0"),  # 신규
    ]
    with sqlite3.connect(self._db_path) as conn:
        for col, typedef in new_cols:
            try:
                conn.execute(f"ALTER TABLE poi_cache ADD COLUMN {col} {typedef}")
            except Exception:
                pass
```

- [ ] **Step 7: 혐오시설 쿼리 상수 + _fetch_and_cache 업데이트**

`PoiCollector` 클래스 상단에 상수 추가:

```python
class PoiCollector:
    STATION_RADIUS = 500
    SCHOOL_RADIUS = 1000
    ACADEMY_RADIUS = 1000
    MART_RADIUS = 1000
    CONVENIENCE_RADIUS = 500
    PHARMACY_RADIUS = 500
    MEDICAL_RADIUS = 1000
    PARK_RADIUS = 1000
    RESTAURANT_RADIUS = 500
    CAFE_RADIUS = 500

    _NUISANCE_HIGH_QUERIES = [
        ("화장장",       1000),
        ("납골당",       1000),
        ("자원회수시설", 1500),
        ("하수처리장",   1500),
        ("교도소",       1000),
        ("구치소",       1000),
        ("도축장",       1000),
    ]
    _NUISANCE_MID_QUERIES = [
        ("장례식장", 500),
        ("변전소",   300),
    ]
```

`_fetch_and_cache` 메서드 — cafes 수집 이후에 추가:

```python
    nuisance_high_count = sum(
        1 for kw, radius in self._NUISANCE_HIGH_QUERIES
        if self._search(kw, lat, lng, radius, size=1)
    )
    nuisance_mid_count = sum(
        1 for kw, radius in self._NUISANCE_MID_QUERIES
        if self._search(kw, lat, lng, radius, size=1)
    )
```

`PoiData` 생성 시 두 필드 추가:

```python
    poi = PoiData(
        complex_code=complex_code,
        subway_stations=self._parse_stations(stations),
        schools_count=len(schools),
        academies_count=len(academies),
        marts_count=len(marts),
        convenience_count=len(convenience),
        pharmacy_count=len(pharmacies),
        medical_count=len(medical),
        park_nearest_m=park_nearest_m,
        restaurant_count=len(restaurants),
        cafe_count=len(cafes),
        nuisance_high_count=nuisance_high_count,  # 신규
        nuisance_mid_count=nuisance_mid_count,    # 신규
        collected_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
```

- [ ] **Step 8: _save_cache + _load_cache 업데이트**

`_save_cache`:

```python
def _save_cache(self, complex_code: str, lat: float, lng: float, poi: PoiData) -> None:
    with sqlite3.connect(self._db_path) as conn:
        conn.execute(
            """INSERT OR REPLACE INTO poi_cache
               (complex_code, lat, lng, subway_stations,
                schools_count, academies_count, marts_count,
                convenience_count, pharmacy_count, medical_count,
                park_nearest_m, restaurant_count, cafe_count,
                nuisance_high_count, nuisance_mid_count, collected_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                complex_code, lat, lng,
                json.dumps(poi.subway_stations, ensure_ascii=False),
                poi.schools_count, poi.academies_count, poi.marts_count,
                poi.convenience_count, poi.pharmacy_count, poi.medical_count,
                poi.park_nearest_m, poi.restaurant_count, poi.cafe_count,
                poi.nuisance_high_count, poi.nuisance_mid_count,
                poi.collected_at,
            ),
        )
```

`_load_cache` — SELECT에 두 컬럼 추가, collected_at 인덱스 12로 변경:

```python
def _load_cache(self, complex_code: str) -> Optional[PoiData]:
    with sqlite3.connect(self._db_path) as conn:
        row = conn.execute(
            """SELECT subway_stations, schools_count, academies_count, marts_count,
                      convenience_count, pharmacy_count, medical_count,
                      park_nearest_m, restaurant_count, cafe_count,
                      nuisance_high_count, nuisance_mid_count, collected_at
               FROM poi_cache WHERE complex_code = ?""",
            (complex_code,),
        ).fetchone()
    if not row:
        return None
    if self._is_expired(row[12]):   # collected_at은 index 12
        return None
    return PoiData(
        complex_code=complex_code,
        subway_stations=json.loads(row[0] or "[]"),
        schools_count=row[1] or 0,
        academies_count=row[2] or 0,
        marts_count=row[3] or 0,
        convenience_count=row[4] or 0,
        pharmacy_count=row[5] or 0,
        medical_count=row[6] or 0,
        park_nearest_m=row[7] or 0,
        restaurant_count=row[8] or 0,
        cafe_count=row[9] or 0,
        nuisance_high_count=row[10] or 0,
        nuisance_mid_count=row[11] or 0,
        collected_at=row[12],
    )
```

- [ ] **Step 9: 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_poi_collector.py -v
```

Expected: 전체 PASS

- [ ] **Step 10: 커밋**

```bash
git add src/modules/real_estate/poi_collector.py \
        tests/modules/real_estate/test_poi_collector.py
git commit -m "feat(poi): 혐오시설 9개 키워드 수집 + nuisance_high/mid_count DB 저장"
```

---

## Task 5: report_orchestrator — nuisance 필드 매핑

**Files:**
- Modify: `src/modules/real_estate/report_orchestrator.py`

- [ ] **Step 1: _enrich_with_poi에 nuisance 필드 매핑 추가**

`src/modules/real_estate/report_orchestrator.py`의 `_enrich_with_poi` 함수에서 `poi.cafe_count` 아래에 추가:

```python
                result["poi_restaurant_count"] = poi.restaurant_count
                result["poi_cafe_count"] = poi.cafe_count
                result["poi_nuisance_high_count"] = poi.nuisance_high_count  # 신규
                result["poi_nuisance_mid_count"]  = poi.nuisance_mid_count   # 신규
```

- [ ] **Step 2: 전체 테스트 스위트 실행**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/ -v --tb=short
```

Expected: 전체 PASS (pre-existing 실패 제외)

- [ ] **Step 3: 커밋**

```bash
git add src/modules/real_estate/report_orchestrator.py
git commit -m "feat(orchestrator): _enrich_with_poi nuisance 필드 매핑 추가"
```

---

## 최종 검증

- [ ] **전체 테스트 실행**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: location/ 33개 + poi_collector 10개+ 포함 전체 PASS

- [ ] **SOP result.md 작성** — `docs/features/poi-scoring-enhancement/result.md`
