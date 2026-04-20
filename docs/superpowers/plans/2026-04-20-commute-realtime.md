# 출퇴근 시간 실시간 계산 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `area_intel.json` 수작업 동단위 값을 T-map API 기반 단지별 실시간 출퇴근 시간으로 교체하고, Claude Code에서도 MCP 도구로 즉시 조회할 수 있게 한다.

**Architecture:** `src/modules/real_estate/commute/` 패키지에 TmapClient → CommuteRepository(SQLite 캐시) → CommuteService 3계층을 구축한다. `RealEstateAgent._enrich_transactions()`에서 CommuteService를 호출하고, 별도 MCP 서버가 같은 서비스를 대화형으로 노출한다.

**Tech Stack:** Python 3.12, requests, sqlite3, mcp (FastMCP), T-map Open API, Kakao Local API (기존 GeocoderService 재사용)

---

## File Map

| 파일 | 역할 | 생성/수정 |
|------|------|----------|
| `src/modules/real_estate/commute/__init__.py` | 패키지 마커 | 생성 |
| `src/modules/real_estate/commute/models.py` | CommuteResult dataclass | 생성 |
| `src/modules/real_estate/commute/tmap_client.py` | T-map REST API 래퍼 | 생성 |
| `src/modules/real_estate/commute/commute_repository.py` | SQLite 캐시 CRUD | 생성 |
| `src/modules/real_estate/commute/commute_service.py` | 오케스트레이터 | 생성 |
| `src/mcp_servers/__init__.py` | 패키지 마커 | 생성 |
| `src/mcp_servers/commute_server.py` | MCP 도구 서버 | 생성 |
| `tests/modules/real_estate/commute/__init__.py` | 테스트 패키지 마커 | 생성 |
| `tests/modules/real_estate/commute/test_tmap_client.py` | TmapClient 테스트 | 생성 |
| `tests/modules/real_estate/commute/test_commute_repository.py` | Repository 테스트 | 생성 |
| `tests/modules/real_estate/commute/test_commute_service.py` | Service 테스트 | 생성 |
| `src/modules/real_estate/config.yaml` | commute 설정 추가 | 수정 |
| `.env` | TMAP_API_KEY 추가 | 수정 |
| `requirements.txt` | mcp 패키지 추가 | 수정 |
| `src/modules/real_estate/service.py` | CommuteService 주입 + _enrich_transactions 교체 | 수정 |
| `src/modules/real_estate/scoring.py` | commute_transit_minutes 우선 사용 | 수정 |
| `src/modules/real_estate/prompts/context_analyst.md` | 필드명 업데이트 | 수정 |
| `src/modules/real_estate/prompts/insight_parser.md` | 필드명 업데이트 | 수정 |

---

## Task 1: 패키지 스캐폴딩 + CommuteResult 모델

**Files:**
- Create: `src/modules/real_estate/commute/__init__.py`
- Create: `src/modules/real_estate/commute/models.py`
- Create: `src/mcp_servers/__init__.py`
- Create: `tests/modules/real_estate/commute/__init__.py`

- [ ] **Step 1: 디렉토리 및 __init__.py 생성**

```bash
mkdir -p src/modules/real_estate/commute
mkdir -p src/mcp_servers
mkdir -p tests/modules/real_estate/commute
touch src/modules/real_estate/commute/__init__.py
touch src/mcp_servers/__init__.py
touch tests/modules/real_estate/commute/__init__.py
```

- [ ] **Step 2: `src/modules/real_estate/commute/models.py` 작성**

```python
from dataclasses import dataclass, field


@dataclass
class CommuteResult:
    origin_key: str          # 캐시 식별자: "{district_code}__{apt_name}"
    destination: str         # 예: "삼성역"
    mode: str                # "transit" | "car" | "walking"
    duration_minutes: int
    distance_meters: int
    cached: bool = field(default=False)
```

- [ ] **Step 3: requirements.txt에 mcp 추가**

`requirements.txt` 파일 끝에 아래 줄 추가:

```
mcp>=1.0.0
```

- [ ] **Step 4: mcp 패키지 설치**

```bash
arch -arm64 .venv/bin/pip install mcp
```

Expected: `Successfully installed mcp-...`

- [ ] **Step 5: Commit**

```bash
git add src/modules/real_estate/commute/ src/mcp_servers/__init__.py \
        tests/modules/real_estate/commute/__init__.py requirements.txt
git commit -m "feat(commute): scaffold commute package + CommuteResult model"
```

---

## Task 2: TmapClient (TDD)

**Files:**
- Create: `src/modules/real_estate/commute/tmap_client.py`
- Create: `tests/modules/real_estate/commute/test_tmap_client.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/modules/real_estate/commute/test_tmap_client.py`:

