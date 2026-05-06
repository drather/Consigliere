# 출퇴근 경로 상세 정보 (route_summary + legs) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** T-map API 응답에서 경유 단계(legs)를 파싱하여 CommuteResult에 구조화 저장하고, FastAPI·대시보드·LLM 리포트에 경로 요약을 노출한다.

**Architecture:** `TmapClient`에 `route_with_legs()` 메서드를 비파괴적으로 추가하고, `CommuteResult`에 `legs`/`route_summary` 필드를 추가한다. DB는 `ALTER TABLE` 마이그레이션으로 기존 캐시를 보존하며, `CommuteService.get()`이 새 메서드를 호출해 경로를 함께 저장한다.

**Tech Stack:** Python 3.12, sqlite3, requests, FastAPI, Streamlit, 기존 T-map Open API

**Working directory:** `/Users/kks/Desktop/Laboratory/Consigliere/.worktrees/feature-commute-realtime`
**Python:** `arch -arm64 /Users/kks/Desktop/Laboratory/Consigliere/.venv/bin/python3.12`

---

## File Map

| 파일 | 역할 | 변경 |
|------|------|------|
| `src/modules/real_estate/commute/models.py` | CommuteResult 필드 추가 | 수정 |
| `src/modules/real_estate/commute/tmap_client.py` | route_with_legs() + 파서 추가 | 수정 |
| `src/modules/real_estate/commute/commute_repository.py` | route_json 컬럼 + 마이그레이션 | 수정 |
| `src/modules/real_estate/commute/commute_service.py` | route_with_legs() 호출로 교체 | 수정 |
| `src/api/routers/real_estate.py` | commute 엔드포인트 응답 확장 | 수정 |
| `src/modules/real_estate/service.py` | _enrich_transactions() route_summary 추가 | 수정 |
| `src/dashboard/views/real_estate.py` | 3단 카드 컴포넌트 추가 | 수정 |
| `src/modules/real_estate/prompts/insight_parser.md` | route_summary 필드 프롬프트 추가 | 수정 |
| `src/modules/real_estate/prompts/context_analyst.md` | route_summary 필드 언급 추가 | 수정 |
| `tests/modules/real_estate/commute/test_tmap_client.py` | route_with_legs 테스트 추가 | 수정 |
| `tests/modules/real_estate/commute/test_commute_repository.py` | legs 저장/복원, 마이그레이션 테스트 | 수정 |
| `tests/modules/real_estate/commute/test_commute_service.py` | legs 포함 확인 테스트 | 수정 |
| `tests/api/test_commute_api.py` | legs/summary 응답 확인 테스트 | 수정 |

---

## Task 1: CommuteResult 모델 확장 (TDD)

**Files:**
- Modify: `src/modules/real_estate/commute/models.py`
- Modify: `tests/modules/real_estate/commute/test_commute_repository.py` (기존 파일에 테스트 추가)

- [ ] **Step 1: 실패하는 테스트 추가**

`tests/modules/real_estate/commute/test_commute_repository.py` 파일 끝에 추가:

```python
class TestCommuteResultModel:
    def test_legs_defaults_to_empty_list(self):
        from modules.real_estate.commute.models import CommuteResult
        r = CommuteResult("k", "삼성역", "transit", 59, 1200)
        assert r.legs == []
        assert r.route_summary == ""

    def test_legs_can_be_set(self):
        from modules.real_estate.commute.models import CommuteResult
        legs = [{"mode": "BUS", "route": "302", "from_name": "가락시장", "to_name": "잠실역",
                 "duration_minutes": 12, "stop_count": 4}]
        r = CommuteResult("k", "삼성역", "transit", 59, 1200, legs=legs, route_summary="302번 → 잠실역 → 2호선 → 삼성역")
        assert r.legs[0]["route"] == "302"
        assert r.route_summary == "302번 → 잠실역 → 2호선 → 삼성역"
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd /Users/kks/Desktop/Laboratory/Consigliere/.worktrees/feature-commute-realtime
arch -arm64 /Users/kks/Desktop/Laboratory/Consigliere/.venv/bin/python3.12 -m pytest tests/modules/real_estate/commute/test_commute_repository.py::TestCommuteResultModel -v
```

Expected: `TypeError` (legs 파라미터 없음)

- [ ] **Step 3: `src/modules/real_estate/commute/models.py` 수정**

```python
from dataclasses import dataclass, field
from typing import List


@dataclass
class CommuteResult:
    origin_key: str          # 캐시 식별자: "{district_code}__{apt_name}"
    destination: str         # 예: "삼성역"
    mode: str                # "transit" | "car" | "walking"
    duration_minutes: int
    distance_meters: int
    cached: bool = field(default=False)
    legs: List[dict] = field(default_factory=list)   # 구조화 단계 목록
    route_summary: str = ""                           # LLM용 한 줄 요약
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
arch -arm64 /Users/kks/Desktop/Laboratory/Consigliere/.venv/bin/python3.12 -m pytest tests/modules/real_estate/commute/test_commute_repository.py -v
```

Expected: 모든 테스트 PASS (기존 6개 + 신규 2개)

- [ ] **Step 5: Commit**

```bash
git add src/modules/real_estate/commute/models.py tests/modules/real_estate/commute/test_commute_repository.py
git commit -m "feat(commute): CommuteResult에 legs + route_summary 필드 추가"
```

---

## Task 2: TmapClient — route_with_legs() + 파서 (TDD)

**Files:**
- Modify: `src/modules/real_estate/commute/tmap_client.py`
- Modify: `tests/modules/real_estate/commute/test_tmap_client.py`

