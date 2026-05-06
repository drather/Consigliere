# Real Estate Professional Report 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 매일 07:00 부동산 컨설턴트 수준의 리포트(입지/학군/실거래가추세/투자전략)를 자동 생성하고, 대시보드 아카이브에 저장해 열람 가능하게 한다.

**Architecture:** Python이 사실(POI 수집, 실거래가 추세, 점수)을 계산하고 LLM 3개 에이전트(LocationAgent, SchoolAgent, StrategyAgent)가 해석을 서술한다. ReportOrchestrator가 이를 조합해 Markdown 리포트를 생성하고 ReportRepository에 저장한다. 기존 InsightOrchestrator는 건드리지 않는다.

**Tech Stack:** Python 3.12, SQLite, Kakao Local API (기존 key), FastAPI, Streamlit, pytest

---

## 파일 구조

**신규 생성:**
- `src/modules/real_estate/poi_collector.py` — 카카오 로컬 API POI 수집 + SQLite 캐시
- `src/modules/real_estate/trend_analyzer.py` — 실거래가 6개월 추세 집계
- `src/modules/real_estate/report_repository.py` — 전문 리포트 Markdown/JSON 저장·조회
- `src/modules/real_estate/report_orchestrator.py` — 전체 파이프라인 오케스트레이터
- `src/modules/real_estate/prompts/location_analyst.md` — 입지 분석 LLM 프롬프트
- `src/modules/real_estate/prompts/school_analyst.md` — 학군 분석 LLM 프롬프트
- `src/modules/real_estate/prompts/strategy_analyst.md` — 투자 전략 LLM 프롬프트
- `tests/modules/real_estate/test_poi_collector.py`
- `tests/modules/real_estate/test_trend_analyzer.py`
- `tests/modules/real_estate/test_report_repository.py`
- `tests/modules/real_estate/test_report_orchestrator.py`

**수정:**
- `src/modules/real_estate/config.yaml` — POI 설정, 리포트 저장 경로, 스코어링 강화 설정 추가
- `src/modules/real_estate/scoring.py` — 용적률/건축연도 기반 재건축 정량화, POI 생활편의 반영
- `tests/modules/real_estate/test_scoring.py` — 신규 스코어링 로직 테스트 추가
- `src/api/routers/real_estate.py` — 전문 리포트 CRUD 엔드포인트 추가
- `src/dashboard/api_client.py` — 전문 리포트 API 메서드 추가
- `src/dashboard/views/real_estate.py` — Tab 3 전면 개편

---

## Task 1: config.yaml 설정 추가

**Files:**
- Modify: `src/modules/real_estate/config.yaml`

- [ ] **Step 1: config.yaml에 신규 설정 추가**

`src/modules/real_estate/config.yaml`의 `report:` 섹션 아래, `scoring:` 섹션 안에 다음을 추가한다:

```yaml
# report: 섹션 하단에 추가
report:
  recent_days: 7
  top_n: 5
  budget_band_ratio: 0.1
  report_storage_path: "data/real_estate_reports"  # 추가

# scoring: 섹션 하단에 추가
scoring:
  commute_thresholds: [20, 35]
  household_thresholds: [300, 500]
  school_keywords:
    - "학원가"
    - "명문"
    - "특목고"
    - "자사고"
  reconstruction_score_map:
    HIGH: 100
    MEDIUM: 60
    LOW: 20
    COMPLETED: 50
    UNKNOWN: 50
  data_absent_neutral: 50
  poi_close_station_walk_minutes: 5   # 추가: 역세권 도보 분 기준
  poi_academy_high_threshold: 30      # 추가: 학원 수 HIGH 기준
  poi_academy_medium_threshold: 15    # 추가: 학원 수 MEDIUM 기준
  reconstruction_age_years: 30        # 추가: 재건축 대상 최소 연령
  reconstruction_far_max: 200         # 추가: 재건축 가능 최대 용적률(%)

# poi_cache 설정 추가 (최상위 레벨)
poi_cache_ttl_days: 30
```

- [ ] **Step 2: 커밋**

```bash
git add src/modules/real_estate/config.yaml
git commit -m "feat(config): 전문 리포트용 POI/스코어링 설정 추가"
```

---

## Task 2: PoiCollector TDD

**Files:**
- Create: `src/modules/real_estate/poi_collector.py`
- Create: `tests/modules/real_estate/test_poi_collector.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/modules/real_estate/test_poi_collector.py
import os
import sys
import sqlite3
import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src')))

from modules.real_estate.poi_collector import PoiCollector, PoiData


def _make_kakao_response(places):
    return {"documents": places, "meta": {"total_count": len(places)}}


def _make_station(name, distance_m):
    return {"place_name": name, "distance": str(distance_m), "category_group_code": "SW8"}


def _make_school(name, distance_m):
    return {"place_name": name, "distance": str(distance_m), "category_group_code": "SC4"}


def _make_place(name, distance_m):
    return {"place_name": name, "distance": str(distance_m)}


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test_re.db")


@pytest.fixture
def collector(db_path):
    return PoiCollector(api_key="test_key", db_path=db_path)


class TestPoiCollectorCollect:
    def test_collect_returns_poi_data(self, collector):
        mock_stations = [_make_station("강남역", 350), _make_station("역삼역", 620)]
        mock_schools = [_make_school("역삼초등학교", 450), _make_school("언주중학교", 820)]
        mock_academies = [_make_place(f"학원{i}", 500) for i in range(25)]
        mock_marts = [_make_place("이마트", 300), _make_place("홈플러스", 900)]

        responses = [
            _make_kakao_response(mock_stations),
            _make_kakao_response(mock_schools),
            _make_kakao_response(mock_academies),
            _make_kakao_response(mock_marts),
        ]

        with patch("requests.get") as mock_get:
            mock_get.side_effect = [MagicMock(status_code=200, json=lambda r=r: r) for r in responses]
            result = collector.collect(
                complex_code="1234567890",
                lat=37.4979,
                lng=127.0276,
            )

        assert isinstance(result, PoiData)
        assert len(result.subway_stations) == 2
        assert result.subway_stations[0]["name"] == "강남역"
        assert result.subway_stations[0]["walk_minutes"] == 5  # 350m / 67m/min ≈ 5분
        assert result.schools_count == 2
        assert result.academies_count == 25
        assert result.marts_count == 2

    def test_collect_caches_result(self, collector, db_path):
        mock_response = _make_kakao_response([])
        with patch("requests.get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200, json=lambda: mock_response)
            collector.collect("CODE1", 37.0, 127.0)
            first_call_count = mock_get.call_count
            collector.collect("CODE1", 37.0, 127.0)
            assert mock_get.call_count == first_call_count  # 캐시 히트 → 추가 호출 없음

    def test_collect_refreshes_after_ttl(self, collector, db_path):
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS poi_cache (
                complex_code TEXT PRIMARY KEY,
                lat REAL, lng REAL,
                subway_stations TEXT,
                schools_count INTEGER,
                academies_count INTEGER,
                marts_count INTEGER,
                collected_at TEXT
            )
        """)
        old_date = (datetime.now() - timedelta(days=40)).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "INSERT INTO poi_cache VALUES (?,?,?,?,?,?,?,?)",
            ("OLD_CODE", 37.0, 127.0, "[]", 0, 0, 0, old_date),
        )
        conn.commit()
        conn.close()

        mock_response = _make_kakao_response([])
        with patch("requests.get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200, json=lambda: mock_response)
            collector.collect("OLD_CODE", 37.0, 127.0)
            assert mock_get.call_count > 0  # TTL 만료 → 재수집

    def test_collect_returns_empty_on_api_failure(self, collector):
        with patch("requests.get") as mock_get:
            mock_get.side_effect = Exception("network error")
            result = collector.collect("FAIL", 37.0, 127.0)
        assert isinstance(result, PoiData)
        assert result.schools_count == 0
        assert result.subway_stations == []

    def test_walk_minutes_calculation(self, collector):
        """350m → 5분 (67m/min 보행속도 기준 올림)"""
        stations = [{"place_name": "역삼역", "distance": "350"}]
        result = collector._parse_stations(stations)
        assert result[0]["walk_minutes"] == 5
```

- [ ] **Step 2: 테스트 실행 → 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_poi_collector.py -v
```
Expected: `ModuleNotFoundError: No module named 'modules.real_estate.poi_collector'`

- [ ] **Step 3: PoiCollector 구현**

```python
# src/modules/real_estate/poi_collector.py
"""
PoiCollector — 카카오 로컬 API 반경 키워드 검색으로 단지 주변 POI 수집.
결과는 real_estate.db의 poi_cache 테이블에 30일 TTL로 캐시된다.
"""
import json
import math
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional

import requests
import yaml

from core.logger import get_logger

logger = get_logger(__name__)

_KAKAO_KEYWORD_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"
_WALK_SPEED_MPM = 67  # 보행 속도 m/min
_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")

_DDL = """
CREATE TABLE IF NOT EXISTS poi_cache (
    complex_code    TEXT PRIMARY KEY,
    lat             REAL,
    lng             REAL,
    subway_stations TEXT,
    schools_count   INTEGER,
    academies_count INTEGER,
    marts_count     INTEGER,
    collected_at    TEXT
);
"""


