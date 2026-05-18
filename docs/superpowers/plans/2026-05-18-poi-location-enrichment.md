# POI 기반 입지분석 고도화 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 데일리 리포트 카드에 "📍 입지 현황" 블록을 추가하고, 학교알리미 전입률(avg_transfer_rate)을 SchoolScore에 저장해 학군 라벨을 정확하게 표시한다.

**Architecture:** TypedDict 계약(`LocationSummaryData`) → 순수 함수 렌더러(`render_location_summary`) → orchestrator enrichment 파이프라인(`_enrich_with_school`) 순서로 하위 계층부터 구축한다. SchoolScore 모델과 Repository에 avg_transfer_rate 필드를 먼저 추가해 상위 코드가 의존할 수 있게 한다.

**Tech Stack:** Python 3.12, TypedDict (typing_extensions), SQLite3, pytest, unittest.mock

---

## 파일 목록

| 변경 | 파일 |
|------|------|
| Modify | `src/modules/real_estate/school/models.py` |
| Modify | `src/modules/real_estate/school/school_repository.py` |
| Modify | `src/modules/real_estate/school/school_service.py` |
| Modify | `src/modules/real_estate/daily_report/report_types.py` |
| Modify | `src/modules/real_estate/daily_report/report_formatter.py` |
| Modify | `src/modules/real_estate/daily_report/daily_report_orchestrator.py` |
| Modify | `src/modules/real_estate/service.py` |
| Modify | `tests/modules/real_estate/school/test_school_repository.py` |
| Modify | `tests/modules/real_estate/daily_report/test_report_formatter.py` |
| Modify | `tests/modules/real_estate/daily_report/test_report_types.py` |
| Create | `tests/modules/real_estate/daily_report/test_report_formatter_location.py` |
| Create | `tests/modules/real_estate/daily_report/test_enrich_school.py` |

---

## Task 1: SchoolScore에 avg_transfer_rate 추가

`SchoolScore` 모델, Repository DDL, upsert/get, SchoolService 계산 결과 저장까지 한번에 처리한다.

**Files:**
- Modify: `src/modules/real_estate/school/models.py`
- Modify: `src/modules/real_estate/school/school_repository.py`
- Modify: `src/modules/real_estate/school/school_service.py`
- Modify: `tests/modules/real_estate/school/test_school_repository.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/modules/real_estate/school/test_school_repository.py` 파일 하단에 추가:

```python
def test_school_score_has_avg_transfer_rate_field():
    """SchoolScore dataclass에 avg_transfer_rate 필드가 존재해야 한다."""
    sc = SchoolScore(
        complex_code="CC001",
        school_kind="total",
        nearby_school_count=3,
        avg_students_per_class=0.0,
        avg_students_per_teacher=14.5,
        score=78,
        collected_at="2026-05-18T00:00:00+00:00",
        avg_transfer_rate=0.065,
    )
    assert sc.avg_transfer_rate == 0.065


def test_upsert_and_get_score_roundtrip_with_transfer_rate():
    """avg_transfer_rate가 저장되고 조회된다."""
    repo = SchoolRepository(db_path=":memory:")
    sc = SchoolScore(
        complex_code="CC_TRANSFER",
        school_kind="total",
        nearby_school_count=4,
        avg_students_per_class=0.0,
        avg_students_per_teacher=15.2,
        score=82,
        collected_at="2026-05-18T00:00:00+00:00",
        avg_transfer_rate=0.072,
    )
    repo.upsert_school_score(sc)
    retrieved = repo.get_score("CC_TRANSFER", "total")
    assert retrieved is not None
    assert retrieved.avg_transfer_rate == 0.072
```

- [ ] **Step 2: 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/school/test_school_repository.py::test_school_score_has_avg_transfer_rate_field tests/modules/real_estate/school/test_school_repository.py::test_upsert_and_get_score_roundtrip_with_transfer_rate -v
```

Expected: `FAILED` — `TypeError: SchoolScore.__init__() got an unexpected keyword argument 'avg_transfer_rate'`

- [ ] **Step 3: 구현 — SchoolScore 모델 변경**

`src/modules/real_estate/school/models.py` — `SchoolScore` dataclass에 필드 추가:

```python
@dataclass
class SchoolScore:
    complex_code: str
    school_kind: str            # "elementary" / "middle" / "high" / "total"
    nearby_school_count: int
    avg_students_per_class: float
    avg_students_per_teacher: float
    score: int                  # 0~100
    collected_at: str
    avg_transfer_rate: float = 0.0   # 전입생 비율 평균 (MVIN_SUM / STDNT_SUM)
```

- [ ] **Step 4: 구현 — SchoolRepository DDL + _migrate + upsert_school_score + _row_to_score 변경**

`src/modules/real_estate/school/school_repository.py`:

**(A) `_DDL` 상수의 `school_scores` 테이블에 컬럼 추가** (CREATE TABLE IF NOT EXISTS이므로 신규 DB에 적용):

```python
CREATE TABLE IF NOT EXISTS school_scores (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    complex_code                TEXT NOT NULL,
    school_kind                 TEXT NOT NULL,
    nearby_school_count         INTEGER NOT NULL DEFAULT 0,
    avg_students_per_class      REAL NOT NULL DEFAULT 0,
    avg_students_per_teacher    REAL NOT NULL DEFAULT 0,
    avg_transfer_rate           REAL NOT NULL DEFAULT 0,
    score                       INTEGER NOT NULL DEFAULT 50,
    collected_at                TEXT NOT NULL,
    UNIQUE(complex_code, school_kind)
);
CREATE INDEX IF NOT EXISTS idx_ss_complex ON school_scores(complex_code);
```

**(B) `_migrate()` 메서드에 마이그레이션 추가** — 기존 DB 호환:

```python
def _migrate(self) -> None:
    with self._conn() as conn:
        try:
            conn.execute(
                "ALTER TABLE school_teacher_records"
                " ADD COLUMN transfer_in_rate REAL NOT NULL DEFAULT 0.0"
            )
        except Exception:
            pass  # column already exists
        try:
            conn.execute(
                "ALTER TABLE school_scores"
                " ADD COLUMN avg_transfer_rate REAL NOT NULL DEFAULT 0"
            )
        except Exception:
            pass  # column already exists