- [ ] **Step 1: 실패하는 테스트 추가**

`tests/modules/real_estate/commute/test_tmap_client.py` 파일 끝에 추가:

```python
TRANSIT_RESPONSE_WITH_LEGS = {
    "metaData": {
        "plan": {
            "itineraries": [{
                "totalTime": 3540,
                "totalWalkDistance": 456,
                "legs": [
                    {
                        "mode": "WALK",
                        "sectionTime": 300,
                        "distance": 400,
                        "start": {"name": "출발지"},
                        "end": {"name": "가락시장 정류장"},
                    },
                    {
                        "mode": "BUS",
                        "route": "302",
                        "sectionTime": 720,
                        "distance": 3200,
                        "start": {"name": "가락시장"},
                        "end": {"name": "잠실역"},
                        "passStopList": {
                            "stationList": [
                                {"stationName": "가락시장"},
                                {"stationName": "석촌"},
                                {"stationName": "잠실"},
                                {"stationName": "잠실역"},
                            ]
                        },
                    },
                    {
                        "mode": "SUBWAY",
                        "route": "2호선",
                        "sectionTime": 480,
                        "distance": 4100,
                        "start": {"name": "잠실역"},
                        "end": {"name": "삼성역"},
                        "passStopList": {
                            "stationList": [
                                {"stationName": "잠실역"},
                                {"stationName": "종합운동장"},
                                {"stationName": "삼성역"},
                            ]
                        },
                    },
                    {
                        "mode": "WALK",
                        "sectionTime": 180,
                        "distance": 200,
                        "start": {"name": "삼성역 5번 출구"},
                        "end": {"name": "목적지"},
                    },
                ],
            }]
        }
    }
}

CAR_RESPONSE_WITH_FEATURES = {
    "features": [
        {
            "type": "Feature",
            "geometry": {"type": "Point"},
            "properties": {"totalTime": 2100, "totalDistance": 15000},
        },
        {
            "type": "Feature",
            "geometry": {"type": "LineString"},
            "properties": {"index": 1, "name": "올림픽대로", "distance": 8000},
        },
        {
            "type": "Feature",
            "geometry": {"type": "LineString"},
            "properties": {"index": 2, "name": "잠실대교", "distance": 1500},
        },
        {
            "type": "Feature",
            "geometry": {"type": "LineString"},
            "properties": {"index": 3, "name": "테헤란로", "distance": 3000},
        },
    ]
}


class TestTmapClientRouteWithLegs:
    def test_transit_legs_parsed_correctly(self):
        """route_with_legs transit — legs 4개, 버스 302번, 2호선 포함."""
        from modules.real_estate.commute.tmap_client import TmapClient
        client = TmapClient(api_key="test-key")
        mock_resp = MagicMock()
        mock_resp.json.return_value = TRANSIT_RESPONSE_WITH_LEGS
        mock_resp.raise_for_status.return_value = None

        with patch("modules.real_estate.commute.tmap_client.requests.post", return_value=mock_resp):
            duration, distance, legs, summary = client.route_with_legs(
                37.4942, 127.0611, 37.5088, 127.0633, mode="transit"
            )

        assert duration == 59
        assert len(legs) == 4
        bus_leg = next(l for l in legs if l["mode"] == "BUS")
        assert bus_leg["route"] == "302"
        assert bus_leg["stop_count"] == 4
        subway_leg = next(l for l in legs if l["mode"] == "SUBWAY")
        assert subway_leg["route"] == "2호선"
        assert subway_leg["stop_count"] == 3

    def test_transit_summary_contains_bus_and_subway(self):
        """transit route_summary에 버스 번호와 지하철 노선 포함."""
        from modules.real_estate.commute.tmap_client import TmapClient
        client = TmapClient(api_key="test-key")
        mock_resp = MagicMock()
        mock_resp.json.return_value = TRANSIT_RESPONSE_WITH_LEGS
        mock_resp.raise_for_status.return_value = None

        with patch("modules.real_estate.commute.tmap_client.requests.post", return_value=mock_resp):
            _, _, _, summary = client.route_with_legs(
                37.4942, 127.0611, 37.5088, 127.0633, mode="transit"
            )

        assert "302" in summary
        assert "2호선" in summary or "삼성역" in summary

    def test_car_legs_contains_road_names(self):
        """route_with_legs car — 주요 도로명 포함."""
        from modules.real_estate.commute.tmap_client import TmapClient
        client = TmapClient(api_key="test-key")
        mock_resp = MagicMock()
        mock_resp.json.return_value = CAR_RESPONSE_WITH_FEATURES
        mock_resp.raise_for_status.return_value = None

        with patch("modules.real_estate.commute.tmap_client.requests.post", return_value=mock_resp):
            duration, distance, legs, summary = client.route_with_legs(
                37.4942, 127.0611, 37.5088, 127.0633, mode="car"
            )

        assert duration == 35
        assert any(l["road_name"] == "올림픽대로" for l in legs)
        assert "올림픽대로" in summary

    def test_car_summary_contains_distance(self):
        """car summary에 km 단위 거리 포함."""
        from modules.real_estate.commute.tmap_client import TmapClient
        client = TmapClient(api_key="test-key")
        mock_resp = MagicMock()
        mock_resp.json.return_value = CAR_RESPONSE_WITH_FEATURES
        mock_resp.raise_for_status.return_value = None

        with patch("modules.real_estate.commute.tmap_client.requests.post", return_value=mock_resp):
            _, _, _, summary = client.route_with_legs(
                37.4942, 127.0611, 37.5088, 127.0633, mode="car"
            )

        assert "km" in summary

    def test_existing_route_still_works(self):
        """기존 route() 메서드는 변경 없이 동작해야 한다."""
        from modules.real_estate.commute.tmap_client import TmapClient
        client = TmapClient(api_key="test-key")
        mock_resp = MagicMock()
        mock_resp.json.return_value = CAR_RESPONSE_WITH_FEATURES
        mock_resp.raise_for_status.return_value = None

        with patch("modules.real_estate.commute.tmap_client.requests.post", return_value=mock_resp):
            duration, distance = client.route(37.4942, 127.0611, 37.5088, 127.0633, mode="car")

        assert duration == 35
        assert distance == 15000
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
arch -arm64 /Users/kks/Desktop/Laboratory/Consigliere/.venv/bin/python3.12 -m pytest tests/modules/real_estate/commute/test_tmap_client.py::TestTmapClientRouteWithLegs -v
```