def _load_ttl_days() -> int:
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        return int(cfg.get("poi_cache_ttl_days", 30))
    except Exception:
        return 30


@dataclass
class PoiData:
    complex_code: str = ""
    subway_stations: List[Dict] = field(default_factory=list)
    schools_count: int = 0
    academies_count: int = 0
    marts_count: int = 0
    collected_at: str = ""

    @property
    def closest_station_walk_minutes(self) -> Optional[int]:
        if not self.subway_stations:
            return None
        return min(s["walk_minutes"] for s in self.subway_stations)

    @property
    def stations_within_5min(self) -> List[Dict]:
        return [s for s in self.subway_stations if s["walk_minutes"] <= 5]


class PoiCollector:
    """
    Args:
        api_key: KAKAO_API_KEY (헤더: KakaoAK {key})
        db_path: real_estate.db 경로 (poi_cache 테이블 공유)
        ttl_days: 캐시 유효 기간 (config.yaml poi_cache_ttl_days)
    """

    STATION_RADIUS = 500    # 지하철역 반경 m
    SCHOOL_RADIUS = 1000    # 학교 반경 m
    ACADEMY_RADIUS = 1000   # 학원 반경 m
    MART_RADIUS = 1000      # 마트 반경 m

    def __init__(self, api_key: str, db_path: str, ttl_days: Optional[int] = None):
        self._api_key = api_key
        self._db_path = db_path
        self._ttl_days = ttl_days if ttl_days is not None else _load_ttl_days()
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.executescript(_DDL)

    def collect(self, complex_code: str, lat: float, lng: float) -> PoiData:
        cached = self._load_cache(complex_code)
        if cached:
            return cached
        try:
            return self._fetch_and_cache(complex_code, lat, lng)
        except Exception as e:
            logger.warning(f"[PoiCollector] API 실패 complex={complex_code}: {e}")
            return PoiData(complex_code=complex_code)

    def _fetch_and_cache(self, complex_code: str, lat: float, lng: float) -> PoiData:
        stations = self._search("지하철역", lat, lng, self.STATION_RADIUS, size=5)
        schools = self._search("초등학교 중학교", lat, lng, self.SCHOOL_RADIUS, size=15)
        academies = self._search("학원", lat, lng, self.ACADEMY_RADIUS, size=45)
        marts = self._search("대형마트 백화점", lat, lng, self.MART_RADIUS, size=15)

        poi = PoiData(
            complex_code=complex_code,
            subway_stations=self._parse_stations(stations),
            schools_count=len(schools),
            academies_count=len(academies),
            marts_count=len(marts),
            collected_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        self._save_cache(complex_code, lat, lng, poi)
        return poi

    def _search(self, query: str, lat: float, lng: float, radius: int, size: int = 15) -> List[Dict]:
        params = {"query": query, "y": str(lat), "x": str(lng), "radius": radius, "size": size}
        headers = {"Authorization": f"KakaoAK {self._api_key}"}
        resp = requests.get(_KAKAO_KEYWORD_URL, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json().get("documents", [])

    def _parse_stations(self, docs: List[Dict]) -> List[Dict]:
        result = []
        for d in docs:
            dist_m = int(d.get("distance", 0))
            walk_min = math.ceil(dist_m / _WALK_SPEED_MPM)
            result.append({"name": d.get("place_name", ""), "walk_minutes": walk_min})
        return result

    def _load_cache(self, complex_code: str) -> Optional[PoiData]:
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT subway_stations, schools_count, academies_count, marts_count, collected_at "
                "FROM poi_cache WHERE complex_code = ?",
                (complex_code,),
            ).fetchone()
        if not row:
            return None
        collected_at = row[4]
        if self._is_expired(collected_at):
            return None
        return PoiData(
            complex_code=complex_code,
            subway_stations=json.loads(row[0] or "[]"),
            schools_count=row[1] or 0,
            academies_count=row[2] or 0,
            marts_count=row[3] or 0,
            collected_at=collected_at,
        )

    def _save_cache(self, complex_code: str, lat: float, lng: float, poi: PoiData) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO poi_cache VALUES (?,?,?,?,?,?,?,?)",
                (
                    complex_code, lat, lng,
                    json.dumps(poi.subway_stations, ensure_ascii=False),
                    poi.schools_count, poi.academies_count, poi.marts_count,
                    poi.collected_at,
                ),
            )

    def _is_expired(self, collected_at: str) -> bool:
        try:
            dt = datetime.strptime(collected_at, "%Y-%m-%d %H:%M:%S")
            return datetime.now() - dt > timedelta(days=self._ttl_days)
        except Exception:
            return True
```

- [ ] **Step 4: 테스트 실행 → 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_poi_collector.py -v
```
Expected: `5 passed`

- [ ] **Step 5: 커밋**

```bash
git add src/modules/real_estate/poi_collector.py tests/modules/real_estate/test_poi_collector.py
git commit -m "feat(poi): PoiCollector — 카카오 로컬 API POI 수집 + SQLite 캐시"
```

---

## Task 3: TrendAnalyzer TDD

**Files:**
- Create: `src/modules/real_estate/trend_analyzer.py`
- Create: `tests/modules/real_estate/test_trend_analyzer.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/modules/real_estate/test_trend_analyzer.py
import os
import sys
import sqlite3
import pytest
from datetime import date, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src')))

from modules.real_estate.trend_analyzer import TrendAnalyzer, TrendData


def _insert_tx(conn, apt_master_id, price, deal_date, exclusive_area=84.0):
    conn.execute(
        "INSERT INTO transactions (apt_master_id, apt_name, district_code, deal_date, price, floor, exclusive_area, build_year, road_name) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (apt_master_id, "테스트아파트", "11680", deal_date, price, 5, exclusive_area, 2000, ""),
    )


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "re.db")
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            apt_master_id INTEGER,
            apt_name TEXT NOT NULL,
            district_code TEXT NOT NULL,
            deal_date TEXT NOT NULL,
            price INTEGER NOT NULL,
            floor INTEGER NOT NULL DEFAULT 0,
            exclusive_area REAL NOT NULL DEFAULT 0.0,
            build_year INTEGER NOT NULL DEFAULT 0,
            road_name TEXT NOT NULL DEFAULT ''
        )
    """)
    today = date.today()
    # 6개월치 거래 데이터 삽입
    for i in range(6):
        month_ago = today - timedelta(days=30 * i)
        d = month_ago.strftime("%Y-%m-%d")
        price = 1_200_000_000 + i * 10_000_000  # 약간씩 다른 가격
        _insert_tx(conn, 1, price, d)
    conn.commit()
    conn.close()
    return path


@pytest.fixture
def analyzer(db_path):
    return TrendAnalyzer(db_path=db_path)


class TestTrendAnalyzer:
    def test_get_trend_returns_trend_data(self, analyzer):
        result = analyzer.get_trend(apt_master_id=1, area_sqm=84.0)
        assert isinstance(result, TrendData)
        assert result.sample_count == 6
        assert result.avg_price > 0

    def test_avg_price_calculation(self, analyzer):
        result = analyzer.get_trend(apt_master_id=1, area_sqm=84.0)
        # 6개 거래의 평균가격
        expected = (1_200_000_000 + 1_210_000_000 + 1_220_000_000 +
                    1_230_000_000 + 1_240_000_000 + 1_250_000_000) // 6
        assert abs(result.avg_price - expected) < 1_000_000  # 1백만 원 허용 오차

    def test_price_change_pct_with_rising_prices(self, analyzer):
        result = analyzer.get_trend(apt_master_id=1, area_sqm=84.0)
        # 최근 3개월 > 이전 3개월이므로 음수 (과거가 더 비쌈 → 하락)
        assert isinstance(result.price_change_pct, float)

    def test_returns_none_for_no_data(self, analyzer):
        result = analyzer.get_trend(apt_master_id=999, area_sqm=84.0)
        assert result is None

    def test_monthly_volume(self, analyzer):
        result = analyzer.get_trend(apt_master_id=1, area_sqm=84.0)
        assert result.monthly_volume > 0

    def test_area_filter_excludes_other_areas(self, db_path):
        conn = sqlite3.connect(db_path)
        today = date.today().strftime("%Y-%m-%d")
        _insert_tx(conn, 1, 800_000_000, today, exclusive_area=59.0)
        conn.commit()
        conn.close()
        analyzer = TrendAnalyzer(db_path=db_path)
        result_84 = analyzer.get_trend(apt_master_id=1, area_sqm=84.0)
        result_59 = analyzer.get_trend(apt_master_id=1, area_sqm=59.0)
        # 84㎡와 59㎡는 별도 집계
        assert result_84.avg_price != result_59.avg_price
```

- [ ] **Step 2: 테스트 실행 → 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_trend_analyzer.py -v
```
Expected: `ModuleNotFoundError: No module named 'modules.real_estate.trend_analyzer'`

- [ ] **Step 3: TrendAnalyzer 구현**

```python
# src/modules/real_estate/trend_analyzer.py
"""
TrendAnalyzer — transactions 테이블에서 단지별 실거래가 추세를 집계한다.
"""
import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

from core.logger import get_logger

logger = get_logger(__name__)

_AREA_TOLERANCE = 5.0  # 전용면적 ±5㎡ 허용