```

**(C) `upsert_school_score()` SQL 변경** — avg_transfer_rate 포함:

```python
def upsert_school_score(self, sc: SchoolScore) -> None:
    sql = """
    INSERT INTO school_scores
        (complex_code, school_kind, nearby_school_count,
         avg_students_per_class, avg_students_per_teacher,
         avg_transfer_rate, score, collected_at)
    VALUES
        (:complex_code, :school_kind, :nearby_school_count,
         :avg_students_per_class, :avg_students_per_teacher,
         :avg_transfer_rate, :score, :collected_at)
    ON CONFLICT(complex_code, school_kind) DO UPDATE SET
        nearby_school_count=excluded.nearby_school_count,
        avg_students_per_class=excluded.avg_students_per_class,
        avg_students_per_teacher=excluded.avg_students_per_teacher,
        avg_transfer_rate=excluded.avg_transfer_rate,
        score=excluded.score,
        collected_at=excluded.collected_at
    """
    with self._conn() as conn:
        conn.execute(sql, {
            "complex_code": sc.complex_code,
            "school_kind": sc.school_kind,
            "nearby_school_count": sc.nearby_school_count,
            "avg_students_per_class": sc.avg_students_per_class,
            "avg_students_per_teacher": sc.avg_students_per_teacher,
            "avg_transfer_rate": sc.avg_transfer_rate,
            "score": sc.score,
            "collected_at": sc.collected_at or datetime.now(timezone.utc).isoformat(),
        })
```

**(D) `_row_to_score()` 함수 변경** — avg_transfer_rate 읽기:

```python
def _row_to_score(r: sqlite3.Row) -> SchoolScore:
    return SchoolScore(
        complex_code=r["complex_code"],
        school_kind=r["school_kind"],
        nearby_school_count=r["nearby_school_count"],
        avg_students_per_class=r["avg_students_per_class"],
        avg_students_per_teacher=r["avg_students_per_teacher"],
        score=r["score"],
        collected_at=r["collected_at"],
        avg_transfer_rate=r["avg_transfer_rate"] if "avg_transfer_rate" in r.keys() else 0.0,
    )
```

- [ ] **Step 5: 구현 — SchoolService.calculate_score() avg_transfer_rate 저장**

`src/modules/real_estate/school/school_service.py` — `calculate_score()` 메서드 마지막 부분에서 `SchoolScore` 생성 시 `avg_transfer_rate` 추가:

```python
        # 7. Persist and return
        result = SchoolScore(
            complex_code=complex_code,
            school_kind="total",
            nearby_school_count=len(nearby),
            avg_students_per_class=0.0,
            avg_students_per_teacher=avg_per_teacher,
            score=score,
            collected_at=now,
            avg_transfer_rate=avg_transfer_rate,   # NEW
        )
        self._repo.upsert_school_score(result)
        return result
```

중간 `if not nearby:` 분기의 neutral result에도 추가:

```python
        if not nearby:
            result = SchoolScore(
                complex_code=complex_code,
                school_kind="total",
                nearby_school_count=0,
                avg_students_per_class=0.0,
                avg_students_per_teacher=0.0,
                score=50,
                collected_at=now,
                avg_transfer_rate=0.0,   # NEW
            )
            self._repo.upsert_school_score(result)
            return result
```

- [ ] **Step 6: 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/school/test_school_repository.py -v
```

Expected: 모든 테스트 PASS

- [ ] **Step 7: 커밋**

```bash
git add src/modules/real_estate/school/models.py \
        src/modules/real_estate/school/school_repository.py \
        src/modules/real_estate/school/school_service.py \
        tests/modules/real_estate/school/test_school_repository.py
git commit -m "feat(school): SchoolScore에 avg_transfer_rate 필드 추가 및 Repository 마이그레이션"
```

---

## Task 2: LocationSummaryData TypedDict 추가

**Files:**
- Modify: `src/modules/real_estate/daily_report/report_types.py`
- Modify: `tests/modules/real_estate/daily_report/test_report_types.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/modules/real_estate/daily_report/test_report_types.py` 파일 하단에 추가:

```python
def test_subway_station_structure():
    from modules.real_estate.daily_report.report_types import SubwayStation
    s: SubwayStation = {"name": "강남", "line": "2호선", "walk_minutes": 8}
    assert s["name"] == "강남"
    assert s["walk_minutes"] == 8


def test_location_summary_data_full():
    from modules.real_estate.daily_report.report_types import LocationSummaryData, SubwayStation
    loc: LocationSummaryData = {
        "subway_stations": [{"name": "강남", "line": "2호선", "walk_minutes": 8}],
        "mart_count": 2,
        "convenience_count": 6,
        "cafe_count": 11,
        "restaurant_count": 38,
        "pharmacy_count": 4,
        "medical_count": 7,
        "park_nearest_m": 300,
        "school_nearby_count": 5,
        "school_transfer_rate": 0.072,
        "school_avg_per_teacher": 14.0,
        "school_score": 85,
        "school_label": "학군 우수",
        "nuisance_high_count": 0,
        "nuisance_mid_count": 0,
    }
    assert loc["mart_count"] == 2
    assert loc["school_label"] == "학군 우수"
    assert loc["school_transfer_rate"] == 0.072


def test_location_summary_data_partial():
    """total=False이므로 키 일부만 있어도 유효하다."""
    from modules.real_estate.daily_report.report_types import LocationSummaryData
    loc: LocationSummaryData = {
        "subway_stations": [],
        "mart_count": 0,
    }
    assert loc["mart_count"] == 0
    assert "school_score" not in loc
```