Expected: `AttributeError: 'TmapClient' object has no attribute 'route_with_legs'`

- [ ] **Step 3: `src/modules/real_estate/commute/tmap_client.py` 수정**

파일 전체를 아래 내용으로 교체:

```python
import logging
import math
import requests
from typing import List, Tuple

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

    # ── 기존 메서드 (변경 없음) ───────────────────────────────────────

    def route(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        mode: str,
    ) -> Tuple[int, int]:
        """Returns (duration_minutes, distance_meters)."""
        if mode not in _VALID_MODES:
            raise ValueError(f"mode must be one of {_VALID_MODES}, got '{mode}'")
        if mode == "transit":
            return self._route_transit(origin_lat, origin_lng, dest_lat, dest_lng)
        if mode == "car":
            return self._route_feature_based(origin_lat, origin_lng, dest_lat, dest_lng, f"{_CAR_URL}?version=1")
        return self._route_feature_based(origin_lat, origin_lng, dest_lat, dest_lng, f"{_WALKING_URL}?version=1")

    def _headers(self) -> dict:
        return {"appKey": self._api_key, "Content-Type": "application/json"}

    def _route_transit(self, olat, olng, dlat, dlng) -> Tuple[int, int]:
        payload = {
            "startX": str(olng), "startY": str(olat),
            "endX": str(dlng), "endY": str(dlat),
            "count": 1, "lang": 0, "format": "json",
        }
        resp = requests.post(_TRANSIT_URL, json=payload, headers=self._headers(), timeout=self._timeout)
        resp.raise_for_status()
        data = resp.json()
        itineraries = data.get("metaData", {}).get("plan", {}).get("itineraries", [])
        if not itineraries:
            raise ValueError("T-map transit: empty itineraries in response")
        best = itineraries[0]
        return math.ceil(best["totalTime"] / 60), best.get("totalWalkDistance", 0)

    def _route_feature_based(self, olat, olng, dlat, dlng, url: str) -> Tuple[int, int]:
        payload = {
            "startX": str(olng), "startY": str(olat),
            "endX": str(dlng), "endY": str(dlat),
            "reqCoordType": "WGS84GEO", "resCoordType": "WGS84GEO",
            "startName": "출발", "endName": "도착",
        }
        resp = requests.post(url, json=payload, headers=self._headers(), timeout=self._timeout)
        resp.raise_for_status()
        features = resp.json().get("features", [])
        if not features:
            raise ValueError(f"T-map {url}: empty features in response")
        props = features[0]["properties"]
        return math.ceil(props["totalTime"] / 60), props.get("totalDistance", 0)

    def _route_car(self, olat, olng, dlat, dlng) -> Tuple[int, int]:
        return self._route_feature_based(olat, olng, dlat, dlng, f"{_CAR_URL}?version=1")

    def _route_walking(self, olat, olng, dlat, dlng) -> Tuple[int, int]:
        return self._route_feature_based(olat, olng, dlat, dlng, f"{_WALKING_URL}?version=1")

    # ── 신규 메서드: 경로 상세 포함 ──────────────────────────────────

    def route_with_legs(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        mode: str,
    ) -> Tuple[int, int, List[dict], str]:
        """Returns (duration_minutes, distance_meters, legs, route_summary)."""
        if mode not in _VALID_MODES:
            raise ValueError(f"mode must be one of {_VALID_MODES}, got '{mode}'")
        if mode == "transit":
            return self._route_transit_with_legs(origin_lat, origin_lng, dest_lat, dest_lng)
        url = f"{_CAR_URL}?version=1" if mode == "car" else f"{_WALKING_URL}?version=1"
        return self._route_feature_based_with_legs(origin_lat, origin_lng, dest_lat, dest_lng, url, mode)

    def _route_transit_with_legs(self, olat, olng, dlat, dlng) -> Tuple[int, int, List[dict], str]:
        payload = {
            "startX": str(olng), "startY": str(olat),
            "endX": str(dlng), "endY": str(dlat),
            "count": 1, "lang": 0, "format": "json",
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
        legs = self._parse_transit_legs(best.get("legs", []))
        summary = self._build_summary(legs, distance, "transit")
        return duration, distance, legs, summary

    def _route_feature_based_with_legs(self, olat, olng, dlat, dlng, url, mode) -> Tuple[int, int, List[dict], str]:
        payload = {
            "startX": str(olng), "startY": str(olat),
            "endX": str(dlng), "endY": str(dlat),
            "reqCoordType": "WGS84GEO", "resCoordType": "WGS84GEO",
            "startName": "출발", "endName": "도착",
        }
        resp = requests.post(url, json=payload, headers=self._headers(), timeout=self._timeout)
        resp.raise_for_status()
        features = resp.json().get("features", [])
        if not features:
            raise ValueError(f"T-map {url}: empty features in response")
        props = features[0]["properties"]
        duration = math.ceil(props["totalTime"] / 60)
        distance = props.get("totalDistance", 0)
        legs = self._parse_feature_legs(features)
        summary = self._build_summary(legs, distance, mode)
        return duration, distance, legs, summary

    def _parse_transit_legs(self, legs_data: list) -> List[dict]:
        """대중교통 legs[] → 구조화 dict 목록."""
        legs = []
        for leg in legs_data:
            mode = leg.get("mode", "WALK")
            entry: dict = {
                "mode": mode,
                "from_name": leg.get("start", {}).get("name", ""),
                "to_name": leg.get("end", {}).get("name", ""),
                "duration_minutes": math.ceil(leg.get("sectionTime", 0) / 60),
            }
            if mode in ("BUS", "SUBWAY", "RAIL"):
                entry["route"] = leg.get("route", "")
                stations = leg.get("passStopList", {}).get("stationList", [])
                entry["stop_count"] = len(stations)
            legs.append(entry)
        return legs

    def _parse_feature_legs(self, features: list) -> List[dict]:
        """자가용/도보 features[] → 도로명 목록 (LineString만, 중복 제거, 최대 5개)."""
        legs = []
        seen: set = set()
        for feat in features:
            if feat.get("geometry", {}).get("type") != "LineString":
                continue
            props = feat.get("properties", {})
            name = props.get("name", "").strip()
            if not name or name in seen:
                continue
            seen.add(name)
            legs.append({
                "mode": "ROAD",
                "road_name": name,
                "distance_meters": props.get("distance", 0),
            })
            if len(legs) >= 5:
                break
        return legs

    def _build_summary(self, legs: List[dict], distance_meters: int, mode: str) -> str:
        """legs + 거리 → 한 줄 요약 문자열."""
        if mode == "transit":
            parts: List[str] = []
            for leg in legs:
                m = leg["mode"]
                if m == "WALK":
                    mins = leg.get("duration_minutes", 0)
                    if mins > 0:
                        parts.append(f"도보 {mins}분")
                elif m == "BUS":
                    parts.append(f"{leg.get('route', '')}번 버스")
                    to = leg.get("to_name", "")
                    if to:
                        parts.append(to)
                elif m in ("SUBWAY", "RAIL"):
                    parts.append(leg.get("route", "지하철"))
                    to = leg.get("to_name", "")
                    if to:
                        parts.append(to)
            return " → ".join(parts) if parts else ""
        else:
            road_names = [l["road_name"] for l in legs if l.get("road_name")]
            km = distance_meters / 1000
            roads = " → ".join(road_names[:4])
            return f"{roads} ({km:.1f}km)" if roads else f"{km:.1f}km"
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
arch -arm64 /Users/kks/Desktop/Laboratory/Consigliere/.venv/bin/python3.12 -m pytest tests/modules/real_estate/commute/test_tmap_client.py -v
```