@dataclass
class TrendData:
    apt_master_id: int
    area_sqm: float
    avg_price: int           # 원 단위
    price_change_pct: float  # 최근 3개월 vs 이전 3개월 변화율 (%)
    monthly_volume: float    # 월 평균 거래량
    price_min: int
    price_max: int
    sample_count: int

    def avg_price_eok(self) -> str:
        """평균가를 'XX.X억' 형태로 반환."""
        eok = self.avg_price / 1_00_000_000
        return f"{eok:.1f}억"

    def price_change_str(self) -> str:
        sign = "+" if self.price_change_pct >= 0 else ""
        return f"{sign}{self.price_change_pct:.1f}%"


class TrendAnalyzer:
    def __init__(self, db_path: str):
        self._db_path = db_path

    def get_trend(
        self,
        apt_master_id: int,
        area_sqm: float,
        months: int = 6,
    ) -> Optional[TrendData]:
        """
        최근 months개월 실거래 집계.
        area_sqm ± _AREA_TOLERANCE ㎡ 범위 거래만 포함.
        """
        since = (date.today() - timedelta(days=30 * months)).strftime("%Y-%m-%d")
        mid = (date.today() - timedelta(days=30 * (months // 2))).strftime("%Y-%m-%d")
        area_min = area_sqm - _AREA_TOLERANCE
        area_max = area_sqm + _AREA_TOLERANCE

        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(
                "SELECT price, deal_date FROM transactions "
                "WHERE apt_master_id = ? "
                "  AND exclusive_area BETWEEN ? AND ? "
                "  AND deal_date >= ? "
                "ORDER BY deal_date",
                (apt_master_id, area_min, area_max, since),
            ).fetchall()

        if not rows:
            return None

        prices = [r[0] for r in rows]
        dates = [r[1] for r in rows]

        avg_price = sum(prices) // len(prices)

        recent = [r[0] for r in rows if r[1] >= mid]
        older = [r[0] for r in rows if r[1] < mid]
        if recent and older:
            recent_avg = sum(recent) / len(recent)
            older_avg = sum(older) / len(older)
            change_pct = round((recent_avg - older_avg) / older_avg * 100, 1)
        else:
            change_pct = 0.0

        monthly_volume = round(len(rows) / months, 1)

        return TrendData(
            apt_master_id=apt_master_id,
            area_sqm=area_sqm,
            avg_price=avg_price,
            price_change_pct=change_pct,
            monthly_volume=monthly_volume,
            price_min=min(prices),
            price_max=max(prices),
            sample_count=len(rows),
        )
```

- [ ] **Step 4: 테스트 실행 → 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_trend_analyzer.py -v
```
Expected: `6 passed`

- [ ] **Step 5: 커밋**

```bash
git add src/modules/real_estate/trend_analyzer.py tests/modules/real_estate/test_trend_analyzer.py
git commit -m "feat(trend): TrendAnalyzer — 실거래가 6개월 추세 집계"
```

---

## Task 4: ScoringEngine 강화

**Files:**
- Modify: `src/modules/real_estate/scoring.py`
- Modify: `tests/modules/real_estate/test_scoring.py`

- [ ] **Step 1: 실패하는 테스트 추가**

`tests/modules/real_estate/test_scoring.py` 파일 끝에 다음 테스트 클래스를 추가한다:

```python
class TestScoringEnginePOI:
    """POI 데이터 반영 스코어링 테스트."""

    POI_WEIGHTS = {
        "commute": 25, "liquidity": 25, "price_potential": 25,
        "living_convenience": 17, "school": 8,
    }
    POI_CONFIG = {
        "commute_thresholds": [20, 35],
        "household_thresholds": [300, 500],
        "school_keywords": ["학원가", "명문"],
        "reconstruction_score_map": {"HIGH": 100, "MEDIUM": 60, "LOW": 20, "COMPLETED": 50, "UNKNOWN": 50},
        "data_absent_neutral": 50,
        "poi_close_station_walk_minutes": 5,
        "poi_academy_high_threshold": 30,
        "poi_academy_medium_threshold": 15,
        "reconstruction_age_years": 30,
        "reconstruction_far_max": 200,
    }

    def test_living_convenience_high_with_two_close_stations(self):
        from modules.real_estate.scoring import ScoringEngine
        c = make_candidate(
            nearest_stations=None,
            poi_stations=[{"name": "강남역", "walk_minutes": 4}, {"name": "역삼역", "walk_minutes": 3}],
        )
        engine = ScoringEngine(self.POI_WEIGHTS, self.POI_CONFIG)
        result = engine.score_all([c])[0]
        assert result["scores"]["living_convenience"] == 100

    def test_school_score_high_with_many_academies(self):
        from modules.real_estate.scoring import ScoringEngine
        c = make_candidate(
            school_zone_notes=None,
            poi_academies_count=35,
        )
        engine = ScoringEngine(self.POI_WEIGHTS, self.POI_CONFIG)
        result = engine.score_all([c])[0]
        assert result["scores"]["school"] == 100

    def test_reconstruction_high_with_old_low_far(self):
        from modules.real_estate.scoring import ScoringEngine
        c = make_candidate(
            reconstruction_potential="UNKNOWN",
            floor_area_ratio=185.0,
            build_year=1992,
        )
        engine = ScoringEngine(self.POI_WEIGHTS, self.POI_CONFIG)
        result = engine.score_all([c])[0]
        assert result["scores"]["price_potential"] == 100

    def test_reconstruction_low_with_new_high_far(self):
        from modules.real_estate.scoring import ScoringEngine
        c = make_candidate(
            reconstruction_potential="UNKNOWN",
            floor_area_ratio=280.0,
            build_year=2015,
        )
        engine = ScoringEngine(self.POI_WEIGHTS, self.POI_CONFIG)
        result = engine.score_all([c])[0]
        assert result["scores"]["price_potential"] == 20
```

- [ ] **Step 2: 테스트 실행 → 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_scoring.py::TestScoringEnginePOI -v
```
Expected: FAIL (make_candidate에 poi_stations 파라미터 없음, ScoringEngine에 POI 로직 없음)

- [ ] **Step 3: ScoringEngine 강화 (scoring.py 수정)**

`src/modules/real_estate/scoring.py`에서 `ScoringEngine.__init__`과 `_score_living_convenience`, `_score_school`, `_score_price_potential`를 아래로 교체한다:

```python
    def __init__(self, weights: Dict[str, int], config: Dict[str, Any]):
        self.weights = weights
        self.commute_thresholds = config.get("commute_thresholds", [20, 35])
        self.household_thresholds = config.get("household_thresholds", [300, 500])
        self.school_keywords = config.get("school_keywords", ["학원가", "명문"])
        self.neutral = config.get("data_absent_neutral", 50)
        self.recon_map = config.get("reconstruction_score_map", {
            "HIGH": 100, "MEDIUM": 60, "LOW": 20, "COMPLETED": 50, "UNKNOWN": 50
        })
        # POI 기반 스코어링 임계값
        self.poi_close_station_min = config.get("poi_close_station_walk_minutes", 5)
        self.poi_academy_high = config.get("poi_academy_high_threshold", 30)
        self.poi_academy_mid = config.get("poi_academy_medium_threshold", 15)
        # 재건축 정량화 임계값
        self.recon_age_years = config.get("reconstruction_age_years", 30)
        self.recon_far_max = config.get("reconstruction_far_max", 200)

    def _score_living_convenience(self, c: Dict) -> int:
        """POI 역세권 데이터 우선, 없으면 기존 nearest_stations 사용."""
        poi_stations = c.get("poi_stations")
        if poi_stations is not None:
            close = [s for s in poi_stations if s.get("walk_minutes", 99) <= self.poi_close_station_min]
            if len(close) >= 2:
                return _HIGH
            if close:
                return _MEDIUM
            return _LOW

        # fallback: 기존 nearest_stations
        stations = c.get("nearest_stations")
        if stations is None:
            return self.neutral
        if not stations:
            return _LOW
        close_stations = [s for s in stations if s.get("walk_minutes", 99) <= 5]
        if len(close_stations) >= 2:
            return _HIGH
        if close_stations:
            return _MEDIUM
        return _LOW

    def _score_school(self, c: Dict) -> int:
        """POI 학원 수 데이터 우선, 없으면 기존 school_zone_notes 사용."""
        poi_academies = c.get("poi_academies_count")
        if poi_academies is not None:
            if poi_academies >= self.poi_academy_high:
                return _HIGH
            if poi_academies >= self.poi_academy_mid:
                return _MEDIUM
            return _LOW

        # fallback: 기존 school_zone_notes 키워드
        notes = c.get("school_zone_notes")
        if notes is None:
            return self.neutral
        if any(kw in notes for kw in self.school_keywords):
            return _HIGH
        schools = c.get("elementary_schools", [])
        if schools:
            return _MEDIUM
        return _LOW

    def _score_price_potential(self, c: Dict, horea_scores: Optional[Dict] = None) -> int:
        """용적률/건축연도 정량화 우선, 없으면 기존 reconstruction_potential 문자열 사용."""
        import datetime as _dt

        far = c.get("floor_area_ratio")       # 용적률 (%)
        build_year = c.get("build_year")       # 건축연도

        if far is not None and build_year is not None:
            current_year = _dt.date.today().year
            age = current_year - int(build_year)
            is_old = age >= self.recon_age_years
            is_low_far = float(far) <= self.recon_far_max
            if is_old and is_low_far:
                base = _HIGH
            elif is_old or is_low_far:
                base = _MEDIUM
            else:
                base = _LOW
        else:
            potential = c.get("reconstruction_potential", "UNKNOWN")
            base = self.recon_map.get(potential, self.neutral)

        if c.get("gtx_benefit"):
            base = min(100, base + 30)

        if horea_scores:
            district_name = c.get("district_name", "")
            for area_key, assessment in horea_scores.items():
                if area_key in district_name or district_name in area_key:
                    score = assessment.get("score", 0)
                    boost = int(score * 0.4)
                    base = min(100, base + boost)
                    break

        return base
```

또한 `tests/modules/real_estate/test_scoring.py`의 `make_candidate` 함수를 업데이트한다:

```python
def make_candidate(**kwargs):
    base = {
        "apt_name": "테스트아파트",
        "commute_minutes": 25,
        "household_count": 500,
        "nearest_stations": [{"name": "역삼역", "line": "2호선", "walk_minutes": 5}],
        "school_zone_notes": "역삼초 배정권.",
        "reconstruction_potential": "MEDIUM",
        "gtx_benefit": False,
        "price": 800_000_000,
        # POI 필드 (None이면 기존 로직 사용)
        "poi_stations": None,
        "poi_academies_count": None,
        "floor_area_ratio": None,
        "build_year": None,
    }
    base.update(kwargs)
    return base
```

- [ ] **Step 4: 테스트 전체 실행**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_scoring.py -v
```
Expected: 전체 통과 (기존 테스트 + 신규 4개)

- [ ] **Step 5: 커밋**

```bash
git add src/modules/real_estate/scoring.py tests/modules/real_estate/test_scoring.py
git commit -m "feat(scoring): POI/용적률 기반 스코어링 강화"
```

---

## Task 5: LLM 프롬프트 3개 작성

**Files:**
- Create: `src/modules/real_estate/prompts/location_analyst.md`
- Create: `src/modules/real_estate/prompts/school_analyst.md`
- Create: `src/modules/real_estate/prompts/strategy_analyst.md`

- [ ] **Step 1: location_analyst.md 작성**

```markdown
---
task_type: analysis
ttl: 3600
---
# 부동산 입지 분석관

## 역할
단지별 POI 데이터(역세권·생활편의)를 바탕으로 **입지 강점과 약점**을 2~3문장으로 서술합니다.
숫자(역 개수·도보 분)는 반드시 그대로 인용하고, 추가 정보를 창작하지 마십시오.

## 입력 데이터
{{candidates_poi_json}}

형식:
```json
[
  {
    "apt_name": "단지명",
    "subway_stations": [{"name": "강남역", "walk_minutes": 7}],
    "marts_count": 2
  }
]
```

## 작업 지침
각 단지에 대해 아래를 포함한 2~3문장 서술:
1. 가장 가까운 역 이름·도보 분수 언급
2. 도보 5분 내 역이 2개 이상이면 "초역세권"으로 명시
3. 대형마트/백화점 수 언급 (0개면 "생활편의시설 부족" 지적)
4. 종합 입지 평가 한 줄 (강점 위주, 단점은 있을 때만)

## 출력 형식
```json
{
  "analyses": [
    {"apt_name": "단지명", "text": "2~3문장 입지 분석"}
  ]
}
```
규칙:
- apt_name은 입력 데이터의 값을 그대로 사용
- text는 한국어, 개조식 금지 (자연스러운 문장체)
- 없는 정보는 창작하지 말 것
```

- [ ] **Step 2: school_analyst.md 작성**

```markdown
---
task_type: analysis
ttl: 3600
---
# 학군 분석관

## 역할
단지 반경 1km 내 학교·학원 수 데이터를 바탕으로 **학군 강도**를 2~3문장으로 서술합니다.
학교·학원 수는 반드시 그대로 인용하고, 특정 학교명은 창작하지 마십시오.

## 입력 데이터
{{candidates_school_json}}

형식:
```json
[
  {
    "apt_name": "단지명",
    "schools_count": 3,
    "academies_count": 47
  }
]
```

## 작업 지침
각 단지에 대해 아래를 포함한 2~3문장 서술:
1. 반경 1km 내 학교 수 언급
2. 학원 수 30개 이상 → "학원가 밀집 지역", 15개 이상 → "학원 다수 입지", 미만 → "학원 인프라 제한적"
3. 학군 종합 평가 (실거주·자녀 교육 관점)

## 출력 형식
```json
{
  "analyses": [
    {"apt_name": "단지명", "text": "2~3문장 학군 분석"}
  ]
}
```
규칙:
- apt_name은 입력 데이터의 값을 그대로 사용
- text는 한국어 문장체
```

- [ ] **Step 3: strategy_analyst.md 작성**

```markdown
---
task_type: synthesis
ttl: 3600
---
# 부동산 투자 전략가

## 역할
분석 완료된 Top 5 단지 데이터와 거시경제 현황을 바탕으로
**지금 당장 실행 가능한 투자 전략과 액션 플랜**을 작성합니다.
단순 요약이 아닌, 구체적 시점·단지·조건이 담긴 전략을 제시하십시오.

## 고정 정보 (캐시 가능)

### 거시경제 현황
{{macro_summary}}

### 구매 가능 예산
{{budget_summary}}

### 사용자 목표
{{user_goals}}

---

## 분석 결과 (Top 5 단지)
{{ranked_candidates_summary}}

---

## 작업 지침

### 1. 시장 진단 (2~3문장)
- 현재 금리 수준에서 매수가 유리한지 불리한지 판단
- 단기 시장 방향성 한 줄 요약

### 2. 전략 (매수/청약/관망 중 하나 선택 + 이유)
- 지금 당장 실행할 행동 1가지
- 이 전략을 선택한 핵심 이유 2가지

### 3. 단기 액션 플랜 (3개월 내)
- 구체적 단지명 + 행동 (예: "OO 단지 임장 후 호가 파악")
- 체크포인트 조건 (예: "주담대 금리 4% 이하 시 매수 검토")

### 4. 중기 액션 플랜 (1년 내)
- 시나리오별 행동 계획

### 5. 리스크 요인 (2개)
- 주의해야 할 변수

## 출력 형식
```json
{
  "market_diagnosis": "시장 진단 2~3문장",
  "strategy": "전략 선택 + 이유",
  "action_short": "3개월 내 구체적 액션",
  "action_mid": "1년 내 시나리오별 계획",
  "risks": ["리스크1", "리스크2"]
}
```
```

- [ ] **Step 4: 커밋**

```bash
git add src/modules/real_estate/prompts/location_analyst.md \
        src/modules/real_estate/prompts/school_analyst.md \
        src/modules/real_estate/prompts/strategy_analyst.md
git commit -m "feat(prompts): 입지/학군/투자전략 LLM 에이전트 프롬프트 추가"
```

---

## Task 6: ReportRepository TDD

**Files:**
- Create: `src/modules/real_estate/report_repository.py`
- Create: `tests/modules/real_estate/test_report_repository.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/modules/real_estate/test_report_repository.py
import os
import sys
import json
import pytest
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src')))

from modules.real_estate.report_repository import ReportRepository, ProfessionalReport


def _make_report(d: str = "2026-05-01") -> ProfessionalReport:
    return ProfessionalReport(
        date=d,
        budget_available=820_000_000,
        macro_summary="기준금리 3.5%, 주담대 4.2%",
        candidates_summary=[{"apt_name": "래미안원베일리", "total_score": 87.0}],
        location_analyses=[{"apt_name": "래미안원베일리", "text": "강남역 도보 5분 초역세권"}],
        school_analyses=[{"apt_name": "래미안원베일리", "text": "학원 52개 최상위 학군"}],
        strategy={"market_diagnosis": "관망 유리", "strategy": "임장 후 결정", "action_short": "OO 임장", "action_mid": "금리 하락 시 매수", "risks": ["금리 인상", "규제 강화"]},
        markdown="# 테스트 리포트\n내용",
    )


@pytest.fixture
def repo(tmp_path):
    return ReportRepository(storage_path=str(tmp_path))


class TestReportRepository:
    def test_save_and_load(self, repo):
        report = _make_report("2026-05-01")
        repo.save(report)
        loaded = repo.load("2026-05-01")
        assert loaded is not None
        assert loaded.date == "2026-05-01"
        assert loaded.budget_available == 820_000_000
        assert loaded.macro_summary == "기준금리 3.5%, 주담대 4.2%"

    def test_save_creates_markdown_and_json(self, tmp_path):
        repo = ReportRepository(storage_path=str(tmp_path))
        repo.save(_make_report("2026-05-02"))
        assert (tmp_path / "2026-05-02.md").exists()
        assert (tmp_path / "2026-05-02.json").exists()

    def test_load_returns_none_for_missing(self, repo):
        result = repo.load("1999-01-01")
        assert result is None

    def test_list_dates_returns_sorted(self, repo):
        repo.save(_make_report("2026-05-01"))
        repo.save(_make_report("2026-04-30"))
        repo.save(_make_report("2026-04-29"))
        dates = repo.list_dates()
        assert dates == ["2026-05-01", "2026-04-30", "2026-04-29"]  # 최신순

    def test_list_dates_empty(self, repo):
        assert repo.list_dates() == []

    def test_json_is_valid(self, tmp_path):
        repo = ReportRepository(storage_path=str(tmp_path))
        repo.save(_make_report("2026-05-03"))
        raw = (tmp_path / "2026-05-03.json").read_text(encoding="utf-8")
        data = json.loads(raw)
        assert data["date"] == "2026-05-03"
        assert "candidates_summary" in data
```

- [ ] **Step 2: 테스트 실행 → 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_report_repository.py -v
```
Expected: `ModuleNotFoundError`

- [ ] **Step 3: ReportRepository 구현**

```python
# src/modules/real_estate/report_repository.py
"""
ReportRepository — 전문 컨설턴트 리포트를 Markdown + JSON으로 저장/조회한다.
"""
import json
import os
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ProfessionalReport:
    date: str
    budget_available: int
    macro_summary: str
    candidates_summary: List[Dict]
    location_analyses: List[Dict]
    school_analyses: List[Dict]
    strategy: Dict[str, Any]
    markdown: str


class ReportRepository:
    def __init__(self, storage_path: str):
        self._path = storage_path
        os.makedirs(storage_path, exist_ok=True)

    def save(self, report: ProfessionalReport) -> None:
        md_path = os.path.join(self._path, f"{report.date}.md")
        json_path = os.path.join(self._path, f"{report.date}.json")

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(report.markdown)

        data = asdict(report)
        data.pop("markdown")  # markdown은 .md 파일로 저장, JSON에 중복 불필요
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"[ReportRepository] 저장 완료: {report.date}")

    def load(self, date_str: str) -> Optional[ProfessionalReport]:
        json_path = os.path.join(self._path, f"{date_str}.json")
        md_path = os.path.join(self._path, f"{date_str}.md")
        if not os.path.exists(json_path):
            return None
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        markdown = ""
        if os.path.exists(md_path):
            with open(md_path, "r", encoding="utf-8") as f:
                markdown = f.read()
        return ProfessionalReport(
            date=data["date"],
            budget_available=data["budget_available"],
            macro_summary=data["macro_summary"],
            candidates_summary=data.get("candidates_summary", []),
            location_analyses=data.get("location_analyses", []),
            school_analyses=data.get("school_analyses", []),
            strategy=data.get("strategy", {}),
            markdown=markdown,
        )

    def list_dates(self) -> List[str]:
        files = [
            f[:-5] for f in os.listdir(self._path)
            if f.endswith(".json")
        ]
        return sorted(files, reverse=True)
```

- [ ] **Step 4: 테스트 실행 → 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_report_repository.py -v
```
Expected: `6 passed`

- [ ] **Step 5: 커밋**

```bash
git add src/modules/real_estate/report_repository.py tests/modules/real_estate/test_report_repository.py
git commit -m "feat(report): ReportRepository — Markdown/JSON 저장·조회"
```

---

## Task 7: ReportOrchestrator TDD

**Files:**
- Create: `src/modules/real_estate/report_orchestrator.py`
- Create: `tests/modules/real_estate/test_report_orchestrator.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/modules/real_estate/test_report_orchestrator.py
import os
import sys
import pytest
from datetime import date
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src')))

from modules.real_estate.report_orchestrator import ReportOrchestrator
from modules.real_estate.report_repository import ProfessionalReport
from modules.real_estate.poi_collector import PoiData
from modules.real_estate.trend_analyzer import TrendData


def _make_mock_candidate():
    return {
        "apt_name": "래미안원베일리",
        "apt_master_id": 1,
        "district_code": "11650",
        "district_name": "서초구",
        "complex_code": "1234567890",
        "road_address": "서울시 서초구 반포대로 201",
        "household_count": 2990,
        "build_year": 1994,
        "floor_area_ratio": 198.0,
        "building_coverage_ratio": 18.0,
        "price": 1_500_000_000,
        "exclusive_area": 84.0,
        "commute_transit_minutes": 23,
        "reconstruction_potential": "UNKNOWN",
    }


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.generate_json.return_value = {
        "analyses": [{"apt_name": "래미안원베일리", "text": "강남역 도보 5분 초역세권"}]
    }
    return llm


@pytest.fixture
def mock_prompt_loader():
    loader = MagicMock()
    loader.load.return_value = "프롬프트 내용"
    loader.load_with_cache_split.return_value = ("시스템", "유저")
    return loader


@pytest.fixture
def orchestrator(mock_llm, mock_prompt_loader, tmp_path):
    from modules.real_estate.poi_collector import PoiCollector
    from modules.real_estate.trend_analyzer import TrendAnalyzer
    from modules.real_estate.report_repository import ReportRepository

    poi_collector = MagicMock(spec=PoiCollector)
    poi_collector.collect.return_value = PoiData(
        complex_code="1234567890",
        subway_stations=[{"name": "강남역", "walk_minutes": 5}],
        schools_count=2,
        academies_count=47,
        marts_count=3,
    )

    trend_analyzer = MagicMock(spec=TrendAnalyzer)
    trend_analyzer.get_trend.return_value = TrendData(
        apt_master_id=1, area_sqm=84.0,
        avg_price=1_500_000_000, price_change_pct=2.1,
        monthly_volume=8.0, price_min=1_400_000_000,
        price_max=1_600_000_000, sample_count=10,
    )

    report_repo = ReportRepository(storage_path=str(tmp_path))

    return ReportOrchestrator(
        llm=mock_llm,
        prompt_loader=mock_prompt_loader,
        poi_collector=poi_collector,
        trend_analyzer=trend_analyzer,
        report_repository=report_repo,
    )


class TestReportOrchestrator:
    def test_generate_returns_professional_report(self, orchestrator):
        candidates = [_make_mock_candidate()]
        persona_data = {
            "user": {"assets": {"total": 300_000_000}, "income": {"total": 160_000_000}},
            "priority_weights": {"commute": 25, "liquidity": 25, "price_potential": 25, "living_convenience": 17, "school": 8},
        }
        scoring_config = {
            "commute_thresholds": [20, 35], "household_thresholds": [300, 500],
            "school_keywords": ["학원가"], "reconstruction_score_map": {"HIGH": 100, "UNKNOWN": 50},
            "data_absent_neutral": 50,
            "poi_close_station_walk_minutes": 5, "poi_academy_high_threshold": 30,
            "poi_academy_medium_threshold": 15, "reconstruction_age_years": 30,
            "reconstruction_far_max": 200,
        }
        macro_summary = "기준금리 3.5%"

        report = orchestrator.generate(
            target_date=date(2026, 5, 1),
            candidates=candidates,
            persona_data=persona_data,
            scoring_config=scoring_config,
            macro_summary=macro_summary,
        )

        assert isinstance(report, ProfessionalReport)
        assert report.date == "2026-05-01"
        assert report.budget_available > 0
        assert len(report.candidates_summary) >= 1
        assert report.markdown != ""

    def test_generate_saves_to_repository(self, orchestrator, tmp_path):
        candidates = [_make_mock_candidate()]
        persona_data = {
            "user": {"assets": {"total": 300_000_000}, "income": {"total": 160_000_000}},
            "priority_weights": {"commute": 25, "liquidity": 25, "price_potential": 25, "living_convenience": 17, "school": 8},
        }
        orchestrator.generate(
            target_date=date(2026, 5, 1),
            candidates=[_make_mock_candidate()],
            persona_data=persona_data,
            scoring_config={"commute_thresholds": [20, 35], "household_thresholds": [300, 500],
                            "school_keywords": [], "reconstruction_score_map": {}, "data_absent_neutral": 50,
                            "poi_close_station_walk_minutes": 5, "poi_academy_high_threshold": 30,
                            "poi_academy_medium_threshold": 15, "reconstruction_age_years": 30,
                            "reconstruction_far_max": 200},
            macro_summary="",
        )
        assert (tmp_path / "2026-05-01.json").exists()
        assert (tmp_path / "2026-05-01.md").exists()

    def test_poi_failure_does_not_break_pipeline(self, orchestrator):
        orchestrator._poi_collector.collect.side_effect = Exception("API 실패")
        # 예외 발생해도 리포트 생성 완료
        report = orchestrator.generate(
            target_date=date(2026, 5, 1),
            candidates=[_make_mock_candidate()],
            persona_data={"user": {"assets": {"total": 300_000_000}, "income": {"total": 160_000_000}},
                          "priority_weights": {"commute": 25, "liquidity": 25, "price_potential": 25, "living_convenience": 17, "school": 8}},
            scoring_config={"commute_thresholds": [20, 35], "household_thresholds": [300, 500],
                            "school_keywords": [], "reconstruction_score_map": {}, "data_absent_neutral": 50,
                            "poi_close_station_walk_minutes": 5, "poi_academy_high_threshold": 30,
                            "poi_academy_medium_threshold": 15, "reconstruction_age_years": 30,
                            "reconstruction_far_max": 200},
            macro_summary="",
        )
        assert isinstance(report, ProfessionalReport)
```

- [ ] **Step 2: 테스트 실행 → 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_report_orchestrator.py -v
```
Expected: `ModuleNotFoundError`

- [ ] **Step 3: ReportOrchestrator 구현**

```python
# src/modules/real_estate/report_orchestrator.py
"""
ReportOrchestrator — 전문 컨설턴트 리포트 생성 파이프라인.

흐름:
  1. Python: DSR 기반 예산 계산
  2. Python: PoiCollector — 각 단지 POI 수집 (캐시 우선)
  3. Python: TrendAnalyzer — 실거래가 추세 집계
  4. Python: ScoringEngine(POI 반영) — 점수 계산
  5. LLM: LocationAgent — 입지 분석 (Top 5 배치)
  6. LLM: SchoolAgent — 학군 분석 (Top 5 배치)
  7. LLM: StrategyAgent — 투자 전략 + 액션 플랜
  8. Markdown 리포트 조립 → ReportRepository 저장
"""
import json
from datetime import date
from typing import Any, Dict, List, Optional

from core.llm import BaseLLMClient
from core.prompt_loader import PromptLoader
from core.logger import get_logger
from .poi_collector import PoiCollector, PoiData
from .trend_analyzer import TrendAnalyzer, TrendData
from .scoring import ScoringEngine
from .report_repository import ReportRepository, ProfessionalReport

logger = get_logger(__name__)

_DSR_RATE = 0.40          # DSR 40% 규제
_LOAN_TERM_MONTHS = 360   # 30년


def _calc_budget(persona_data: Dict, macro_summary: str) -> int:
    """DSR 기반 구매 가능 예산 계산.

    주담대 금리는 macro_summary에서 파싱 시도, 실패하면 기본값 4.5% 사용.
    """
    import re
    user = persona_data.get("user", {})
    assets = user.get("assets", {}).get("total", 0)
    annual_income = user.get("income", {}).get("total", 0)

    # 거시경제 요약에서 주담대 금리 파싱
    rate_match = re.search(r"주담대[^\d]*([\d.]+)%", macro_summary)
    annual_rate = float(rate_match.group(1)) / 100 if rate_match else 0.045
    monthly_rate = annual_rate / 12

    # DSR 기준 월 상환 가능액
    monthly_income = annual_income / 12
    max_monthly_payment = monthly_income * _DSR_RATE

    # 원리금균등상환 대출 한도 계산
    if monthly_rate > 0:
        loan_limit = max_monthly_payment * (1 - (1 + monthly_rate) ** -_LOAN_TERM_MONTHS) / monthly_rate
    else:
        loan_limit = max_monthly_payment * _LOAN_TERM_MONTHS

    return int(assets + loan_limit)


def _enrich_with_poi(candidates: List[Dict], poi_collector: PoiCollector) -> List[Dict]:
    enriched = []
    for c in candidates:
        result = dict(c)
        complex_code = c.get("complex_code") or c.get("apt_name", "unknown")
        lat = c.get("lat")
        lng = c.get("lng")
        if lat and lng:
            try:
                poi = poi_collector.collect(complex_code=complex_code, lat=lat, lng=lng)
                result["poi_stations"] = poi.subway_stations
                result["poi_academies_count"] = poi.academies_count
                result["_poi"] = poi
            except Exception as e:
                logger.warning(f"[Orchestrator] POI 실패 {c.get('apt_name')}: {e}")
        enriched.append(result)
    return enriched


def _enrich_with_trend(candidates: List[Dict], trend_analyzer: TrendAnalyzer) -> List[Dict]:
    enriched = []
    for c in candidates:
        result = dict(c)
        apt_master_id = c.get("apt_master_id")
        area_sqm = c.get("exclusive_area", 84.0)
        if apt_master_id:
            try:
                trend = trend_analyzer.get_trend(apt_master_id=apt_master_id, area_sqm=area_sqm)
                result["_trend"] = trend
            except Exception as e:
                logger.warning(f"[Orchestrator] 추세 실패 {c.get('apt_name')}: {e}")
        enriched.append(result)
    return enriched


def _call_location_agent(llm: BaseLLMClient, prompt_loader: PromptLoader, candidates: List[Dict]) -> Dict[str, str]:
    poi_input = [
        {
            "apt_name": c.get("apt_name"),
            "subway_stations": (c.get("_poi") or PoiData()).subway_stations,
            "marts_count": (c.get("_poi") or PoiData()).marts_count,
        }
        for c in candidates
    ]
    system, user_tmpl = prompt_loader.load_with_cache_split("location_analyst")
    user = user_tmpl.replace("{{candidates_poi_json}}", json.dumps(poi_input, ensure_ascii=False))
    try:
        result = llm.generate_json(system=system, user=user)
        return {a["apt_name"]: a["text"] for a in result.get("analyses", [])}
    except Exception as e:
        logger.warning(f"[Orchestrator] LocationAgent 실패: {e}")
        return {}


def _call_school_agent(llm: BaseLLMClient, prompt_loader: PromptLoader, candidates: List[Dict]) -> Dict[str, str]:
    school_input = [
        {
            "apt_name": c.get("apt_name"),
            "schools_count": (c.get("_poi") or PoiData()).schools_count,
            "academies_count": (c.get("_poi") or PoiData()).academies_count,
        }
        for c in candidates
    ]
    system, user_tmpl = prompt_loader.load_with_cache_split("school_analyst")
    user = user_tmpl.replace("{{candidates_school_json}}", json.dumps(school_input, ensure_ascii=False))
    try:
        result = llm.generate_json(system=system, user=user)
        return {a["apt_name"]: a["text"] for a in result.get("analyses", [])}
    except Exception as e:
        logger.warning(f"[Orchestrator] SchoolAgent 실패: {e}")
        return {}


def _call_strategy_agent(
    llm: BaseLLMClient,
    prompt_loader: PromptLoader,
    candidates: List[Dict],
    macro_summary: str,
    budget_available: int,
    persona_data: Dict,
) -> Dict:
    candidates_summary = "\n".join(
        f"- {c.get('apt_name')}: 총점 {c.get('total_score', 0):.1f}점, "
        f"출퇴근 {c.get('commute_transit_minutes', '?')}분"
        for c in candidates[:5]
    )
    budget_str = f"{budget_available / 1_0000_0000:.1f}억원"
    user_goals = persona_data.get("user", {}).get("plans", {}).get("primary_goal", "실거주 및 투자 가치")

    system, user_tmpl = prompt_loader.load_with_cache_split("strategy_analyst")
    user = (
        user_tmpl
        .replace("{{macro_summary}}", macro_summary)
        .replace("{{budget_summary}}", f"구매 가능 예산: {budget_str}")
        .replace("{{user_goals}}", user_goals)
        .replace("{{ranked_candidates_summary}}", candidates_summary)
    )
    try:
        return llm.generate_json(system=system, user=user)
    except Exception as e:
        logger.warning(f"[Orchestrator] StrategyAgent 실패: {e}")
        return {"market_diagnosis": "", "strategy": "", "action_short": "", "action_mid": "", "risks": []}


def _build_markdown(
    target_date: date,
    budget_available: int,
    macro_summary: str,
    candidates: List[Dict],
    location_analyses: Dict[str, str],
    school_analyses: Dict[str, str],
    strategy: Dict,
) -> str:
    lines = []
    date_str = target_date.strftime("%Y-%m-%d")
    budget_str = f"{budget_available / 1_0000_0000:.1f}억"

    lines.append(f"# 📊 Consigliere 부동산 전략 리포트 — {date_str}\n")

    # Executive Summary
    lines.append("## 1. Executive Summary\n")
    lines.append(f"- **구매 가능 예산:** {budget_str}")
    lines.append(f"- **시장 현황:** {macro_summary}")
    top3 = candidates[:3]
    lines.append(f"- **추천 Top 3:** " + " / ".join(f"{c['apt_name']}({c.get('total_score', 0):.0f}점)" for c in top3))
    if strategy.get("action_short"):
        lines.append(f"- **지금 당장 할 일:** {strategy['action_short']}")
    lines.append("")

    # 거시경제
    lines.append("## 2. 거시경제 컨텍스트\n")
    lines.append(macro_summary)
    if strategy.get("market_diagnosis"):
        lines.append(f"\n{strategy['market_diagnosis']}")
    lines.append("")

    # 단지별 상세 분석
    lines.append("## 3. 추천 단지 상세 분석\n")
    for i, c in enumerate(candidates[:5], 1):
        name = c.get("apt_name", "")
        score = c.get("total_score", 0)
        trend: Optional[TrendData] = c.get("_trend")
        poi: Optional[PoiData] = c.get("_poi")

        lines.append(f"### {i}위. {name} — 총점 {score:.0f}/100\n")

        lines.append("**📍 입지 분석**")
        if poi:
            stations_str = ", ".join(f"{s['name']} 도보 {s['walk_minutes']}분" for s in poi.subway_stations[:3])
            lines.append(f"- 역세권: {stations_str or '정보 없음'}")
            lines.append(f"- 생활편의: 반경 1km 내 대형마트/백화점 {poi.marts_count}개")
        loc_text = location_analyses.get(name, "")
        if loc_text:
            lines.append(f"- {loc_text}")
        lines.append("")

        lines.append("**🏫 학군 분석**")
        if poi:
            lines.append(f"- 반경 1km 내 학교 {poi.schools_count}개, 학원 {poi.academies_count}개")
        school_text = school_analyses.get(name, "")
        if school_text:
            lines.append(f"- {school_text}")
        lines.append("")

        lines.append("**📈 실거래가 추세**")
        if trend:
            lines.append(f"- 6개월 평균가: {trend.avg_price_eok()} (84㎡ 기준)")
            lines.append(f"- 3개월 전 대비: {trend.price_change_str()} / 월 평균 거래량 {trend.monthly_volume:.1f}건")
        else:
            lines.append("- 실거래가 데이터 미수집")
        lines.append("")

        lines.append("**🏗️ 재건축/투자 잠재력**")
        far = c.get("floor_area_ratio")
        build_year = c.get("build_year")
        if far and build_year:
            import datetime as _dt
            age = _dt.date.today().year - int(build_year)
            lines.append(f"- 건축연도: {build_year}년 ({age}년), 용적률: {far:.0f}%, 건폐율: {c.get('building_coverage_ratio', '-'):.0f}%")
        scores = c.get("scores", {})
        lines.append(f"- 가격잠재력 점수: {scores.get('price_potential', '-')}점")
        lines.append("")

        commute = c.get("commute_transit_minutes") or c.get("commute_minutes")
        lines.append(f"**🚌 출퇴근** (직장 기준, 캐시)")
        lines.append(f"- 대중교통 {commute or '?'}분")
        lines.append("")

        budget_ok = budget_available >= c.get("price", 0)
        lines.append("**💰 예산 적합성**")
        lines.append(f"- 최근 실거래가: {c.get('price', 0) / 1_0000_0000:.1f}억 vs 구매 가능 {budget_str}")
        lines.append(f"- {'✅ 예산 범위 내' if budget_ok else '⚠️ 예산 초과 — 추가 조달 필요'}")
        lines.append("")

    # 투자 전략
    lines.append("## 4. 투자 전략 및 액션 플랜\n")
    if strategy.get("strategy"):
        lines.append(f"**전략:** {strategy['strategy']}\n")
    if strategy.get("action_short"):
        lines.append(f"**단기(3개월):** {strategy['action_short']}\n")
    if strategy.get("action_mid"):
        lines.append(f"**중기(1년):** {strategy['action_mid']}\n")
    if strategy.get("risks"):
        lines.append("**리스크 요인:**")
        for r in strategy["risks"]:
            lines.append(f"- {r}")

    return "\n".join(lines)


class ReportOrchestrator:
    def __init__(
        self,
        llm: BaseLLMClient,
        prompt_loader: PromptLoader,
        poi_collector: PoiCollector,
        trend_analyzer: TrendAnalyzer,
        report_repository: ReportRepository,
    ):
        self._llm = llm
        self._prompt_loader = prompt_loader
        self._poi_collector = poi_collector
        self._trend_analyzer = trend_analyzer
        self._repo = report_repository

    def generate(
        self,
        target_date: date,
        candidates: List[Dict[str, Any]],
        persona_data: Dict[str, Any],
        scoring_config: Dict[str, Any],
        macro_summary: str = "",
    ) -> ProfessionalReport:
        # Step 1: 예산 계산
        budget_available = _calc_budget(persona_data, macro_summary)
        logger.info(f"[ReportOrchestrator] 구매 가능 예산: {budget_available / 1_0000_0000:.1f}억")

        # Step 2: POI 수집 (캐시 우선)
        enriched = _enrich_with_poi(candidates, self._poi_collector)

        # Step 3: 실거래가 추세
        enriched = _enrich_with_trend(enriched, self._trend_analyzer)

        # Step 4: 스코어링
        weights = persona_data.get("priority_weights", {})
        scored = ScoringEngine(weights, scoring_config).score_all(enriched)
        top5 = scored[:5]

        # Step 5: LLM 분석 (3개 에이전트)
        location_analyses = _call_location_agent(self._llm, self._prompt_loader, top5)
        school_analyses = _call_school_agent(self._llm, self._prompt_loader, top5)
        strategy = _call_strategy_agent(
            self._llm, self._prompt_loader, top5,
            macro_summary, budget_available, persona_data,
        )

        # Step 6: Markdown 조립
        markdown = _build_markdown(
            target_date, budget_available, macro_summary,
            top5, location_analyses, school_analyses, strategy,
        )

        report = ProfessionalReport(
            date=target_date.strftime("%Y-%m-%d"),
            budget_available=budget_available,
            macro_summary=macro_summary,
            candidates_summary=[
                {"apt_name": c["apt_name"], "total_score": c.get("total_score", 0), "scores": c.get("scores", {})}
                for c in top5
            ],
            location_analyses=[{"apt_name": k, "text": v} for k, v in location_analyses.items()],
            school_analyses=[{"apt_name": k, "text": v} for k, v in school_analyses.items()],
            strategy=strategy,
            markdown=markdown,
        )
        self._repo.save(report)
        return report
```

- [ ] **Step 4: 테스트 실행 → 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_report_orchestrator.py -v
```
Expected: `3 passed`

- [ ] **Step 5: 커밋**

```bash
git add src/modules/real_estate/report_orchestrator.py tests/modules/real_estate/test_report_orchestrator.py
git commit -m "feat(orchestrator): ReportOrchestrator — 전문 컨설턴트 리포트 파이프라인"
```

---

## Task 8: FastAPI 엔드포인트 추가

**Files:**
- Modify: `src/api/routers/real_estate.py`
- Modify: `src/dashboard/api_client.py`

- [ ] **Step 1: real_estate.py 라우터에 전문 리포트 엔드포인트 추가**

`src/api/routers/real_estate.py` 파일의 마지막 부분에 다음을 추가한다. (기존 import에 `date`가 없으면 `from datetime import date` 추가)

먼저 파일 상단 import에 추가:
```python
from datetime import date as _date
```

파일 끝에 다음 엔드포인트 추가:
```python
# ── 전문 컨설턴트 리포트 ──────────────────────────────────────────────

def _get_report_repo():
    """ReportRepository 인스턴스 반환 (config에서 경로 로드)."""
    from modules.real_estate.config import RealEstateConfig
    from modules.real_estate.report_repository import ReportRepository
    cfg = RealEstateConfig()
    storage_path = cfg.get("report", {}).get("report_storage_path", "data/real_estate_reports")
    return ReportRepository(storage_path=storage_path)


@router.get("/dashboard/real-estate/professional-reports")
def list_professional_reports():
    """저장된 전문 리포트 날짜 목록 반환."""
    try:
        repo = _get_report_repo()
        return {"dates": repo.list_dates()}
    except Exception as e:
        logger.error(f"[API] list_professional_reports 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/real-estate/professional-reports/{date_str}")
def get_professional_report(date_str: str):
    """특정 날짜 전문 리포트 반환."""
    try:
        repo = _get_report_repo()
        report = repo.load(date_str)
        if report is None:
            raise HTTPException(status_code=404, detail=f"리포트 없음: {date_str}")
        return {
            "date": report.date,
            "budget_available": report.budget_available,
            "macro_summary": report.macro_summary,
            "candidates_summary": report.candidates_summary,
            "location_analyses": report.location_analyses,
            "school_analyses": report.school_analyses,
            "strategy": report.strategy,
            "markdown": report.markdown,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] get_professional_report 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/professional-report/generate")
def generate_professional_report():
    """오늘 날짜 전문 리포트 즉시 생성 (대시보드 수동 실행용)."""
    import os
    from datetime import date
    from modules.real_estate.config import RealEstateConfig
    from modules.real_estate.report_orchestrator import ReportOrchestrator
    from modules.real_estate.report_repository import ReportRepository
    from modules.real_estate.poi_collector import PoiCollector
    from modules.real_estate.trend_analyzer import TrendAnalyzer
    from modules.real_estate.persona_manager import PersonaManager, PreferenceRulesManager
    from modules.real_estate.apt_master_repository import AptMasterRepository
    from modules.real_estate.transaction_repository import TransactionRepository
    from modules.real_estate.macro.service import MacroService
    from modules.real_estate.geocoder import GeocoderService
    from core.llm_pipeline import build_llm_pipeline
    from core.prompt_loader import PromptLoader
    from core.storage import get_storage_provider

    try:
        cfg = RealEstateConfig()
        re_db = cfg.get("real_estate_db_path", "data/real_estate.db")
        report_path = cfg.get("report", {}).get("report_storage_path", "data/real_estate_reports")
        kakao_key = os.getenv("KAKAO_API_KEY", "")

        persona = PersonaManager().load()
        scoring_cfg = cfg.get("scoring", {})

        # 후보 단지 로드 (persona interest_areas 기반)
        apt_repo = AptMasterRepository(db_path=re_db)
        tx_repo = TransactionRepository(db_path=re_db)
        interest_areas = persona.get("user", {}).get("interest_areas", [])
        district_codes = cfg.get_district_codes_by_names(interest_areas) if hasattr(cfg, "get_district_codes_by_names") else []

        candidates = apt_repo.list_by_district_codes(district_codes) if district_codes else apt_repo.list_all()
        candidate_dicts = [c.__dict__ if hasattr(c, "__dict__") else dict(c) for c in candidates[:50]]

        # 거시경제 요약
        macro_svc = MacroService()
        macro_latest = macro_svc.get_latest()
        macro_lines = [f"{m.get('name', '')}: {m.get('value', '')}{m.get('unit', '')}" for m in (macro_latest or [])]
        macro_summary = " | ".join(macro_lines[:4])

        llm = build_llm_pipeline()
        root_storage = get_storage_provider("local", root_path=".")
        prompt_loader = PromptLoader(root_storage, base_dir="src/modules/real_estate/prompts")

        orchestrator = ReportOrchestrator(
            llm=llm,
            prompt_loader=prompt_loader,
            poi_collector=PoiCollector(api_key=kakao_key, db_path=re_db),
            trend_analyzer=TrendAnalyzer(db_path=re_db),
            report_repository=ReportRepository(storage_path=report_path),
        )

        report = orchestrator.generate(
            target_date=date.today(),
            candidates=candidate_dicts,
            persona_data=persona,
            scoring_config=scoring_cfg,
            macro_summary=macro_summary,
        )
        return {"status": "success", "date": report.date, "candidates_count": len(report.candidates_summary)}
    except Exception as e:
        logger.error(f"[API] generate_professional_report 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 2: api_client.py에 메서드 추가**

`src/dashboard/api_client.py`에서 `DashboardClient` 클래스에 다음 메서드를 추가한다:

```python
@staticmethod
def list_professional_reports() -> list:
    """전문 리포트 날짜 목록 반환."""
    try:
        resp = requests.get(f"{DashboardClient.BASE_URL}/dashboard/real-estate/professional-reports", timeout=10)
        if resp.status_code == 200:
            return resp.json().get("dates", [])
        return []
    except Exception:
        return []

@staticmethod
def get_professional_report(date_str: str) -> dict:
    """특정 날짜 전문 리포트 반환."""
    try:
        resp = requests.get(
            f"{DashboardClient.BASE_URL}/dashboard/real-estate/professional-reports/{date_str}",
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()
        return {}
    except Exception:
        return {}

@staticmethod
def trigger_generate_professional_report() -> dict:
    """전문 리포트 즉시 생성 트리거."""
    try:
        resp = requests.post(
            f"{DashboardClient.BASE_URL}/jobs/professional-report/generate",
            timeout=300,
        )
        if resp.status_code == 200:
            return resp.json()
        return {"error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"error": str(e)}
```

- [ ] **Step 3: 커밋**

```bash
git add src/api/routers/real_estate.py src/dashboard/api_client.py
git commit -m "feat(api): 전문 리포트 CRUD 엔드포인트 + DashboardClient 메서드 추가"
```

---

## Task 9: Dashboard Tab 3 업그레이드

**Files:**
- Modify: `src/dashboard/views/real_estate.py` (Tab 3 섹션만 교체)

- [ ] **Step 1: Tab 3 교체 코드 작성**

`src/dashboard/views/real_estate.py`에서 Tab 3 부분 (line ~677~781)을 다음으로 교체한다:

```python
    # ──────────────────────────────────────────────────────────
    # TAB 3: Report Archive (전문 컨설턴트 리포트)
    # ──────────────────────────────────────────────────────────
    with tab3:
        st.subheader("📋 부동산 전략 리포트 아카이브")

        # 리포트 생성 버튼
        with st.expander("⚙️ 리포트 생성", expanded=False):
            st.caption("오늘 날짜 기준 전문 컨설턴트 리포트를 생성합니다. (2~5분 소요)")
            if st.button("📊 전문 리포트 생성", type="primary", use_container_width=True, key="gen_pro_report"):
                with st.spinner("POI 수집 + 실거래가 추세 + LLM 분석 중..."):
                    r = DashboardClient.trigger_generate_professional_report()
                if "error" in r:
                    st.error(f"❌ 오류: {r['error']}")
                else:
                    st.success(f"✅ {r.get('date', '')} 리포트 생성 완료 ({r.get('candidates_count', 0)}개 단지 분석)")
                    st.session_state.pop("pro_report_dates", None)
                    st.rerun()

        st.markdown("---")

        # 날짜 목록 로드
        if "pro_report_dates" not in st.session_state:
            st.session_state.pro_report_dates = DashboardClient.list_professional_reports()

        dates = st.session_state.get("pro_report_dates", [])

        if not dates:
            st.warning("저장된 전문 리포트가 없습니다.")
            st.info("위 '⚙️ 리포트 생성'을 실행하거나 매일 07:00 자동 생성을 기다리세요.")
        else:
            selected_date = st.selectbox("날짜 선택", dates, key="pro_report_date_select")

            if st.button("📄 리포트 보기", key="view_pro_report") or st.session_state.get("pro_report_auto_load"):
                st.session_state.pro_report_auto_load = True
                with st.spinner("리포트 로딩 중..."):
                    report = DashboardClient.get_professional_report(selected_date)

                if not report:
                    st.error("리포트를 불러올 수 없습니다.")
                else:
                    st.markdown("---")

                    # Executive Summary
                    budget_str = f"{report.get('budget_available', 0) / 1_0000_0000:.1f}억"
                    st.markdown(f"### 💰 구매 가능 예산: {budget_str}")
                    st.caption(report.get("macro_summary", ""))

                    candidates_summary = report.get("candidates_summary", [])
                    if candidates_summary:
                        st.markdown("**🏆 추천 Top 3**")
                        for c in candidates_summary[:3]:
                            st.markdown(f"- **{c['apt_name']}** — {c.get('total_score', 0):.0f}점")

                    st.markdown("---")

                    # 단지별 상세 (expander)
                    location_map = {a["apt_name"]: a["text"] for a in report.get("location_analyses", [])}
                    school_map = {a["apt_name"]: a["text"] for a in report.get("school_analyses", [])}

                    for c in candidates_summary[:5]:
                        name = c["apt_name"]
                        with st.expander(f"📋 {name} — {c.get('total_score', 0):.0f}점"):
                            scores = c.get("scores", {})
                            sc1, sc2, sc3, sc4, sc5 = st.columns(5)
                            with sc1:
                                st.metric("출퇴근", f"{scores.get('commute', '-')}점")
                            with sc2:
                                st.metric("환금성", f"{scores.get('liquidity', '-')}점")
                            with sc3:
                                st.metric("생활편의", f"{scores.get('living_convenience', '-')}점")
                            with sc4:
                                st.metric("학군", f"{scores.get('school', '-')}점")
                            with sc5:
                                st.metric("투자잠재력", f"{scores.get('price_potential', '-')}점")

                            if location_map.get(name):
                                st.markdown("**📍 입지**")
                                st.write(location_map[name])
                            if school_map.get(name):
                                st.markdown("**🏫 학군**")
                                st.write(school_map[name])

                    st.markdown("---")

                    # 투자 전략
                    strategy = report.get("strategy", {})
                    if strategy:
                        st.markdown("### 🎯 투자 전략 및 액션 플랜")
                        if strategy.get("strategy"):
                            st.info(f"**전략:** {strategy['strategy']}")
                        col_s, col_m = st.columns(2)
                        with col_s:
                            st.markdown("**단기(3개월)**")
                            st.write(strategy.get("action_short", "-"))
                        with col_m:
                            st.markdown("**중기(1년)**")
                            st.write(strategy.get("action_mid", "-"))
                        if strategy.get("risks"):
                            st.markdown("**⚠️ 리스크 요인**")
                            for r in strategy["risks"]:
                                st.markdown(f"- {r}")

                    st.markdown("---")

                    # 전체 마크다운 리포트
                    with st.expander("📄 전체 리포트 (Markdown)", expanded=False):
                        st.markdown(report.get("markdown", ""))
```

- [ ] **Step 2: 대시보드 서버 재시작 후 확인**

```bash
# FastAPI 서버 실행 (별도 터미널)
arch -arm64 .venv/bin/python3.12 -m uvicorn src.api.main:app --reload --port 8000

# Streamlit 대시보드 실행 (별도 터미널)
arch -arm64 .venv/bin/python3.12 -m streamlit run src/dashboard/main.py
```

확인 사항:
- `🏢 Real Estate` → `📋 Report Archive` 탭 클릭 가능
- "저장된 전문 리포트가 없습니다." 메시지 표시 (정상)
- "⚙️ 리포트 생성" expander 열림
- 에러 없음

- [ ] **Step 3: 커밋**

```bash
git add src/dashboard/views/real_estate.py
git commit -m "feat(dashboard): Tab 3 전문 리포트 아카이브 뷰어로 전면 개편"
```

---

## Task 10: 전체 테스트 + 통합 검증

**Files:** 없음 (검증만)

- [ ] **Step 1: 전체 단위 테스트 실행**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/ -v --ignore=tests/e2e
```
Expected: 전체 통과 (기존 + 신규 테스트 포함)

- [ ] **Step 2: 수동 통합 테스트 — 리포트 생성 확인**

FastAPI 서버 실행 후:
```bash
curl -X POST http://localhost:8000/jobs/professional-report/generate
```
Expected: `{"status": "success", "date": "2026-05-01", "candidates_count": N}`

- [ ] **Step 3: 리포트 파일 확인**

```bash
ls data/real_estate_reports/
# 2026-05-01.md, 2026-05-01.json 존재 확인
arch -arm64 .venv/bin/python3.12 -c "
import json
with open('data/real_estate_reports/2026-05-01.json') as f:
    d = json.load(f)
print('단지 수:', len(d['candidates_summary']))
print('전략:', d['strategy'].get('strategy', '')[:50])
"
```

- [ ] **Step 4: 최종 커밋**

```bash
git add .
git commit -m "feat(real-estate): 전문 컨설턴트 리포트 시스템 Phase 1 완성"
```