- [ ] **Step 2: 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/daily_report/test_report_types.py::test_subway_station_structure tests/modules/real_estate/daily_report/test_report_types.py::test_location_summary_data_full -v
```

Expected: `FAILED` — `ImportError: cannot import name 'SubwayStation'`

- [ ] **Step 3: 구현**

`src/modules/real_estate/daily_report/report_types.py` 에 아래 두 클래스 추가 (파일 끝에 추가):

```python
class SubwayStation(TypedDict):
    name: str           # "강남"
    line: str           # "2호선"
    walk_minutes: int   # 도보 분


class LocationSummaryData(TypedDict, total=False):
    # 역세권
    subway_stations: List[SubwayStation]
    # 생활편의
    mart_count: int
    convenience_count: int
    cafe_count: int
    restaurant_count: int
    pharmacy_count: int
    medical_count: int
    # 자연
    park_nearest_m: int     # 0 = 반경 내 없음
    # 학군
    school_nearby_count: int
    school_transfer_rate: float   # 0.0~1.0
    school_avg_per_teacher: float
    school_score: int             # 0~100
    school_label: str             # "학군 우수" / "학군 양호" / "학군 평이"
    # 혐오시설
    nuisance_high_count: int
    nuisance_mid_count: int
```

- [ ] **Step 4: 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/daily_report/test_report_types.py -v
```

Expected: 모든 테스트 PASS

- [ ] **Step 5: 커밋**

```bash
git add src/modules/real_estate/daily_report/report_types.py \
        tests/modules/real_estate/daily_report/test_report_types.py
git commit -m "feat(report-types): SubwayStation, LocationSummaryData TypedDict 추가"
```

---

## Task 3: render_location_summary() 구현

**Files:**
- Modify: `src/modules/real_estate/daily_report/report_formatter.py`
- Create: `tests/modules/real_estate/daily_report/test_report_formatter_location.py`

- [ ] **Step 1: 테스트 파일 생성**

`tests/modules/real_estate/daily_report/test_report_formatter_location.py` 새 파일:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

from modules.real_estate.daily_report.report_formatter import (
    render_location_summary,
    _school_label,
    _extract_location_summary,
)
from modules.real_estate.daily_report.report_types import LocationSummaryData


def _full_loc() -> LocationSummaryData:
    return {
        "subway_stations": [
            {"name": "강남", "line": "2호선", "walk_minutes": 8},
            {"name": "선릉", "line": "분당선", "walk_minutes": 12},
        ],
        "mart_count": 2,
        "convenience_count": 6,
        "cafe_count": 11,
        "restaurant_count": 38,
        "pharmacy_count": 4,
        "medical_count": 7,
        "park_nearest_m": 300,
        "school_nearby_count": 5,
        "school_transfer_rate": 0.072,
        "school_avg_per_teacher": 14.0,
        "school_score": 85,
        "school_label": "학군 우수",
        "nuisance_high_count": 0,
        "nuisance_mid_count": 0,
    }


# ── _school_label ────────────────────────────────────────────────
def test_school_label_high_transfer_rate():
    assert _school_label(0.08, 5) == "학군 우수"

def test_school_label_high_nearby():
    assert _school_label(0.01, 3) == "학군 우수"

def test_school_label_medium_transfer_rate():
    assert _school_label(0.04, 2) == "학군 양호"

def test_school_label_medium_nearby():
    assert _school_label(0.01, 1) == "학군 양호"

def test_school_label_low():
    assert _school_label(0.01, 0) == "학군 평이"

def test_school_label_boundary_high():
    assert _school_label(0.06, 0) == "학군 우수"

def test_school_label_boundary_medium():
    assert _school_label(0.03, 0) == "학군 양호"


# ── render_location_summary ──────────────────────────────────────
def test_render_location_summary_contains_header():
    result = render_location_summary(_full_loc())
    assert "📍 입지 현황" in result

def test_render_location_summary_subway_names():
    result = render_location_summary(_full_loc())
    assert "강남(2호선)" in result
    assert "도보 8분" in result
    assert "선릉(분당선)" in result
    assert "도보 12분" in result

def test_render_location_summary_amenities():
    result = render_location_summary(_full_loc())
    assert "마트 2" in result
    assert "카페 11" in result
    assert "식당 38" in result

def test_render_location_summary_medical():
    result = render_location_summary(_full_loc())
    assert "7곳" in result

def test_render_location_summary_park():
    result = render_location_summary(_full_loc())
    assert "300m" in result

def test_render_location_summary_school_label():
    result = render_location_summary(_full_loc())
    assert "학군 우수" in result

def test_render_location_summary_no_nuisance_row_when_zero():
    result = render_location_summary(_full_loc())
    assert "⚠️" not in result

def test_render_location_summary_nuisance_row_shown():
    loc = dict(_full_loc())
    loc["nuisance_high_count"] = 1
    loc["nuisance_mid_count"] = 0
    result = render_location_summary(loc)
    assert "⚠️" in result
    assert "고위험 1곳" in result