Expected: 기존 6개 + 신규 5개 = 11개 PASS

- [ ] **Step 5: Commit**

```bash
git add src/modules/real_estate/commute/tmap_client.py tests/modules/real_estate/commute/test_tmap_client.py
git commit -m "feat(commute): TmapClient.route_with_legs() — legs 파싱 + route_summary 생성"
```

---

## Task 3: CommuteRepository — route_json 컬럼 + 마이그레이션 (TDD)

**Files:**
- Modify: `src/modules/real_estate/commute/commute_repository.py`
- Modify: `tests/modules/real_estate/commute/test_commute_repository.py`

- [ ] **Step 1: 실패하는 테스트 추가**

`tests/modules/real_estate/commute/test_commute_repository.py`의 `class TestCommuteRepository:` 블록 끝에 추가:

```python
    def test_upsert_and_get_preserves_legs(self):
        """legs와 route_summary가 저장 후 복원돼야 한다."""
        repo = self._repo()
        legs = [
            {"mode": "WALK", "from_name": "출발지", "to_name": "정류장", "duration_minutes": 5},
            {"mode": "BUS", "route": "302", "from_name": "가락시장", "to_name": "잠실역",
             "duration_minutes": 12, "stop_count": 4},
        ]
        r = CommuteResult(
            origin_key="11710__파크데일", destination="삼성역", mode="transit",
            duration_minutes=59, distance_meters=1200,
            legs=legs, route_summary="도보 5분 → 302번 버스 → 잠실역",
        )
        repo.upsert(r)
        got = repo.get("11710__파크데일", "삼성역", "transit")
        assert got is not None
        assert len(got.legs) == 2
        assert got.legs[1]["route"] == "302"
        assert got.route_summary == "도보 5분 → 302번 버스 → 잠실역"

    def test_migration_adds_columns_to_old_db(self):
        """route_json 컬럼 없는 구형 DB에서도 정상 동작해야 한다."""
        import sqlite3
        from modules.real_estate.commute.commute_repository import CommuteRepository

        conn = sqlite3.connect(":memory:")
        conn.executescript("""
            CREATE TABLE commute_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                origin_key TEXT NOT NULL,
                destination TEXT NOT NULL,
                mode TEXT NOT NULL,
                duration_minutes INTEGER NOT NULL,
                distance_meters INTEGER NOT NULL DEFAULT 0,
                cached_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                UNIQUE(origin_key, destination, mode)
            )
        """)
        conn.commit()
        # 구형 row 삽입
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)
        conn.execute(
            "INSERT INTO commute_cache (origin_key, destination, mode, duration_minutes, "
            "distance_meters, cached_at, expires_at) VALUES (?,?,?,?,?,?,?)",
            ("k", "삼성역", "transit", 59, 0, now.isoformat(), (now + timedelta(days=90)).isoformat()),
        )
        conn.commit()

        # CommuteRepository가 :memory:가 아닌 위의 conn을 재활용할 수 없으므로
        # file-based DB로 우회 테스트
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            tmp_path = f.name
        try:
            conn2 = sqlite3.connect(tmp_path)
            conn2.executescript("""
                CREATE TABLE commute_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    origin_key TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    duration_minutes INTEGER NOT NULL,
                    distance_meters INTEGER NOT NULL DEFAULT 0,
                    cached_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    UNIQUE(origin_key, destination, mode)
                )
            """)
            conn2.execute(
                "INSERT INTO commute_cache (origin_key, destination, mode, duration_minutes, "
                "distance_meters, cached_at, expires_at) VALUES (?,?,?,?,?,?,?)",
                ("k", "삼성역", "transit", 59, 0, now.isoformat(), (now + timedelta(days=90)).isoformat()),
            )
            conn2.commit()
            conn2.close()

            repo = CommuteRepository(db_path=tmp_path, ttl_days=90)
            got = repo.get("k", "삼성역", "transit")
            assert got is not None
            assert got.duration_minutes == 59
            assert got.legs == []
            assert got.route_summary == ""
        finally:
            os.unlink(tmp_path)
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
arch -arm64 /Users/kks/Desktop/Laboratory/Consigliere/.venv/bin/python3.12 -m pytest tests/modules/real_estate/commute/test_commute_repository.py::TestCommuteRepository::test_upsert_and_get_preserves_legs -v
```