```python
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))


TRANSIT_RESPONSE = {
    "metaData": {
        "plan": {
            "itineraries": [
                {"totalTime": 3540, "totalWalkDistance": 456}
            ]
        }
    }
}

CAR_RESPONSE = {
    "features": [
        {"type": "Feature", "properties": {"totalTime": 2400, "totalDistance": 15000}}
    ]
}

WALKING_RESPONSE = {
    "features": [
        {"type": "Feature", "properties": {"totalTime": 3600, "totalDistance": 5000}}
    ]
}


class TestTmapClientTransit:
    def test_transit_duration_seconds_to_minutes(self):
        """3540초 = 59분으로 파싱되어야 한다."""
        from modules.real_estate.commute.tmap_client import TmapClient
        client = TmapClient(api_key="test-key")

        mock_resp = MagicMock()
        mock_resp.json.return_value = TRANSIT_RESPONSE
        mock_resp.raise_for_status.return_value = None

        with patch("modules.real_estate.commute.tmap_client.requests.post", return_value=mock_resp) as mock_post:
            duration, distance = client.route(
                origin_lat=37.4942, origin_lng=127.0611,
                dest_lat=37.5088, dest_lng=127.0633,
                mode="transit",
            )

        assert duration == 59
        assert distance == 456
        call_url = mock_post.call_args[0][0]
        assert "transit/routes" in call_url

    def test_transit_missing_itineraries_raises(self):
        from modules.real_estate.commute.tmap_client import TmapClient
        client = TmapClient(api_key="test-key")

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"metaData": {"plan": {"itineraries": []}}}
        mock_resp.raise_for_status.return_value = None

        with patch("modules.real_estate.commute.tmap_client.requests.post", return_value=mock_resp):
            with pytest.raises(ValueError, match="itineraries"):
                client.route(37.4942, 127.0611, 37.5088, 127.0633, mode="transit")


class TestTmapClientCar:
    def test_car_duration_seconds_to_minutes(self):
        """2400초 = 40분으로 파싱되어야 한다."""
        from modules.real_estate.commute.tmap_client import TmapClient
        client = TmapClient(api_key="test-key")

        mock_resp = MagicMock()
        mock_resp.json.return_value = CAR_RESPONSE
        mock_resp.raise_for_status.return_value = None

        with patch("modules.real_estate.commute.tmap_client.requests.post", return_value=mock_resp) as mock_post:
            duration, distance = client.route(37.4942, 127.0611, 37.5088, 127.0633, mode="car")

        assert duration == 40
        assert distance == 15000
        call_url = mock_post.call_args[0][0]
        assert "tmap/routes" in call_url
        assert "pedestrian" not in call_url


class TestTmapClientWalking:
    def test_walking_duration_seconds_to_minutes(self):
        """3600초 = 60분으로 파싱되어야 한다."""
        from modules.real_estate.commute.tmap_client import TmapClient
        client = TmapClient(api_key="test-key")

        mock_resp = MagicMock()
        mock_resp.json.return_value = WALKING_RESPONSE
        mock_resp.raise_for_status.return_value = None

        with patch("modules.real_estate.commute.tmap_client.requests.post", return_value=mock_resp) as mock_post:
            duration, distance = client.route(37.4942, 127.0611, 37.5088, 127.0633, mode="walking")

        assert duration == 60
        assert distance == 5000
        call_url = mock_post.call_args[0][0]
        assert "pedestrian" in call_url

    def test_invalid_mode_raises(self):
        from modules.real_estate.commute.tmap_client import TmapClient
        client = TmapClient(api_key="test-key")
        with pytest.raises(ValueError, match="mode"):
            client.route(0, 0, 0, 0, mode="bicycle")
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/commute/test_tmap_client.py -v
```

Expected: `ModuleNotFoundError` (tmap_client.py 미존재)

- [ ] **Step 3: `src/modules/real_estate/commute/tmap_client.py` 구현**

```python
import logging
import math
import requests
from typing import Tuple

logger = logging.getLogger(__name__)

_TRANSIT_URL = "https://apis.openapi.sk.com/transit/routes"
_CAR_URL = "https://apis.openapi.sk.com/tmap/routes"
_WALKING_URL = "https://apis.openapi.sk.com/tmap/routes/pedestrian"

_VALID_MODES = {"transit", "car", "walking"}


class TmapClient:
    """T-map Open API 래퍼. transit / car / walking 3가지 경로를 조회한다."""

    def __init__(self, api_key: str, timeout: int = 10):
        self._api_key = api_key
        self._timeout = timeout

    def route(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        mode: str,
    ) -> Tuple[int, int]:
        """
        Returns (duration_minutes, distance_meters).
        T-map 좌표 파라미터: X=경도(lng), Y=위도(lat).
        """
        if mode not in _VALID_MODES:
            raise ValueError(f"mode must be one of {_VALID_MODES}, got '{mode}'")

        if mode == "transit":
            return self._route_transit(origin_lat, origin_lng, dest_lat, dest_lng)
        if mode == "car":
            return self._route_car(origin_lat, origin_lng, dest_lat, dest_lng)
        return self._route_walking(origin_lat, origin_lng, dest_lat, dest_lng)

    def _headers(self) -> dict:
        return {"appKey": self._api_key, "Content-Type": "application/json"}

    def _route_transit(self, olat, olng, dlat, dlng) -> Tuple[int, int]:
        payload = {
            "startX": str(olng),
            "startY": str(olat),
            "endX": str(dlng),
            "endY": str(dlat),
            "count": 1,
            "lang": 0,
            "format": "json",
        }
        resp = requests.post(_TRANSIT_URL, json=payload, headers=self._headers(), timeout=self._timeout)
        resp.raise_for_status()
        data = resp.json()
        itineraries = data.get("metaData", {}).get("plan", {}).get("itineraries", [])
        if not itineraries:
            raise ValueError("T-map transit: empty itineraries in response")
        best = itineraries[0]
        duration = math.ceil(best["totalTime"] / 60)
        distance = best.get("totalWalkDistance", 0)
        return duration, distance

    def _route_car(self, olat, olng, dlat, dlng) -> Tuple[int, int]:
        payload = {
            "startX": str(olng),
            "startY": str(olat),
            "endX": str(dlng),
            "endY": str(dlat),
            "reqCoordType": "WGS84GEO",
            "resCoordType": "WGS84GEO",
            "startName": "출발",
            "endName": "도착",
        }
        resp = requests.post(f"{_CAR_URL}?version=1", json=payload, headers=self._headers(), timeout=self._timeout)
        resp.raise_for_status()
        features = resp.json().get("features", [])
        if not features:
            raise ValueError("T-map car: empty features in response")
        props = features[0]["properties"]
        duration = math.ceil(props["totalTime"] / 60)
        distance = props.get("totalDistance", 0)
        return duration, distance

    def _route_walking(self, olat, olng, dlat, dlng) -> Tuple[int, int]:
        payload = {
            "startX": str(olng),
            "startY": str(olat),
            "endX": str(dlng),
            "endY": str(dlat),
            "reqCoordType": "WGS84GEO",
            "resCoordType": "WGS84GEO",
            "startName": "출발",
            "endName": "도착",
        }
        resp = requests.post(f"{_WALKING_URL}?version=1", json=payload, headers=self._headers(), timeout=self._timeout)
        resp.raise_for_status()
        features = resp.json().get("features", [])
        if not features:
            raise ValueError("T-map walking: empty features in response")
        props = features[0]["properties"]
        duration = math.ceil(props["totalTime"] / 60)
        distance = props.get("totalDistance", 0)
        return duration, distance
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/commute/test_tmap_client.py -v
```

Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add src/modules/real_estate/commute/tmap_client.py \
        tests/modules/real_estate/commute/test_tmap_client.py