def test_render_location_summary_nuisance_mid_shown():
    loc = dict(_full_loc())
    loc["nuisance_high_count"] = 0
    loc["nuisance_mid_count"] = 2
    result = render_location_summary(loc)
    assert "⚠️" in result
    assert "중위험 2곳" in result

def test_render_location_summary_no_subway():
    loc = dict(_full_loc())
    loc["subway_stations"] = []
    result = render_location_summary(loc)
    assert "역 없음" in result

def test_render_location_summary_no_medical_row_when_zero():
    loc = dict(_full_loc())
    loc["medical_count"] = 0
    result = render_location_summary(loc)
    assert "병원" not in result

def test_render_location_summary_zero_amenity_hidden():
    loc = dict(_full_loc())
    loc["mart_count"] = 0
    result = render_location_summary(loc)
    assert "마트 0" not in result

def test_render_location_summary_no_school_data():
    loc: LocationSummaryData = {
        "subway_stations": [],
        "mart_count": 1,
        "convenience_count": 0,
        "cafe_count": 3,
        "restaurant_count": 10,
        "pharmacy_count": 1,
        "medical_count": 2,
        "park_nearest_m": 0,
        "nuisance_high_count": 0,
        "nuisance_mid_count": 0,
    }
    result = render_location_summary(loc)
    assert "학교 정보 수집 전" in result

def test_render_location_summary_no_park():
    loc = dict(_full_loc())
    loc["park_nearest_m"] = 0
    result = render_location_summary(loc)
    assert "공원 없음" in result or "없음" in result


# ── _extract_location_summary ────────────────────────────────────
def test_extract_location_summary_no_poi_returns_none():
    result = _extract_location_summary({"apt_name": "래미안"})
    assert result is None

def test_extract_location_summary_with_poi():
    from unittest.mock import MagicMock
    mock_poi = MagicMock()
    mock_poi.subway_stations = [
        {"name": "강남", "line": "2호선", "walk_minutes": 8}
    ]
    mock_poi.marts_count = 2
    mock_poi.convenience_count = 6
    mock_poi.cafe_count = 11
    mock_poi.restaurant_count = 38
    mock_poi.pharmacy_count = 4
    mock_poi.medical_count = 7
    mock_poi.park_nearest_m = 300
    mock_poi.nuisance_high_count = 0
    mock_poi.nuisance_mid_count = 0

    c = {
        "_poi": mock_poi,
        "school_score": 85,
        "school_nearby_count": 5,
        "school_transfer_rate": 0.072,
        "school_avg_per_teacher": 14.0,
    }
    result = _extract_location_summary(c)
    assert result is not None
    assert result["mart_count"] == 2
    assert result["school_score"] == 85
    assert result["school_label"] == "학군 우수"

def test_extract_location_summary_without_school_fields():
    from unittest.mock import MagicMock
    mock_poi = MagicMock()
    mock_poi.subway_stations = []
    mock_poi.marts_count = 1
    mock_poi.convenience_count = 0
    mock_poi.cafe_count = 3
    mock_poi.restaurant_count = 12
    mock_poi.pharmacy_count = 2
    mock_poi.medical_count = 1
    mock_poi.park_nearest_m = 0
    mock_poi.nuisance_high_count = 0
    mock_poi.nuisance_mid_count = 0

    c = {"_poi": mock_poi}
    result = _extract_location_summary(c)
    assert result is not None
    assert "school_score" not in result
    assert "school_label" not in result

def test_extract_location_summary_subway_sorted_by_walk():
    from unittest.mock import MagicMock
    mock_poi = MagicMock()
    mock_poi.subway_stations = [
        {"name": "선릉", "line": "분당선", "walk_minutes": 12},
        {"name": "강남", "line": "2호선", "walk_minutes": 8},
        {"name": "역삼", "line": "2호선", "walk_minutes": 15},
    ]
    mock_poi.marts_count = 0
    mock_poi.convenience_count = 0
    mock_poi.cafe_count = 0
    mock_poi.restaurant_count = 0
    mock_poi.pharmacy_count = 0
    mock_poi.medical_count = 0
    mock_poi.park_nearest_m = 0
    mock_poi.nuisance_high_count = 0
    mock_poi.nuisance_mid_count = 0

    c = {"_poi": mock_poi}
    result = _extract_location_summary(c)
    assert result is not None
    stations = result["subway_stations"]
    assert len(stations) == 2
    assert stations[0]["name"] == "강남"   # 8분이 먼저
    assert stations[1]["name"] == "선릉"   # 12분
```

- [ ] **Step 2: 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/daily_report/test_report_formatter_location.py -v
```

Expected: `FAILED` — `ImportError: cannot import name 'render_location_summary'`

- [ ] **Step 3: 구현**

`src/modules/real_estate/daily_report/report_formatter.py` — 파일 상단 import에 추가:

```python
from .report_types import TrendData, CommuteData, LocationSummaryData
```

다음 함수들을 `report_formatter.py`의 `render_commute` 함수 아래에 추가:

```python
def _school_label(transfer_rate: float, nearby: int) -> str:
    if transfer_rate >= 0.06 or nearby >= 3:
        return "학군 우수"
    elif transfer_rate >= 0.03 or nearby >= 1:
        return "학군 양호"
    else:
        return "학군 평이"


def render_location_summary(loc: LocationSummaryData) -> str:
    lines = ["**📍 입지 현황**", ""]

    # 역세권
    stations = loc.get("subway_stations", [])
    if stations:
        station_parts = [
            f"{s['name']}({s['line']}) 도보 {s['walk_minutes']}분"
            for s in stations
        ]
        lines.append(f"🚇 **역세권** {'  ·  '.join(station_parts)}")
    else:
        lines.append("🚇 **역세권** 역 없음")

    # 생활편의
    amenity_parts = []
    if loc.get("mart_count", 0) > 0:
        amenity_parts.append(f"마트 {loc['mart_count']}")
    if loc.get("convenience_count", 0) > 0:
        amenity_parts.append(f"편의점 {loc['convenience_count']}")
    if loc.get("cafe_count", 0) > 0:
        amenity_parts.append(f"카페 {loc['cafe_count']}")
    if loc.get("restaurant_count", 0) > 0:
        amenity_parts.append(f"식당 {loc['restaurant_count']}")
    if loc.get("pharmacy_count", 0) > 0:
        amenity_parts.append(f"약국 {loc['pharmacy_count']}")
    if amenity_parts:
        lines.append(f"🛒 **생활편의** {'  ·  '.join(amenity_parts)}")

    # 의료
    medical = loc.get("medical_count", 0)
    if medical > 0:
        lines.append(f"🏥 **의료** 병원·의원 {medical}곳")

    # 자연
    park_m = loc.get("park_nearest_m", 0)
    if park_m > 0:
        lines.append(f"🌳 **자연** 공원 {park_m}m 이내")
    else:
        lines.append("🌳 **자연** 반경 내 공원 없음")

    # 학군
    school_score = loc.get("school_score")
    if school_score is not None:
        nearby = loc.get("school_nearby_count", 0)
        transfer = loc.get("school_transfer_rate", 0.0)
        per_teacher = loc.get("school_avg_per_teacher", 0.0)
        label = loc.get("school_label", "")
        school_parts = [f"반경 1km 학교 {nearby}곳"]
        if transfer > 0:
            school_parts.append(f"전입률 {transfer * 100:.1f}%")
        if per_teacher > 0:
            school_parts.append(f"교사1인당 학생 {per_teacher:.0f}명")
        lines.append(f"🏫 **학군** {'  ·  '.join(school_parts)} → **{label}**")
    else:
        lines.append("🏫 **학군** 학교 정보 수집 전")

    # 혐오시설 (있을 때만 행 표시)
    high = loc.get("nuisance_high_count", 0)
    mid = loc.get("nuisance_mid_count", 0)
    if high > 0 or mid > 0:
        nuisance_parts = []
        if high > 0:
            nuisance_parts.append(f"고위험 {high}곳")
        if mid > 0:
            nuisance_parts.append(f"중위험 {mid}곳")
        lines.append(f"⚠️ **혐오시설** {'  ·  '.join(nuisance_parts)}")

    return "\n".join(lines)
```

또한 `_extract_location_summary` 함수를 `_extract_commute` 아래에 추가:

```python
def _extract_location_summary(c: dict) -> Optional[LocationSummaryData]:
    poi = c.get("_poi")
    if poi is None:
        return None

    # 역세권 — 도보 시간순 정렬, 최대 2개
    stations = sorted(poi.subway_stations, key=lambda s: s.get("walk_minutes", 99))[:2]
    subway = [
        {"name": s.get("name", "?"), "line": s.get("line", "?"), "walk_minutes": s.get("walk_minutes", 0)}
        for s in stations
    ]

    loc: LocationSummaryData = {
        "subway_stations": subway,
        "mart_count": poi.marts_count,
        "convenience_count": poi.convenience_count,
        "cafe_count": poi.cafe_count,
        "restaurant_count": poi.restaurant_count,
        "pharmacy_count": poi.pharmacy_count,
        "medical_count": poi.medical_count,
        "park_nearest_m": poi.park_nearest_m,
        "nuisance_high_count": poi.nuisance_high_count,
        "nuisance_mid_count": poi.nuisance_mid_count,
    }

    school_score = c.get("school_score")
    if school_score is not None:
        loc["school_nearby_count"] = c.get("school_nearby_count", 0)
        loc["school_transfer_rate"] = c.get("school_transfer_rate", 0.0)
        loc["school_avg_per_teacher"] = c.get("school_avg_per_teacher", 0.0)
        loc["school_score"] = school_score
        loc["school_label"] = _school_label(
            c.get("school_transfer_rate", 0.0),
            c.get("school_nearby_count", 0),
        )

    return loc
```

파일 상단 `Optional` import 확인 — 이미 있으면 생략:
```python
from typing import Dict, List, Optional
```

- [ ] **Step 4: 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/daily_report/test_report_formatter_location.py -v
```

Expected: 모든 테스트 PASS

- [ ] **Step 5: 커밋**

```bash
git add src/modules/real_estate/daily_report/report_formatter.py \
        src/modules/real_estate/daily_report/report_types.py \
        tests/modules/real_estate/daily_report/test_report_formatter_location.py
git commit -m "feat(formatter): render_location_summary, _extract_location_summary, _school_label 추가"
```

---

## Task 4: render_scores() evidence 제거 + build_candidate_card() 순서 변경

기존 `render_scores()` evidence bullets는 새 "📍 입지 현황" 블록과 중복이다. 제거하고 점수 숫자만 표시한다. `build_candidate_card()`에 location 블록을 commute 다음에 삽입한다.

**Files:**
- Modify: `src/modules/real_estate/daily_report/report_formatter.py`
- Modify: `tests/modules/real_estate/daily_report/test_report_formatter.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/modules/real_estate/daily_report/test_report_formatter.py` — 두 테스트를 **각각 올바른 클래스**에 추가:

`TestRenderScores` 클래스에 추가:
```python
    def test_evidence_bullets_not_shown(self):
        from modules.real_estate.daily_report.report_formatter import render_scores
        from modules.real_estate.location.dimension_result import DimensionResult
        res = [DimensionResult(id="transportation", label="🚇 교통", score=80, evidence=["대중교통 22분", "2호선 경로"])]
        result = render_scores(res, [])
        assert "대중교통 22분" not in result
        assert "2호선 경로" not in result