Expected: `FAIL` (route_json 컬럼 없음)

- [ ] **Step 3: `src/modules/real_estate/commute/commute_repository.py` 수정**

파일 전체를 아래로 교체:

```python
import json
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
    route_json       TEXT NOT NULL DEFAULT '[]',
    route_summary    TEXT NOT NULL DEFAULT '',
    cached_at        TEXT NOT NULL,
    expires_at       TEXT NOT NULL,
    UNIQUE(origin_key, destination, mode)
)
"""


class CommuteRepository:
    def __init__(self, db_path: str, ttl_days: int = 90):
        self._db_path = db_path
        self._ttl_days = ttl_days
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        self._conn.executescript(_DDL)
        self._conn.commit()
        self._migrate()

    def _migrate(self):
        """기존 DB에 route_json / route_summary 컬럼이 없으면 추가."""
        cols = {row[1] for row in self._conn.execute("PRAGMA table_info(commute_cache)")}
        if "route_json" not in cols:
            self._conn.execute("ALTER TABLE commute_cache ADD COLUMN route_json TEXT NOT NULL DEFAULT '[]'")
        if "route_summary" not in cols:
            self._conn.execute("ALTER TABLE commute_cache ADD COLUMN route_summary TEXT NOT NULL DEFAULT ''")
        self._conn.commit()

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def get(self, origin_key: str, destination: str, mode: str) -> Optional[CommuteResult]:
        """유효한 캐시가 있으면 CommuteResult(cached=True) 반환, 없거나 만료시 None."""
        row = self._conn.execute(
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
        try:
            legs = json.loads(row["route_json"])
        except (json.JSONDecodeError, TypeError):
            legs = []
        return CommuteResult(
            origin_key=row["origin_key"],
            destination=row["destination"],
            mode=row["mode"],
            duration_minutes=row["duration_minutes"],
            distance_meters=row["distance_meters"],
            cached=True,
            legs=legs,
            route_summary=row["route_summary"] or "",
        )

    def upsert(self, result: CommuteResult):
        """캐시 저장 또는 갱신."""
        now = self._now()
        expires_at = now + timedelta(days=self._ttl_days)
        self._conn.execute(
            """
            INSERT INTO commute_cache
                (origin_key, destination, mode, duration_minutes, distance_meters,
                 route_json, route_summary, cached_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(origin_key, destination, mode) DO UPDATE SET
                duration_minutes = excluded.duration_minutes,
                distance_meters  = excluded.distance_meters,
                route_json       = excluded.route_json,
                route_summary    = excluded.route_summary,
                cached_at        = excluded.cached_at,
                expires_at       = excluded.expires_at
            """,
            (
                result.origin_key, result.destination, result.mode,
                result.duration_minutes, result.distance_meters,
                json.dumps(result.legs, ensure_ascii=False),
                result.route_summary,
                now.isoformat(), expires_at.isoformat(),
            ),
        )
        self._conn.commit()
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
arch -arm64 /Users/kks/Desktop/Laboratory/Consigliere/.venv/bin/python3.12 -m pytest tests/modules/real_estate/commute/test_commute_repository.py -v
```

Expected: 기존 6개 + 신규 4개 (모델 2 + 저장/마이그레이션 2) = 10개 PASS

- [ ] **Step 5: Commit**

```bash
git add src/modules/real_estate/commute/commute_repository.py tests/modules/real_estate/commute/test_commute_repository.py
git commit -m "feat(commute): CommuteRepository — route_json/route_summary 저장 + 마이그레이션"
```

---

## Task 4: CommuteService — route_with_legs() 호출로 교체 (TDD)

**Files:**
- Modify: `src/modules/real_estate/commute/commute_service.py`
- Modify: `tests/modules/real_estate/commute/test_commute_service.py`

- [ ] **Step 1: 실패하는 테스트 추가**