git commit -m "feat(commute): TmapClient — transit/car/walking 경로 조회"
```

---

## Task 3: CommuteRepository (TDD)

**Files:**
- Create: `src/modules/real_estate/commute/commute_repository.py`
- Create: `tests/modules/real_estate/commute/test_commute_repository.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/modules/real_estate/commute/test_commute_repository.py`:

```python
import os
import sys
import pytest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

from modules.real_estate.commute.models import CommuteResult


def make_result(origin_key="11680__래미안", mode="transit", minutes=25, meters=3000):
    return CommuteResult(
        origin_key=origin_key,
        destination="삼성역",
        mode=mode,
        duration_minutes=minutes,
        distance_meters=meters,
    )


class TestCommuteRepository:
    def _repo(self, ttl_days=90):
        from modules.real_estate.commute.commute_repository import CommuteRepository
        return CommuteRepository(db_path=":memory:", ttl_days=ttl_days)

    def test_get_returns_none_when_empty(self):
        repo = self._repo()
        result = repo.get("11680__없는단지", "삼성역", "transit")
        assert result is None

    def test_upsert_and_get(self):
        repo = self._repo()
        r = make_result()
        repo.upsert(r)
        got = repo.get("11680__래미안", "삼성역", "transit")
        assert got is not None
        assert got.duration_minutes == 25
        assert got.cached is True

    def test_expired_cache_returns_none(self):
        repo = self._repo(ttl_days=0)  # 즉시 만료
        r = make_result()
        repo.upsert(r)
        got = repo.get("11680__래미안", "삼성역", "transit")
        assert got is None

    def test_upsert_updates_existing(self):
        repo = self._repo()
        repo.upsert(make_result(minutes=25))
        repo.upsert(make_result(minutes=59))  # 갱신
        got = repo.get("11680__래미안", "삼성역", "transit")
        assert got.duration_minutes == 59

    def test_different_modes_stored_independently(self):
        repo = self._repo()
        repo.upsert(make_result(mode="transit", minutes=59))
        repo.upsert(make_result(mode="car", minutes=30))
        repo.upsert(make_result(mode="walking", minutes=90))

        assert repo.get("11680__래미안", "삼성역", "transit").duration_minutes == 59
        assert repo.get("11680__래미안", "삼성역", "car").duration_minutes == 30
        assert repo.get("11680__래미안", "삼성역", "walking").duration_minutes == 90

    def test_different_origins_stored_independently(self):
        repo = self._repo()
        repo.upsert(make_result(origin_key="11680__A단지", minutes=20))
        repo.upsert(make_result(origin_key="11710__B단지", minutes=59))

        assert repo.get("11680__A단지", "삼성역", "transit").duration_minutes == 20
        assert repo.get("11710__B단지", "삼성역", "transit").duration_minutes == 59
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/commute/test_commute_repository.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: `src/modules/real_estate/commute/commute_repository.py` 구현**

```python
import sqlite3
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from .models import CommuteResult

logger = logging.getLogger(__name__)

_DDL = """
CREATE TABLE IF NOT EXISTS commute_cache (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    origin_key       TEXT NOT NULL,
    destination      TEXT NOT NULL,
    mode             TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL,
    distance_meters  INTEGER NOT NULL DEFAULT 0,
    cached_at        TEXT NOT NULL,
    expires_at       TEXT NOT NULL,
    UNIQUE(origin_key, destination, mode)
)
"""


class CommuteRepository:
    def __init__(self, db_path: str, ttl_days: int = 90):
        self._db_path = db_path
        self._ttl_days = ttl_days
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self._db_path) as conn:
            conn.executescript(_DDL)
            conn.commit()

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def get(self, origin_key: str, destination: str, mode: str) -> Optional[CommuteResult]:
        """유효한 캐시가 있으면 CommuteResult(cached=True) 반환, 없거나 만료시 None."""
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM commute_cache WHERE origin_key=? AND destination=? AND mode=?",
                (origin_key, destination, mode),
            ).fetchone()

        if row is None:
            return None

        expires_at = datetime.fromisoformat(row["expires_at"])
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if self._now() > expires_at:
            return None

        return CommuteResult(
            origin_key=row["origin_key"],
            destination=row["destination"],
            mode=row["mode"],
            duration_minutes=row["duration_minutes"],
            distance_meters=row["distance_meters"],
            cached=True,
        )

    def upsert(self, result: CommuteResult):
        """캐시 저장 또는 갱신."""
        now = self._now()
        expires_at = now + timedelta(days=self._ttl_days)
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO commute_cache
                    (origin_key, destination, mode, duration_minutes, distance_meters, cached_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(origin_key, destination, mode) DO UPDATE SET
                    duration_minutes = excluded.duration_minutes,
                    distance_meters  = excluded.distance_meters,
                    cached_at        = excluded.cached_at,
                    expires_at       = excluded.expires_at
                """,
                (
                    result.origin_key, result.destination, result.mode,
                    result.duration_minutes, result.distance_meters,
                    now.isoformat(), expires_at.isoformat(),
                ),
            )
            conn.commit()
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/commute/test_commute_repository.py -v
```

Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add src/modules/real_estate/commute/commute_repository.py \
        tests/modules/real_estate/commute/test_commute_repository.py