```

`TestBuildCandidateCard` 클래스에 추가:
```python
    def test_build_candidate_card_has_location_block(self):
        """_poi가 있을 때 입지 현황 블록이 포함된다."""
        from modules.real_estate.daily_report.report_formatter import build_candidate_card
        from unittest.mock import MagicMock
        mock_poi = MagicMock()
        mock_poi.subway_stations = [{"name": "강남", "line": "2호선", "walk_minutes": 8}]
        mock_poi.marts_count = 2
        mock_poi.convenience_count = 0
        mock_poi.cafe_count = 5
        mock_poi.restaurant_count = 20
        mock_poi.pharmacy_count = 3
        mock_poi.medical_count = 4
        mock_poi.park_nearest_m = 250
        mock_poi.nuisance_high_count = 0
        mock_poi.nuisance_mid_count = 0
        c = {
            "apt_name": "래미안", "sigungu": "강남구",
            "exclusive_area": 84.0, "household_count": 1200,
            "composite_score": 0.85, "avg_recent_price": 880_000_000,
            "price_change_pct": 2.5,
            "_recent_tx_points": [{"price_eok": 8.8, "deal_date": "2026-05-10"}],
            "commute_transit_minutes": 22, "commute_car_minutes": 15,
            "commute_walk_minutes": None, "_commute_route_summary": "",
            "_location_score": None, "_verdict": "", "_key_points": [],
            "_poi": mock_poi,
        }
        result = build_candidate_card(c)
        assert "📍 입지 현황" in result
        assert "강남(2호선)" in result
```

- [ ] **Step 2: 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/daily_report/test_report_formatter.py::TestRenderScores::test_evidence_bullets_not_shown tests/modules/real_estate/daily_report/test_report_formatter.py::TestRenderScores::test_build_candidate_card_has_location_block -v
```

Expected: `FAILED` — evidence가 아직 출력됨

- [ ] **Step 3: 구현 — render_scores() evidence 제거**

`src/modules/real_estate/daily_report/report_formatter.py` — `render_scores()` 함수 교체:

```python
def render_scores(residential: List, investment: List) -> str:
    if not residential and not investment:
        return ""
    lines = ["**실거주 점수 분석**"]
    for dr in residential:
        lines.append(f"- {dr.label}: **{dr.score}점**")
    lines += ["", "**투자성 점수 분석**"]
    for dr in investment:
        lines.append(f"- {dr.label}: **{dr.score}점**")
    return "\n".join(lines)
```

- [ ] **Step 4: 구현 — build_candidate_card() location 블록 삽입**

`src/modules/real_estate/daily_report/report_formatter.py` — `build_candidate_card()` 함수 교체:

```python
def build_candidate_card(c: dict, index: int = 0) -> str:
    trend = _extract_trend(c)
    commute = _extract_commute(c)
    location = _extract_location_summary(c)
    ls = c.get("_location_score")

    parts = [
        _render_header(c, index),
        render_trend(trend),
        render_commute(commute),
        render_location_summary(location) if location else "",
        render_scores(ls.residential_results, ls.investment_results) if ls else "",
        render_verdict(c.get("_verdict", "")),
        render_keypoints(c.get("_key_points", [])),
    ]
    return "\n\n".join(p for p in parts if p)
```

- [ ] **Step 5: 기존 테스트 업데이트**

`tests/modules/real_estate/daily_report/test_report_formatter.py` — `TestRenderScores.test_renders_residential_and_investment` 에서 evidence 관련 assert 제거:

기존:
```python
    def test_renders_residential_and_investment(self):
        from modules.real_estate.daily_report.report_formatter import render_scores
        from modules.real_estate.location.dimension_result import DimensionResult
        res = [DimensionResult(id="transportation", label="🚇 교통", score=80, evidence=["22분"])]
        inv = [DimensionResult(id="commercial", label="🛍️ 상업", score=60, evidence=["음식점 15개"])]
        result = render_scores(res, inv)
        assert "🚇 교통" in result
        assert "80점" in result
        assert "🛍️ 상업" in result
        assert "음식점 15개" in result
```

변경 후:
```python
    def test_renders_residential_and_investment(self):
        from modules.real_estate.daily_report.report_formatter import render_scores
        from modules.real_estate.location.dimension_result import DimensionResult
        res = [DimensionResult(id="transportation", label="🚇 교통", score=80, evidence=["22분"])]
        inv = [DimensionResult(id="commercial", label="🛍️ 상업", score=60, evidence=["음식점 15개"])]
        result = render_scores(res, inv)
        assert "🚇 교통" in result
        assert "80점" in result
        assert "🛍️ 상업" in result
        assert "음식점 15개" not in result   # evidence는 표시하지 않음
```

- [ ] **Step 6: 전체 formatter 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/daily_report/test_report_formatter.py tests/modules/real_estate/daily_report/test_report_formatter_location.py -v
```

Expected: 모든 테스트 PASS

- [ ] **Step 7: 커밋**

```bash
git add src/modules/real_estate/daily_report/report_formatter.py \
        tests/modules/real_estate/daily_report/test_report_formatter.py