`tests/modules/real_estate/commute/test_commute_service.py`의 `class TestCommuteServiceCacheMiss:` 블록 끝에 추가:

```python
    def test_cache_miss_stores_legs_in_result(self):
        """캐시 미스 시 route_with_legs()가 호출되어 legs가 CommuteResult에 포함된다."""
        mock_geocoder = MagicMock()
        mock_geocoder.geocode.return_value = (37.49, 127.06)

        mock_client = MagicMock()
        mock_client.route_with_legs.return_value = (
            59, 1200,
            [{"mode": "BUS", "route": "302", "from_name": "가락시장", "to_name": "잠실역",
              "duration_minutes": 12, "stop_count": 4}],
            "도보 5분 → 302번 버스 → 잠실역",
        )

        repo = CommuteRepository(db_path=":memory:", ttl_days=90)
        svc = make_service(repo=repo, tmap_client=mock_client, geocoder=mock_geocoder)

        result = svc.get(
            origin_key="11710__파크데일",
            road_address="서울 송파구 가락동 124",
            apt_name="파크데일",
            district_code="11710",
            mode="transit",
        )

        assert result is not None
        assert result.duration_minutes == 59
        assert len(result.legs) == 1
        assert result.legs[0]["route"] == "302"
        assert result.route_summary == "도보 5분 → 302번 버스 → 잠실역"
        mock_client.route_with_legs.assert_called_once()
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
arch -arm64 /Users/kks/Desktop/Laboratory/Consigliere/.venv/bin/python3.12 -m pytest tests/modules/real_estate/commute/test_commute_service.py::TestCommuteServiceCacheMiss::test_cache_miss_stores_legs_in_result -v
```

Expected: `FAIL` (route_with_legs 호출 안 됨 — 현재는 route() 호출)

- [ ] **Step 3: `src/modules/real_estate/commute/commute_service.py` 수정**

`get()` 메서드 내 `self._client.route(...)` 호출 블록을 교체:

**교체 전:**
```python
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
```

**교체 후:**
```python
        try:
            duration, distance, legs, route_summary = self._client.route_with_legs(
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
            legs=legs,
            route_summary=route_summary,
        )
```

- [ ] **Step 4: 전체 service 테스트 통과 확인**

```bash
arch -arm64 /Users/kks/Desktop/Laboratory/Consigliere/.venv/bin/python3.12 -m pytest tests/modules/real_estate/commute/test_commute_service.py -v
```

Expected: 기존 6개 + 신규 1개 = 7개 PASS

주의: 기존 `test_cache_miss_calls_tmap_and_stores` 는 `mock_client.route.return_value`를 사용하는데, 이제 `route_with_legs`를 호출하므로 해당 테스트도 수정이 필요하다. 다음과 같이 변경:

**`test_cache_miss_calls_tmap_and_stores`에서:**
```python
        mock_client = MagicMock()
        mock_client.route.return_value = (59, 1200)
```
→
```python
        mock_client = MagicMock()
        mock_client.route_with_legs.return_value = (59, 1200, [], "")
```

그리고:
```python
        mock_client.route.assert_called_once()
```
→
```python
        mock_client.route_with_legs.assert_called_once()
```

**`test_tmap_failure_returns_none`에서:**
```python
        mock_client.route.side_effect = Exception("T-map 오류")
```
→
```python
        mock_client.route_with_legs.side_effect = Exception("T-map 오류")
```

**`test_get_all_modes_returns_three_results`에서:**
```python
        mock_client.route.side_effect = [(59, 1200), (30, 15000), (90, 5000)]
```
→
```python
        mock_client.route_with_legs.side_effect = [
            (59, 1200, [], ""), (30, 15000, [], ""), (90, 5000, [], "")
        ]
```

**`test_get_all_modes_partial_failure_skips_failed_mode`에서:**
```python
        mock_client.route.side_effect = [(59, 1200), Exception("car 오류"), (90, 5000)]
```
→
```python
        mock_client.route_with_legs.side_effect = [
            (59, 1200, [], ""), Exception("car 오류"), (90, 5000, [], "")
        ]
```

- [ ] **Step 5: Commit**

```bash
git add src/modules/real_estate/commute/commute_service.py tests/modules/real_estate/commute/test_commute_service.py
git commit -m "feat(commute): CommuteService — route_with_legs() 호출로 교체, legs/summary 저장"
```

---

## Task 5: FastAPI 응답 확장 + service.py route_summary 추가 (TDD)

**Files:**
- Modify: `src/api/routers/real_estate.py`
- Modify: `src/modules/real_estate/service.py`
- Modify: `tests/api/test_commute_api.py`

- [ ] **Step 1: API 테스트에 legs/summary 검증 추가**

`tests/api/test_commute_api.py`에서 `class TestCommuteAPI:` 안에 테스트 추가:

```python
    def test_response_includes_legs_and_summary(self):
        """응답에 transit_legs, transit_summary 포함돼야 한다."""
        from modules.real_estate.commute.models import CommuteResult

        legs = [{"mode": "BUS", "route": "302", "from_name": "가락시장",
                 "to_name": "잠실역", "duration_minutes": 12, "stop_count": 4}]
        mock_svc = MagicMock()
        mock_svc.get_all_modes.return_value = {
            "transit": CommuteResult("k", "삼성역", "transit", 59, 1200,
                                     legs=legs, route_summary="도보 5분 → 302번 버스 → 잠실역"),
            "car": CommuteResult("k", "삼성역", "car", 35, 15000,
                                  legs=[{"mode": "ROAD", "road_name": "올림픽대로", "distance_meters": 8000}],
                                  route_summary="올림픽대로 → 테헤란로 (15.0km)"),
            "walking": CommuteResult("k", "삼성역", "walking", 90, 5000,
                                      legs=[], route_summary="가락로 (5.0km)"),
        }
        client = TestClient(_make_app(mock_svc))
        resp = client.get("/dashboard/real-estate/commute", params={
            "address": "서울 송파구 가락동 124",
            "apt_name": "송파파크데일1단지",
            "district_code": "11710",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["transit_legs"][0]["route"] == "302"
        assert data["transit_summary"] == "도보 5분 → 302번 버스 → 잠실역"
        assert data["car_summary"] == "올림픽대로 → 테헤란로 (15.0km)"
        assert data["walking_legs"] == []
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
arch -arm64 /Users/kks/Desktop/Laboratory/Consigliere/.venv/bin/python3.12 -m pytest tests/api/test_commute_api.py::TestCommuteAPI::test_response_includes_legs_and_summary -v
```

Expected: `FAIL` (transit_legs 키 없음)

- [ ] **Step 3: `src/api/routers/real_estate.py` 엔드포인트 수정**

파일 끝의 `GET /dashboard/real-estate/commute` 엔드포인트를 아래로 교체:

```python
@router.get("/dashboard/real-estate/commute")
def get_commute_time(
    address: str,
    apt_name: str,
    district_code: str,
    commute_service: CommuteService = Depends(get_commute_service),
):
    """아파트 주소 → 삼성역 출퇴근 시간 + 경로 상세 조회 (대중교통·자차·도보).

    캐시 히트 시 즉시 반환, 캐시 미스 시 T-map API 호출 후 저장.
    """
    try:
        origin_key = f"{district_code}__{apt_name}"
        results = commute_service.get_all_modes(
            origin_key=origin_key,
            road_address=address,
            apt_name=apt_name,
            district_code=district_code,
        )
        return {
            "apt_name": apt_name,
            "destination": "삼성역",
            "transit": results["transit"].duration_minutes if "transit" in results else None,
            "car": results["car"].duration_minutes if "car" in results else None,
            "walking": results["walking"].duration_minutes if "walking" in results else None,
            "transit_legs": results["transit"].legs if "transit" in results else [],
            "car_legs": results["car"].legs if "car" in results else [],
            "walking_legs": results["walking"].legs if "walking" in results else [],
            "transit_summary": results["transit"].route_summary if "transit" in results else "",
            "car_summary": results["car"].route_summary if "car" in results else "",
            "walking_summary": results["walking"].route_summary if "walking" in results else "",
            "cached": all(r.cached for r in results.values()) if results else False,
        }
    except Exception as e:
        logger.error(f"Commute API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 4: `src/modules/real_estate/service.py` — `_enrich_transactions()` route_summary 추가**

`service.py`에서 commute 블록 끝 (commute_minutes 할당 직후)에 3줄 추가:

기존 코드 (약 693-695번째 줄):
```python
            tx["commute_transit_minutes"] = commute_results["transit"].duration_minutes if "transit" in commute_results else None
            tx["commute_car_minutes"] = commute_results["car"].duration_minutes if "car" in commute_results else None
            tx["commute_walk_minutes"] = commute_results["walking"].duration_minutes if "walking" in commute_results else None
            # 하위호환: scoring.py의 commute_minutes fallback 지원
            tx["commute_minutes"] = tx["commute_transit_minutes"]
```

그 바로 뒤에 추가:
```python
            tx["transit_summary"] = commute_results["transit"].route_summary if "transit" in commute_results else None
            tx["car_summary"] = commute_results["car"].route_summary if "car" in commute_results else None
            tx["walking_summary"] = commute_results["walking"].route_summary if "walking" in commute_results else None
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
arch -arm64 /Users/kks/Desktop/Laboratory/Consigliere/.venv/bin/python3.12 -m pytest tests/api/test_commute_api.py -v
```

Expected: 기존 3개 + 신규 1개 = 4개 PASS

- [ ] **Step 6: Commit**

```bash
git add src/api/routers/real_estate.py src/modules/real_estate/service.py tests/api/test_commute_api.py
git commit -m "feat(commute): FastAPI 응답에 legs/summary 추가, _enrich_transactions route_summary 연동"
```

---

## Task 6: 대시보드 3단 카드 UI

**Files:**
- Modify: `src/dashboard/views/real_estate.py`

이 태스크는 Streamlit UI이므로 TDD 불가. 기능 검증은 수동 확인.

- [ ] **Step 1: `_render_commute_card()` 함수 추가**

`src/dashboard/views/real_estate.py`의 import 블록 아래 (첫 번째 함수 정의 위)에 삽입:

```python
def _render_commute_card(commute_data: dict):
    """출퇴근 경로 3단 카드 렌더링."""
    import streamlit as st

    transit_min = commute_data.get("transit")
    car_min = commute_data.get("car")
    walking_min = commute_data.get("walking")
    transit_legs = commute_data.get("transit_legs", [])
    car_legs = commute_data.get("car_legs", [])
    walking_legs = commute_data.get("walking_legs", [])
    transit_summary = commute_data.get("transit_summary", "")
    car_summary = commute_data.get("car_summary", "")
    walking_summary = commute_data.get("walking_summary", "")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### 🚌 대중교통")
        if transit_min is not None:
            st.metric("소요시간", f"{transit_min}분")
            if transit_legs:
                for leg in transit_legs:
                    mode = leg.get("mode", "")
                    if mode == "WALK":
                        st.caption(f"🚶 도보 {leg.get('duration_minutes', 0)}분")
                    elif mode == "BUS":
                        st.caption(f"🚌 {leg.get('route', '')}번 버스 ({leg.get('stop_count', 0)}정거장)")
                    elif mode in ("SUBWAY", "RAIL"):
                        st.caption(f"🚇 {leg.get('route', '')} ({leg.get('stop_count', 0)}정거장)")
            elif transit_summary:
                st.caption(transit_summary)
        else:
            st.caption("조회 실패")

    with col2:
        st.markdown("#### 🚗 자가용")
        if car_min is not None:
            st.metric("소요시간", f"{car_min}분")
            if car_legs:
                for leg in car_legs:
                    st.caption(f"🛣️ {leg.get('road_name', '')}")
            elif car_summary:
                st.caption(car_summary)
        else:
            st.caption("조회 실패")

    with col3:
        st.markdown("#### 🚶 도보")
        if walking_min is not None:
            st.metric("소요시간", f"{walking_min}분")
            if walking_legs:
                for leg in walking_legs:
                    st.caption(f"🛤️ {leg.get('road_name', '')}")
            elif walking_summary:
                st.caption(walking_summary)
        else:
            st.caption("조회 실패")