git commit -m "feat(commute): CommuteRepository — SQLite 캐시 + TTL 만료 판정"
```

---

## Task 4: CommuteService (TDD)

**Files:**
- Create: `src/modules/real_estate/commute/commute_service.py`
- Create: `tests/modules/real_estate/commute/test_commute_service.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/modules/real_estate/commute/test_commute_service.py`:

```python
import os
import sys
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

from modules.real_estate.commute.models import CommuteResult
from modules.real_estate.commute.commute_repository import CommuteRepository


def make_service(repo=None, tmap_client=None, geocoder=None, config=None):
    from modules.real_estate.commute.commute_service import CommuteService
    repo = repo or CommuteRepository(db_path=":memory:", ttl_days=90)
    config = config or {
        "destination": "삼성역",
        "destination_lat": 37.5088,
        "destination_lng": 127.0633,
    }
    return CommuteService(
        repo=repo,
        tmap_client=tmap_client or MagicMock(),
        geocoder=geocoder or MagicMock(),
        config=config,
    )


class TestCommuteServiceCacheHit:
    def test_cache_hit_returns_without_api_call(self):
        """캐시에 유효한 값이 있으면 tmap_client를 호출하지 않는다."""
        repo = CommuteRepository(db_path=":memory:", ttl_days=90)
        repo.upsert(CommuteResult(
            origin_key="11680__래미안",
            destination="삼성역",
            mode="transit",
            duration_minutes=20,
            distance_meters=1000,
        ))
        mock_client = MagicMock()
        svc = make_service(repo=repo, tmap_client=mock_client)

        result = svc.get(
            origin_key="11680__래미안",
            road_address="서울 강남구 역삼동 123",
            apt_name="래미안",
            district_code="11680",
            mode="transit",
        )

        assert result.duration_minutes == 20
        assert result.cached is True
        mock_client.route.assert_not_called()


class TestCommuteServiceCacheMiss:
    def test_cache_miss_calls_tmap_and_stores(self):
        """캐시가 없으면 geocoder → tmap_client 순서로 호출하고 결과를 저장한다."""
        mock_geocoder = MagicMock()
        mock_geocoder.geocode.return_value = (37.4942, 127.0611)

        mock_client = MagicMock()
        mock_client.route.return_value = (59, 1200)

        repo = CommuteRepository(db_path=":memory:", ttl_days=90)
        svc = make_service(repo=repo, tmap_client=mock_client, geocoder=mock_geocoder)

        result = svc.get(
            origin_key="11710__파크데일",
            road_address="서울 송파구 가락동 124",
            apt_name="파크데일",
            district_code="11710",
            mode="transit",
        )

        assert result.duration_minutes == 59
        assert result.cached is False
        mock_geocoder.geocode.assert_called_once()
        mock_client.route.assert_called_once()

        # 저장 확인
        stored = repo.get("11710__파크데일", "삼성역", "transit")
        assert stored is not None
        assert stored.duration_minutes == 59

    def test_geocode_failure_returns_none(self):
        """지오코딩 실패 시 None 반환 (예외 전파 안 함)."""
        mock_geocoder = MagicMock()
        mock_geocoder.geocode.return_value = None

        svc = make_service(geocoder=mock_geocoder)
        result = svc.get("k", "주소없음", "단지", "11680", mode="transit")
        assert result is None

    def test_tmap_failure_returns_none(self):
        """T-map API 오류 시 None 반환."""
        mock_geocoder = MagicMock()
        mock_geocoder.geocode.return_value = (37.49, 127.06)

        mock_client = MagicMock()
        mock_client.route.side_effect = Exception("T-map 오류")

        svc = make_service(geocoder=mock_geocoder, tmap_client=mock_client)
        result = svc.get("k", "주소", "단지", "11680", mode="transit")
        assert result is None


class TestCommuteServiceGetAllModes:
    def test_get_all_modes_returns_three_results(self):
        """get_all_modes는 transit/car/walking 모두 반환한다."""
        mock_geocoder = MagicMock()
        mock_geocoder.geocode.return_value = (37.49, 127.06)

        mock_client = MagicMock()
        mock_client.route.side_effect = [(59, 1200), (30, 15000), (90, 5000)]

        svc = make_service(geocoder=mock_geocoder, tmap_client=mock_client)
        results = svc.get_all_modes("k", "서울 송파구 가락동 124", "파크데일", "11710")

        assert results["transit"].duration_minutes == 59
        assert results["car"].duration_minutes == 30
        assert results["walking"].duration_minutes == 90
        assert mock_client.route.call_count == 3

    def test_get_all_modes_partial_failure_skips_failed_mode(self):
        """일부 모드 실패 시 나머지만 반환한다."""
        mock_geocoder = MagicMock()
        mock_geocoder.geocode.return_value = (37.49, 127.06)

        mock_client = MagicMock()
        mock_client.route.side_effect = [(59, 1200), Exception("car 오류"), (90, 5000)]

        svc = make_service(geocoder=mock_geocoder, tmap_client=mock_client)
        results = svc.get_all_modes("k", "주소", "단지", "11710")

        assert "transit" in results
        assert "car" not in results
        assert "walking" in results
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/commute/test_commute_service.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: `src/modules/real_estate/commute/commute_service.py` 구현**