git commit -m "feat(formatter): 입지 현황 블록 build_candidate_card 삽입, render_scores evidence 제거"
```

---

## Task 5: _enrich_with_school() — orchestrator 파이프라인 통합

**Files:**
- Modify: `src/modules/real_estate/daily_report/daily_report_orchestrator.py`
- Create: `tests/modules/real_estate/daily_report/test_enrich_school.py`

- [ ] **Step 1: 테스트 파일 생성**

`tests/modules/real_estate/daily_report/test_enrich_school.py` 새 파일:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

from unittest.mock import MagicMock, patch
from datetime import date

from modules.real_estate.daily_report.daily_report_orchestrator import DailyReportOrchestrator
from modules.real_estate.school.models import SchoolScore


def _make_orchestrator_with_school_repo(tmp_path, school_repo):
    mock_llm = MagicMock()
    mock_llm.generate_json.return_value = {
        "market_bullets": [],
        "candidate_insights": [],
    }
    mock_prompt_loader = MagicMock()
    mock_prompt_loader.load.return_value = ({"task_type": "REAL_ESTATE_ANALYSIS"}, "prompt")
    mock_aggregator = MagicMock()
    mock_aggregator.aggregate.return_value = []
    mock_repo = MagicMock()
    mock_repo.save.return_value = None

    return DailyReportOrchestrator(
        llm=mock_llm,
        prompt_loader=mock_prompt_loader,
        aggregator=mock_aggregator,
        report_repo=mock_repo,
        db_path=str(tmp_path / "re.db"),
        school_repo=school_repo,
    )


def _make_school_score(complex_code="CC001", score=78, nearby=4,
                       per_teacher=15.2, transfer=0.065):
    return SchoolScore(
        complex_code=complex_code,
        school_kind="total",
        nearby_school_count=nearby,
        avg_students_per_class=0.0,
        avg_students_per_teacher=per_teacher,
        score=score,
        collected_at="2026-05-18T00:00:00+00:00",
        avg_transfer_rate=transfer,
    )


class TestEnrichWithSchool:
    def test_cache_hit_injects_school_fields(self, tmp_path):
        mock_repo = MagicMock()
        mock_repo.get_score.return_value = _make_school_score()
        orch = _make_orchestrator_with_school_repo(tmp_path, mock_repo)

        candidates = [{"complex_code": "CC001", "apt_name": "래미안"}]
        result = orch._enrich_with_school(candidates)

        assert result[0]["school_score"] == 78
        assert result[0]["school_nearby_count"] == 4
        assert result[0]["school_avg_per_teacher"] == 15.2
        assert result[0]["school_transfer_rate"] == 0.065

    def test_no_school_repo_returns_unchanged(self, tmp_path):
        orch = _make_orchestrator_with_school_repo(tmp_path, None)
        candidates = [{"complex_code": "CC001", "apt_name": "래미안"}]
        result = orch._enrich_with_school(candidates)
        assert "school_score" not in result[0]

    def test_cache_miss_no_school_fields(self, tmp_path):
        mock_repo = MagicMock()
        mock_repo.get_score.return_value = None
        orch = _make_orchestrator_with_school_repo(tmp_path, mock_repo)

        candidates = [{"complex_code": "UNKNOWN", "apt_name": "미등록"}]
        result = orch._enrich_with_school(candidates)
        assert "school_score" not in result[0]

    def test_missing_complex_code_skipped(self, tmp_path):
        mock_repo = MagicMock()
        orch = _make_orchestrator_with_school_repo(tmp_path, mock_repo)

        candidates = [{"apt_name": "코드없음"}]  # complex_code 없음
        result = orch._enrich_with_school(candidates)
        mock_repo.get_score.assert_not_called()
        assert "school_score" not in result[0]

    def test_repo_exception_does_not_raise(self, tmp_path):
        mock_repo = MagicMock()
        mock_repo.get_score.side_effect = Exception("DB 연결 실패")
        orch = _make_orchestrator_with_school_repo(tmp_path, mock_repo)

        candidates = [{"complex_code": "CC001", "apt_name": "래미안"}]
        result = orch._enrich_with_school(candidates)  # 예외 없이 반환
        assert result[0]["apt_name"] == "래미안"
        assert "school_score" not in result[0]

    def test_multiple_candidates_all_enriched(self, tmp_path):
        mock_repo = MagicMock()
        mock_repo.get_score.side_effect = lambda code, kind: (
            _make_school_score(code, score=80) if code == "CC001"
            else _make_school_score(code, score=60) if code == "CC002"
            else None
        )
        orch = _make_orchestrator_with_school_repo(tmp_path, mock_repo)

        candidates = [
            {"complex_code": "CC001", "apt_name": "래미안"},
            {"complex_code": "CC002", "apt_name": "힐스테이트"},
            {"complex_code": "NONE", "apt_name": "미수집"},
        ]
        result = orch._enrich_with_school(candidates)
        assert result[0]["school_score"] == 80
        assert result[1]["school_score"] == 60
        assert "school_score" not in result[2]

    def test_orchestrator_accepts_school_repo_in_init(self, tmp_path):
        mock_repo = MagicMock()
        orch = _make_orchestrator_with_school_repo(tmp_path, mock_repo)
        assert orch._school_repo is mock_repo
```

- [ ] **Step 2: 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/daily_report/test_enrich_school.py -v
```

Expected: `FAILED` — `TypeError: DailyReportOrchestrator.__init__() got an unexpected keyword argument 'school_repo'`

- [ ] **Step 3: 구현 — __init__ school_repo 파라미터 추가**

`src/modules/real_estate/daily_report/daily_report_orchestrator.py` — `__init__` 시그니처 변경:

```python
    def __init__(
        self,
        llm: BaseLLMClient,
        prompt_loader: PromptLoader,
        aggregator: TransactionAggregator,
        report_repo: DailyReportRepository,
        db_path: str = "data/real_estate.db",
        poi_collector: Optional[PoiCollector] = None,
        trend_analyzer: Optional[TrendAnalyzer] = None,
        commute_svc=None,
        geocoder=None,
        max_new_commute_api_calls: int = 5,
        school_repo=None,
    ):
        self._llm = llm
        self._prompt_loader = prompt_loader
        self._aggregator = aggregator
        self._repo = report_repo
        self._db_path = db_path
        self._poi_collector = poi_collector
        self._trend_analyzer = trend_analyzer
        self._commute_svc = commute_svc
        self._geocoder = geocoder
        self._max_new_commute_api_calls = max_new_commute_api_calls
        self._school_repo = school_repo