```

- [ ] **Step 2: 단지 상세 패널에서 `_render_commute_card()` 호출**

`src/dashboard/views/real_estate.py`에서 단지 상세 패널을 렌더링하는 함수(`_render_apt_detail_panel` 또는 유사한 이름)를 찾아, 출퇴근 관련 정보를 표시하는 위치 직후에 추가:

```python
    # 출퇴근 경로 상세 카드
    if apt_master_id or (road_address and apt_name and district_code):
        with st.expander("🗺️ 출퇴근 경로 상세", expanded=False):
            try:
                import requests as _req
                commute_resp = _req.get(
                    "http://localhost:8000/dashboard/real-estate/commute",
                    params={
                        "address": road_address or "",
                        "apt_name": apt_name or "",
                        "district_code": district_code or "",
                    },
                    timeout=30,
                )
                if commute_resp.status_code == 200:
                    _render_commute_card(commute_resp.json())
                else:
                    st.caption("출퇴근 정보 조회 실패")
            except Exception:
                st.caption("서버 연결 실패 — FastAPI 서버가 실행 중인지 확인하세요")
```

정확한 삽입 위치는 `views/real_estate.py` 파일에서 `commute_minutes` 또는 `_render_apt_detail_panel` 을 검색하여 맥락에 맞는 위치에 추가한다.

- [ ] **Step 3: Commit**

```bash
git add src/dashboard/views/real_estate.py
git commit -m "feat(commute): 대시보드 3단 카드 — 대중교통/자가용/도보 경로 상세 표시"
```

---

## Task 7: LLM 프롬프트 업데이트 + 전체 회귀 테스트

**Files:**
- Modify: `src/modules/real_estate/prompts/insight_parser.md`
- Modify: `src/modules/real_estate/prompts/context_analyst.md`

- [ ] **Step 1: `insight_parser.md` 교통 섹션 수정**

`src/modules/real_estate/prompts/insight_parser.md`에서:

**찾을 텍스트:**
```
⚡ 교통 — 대중교통 [commute_transit_minutes]분 / 자차 [commute_car_minutes]분 / 도보 [commute_walk_minutes]분 (삼성역 기준)
```

**교체할 텍스트:**
```
⚡ 교통 — 대중교통 [commute_transit_minutes]분 / 자차 [commute_car_minutes]분 / 도보 [commute_walk_minutes]분 (삼성역 기준)
경로: 대중교통 [transit_summary] / 자차 [car_summary]
```

그리고 절대 규칙 인용 목록에서:

**찾을 텍스트:**
```
`commute_transit_minutes`, `commute_car_minutes`, `nearest_stations`, `school_zone_notes`, `reconstruction_status` 필드를 근거로 반드시 인용하십시오.
```

**교체할 텍스트:**
```
`commute_transit_minutes`, `commute_car_minutes`, `transit_summary`, `car_summary`, `nearest_stations`, `school_zone_notes`, `reconstruction_status` 필드를 근거로 반드시 인용하십시오.
```

- [ ] **Step 2: `context_analyst.md` 역세권 분석 섹션 수정**

`src/modules/real_estate/prompts/context_analyst.md`에서:

**찾을 텍스트:**
```
`nearest_stations`(역명·노선·도보분)과 `commute_transit_minutes`(대중교통), `commute_car_minutes`(자차)를 인용하여 직주근접 우수 단지를 구체적으로 명시하십시오.
```

**교체할 텍스트:**
```
`nearest_stations`(역명·노선·도보분)과 `commute_transit_minutes`(대중교통), `commute_car_minutes`(자차), `transit_summary`(환승 경로), `car_summary`(자차 경로)를 인용하여 직주근접 우수 단지를 구체적으로 명시하십시오.
```

- [ ] **Step 3: 전체 회귀 테스트**

```bash
arch -arm64 /Users/kks/Desktop/Laboratory/Consigliere/.venv/bin/python3.12 -m pytest tests/ --ignore=tests/e2e --ignore=tests/test_job4_enhancements.py -q
```

Expected: 신규 테스트 포함 모두 PASS, 기존 6개 pre-existing failure만 남음

- [ ] **Step 4: Final Commit**

```bash
git add src/modules/real_estate/prompts/insight_parser.md src/modules/real_estate/prompts/context_analyst.md
git commit -m "feat(commute): 경로 상세(route_summary+legs) 전체 구현 완료"
```