```python
import logging
from typing import Dict, Optional

from .models import CommuteResult
from .commute_repository import CommuteRepository
from .tmap_client import TmapClient

logger = logging.getLogger(__name__)

_ALL_MODES = ("transit", "car", "walking")


class CommuteService:
    """
    출퇴근 시간 조회 오케스트레이터.
    캐시 히트 → DB 반환. 캐시 미스 → geocode → T-map API → 저장 후 반환.
    """

    def __init__(
        self,
        repo: CommuteRepository,
        tmap_client: TmapClient,
        geocoder,          # GeocoderService (DIP — 인터페이스 의존)
        config: dict,
    ):
        self._repo = repo
        self._client = tmap_client
        self._geocoder = geocoder
        self._dest = config["destination"]
        self._dest_lat = float(config["destination_lat"])
        self._dest_lng = float(config["destination_lng"])

    def get(
        self,
        origin_key: str,
        road_address: str,
        apt_name: str,
        district_code: str,
        mode: str,
    ) -> Optional[CommuteResult]:
        """단일 모드 출퇴근 시간 반환. 실패 시 None."""
        cached = self._repo.get(origin_key, self._dest, mode)
        if cached is not None:
            return cached

        coords = self._geocoder.geocode(apt_name, district_code, address=road_address)
        if coords is None:
            logger.warning("[CommuteService] geocode 실패: %s / %s", apt_name, road_address)
            return None

        origin_lat, origin_lng = coords
        try:
            duration, distance = self._client.route(
                origin_lat, origin_lng, self._dest_lat, self._dest_lng, mode=mode
            )
        except Exception as exc:
            logger.warning("[CommuteService] T-map %s 실패 (%s): %s", mode, apt_name, exc)
            return None

        result = CommuteResult(
            origin_key=origin_key,
            destination=self._dest,
            mode=mode,
            duration_minutes=duration,
            distance_meters=distance,
            cached=False,
        )
        self._repo.upsert(result)
        return result

    def get_all_modes(
        self,
        origin_key: str,
        road_address: str,
        apt_name: str,
        district_code: str,
    ) -> Dict[str, CommuteResult]:
        """transit/car/walking 3가지 결과 dict 반환. 실패한 모드는 제외."""
        results: Dict[str, CommuteResult] = {}
        for mode in _ALL_MODES:
            r = self.get(origin_key, road_address, apt_name, district_code, mode)
            if r is not None:
                results[mode] = r
        return results
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/commute/ -v
```

Expected: `모든 테스트 PASS` (Task 2~4 합산 약 14개)

- [ ] **Step 5: Commit**

```bash
git add src/modules/real_estate/commute/commute_service.py \
        tests/modules/real_estate/commute/test_commute_service.py
git commit -m "feat(commute): CommuteService — 캐시 히트/미스 오케스트레이션"
```

---

## Task 5: 설정 추가 (config.yaml + .env)

**Files:**
- Modify: `src/modules/real_estate/config.yaml`
- Modify: `.env`

- [ ] **Step 1: `config.yaml`에 commute 섹션 추가**

`src/modules/real_estate/config.yaml` 파일 맨 끝 `macro_db_path` 줄 앞에 다음을 추가:

```yaml
commute_cache_db_path: "data/commute_cache.db"

commute:
  destination: "삼성역"
  destination_lat: 37.5088
  destination_lng: 127.0633
  cache_ttl_days: 90
```

- [ ] **Step 2: `.env`에 TMAP_API_KEY 추가**

`.env` 파일에 다음 줄 추가 (실제 T-map 개발자 콘솔에서 발급한 키로 교체):

```
TMAP_API_KEY=<T-map_개발자_콘솔에서_발급>
```

T-map API 키 발급 방법: https://openapi.sk.com 접속 → 회원가입 → 앱 생성 → API 키 복사

- [ ] **Step 3: Commit**

```bash
git add src/modules/real_estate/config.yaml .env
git commit -m "config: commute 설정 + TMAP_API_KEY 환경변수 추가"
```

---

## Task 6: RealEstateAgent 통합 (TDD)

`_enrich_transactions()`에서 `area_intel.json` commute 조회를 CommuteService로 교체한다.

**Files:**
- Modify: `src/modules/real_estate/service.py`
- Create: `tests/modules/real_estate/test_enrich_commute.py`

- [ ] **Step 1: 실패하는 통합 테스트 작성**

`tests/modules/real_estate/test_enrich_commute.py`:

```python
import os
import sys
import pytest
from unittest.mock import MagicMock
from datetime import timezone, datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src"))

from modules.real_estate.commute.models import CommuteResult
from modules.real_estate.service import RealEstateAgent


def _make_agent_with_commute(commute_results: dict):
    """commute_service.get_all_modes가 commute_results를 반환하는 가짜 agent 생성."""
    agent = object.__new__(RealEstateAgent)

    mock_apt_repo = MagicMock()
    mock_apt_repo.get_by_name.return_value = None

    mock_apt_master_repo = MagicMock()
    mock_apt_master_repo.get_by_name.return_value = None

    mock_commute = MagicMock()
    mock_commute.get_all_modes.return_value = commute_results

    agent.apt_repo = mock_apt_repo
    agent.apt_master_repo = mock_apt_master_repo
    agent.commute_service = mock_commute
    return agent


def _make_tx(apt_name="테스트아파트", district_code="11710"):
    return {"apt_name": apt_name, "district_code": district_code, "price": 500_000_000}


class TestEnrichTransactionsCommute:
    def test_transit_minutes_attached_from_commute_service(self):
        """commute_service 결과가 commute_transit_minutes로 붙어야 한다."""
        results = {
            "transit": CommuteResult("k", "삼성역", "transit", 59, 1200),
            "car": CommuteResult("k", "삼성역", "car", 35, 15000),
            "walking": CommuteResult("k", "삼성역", "walking", 90, 5000),
        }
        agent = _make_agent_with_commute(results)
        enriched = agent._enrich_transactions([_make_tx()], area_intel={})

        tx = enriched[0]
        assert tx["commute_transit_minutes"] == 59
        assert tx["commute_car_minutes"] == 35
        assert tx["commute_walk_minutes"] == 90
        assert tx.get("commute_minutes") == 59  # 하위호환 fallback

    def test_partial_commute_result_no_crash(self):
        """일부 모드 실패(dict 키 없음)여도 enrich가 크래시 나지 않아야 한다."""
        results = {
            "transit": CommuteResult("k", "삼성역", "transit", 59, 0),
        }
        agent = _make_agent_with_commute(results)
        enriched = agent._enrich_transactions([_make_tx()], area_intel={})
        tx = enriched[0]
        assert tx["commute_transit_minutes"] == 59
        assert tx.get("commute_car_minutes") is None

    def test_commute_service_failure_sets_none(self):
        """commute_service가 빈 dict 반환 시 필드가 None으로 설정된다."""
        agent = _make_agent_with_commute({})
        enriched = agent._enrich_transactions([_make_tx()], area_intel={})
        tx = enriched[0]
        assert tx.get("commute_transit_minutes") is None
        assert tx.get("commute_minutes") is None
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_enrich_commute.py -v
```