```

- [ ] **Step 4: 구현 — _enrich_with_school() 메서드 추가**

`src/modules/real_estate/daily_report/daily_report_orchestrator.py` — `_enrich_with_commute_quota` 메서드 아래에 추가:

```python
    def _enrich_with_school(self, candidates: List[Dict]) -> List[Dict]:
        if self._school_repo is None:
            return candidates

        enriched = []
        for c in candidates:
            result = dict(c)
            complex_code = c.get("complex_code", "")
            if not complex_code:
                enriched.append(result)
                continue
            try:
                cached = self._school_repo.get_score(complex_code, "total")
                if cached is not None:
                    result["school_score"] = cached.score
                    result["school_nearby_count"] = cached.nearby_school_count
                    result["school_avg_per_teacher"] = cached.avg_students_per_teacher
                    result["school_transfer_rate"] = cached.avg_transfer_rate
            except Exception as e:
                logger.warning(
                    "[DailyOrchestrator] school enrich 실패 %s: %s",
                    c.get("apt_name"), e,
                )
            enriched.append(result)
        return enriched
```

- [ ] **Step 5: 구현 — generate() 파이프라인에 _enrich_with_school 추가**

`src/modules/real_estate/daily_report/daily_report_orchestrator.py` — `generate()` 메서드에서 commute enrichment 직후에 추가:

commute 블록 찾기 (현재):
```python
        if self._commute_svc and self._geocoder:
            dest, dest_lat, dest_lng = _resolve_workplace_coords(persona, self._geocoder)
            candidates = self._enrich_with_commute_quota(
                candidates, dest, dest_lat, dest_lng, self._max_new_commute_api_calls
            )
        if self._trend_analyzer:
```

변경 후:
```python
        if self._commute_svc and self._geocoder:
            dest, dest_lat, dest_lng = _resolve_workplace_coords(persona, self._geocoder)
            candidates = self._enrich_with_commute_quota(
                candidates, dest, dest_lat, dest_lng, self._max_new_commute_api_calls
            )
        if self._school_repo:
            candidates = self._enrich_with_school(candidates)
        if self._trend_analyzer:
```

- [ ] **Step 6: 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/daily_report/test_enrich_school.py tests/modules/real_estate/daily_report/test_daily_report_orchestrator.py -v
```

Expected: 모든 테스트 PASS

- [ ] **Step 7: 커밋**

```bash
git add src/modules/real_estate/daily_report/daily_report_orchestrator.py \
        tests/modules/real_estate/daily_report/test_enrich_school.py
git commit -m "feat(orchestrator): _enrich_with_school 파이프라인 추가, school_repo 의존성 주입"
```

---

## Task 6: service.py — SchoolRepository 주입

**Files:**
- Modify: `src/modules/real_estate/service.py`

이 태스크는 wiring 코드이므로 별도 단위 테스트 없이 기존 테스트 전체로 회귀 검증한다.

- [ ] **Step 1: 구현**

`src/modules/real_estate/service.py` — `_generate_new_daily_report()` 메서드에서 orchestrator 생성 코드에 `school_repo` 주입 추가.

기존 코드에서 import 목록에 추가:
```python
from modules.real_estate.school.school_repository import SchoolRepository
```

기존 `orchestrator = DailyReportOrchestrator(...)` 블록에 파라미터 추가:
```python
            orchestrator = DailyReportOrchestrator(
                llm=self.llm,
                prompt_loader=self.prompt_loader,
                aggregator=TransactionAggregator(db_path=re_db),
                report_repo=report_repo,
                db_path=re_db,
                poi_collector=PoiCollector(api_key=kakao_key, db_path=re_db),
                trend_analyzer=TrendAnalyzer(db_path=re_db),
                commute_svc=self.commute_service,
                geocoder=geocoder,
                max_new_commute_api_calls=daily_cfg.get("max_new_commute_api_calls", 5),
                school_repo=SchoolRepository(db_path=re_db),   # NEW
            )
```

- [ ] **Step 2: 전체 테스트 실행으로 회귀 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/daily_report/ tests/modules/real_estate/school/ -v
```

Expected: 모든 테스트 PASS

- [ ] **Step 3: 커밋**

```bash
git add src/modules/real_estate/service.py
git commit -m "feat(service): DailyReportOrchestrator에 SchoolRepository 주입"
```

---

## 최종 검증

- [ ] **모든 관련 테스트 통과**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest \
  tests/modules/real_estate/school/ \
  tests/modules/real_estate/daily_report/ \
  -v
```

Expected: 전체 PASS, 0 failures

- [ ] **완료 기준 체크**
  - [ ] `render_location_summary()` 테스트 전체 통과
  - [ ] `_enrich_with_school()` 테스트 전체 통과
  - [ ] `build_candidate_card()` 출력에 `📍 입지 현황` 블록 포함 (commute 다음, scores 전)
  - [ ] `render_scores()`에 evidence bullets 없음
  - [ ] `school_score` 없는 candidate에서 오류 없이 렌더링
  - [ ] `<!-- stats -->` 등 오염된 HTML 코멘트 출력 없음