Expected: `AttributeError: 'RealEstateAgent' object has no attribute 'commute_service'`

- [ ] **Step 3: `service.py` — import 추가**

`service.py` 상단 import 블록에 추가:

```python
from .commute.tmap_client import TmapClient
from .commute.commute_repository import CommuteRepository
from .commute.commute_service import CommuteService
from .geocoder import GeocoderService
```

- [ ] **Step 4: `service.py` — `__init__`에 CommuteService 주입**

`RealEstateAgent.__init__`의 `# New SQLite repositories` 블록 직후에 추가:

```python
        # Commute Service (T-map 기반 출퇴근 시간 캐시)
        commute_cfg = self.config.get("commute", {})
        commute_db = self.config.get("commute_cache_db_path", "data/commute_cache.db")
        kakao_key = os.getenv("KAKAO_API_KEY", "")
        tmap_key = os.getenv("TMAP_API_KEY", "")
        self.commute_service = CommuteService(
            repo=CommuteRepository(db_path=commute_db, ttl_days=int(commute_cfg.get("cache_ttl_days", 90))),
            tmap_client=TmapClient(api_key=tmap_key),
            geocoder=GeocoderService(api_key=kakao_key),
            config=commute_cfg,
        )
```

- [ ] **Step 5: `service.py` — `_enrich_transactions()` 수정**

`_enrich_transactions()` 메서드 시그니처를 아래와 같이 변경 (area_intel 파라미터 유지, workplace_station 제거):

```python
    def _enrich_transactions(
        self,
        txs: List[Dict[str, Any]],
        area_intel: Dict[str, Any],
        workplace_station: str = "",   # 하위호환용 — 사용 안 함
    ) -> List[Dict[str, Any]]:
```

메서드 내부에서 commute 관련 기존 코드를 아래로 교체.

**교체 전 (삭제할 코드):**

```python
            if matched_dong:
                tx["commute_minutes"] = matched_dong.get(
                    "commute_minutes", dist_intel.get("default_commute_minutes", 99)
                )
                tx["nearest_stations"] = matched_dong.get("nearest_stations", [])
                tx["school_zone_notes"] = matched_dong.get("school_zone_notes", "")
                tx["elementary_schools"] = matched_dong.get("elementary_schools", [])
            else:
                tx["commute_minutes"] = dist_intel.get("default_commute_minutes", 99)
```

**교체 후 (삽입할 코드):**

```python
            if matched_dong:
                tx["nearest_stations"] = matched_dong.get("nearest_stations", [])
                tx["school_zone_notes"] = matched_dong.get("school_zone_notes", "")
                tx["elementary_schools"] = matched_dong.get("elementary_schools", [])

            # ── T-map 실시간 출퇴근 시간 ──
            # detail은 메서드 상단 _lookup_apt_details 호출로 이미 확보됨 (재호출 불필요)
            road_address = ""
            try:
                if detail:
                    road_address = detail.road_address or ""
            except Exception:
                pass

            origin_key = f"{district_code}__{apt_name}"
            commute_results = {}
            try:
                commute_results = self.commute_service.get_all_modes(
                    origin_key=origin_key,
                    road_address=road_address,
                    apt_name=apt_name,
                    district_code=district_code,
                )
            except Exception as exc:
                logger.warning("[Enrich] commute_service 오류 %s: %s", apt_name, exc)

            tx["commute_transit_minutes"] = commute_results["transit"].duration_minutes if "transit" in commute_results else None
            tx["commute_car_minutes"] = commute_results["car"].duration_minutes if "car" in commute_results else None
            tx["commute_walk_minutes"] = commute_results["walking"].duration_minutes if "walking" in commute_results else None
            # 하위호환: scoring.py의 commute_minutes fallback 지원
            tx["commute_minutes"] = tx["commute_transit_minutes"]
```

- [ ] **Step 6: 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_enrich_commute.py -v
```

Expected: `3 passed`

- [ ] **Step 7: 전체 기존 테스트 회귀 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/ -v --ignore=tests/modules/real_estate/commute
```

Expected: 기존 테스트 모두 PASS (commute_service 없는 테스트는 object.__new__ 패턴이므로 영향 없음)

- [ ] **Step 8: Commit**

```bash
git add src/modules/real_estate/service.py \
        tests/modules/real_estate/test_enrich_commute.py
git commit -m "feat(commute): _enrich_transactions T-map 실시간 출퇴근 연동"
```

---

## Task 7: scoring.py + 프롬프트 필드명 업데이트 (TDD)

**Files:**
- Modify: `src/modules/real_estate/scoring.py`
- Modify: `tests/modules/real_estate/test_scoring.py`
- Modify: `src/modules/real_estate/prompts/context_analyst.md`
- Modify: `src/modules/real_estate/prompts/insight_parser.md`

- [ ] **Step 1: `test_scoring.py`에 신규 필드명 테스트 추가**

`tests/modules/real_estate/test_scoring.py` 파일에서 `class TestScoringEngine:` 블록 안 마지막에 추가:

```python
    def test_score_commute_uses_transit_minutes_first(self):
        """commute_transit_minutes가 있으면 commute_minutes보다 우선 사용한다."""
        from modules.real_estate.scoring import ScoringEngine
        engine = ScoringEngine(weights=DEFAULT_WEIGHTS, config=DEFAULT_CONFIG)
        # commute_transit_minutes=59 → LOW(20), commute_minutes=15 → HIGH(100)
        # transit 우선이면 LOW가 나와야 함
        candidate = make_candidate(commute_transit_minutes=59, commute_minutes=15)
        scored = engine.score_all([candidate])
        assert scored[0]["scores"]["commute"] == 20  # LOW

    def test_score_commute_fallback_to_commute_minutes(self):
        """commute_transit_minutes 없으면 commute_minutes로 fallback한다."""
        from modules.real_estate.scoring import ScoringEngine
        engine = ScoringEngine(weights=DEFAULT_WEIGHTS, config=DEFAULT_CONFIG)
        candidate = make_candidate(commute_minutes=15)
        del candidate["commute_minutes"]  # 제거
        candidate["commute_transit_minutes"] = None
        candidate["commute_minutes"] = 15
        scored = engine.score_all([candidate])
        # commute_minutes=15 → HIGH(100)
        assert scored[0]["scores"]["commute"] == 100
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_scoring.py -v -k "transit"
```

Expected: `FAIL` (아직 transit 우선 로직 없음)

- [ ] **Step 3: `scoring.py` — `_score_commute()` 수정**

```python
    def _score_commute(self, c: Dict) -> int:
        minutes = c.get("commute_transit_minutes")
        if minutes is None:
            minutes = c.get("commute_minutes")
        if minutes is None:
            return self.neutral
        return _threshold_score(minutes, self.commute_thresholds)
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_scoring.py -v
```

Expected: 모든 테스트 PASS

- [ ] **Step 5: `context_analyst.md` 필드명 업데이트**

`src/modules/real_estate/prompts/context_analyst.md` 파일에서:

```
`commute_minutes_to_samsung`이 짧은 단지 강조.
```
→
```
`commute_transit_minutes`(대중교통), `commute_car_minutes`(자차)가 짧은 단지 강조.
```

그리고:

```
`nearest_stations`(역명·노선·도보분)과 `commute_minutes_to_samsung`을 인용하여
```
→
```
`nearest_stations`(역명·노선·도보분)과 `commute_transit_minutes`(대중교통), `commute_car_minutes`(자차)를 인용하여
```

그리고:

```
enriched 필드(`commute_minutes_to_samsung`, `reconstruction_potential`, `school_zone_notes`)를
```
→
```
enriched 필드(`commute_transit_minutes`, `commute_car_minutes`, `reconstruction_potential`, `school_zone_notes`)를
```

- [ ] **Step 6: `insight_parser.md` 필드명 업데이트**

`src/modules/real_estate/prompts/insight_parser.md` 파일에서:

```
| 출퇴근 편의성 | 40% | `commute_minutes_to_samsung` ≤ 20분 → HIGH, ≤ 35분 → MEDIUM, > 35분 → LOW |
```
→
```
| 출퇴근 편의성 | 40% | `commute_transit_minutes`(대중교통) ≤ 20분 → HIGH, ≤ 35분 → MEDIUM, > 35분 → LOW. `commute_car_minutes`(자차)도 병기. |
```

그리고:

```
`analyst_insight`의 enriched 거래 데이터에 포함된 `commute_minutes_to_samsung`, `nearest_stations`, `school_zone_notes`, `reconstruction_status` 필드를 근거로 반드시 인용하십시오.
```
→
```
`analyst_insight`의 enriched 거래 데이터에 포함된 `commute_transit_minutes`, `commute_car_minutes`, `nearest_stations`, `school_zone_notes`, `reconstruction_status` 필드를 근거로 반드시 인용하십시오.
```

그리고:

```
⚡ 교통 — [commute_minutes_to_samsung]분 (삼성역 기준)
```
→
```
⚡ 교통 — 대중교통 [commute_transit_minutes]분 / 자차 [commute_car_minutes]분 / 도보 [commute_walk_minutes]분 (삼성역 기준)
```

- [ ] **Step 7: Commit**

```bash
git add src/modules/real_estate/scoring.py \
        tests/modules/real_estate/test_scoring.py \
        src/modules/real_estate/prompts/context_analyst.md \
        src/modules/real_estate/prompts/insight_parser.md
git commit -m "feat(commute): scoring + 프롬프트 필드명 commute_transit_minutes 전환"
```

---

## Task 8: MCP 서버 구현 + 등록

**Files:**
- Create: `src/mcp_servers/commute_server.py`
- Modify: `~/.claude.json`

- [ ] **Step 1: `src/mcp_servers/commute_server.py` 작성**

```python
"""
commute_server.py — T-map 출퇴근 시간 MCP 서버.
CommuteService를 Claude Code 대화 세션에서 도구로 노출한다.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

import yaml
from mcp.server.fastmcp import FastMCP
from modules.real_estate.commute.tmap_client import TmapClient
from modules.real_estate.commute.commute_repository import CommuteRepository
from modules.real_estate.commute.commute_service import CommuteService
from modules.real_estate.geocoder import GeocoderService

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "modules", "real_estate", "config.yaml")

with open(_CONFIG_PATH, "r", encoding="utf-8") as _f:
    _cfg = yaml.safe_load(_f) or {}

_commute_cfg = _cfg.get("commute", {
    "destination": "삼성역",
    "destination_lat": 37.5088,
    "destination_lng": 127.0633,
    "cache_ttl_days": 90,
})
_commute_db = os.path.join(
    os.path.dirname(__file__), "..", "..", _cfg.get("commute_cache_db_path", "data/commute_cache.db")
)

_commute_service = CommuteService(
    repo=CommuteRepository(db_path=_commute_db, ttl_days=int(_commute_cfg.get("cache_ttl_days", 90))),
    tmap_client=TmapClient(api_key=os.getenv("TMAP_API_KEY", "")),
    geocoder=GeocoderService(api_key=os.getenv("KAKAO_API_KEY", "")),
    config=_commute_cfg,
)

mcp = FastMCP("commute")


@mcp.tool()
def get_commute_time(
    address: str,
    apt_name: str,
    district_code: str,
    mode: str = "transit",
) -> dict:
    """
    아파트 도로명주소 → 삼성역 출퇴근 시간 조회 (캐시 우선).

    Args:
        address: 도로명주소 (예: "서울 송파구 가락동 124")
        apt_name: 아파트 단지명 (예: "송파파크데일1단지")
        district_code: 지역코드 5자리 (예: "11710")
        mode: "transit"(대중교통), "car"(자차), "walking"(도보) 중 하나

    Returns:
        {"duration_minutes": int, "destination": str, "mode": str, "cached": bool}
        조회 실패 시 {"error": str}
    """
    origin_key = f"{district_code}__{apt_name}"
    result = _commute_service.get(
        origin_key=origin_key,
        road_address=address,
        apt_name=apt_name,
        district_code=district_code,
        mode=mode,
    )
    if result is None:
        return {"error": f"출퇴근 시간 조회 실패 — {apt_name} ({mode})"}
    return {
        "duration_minutes": result.duration_minutes,
        "destination": result.destination,
        "mode": result.mode,
        "cached": result.cached,
    }


@mcp.tool()
def get_all_commute_times(
    address: str,
    apt_name: str,
    district_code: str,
) -> dict:
    """
    대중교통·자차·도보 3가지 출퇴근 시간을 한번에 조회한다.

    Args:
        address: 도로명주소 (예: "서울 송파구 가락동 124")
        apt_name: 아파트 단지명
        district_code: 지역코드 5자리

    Returns:
        {"transit": int, "car": int, "walking": int} (분 단위, 조회 실패한 모드는 null)
    """
    origin_key = f"{district_code}__{apt_name}"
    results = _commute_service.get_all_modes(origin_key, address, apt_name, district_code)
    return {
        "transit": results["transit"].duration_minutes if "transit" in results else None,
        "car": results["car"].duration_minutes if "car" in results else None,
        "walking": results["walking"].duration_minutes if "walking" in results else None,
    }


if __name__ == "__main__":
    mcp.run()
```

- [ ] **Step 2: 서버 기동 테스트 (로컬)**

```bash
arch -arm64 .venv/bin/python3.12 src/mcp_servers/commute_server.py
```

Expected: 프로세스가 에러 없이 기동되고 stdin 대기 상태 유지 (`Ctrl+C`로 종료)

- [ ] **Step 3: `~/.claude.json` MCP 서버 등록**

`~/.claude.json` 파일의 `mcpServers` 객체에 아래 항목을 추가:

```json
"commute": {
  "command": "arch",
  "args": [
    "-arm64",
    "/Users/kks/Desktop/Laboratory/Consigliere/.venv/bin/python3.12",
    "src/mcp_servers/commute_server.py"
  ],
  "cwd": "/Users/kks/Desktop/Laboratory/Consigliere"
}
```

- [ ] **Step 4: Claude Code 재시작 후 MCP 도구 확인**

Claude Code를 재시작하고 새 세션에서:

```
/mcp
```

Expected: `commute` 서버가 목록에 표시되고 `get_commute_time`, `get_all_commute_times` 도구가 노출됨

- [ ] **Step 5: Commit**

```bash
git add src/mcp_servers/commute_server.py
git commit -m "feat(commute): MCP 서버 — get_commute_time / get_all_commute_times 도구 노출"
```

---

## Task 9: 전체 회귀 테스트 + 실제 Job4 검증

- [ ] **Step 1: 전체 단위 테스트 실행**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/ -v --ignore=tests/e2e
```

Expected: 178+ tests PASS, 0 FAIL

- [ ] **Step 2: Job4 실행 (실제 T-map API 호출 포함)**

```bash
arch -arm64 .venv/bin/python3.12 -c "
import asyncio
from src.modules.real_estate.service import RealEstateAgent
from datetime import date

async def run():
    agent = RealEstateAgent()
    result = await agent.generate_report(target_date=date.today())
    print(result[:2000])

asyncio.run(run())
"
```

Expected:
- `[CommuteService]` 로그에서 T-map API 호출 확인
- 리포트의 출퇴근 시간이 3가지 교통수단으로 분리 출력
- 송파파크데일1단지 등 실제 값이 네이버 지도와 유사한 범위 (50~70분대)

- [ ] **Step 3: 캐시 동작 확인**

Job4를 한 번 더 실행:

```bash
# 동일 명령 재실행
```

Expected: `[CommuteService]` 로그에 T-map 호출 없이 캐시에서 반환 (`cached=True` 로그 확인)

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat(commute): 출퇴근 시간 실시간 계산 전체 구현 완료"
```
