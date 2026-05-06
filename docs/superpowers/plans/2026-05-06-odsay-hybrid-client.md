# ODsay Hybrid Commute Client Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tmap 대중교통 API(일 10회 제한)를 ODsay LAB API(일 1,000회)로 교체하고, car/walking은 Tmap을 유지한다.

**Architecture:** `OdsayClient`(transit 전용) + `TmapClient`(car/walking)을 `HybridCommuteClient`로 감싸고, 이것을 기존 4개 주입처에서 `TmapClient` 대신 주입한다. `CommuteService`는 시그니처 변경 없음.

**Tech Stack:** Python 3.12, requests, pytest, unittest.mock

---

## 파일 맵

| 액션 | 경로 |
|---|---|
| Create | `src/modules/real_estate/commute/odsay_client.py` |
| Create | `src/modules/real_estate/commute/hybrid_commute_client.py` |
| Create | `tests/modules/real_estate/commute/test_odsay_client.py` |
| Create | `tests/modules/real_estate/commute/test_hybrid_commute_client.py` |
| Modify | `.env` — ODSAY_API_KEY 추가 |
| Modify | `src/modules/real_estate/commute/commute_service.py:22` — 타입 힌트 |
| Modify | `src/api/dependencies.py:88,101` — 주입처 교체 |
| Modify | `src/api/routers/real_estate.py:616,668` — 주입처 교체 |
| Modify | `src/modules/real_estate/service.py:31,109` — 주입처 교체 |
| Modify | `src/mcp_servers/commute_server.py:16,40` — 주입처 교체 |

---

## Task 1: 환경 변수 추가

**Files:**
- Modify: `.env`

- [ ] **Step 1: .env에 ODSAY_API_KEY 추가**

`.env` 파일 41번째 줄 `TMAP_API_KEY` 바로 아래에 추가:
```
ODSAY_API_KEY=W1Dvt1n7FqY6PJ6PSC92Q4RZf+N+scTVyB526Z48kHY
```

- [ ] **Step 2: 확인**

```bash
grep ODSAY .env
```

Expected: `ODSAY_API_KEY=W1Dvt1n7FqY6PJ6PSC92Q4RZf+N+scTVyB526Z48kHY`

- [ ] **Step 3: Commit**

```bash
git add .env
git commit -m "chore: ODSAY_API_KEY 환경변수 추가"
```

---

## Task 2: OdsayClient — 테스트 작성

**Files:**
- Create: `tests/modules/real_estate/commute/test_odsay_client.py`

- [ ] **Step 1: 테스트 파일 작성**

```python
import os
import sys
import math
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

# ODsay 정상 응답 — 지하철+버스+도보 혼합 경로
ODSAY_RESPONSE = {
    "result": {
        "path": [{
            "info": {
                "totalTime": 45,   # 분 단위
                "totalWalk": 800,  # 도보 거리(m)
            },
            "subPath": [
                {
                    "trafficType": 3,     # 도보
                    "sectionTime": 300,   # 초
                    "startName": "출발지",
                    "endName": "강남역",
                },
                {
                    "trafficType": 1,     # 지하철
                    "sectionTime": 900,   # 초
                    "startName": "강남역",
                    "endName": "서울역",
                    "lane": [{"name": "2호선"}],
                    "passStopList": {
                        "stations": [
                            {"stationName": "강남역"},
                            {"stationName": "역삼역"},
                            {"stationName": "서울역"},
                        ]
                    },
                },
                {
                    "trafficType": 2,     # 버스
                    "sectionTime": 600,   # 초
                    "startName": "서울역",
                    "endName": "종로3가역",
                    "lane": [{"busNo": "150"}],
                    "passStopList": {
                        "stations": [
                            {"stationName": "서울역"},
                            {"stationName": "종로3가역"},
                        ]
                    },
                },
                {
                    "trafficType": 3,     # 도보
                    "sectionTime": 180,   # 초
                    "startName": "종로3가역",
                    "endName": "목적지",
                },
            ]
        }]
    }
}

ODSAY_EMPTY_PATH = {"result": {"path": []}}


def _mock_get(response_json):
    mock_resp = MagicMock()
    mock_resp.json.return_value = response_json
    mock_resp.raise_for_status.return_value = None
    return mock_resp


class TestOdsayClientRouteDuration:
    def test_total_time_is_already_minutes(self):
        """ODsay totalTime은 분 단위 — 변환 없이 그대로 반환."""
        from modules.real_estate.commute.odsay_client import OdsayClient
        client = OdsayClient(api_key="test-key")

        with patch("modules.real_estate.commute.odsay_client.requests.get",
                   return_value=_mock_get(ODSAY_RESPONSE)):
            duration, distance = client.route(37.4942, 127.0611, 37.5088, 127.0633)

        assert duration == 45
        assert distance == 800

    def test_empty_path_raises_value_error(self):
        """path가 비어 있으면 ValueError를 발생시킨다."""
        from modules.real_estate.commute.odsay_client import OdsayClient
        client = OdsayClient(api_key="test-key")

        with patch("modules.real_estate.commute.odsay_client.requests.get",
                   return_value=_mock_get(ODSAY_EMPTY_PATH)):
            with pytest.raises(ValueError, match="empty path"):
                client.route(37.4942, 127.0611, 37.5088, 127.0633)


class TestOdsayClientLegs:
    def test_legs_count_matches_subpath(self):
        """subPath 4개 → legs 4개."""
        from modules.real_estate.commute.odsay_client import OdsayClient
        client = OdsayClient(api_key="test-key")

        with patch("modules.real_estate.commute.odsay_client.requests.get",
                   return_value=_mock_get(ODSAY_RESPONSE)):
            _, _, legs, _ = client.route_with_legs(37.4942, 127.0611, 37.5088, 127.0633)

        assert len(legs) == 4

    def test_traffic_type_1_maps_to_subway(self):
        """trafficType=1 → mode='SUBWAY', lane[0].name → route."""
        from modules.real_estate.commute.odsay_client import OdsayClient
        client = OdsayClient(api_key="test-key")

        with patch("modules.real_estate.commute.odsay_client.requests.get",
                   return_value=_mock_get(ODSAY_RESPONSE)):
            _, _, legs, _ = client.route_with_legs(37.4942, 127.0611, 37.5088, 127.0633)

        subway = next(l for l in legs if l["mode"] == "SUBWAY")
        assert subway["route"] == "2호선"
        assert subway["stop_count"] == 3
        assert subway["from_name"] == "강남역"
        assert subway["to_name"] == "서울역"

    def test_traffic_type_2_maps_to_bus(self):
        """trafficType=2 → mode='BUS', lane[0].busNo → route."""
        from modules.real_estate.commute.odsay_client import OdsayClient
        client = OdsayClient(api_key="test-key")

        with patch("modules.real_estate.commute.odsay_client.requests.get",
                   return_value=_mock_get(ODSAY_RESPONSE)):
            _, _, legs, _ = client.route_with_legs(37.4942, 127.0611, 37.5088, 127.0633)

        bus = next(l for l in legs if l["mode"] == "BUS")
        assert bus["route"] == "150"
        assert bus["stop_count"] == 2

    def test_traffic_type_3_maps_to_walk(self):
        """trafficType=3 → mode='WALK', duration_minutes = ceil(sectionTime/60)."""
        from modules.real_estate.commute.odsay_client import OdsayClient
        client = OdsayClient(api_key="test-key")

        with patch("modules.real_estate.commute.odsay_client.requests.get",
                   return_value=_mock_get(ODSAY_RESPONSE)):
            _, _, legs, _ = client.route_with_legs(37.4942, 127.0611, 37.5088, 127.0633)

        walk_legs = [l for l in legs if l["mode"] == "WALK"]
        assert len(walk_legs) == 2
        # 첫 번째 도보: 300초 = 5분
        assert walk_legs[0]["duration_minutes"] == 5

    def test_section_time_seconds_converted_to_minutes(self):
        """sectionTime(초) → duration_minutes(분, ceil)."""
        from modules.real_estate.commute.odsay_client import OdsayClient
        client = OdsayClient(api_key="test-key")

        with patch("modules.real_estate.commute.odsay_client.requests.get",
                   return_value=_mock_get(ODSAY_RESPONSE)):
            _, _, legs, _ = client.route_with_legs(37.4942, 127.0611, 37.5088, 127.0633)

        subway = next(l for l in legs if l["mode"] == "SUBWAY")
        # 900초 = 15분
        assert subway["duration_minutes"] == 15


class TestOdsayClientSummary:
    def test_summary_contains_subway_route(self):
        """route_summary에 지하철 노선명 포함."""
        from modules.real_estate.commute.odsay_client import OdsayClient
        client = OdsayClient(api_key="test-key")

        with patch("modules.real_estate.commute.odsay_client.requests.get",
                   return_value=_mock_get(ODSAY_RESPONSE)):
            _, _, _, summary = client.route_with_legs(37.4942, 127.0611, 37.5088, 127.0633)

        assert "2호선" in summary

    def test_summary_contains_bus_number(self):
        """route_summary에 버스 번호 포함."""
        from modules.real_estate.commute.odsay_client import OdsayClient
        client = OdsayClient(api_key="test-key")

        with patch("modules.real_estate.commute.odsay_client.requests.get",
                   return_value=_mock_get(ODSAY_RESPONSE)):
            _, _, _, summary = client.route_with_legs(37.4942, 127.0611, 37.5088, 127.0633)

        assert "150" in summary

    def test_summary_contains_walk_minutes(self):
        """route_summary에 도보 시간 포함."""
        from modules.real_estate.commute.odsay_client import OdsayClient
        client = OdsayClient(api_key="test-key")

        with patch("modules.real_estate.commute.odsay_client.requests.get",
                   return_value=_mock_get(ODSAY_RESPONSE)):
            _, _, _, summary = client.route_with_legs(37.4942, 127.0611, 37.5088, 127.0633)

        assert "도보" in summary

    def test_request_passes_correct_params(self):
        """GET 요청에 SX=경도, SY=위도 파라미터가 포함된다."""
        from modules.real_estate.commute.odsay_client import OdsayClient
        client = OdsayClient(api_key="test-key")

        with patch("modules.real_estate.commute.odsay_client.requests.get",
                   return_value=_mock_get(ODSAY_RESPONSE)) as mock_get:
            client.route(37.4942, 127.0611, 37.5088, 127.0633)

        call_kwargs = mock_get.call_args[1]
        params = call_kwargs["params"]
        assert params["SX"] == "127.0611"  # 경도
        assert params["SY"] == "37.4942"   # 위도
        assert params["EX"] == "127.0633"
        assert params["EY"] == "37.5088"
        assert params["apiKey"] == "test-key"
```

- [ ] **Step 2: 테스트 실행 (FAIL 확인)**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/commute/test_odsay_client.py -v
```

Expected: `ModuleNotFoundError: No module named 'modules.real_estate.commute.odsay_client'`

---

## Task 3: OdsayClient — 구현

**Files:**
- Create: `src/modules/real_estate/commute/odsay_client.py`

- [ ] **Step 1: odsay_client.py 작성**

```python
import logging
import math
import requests
from typing import List, Tuple

logger = logging.getLogger(__name__)

_TRANSIT_URL = "https://api.odsay.com/v1/api/searchPubTransPathT"

_TRAFFIC_TYPE_MAP = {1: "SUBWAY", 2: "BUS", 3: "WALK"}


class OdsayClient:
    """ODsay LAB 대중교통 경로탐색 API 래퍼. transit 모드 전용."""

    def __init__(self, api_key: str, timeout: int = 10):
        self._api_key = api_key
        self._timeout = timeout

    def route(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        mode: str = "transit",
    ) -> Tuple[int, int]:
        """Returns (duration_minutes, distance_meters)."""
        duration, distance, _, _ = self.route_with_legs(origin_lat, origin_lng, dest_lat, dest_lng)
        return duration, distance

    def route_with_legs(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        mode: str = "transit",
    ) -> Tuple[int, int, List[dict], str]:
        """Returns (duration_minutes, distance_meters, legs, route_summary)."""
        params = {
            "apiKey": self._api_key,
            "SX": str(origin_lng),
            "SY": str(origin_lat),
            "EX": str(dest_lng),
            "EY": str(dest_lat),
        }
        resp = requests.get(_TRANSIT_URL, params=params, timeout=self._timeout)
        resp.raise_for_status()
        data = resp.json()
        paths = data.get("result", {}).get("path", [])
        if not paths:
            raise ValueError("ODsay: empty path in response")
        best = paths[0]
        info = best.get("info", {})
        duration = int(info.get("totalTime", 0))  # 이미 분 단위
        distance = int(info.get("totalWalk", 0))
        legs = self._parse_legs(best.get("subPath", []))
        summary = self._build_summary(legs)
        return duration, distance, legs, summary

    def _parse_legs(self, sub_paths: list) -> List[dict]:
        legs = []
        for sp in sub_paths:
            traffic_type = sp.get("trafficType", 3)
            mode = _TRAFFIC_TYPE_MAP.get(traffic_type, "WALK")
            entry: dict = {
                "mode": mode,
                "from_name": sp.get("startName", ""),
                "to_name": sp.get("endName", ""),
                "duration_minutes": math.ceil(sp.get("sectionTime", 0) / 60),
            }
            if mode in ("BUS", "SUBWAY"):
                lane = sp.get("lane", [{}])[0] if sp.get("lane") else {}
                entry["route"] = lane.get("busNo", "") if mode == "BUS" else lane.get("name", "")
                entry["stop_count"] = len(sp.get("passStopList", {}).get("stations", []))
            legs.append(entry)
        return legs

    def _build_summary(self, legs: List[dict]) -> str:
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
            elif m == "SUBWAY":
                parts.append(leg.get("route", "지하철"))
                to = leg.get("to_name", "")
                if to:
                    parts.append(to)
        return " → ".join(parts) if parts else ""
```

- [ ] **Step 2: 테스트 실행 (PASS 확인)**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/commute/test_odsay_client.py -v
```

Expected: `11 passed`

- [ ] **Step 3: Commit**

```bash
git add src/modules/real_estate/commute/odsay_client.py \
        tests/modules/real_estate/commute/test_odsay_client.py
git commit -m "feat(commute): OdsayClient — ODsay LAB 대중교통 경로탐색 API 클라이언트"
```

---

## Task 4: HybridCommuteClient — 테스트 작성

**Files:**
- Create: `tests/modules/real_estate/commute/test_hybrid_commute_client.py`

- [ ] **Step 1: 테스트 파일 작성**

```python
import os
import sys
import pytest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))


def _make_hybrid(odsay=None, tmap=None):
    from modules.real_estate.commute.hybrid_commute_client import HybridCommuteClient
    return HybridCommuteClient(
        odsay=odsay or MagicMock(),
        tmap=tmap or MagicMock(),
    )


class TestHybridRouteWithLegs:
    def test_transit_delegates_to_odsay(self):
        """transit 모드 → OdsayClient.route_with_legs 호출."""
        mock_odsay = MagicMock()
        mock_odsay.route_with_legs.return_value = (45, 800, [], "2호선 → 서울역")
        mock_tmap = MagicMock()

        client = _make_hybrid(odsay=mock_odsay, tmap=mock_tmap)
        result = client.route_with_legs(37.49, 127.06, 37.51, 127.07, mode="transit")

        mock_odsay.route_with_legs.assert_called_once_with(37.49, 127.06, 37.51, 127.07)
        mock_tmap.route_with_legs.assert_not_called()
        assert result == (45, 800, [], "2호선 → 서울역")

    def test_car_delegates_to_tmap(self):
        """car 모드 → TmapClient.route_with_legs 호출."""
        mock_odsay = MagicMock()
        mock_tmap = MagicMock()
        mock_tmap.route_with_legs.return_value = (30, 15000, [], "올림픽대로 (15.0km)")

        client = _make_hybrid(odsay=mock_odsay, tmap=mock_tmap)
        result = client.route_with_legs(37.49, 127.06, 37.51, 127.07, mode="car")

        mock_tmap.route_with_legs.assert_called_once_with(37.49, 127.06, 37.51, 127.07, mode="car")
        mock_odsay.route_with_legs.assert_not_called()
        assert result == (30, 15000, [], "올림픽대로 (15.0km)")

    def test_walking_delegates_to_tmap(self):
        """walking 모드 → TmapClient.route_with_legs 호출."""
        mock_odsay = MagicMock()
        mock_tmap = MagicMock()
        mock_tmap.route_with_legs.return_value = (90, 5000, [], "도보 (5.0km)")

        client = _make_hybrid(odsay=mock_odsay, tmap=mock_tmap)
        result = client.route_with_legs(37.49, 127.06, 37.51, 127.07, mode="walking")

        mock_tmap.route_with_legs.assert_called_once_with(37.49, 127.06, 37.51, 127.07, mode="walking")
        mock_odsay.route_with_legs.assert_not_called()


class TestHybridRoute:
    def test_transit_route_delegates_to_odsay(self):
        """route() transit → OdsayClient.route 호출."""
        mock_odsay = MagicMock()
        mock_odsay.route.return_value = (45, 800)
        mock_tmap = MagicMock()

        client = _make_hybrid(odsay=mock_odsay, tmap=mock_tmap)
        duration, distance = client.route(37.49, 127.06, 37.51, 127.07, mode="transit")

        mock_odsay.route.assert_called_once_with(37.49, 127.06, 37.51, 127.07)
        mock_tmap.route.assert_not_called()
        assert duration == 45

    def test_car_route_delegates_to_tmap(self):
        """route() car → TmapClient.route 호출."""
        mock_odsay = MagicMock()
        mock_tmap = MagicMock()
        mock_tmap.route.return_value = (30, 15000)

        client = _make_hybrid(odsay=mock_odsay, tmap=mock_tmap)
        duration, distance = client.route(37.49, 127.06, 37.51, 127.07, mode="car")

        mock_tmap.route.assert_called_once_with(37.49, 127.06, 37.51, 127.07, mode="car")
        mock_odsay.route.assert_not_called()
        assert duration == 30
```

- [ ] **Step 2: 테스트 실행 (FAIL 확인)**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/commute/test_hybrid_commute_client.py -v
```

Expected: `ModuleNotFoundError: No module named 'modules.real_estate.commute.hybrid_commute_client'`

---

## Task 5: HybridCommuteClient — 구현

**Files:**
- Create: `src/modules/real_estate/commute/hybrid_commute_client.py`

- [ ] **Step 1: hybrid_commute_client.py 작성**

```python
from typing import List, Tuple
from .odsay_client import OdsayClient
from .tmap_client import TmapClient


class HybridCommuteClient:
    """transit → OdsayClient, car/walking → TmapClient으로 라우팅하는 합성 클라이언트."""

    def __init__(self, odsay: OdsayClient, tmap: TmapClient):
        self._odsay = odsay
        self._tmap = tmap

    def route_with_legs(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        mode: str,
    ) -> Tuple[int, int, List[dict], str]:
        if mode == "transit":
            return self._odsay.route_with_legs(origin_lat, origin_lng, dest_lat, dest_lng)
        return self._tmap.route_with_legs(origin_lat, origin_lng, dest_lat, dest_lng, mode=mode)

    def route(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        mode: str,
    ) -> Tuple[int, int]:
        if mode == "transit":
            return self._odsay.route(origin_lat, origin_lng, dest_lat, dest_lng)
        return self._tmap.route(origin_lat, origin_lng, dest_lat, dest_lng, mode=mode)
```

- [ ] **Step 2: 테스트 실행 (PASS 확인)**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/commute/test_hybrid_commute_client.py -v
```

Expected: `5 passed`

- [ ] **Step 3: Commit**

```bash
git add src/modules/real_estate/commute/hybrid_commute_client.py \
        tests/modules/real_estate/commute/test_hybrid_commute_client.py
git commit -m "feat(commute): HybridCommuteClient — transit=ODsay, car/walking=Tmap 라우팅"
```

---

## Task 6: 주입처 교체 및 타입 힌트 업데이트

**Files:**
- Modify: `src/modules/real_estate/commute/commute_service.py:6,22`
- Modify: `src/api/dependencies.py:88,101`
- Modify: `src/api/routers/real_estate.py:616,668`
- Modify: `src/modules/real_estate/service.py:31,109`
- Modify: `src/mcp_servers/commute_server.py:16,40`

- [ ] **Step 1: commute_service.py 타입 힌트 교체**

`src/modules/real_estate/commute/commute_service.py` 6번째 줄:
```python
# Before
from .tmap_client import TmapClient

# After
from .hybrid_commute_client import HybridCommuteClient
```

22번째 줄:
```python
# Before
        tmap_client: TmapClient,

# After
        tmap_client: HybridCommuteClient,
```

- [ ] **Step 2: api/dependencies.py 교체**

`src/api/dependencies.py` 88번째 줄:
```python
# Before
from modules.real_estate.commute.tmap_client import TmapClient

# After
from modules.real_estate.commute.odsay_client import OdsayClient
from modules.real_estate.commute.tmap_client import TmapClient
from modules.real_estate.commute.hybrid_commute_client import HybridCommuteClient
```

101번째 줄:
```python
# Before
    tmap_client=TmapClient(api_key=os.getenv("TMAP_API_KEY", "")),

# After
    tmap_client=HybridCommuteClient(
        odsay=OdsayClient(api_key=os.getenv("ODSAY_API_KEY", "")),
        tmap=TmapClient(api_key=os.getenv("TMAP_API_KEY", "")),
    ),
```

- [ ] **Step 3: api/routers/real_estate.py 교체**

616번째 줄:
```python
# Before
    from modules.real_estate.commute.tmap_client import TmapClient

# After
    from modules.real_estate.commute.odsay_client import OdsayClient
    from modules.real_estate.commute.tmap_client import TmapClient
    from modules.real_estate.commute.hybrid_commute_client import HybridCommuteClient
```

668번째 줄:
```python
# Before
            tmap_client=TmapClient(api_key=tmap_key),

# After
            tmap_client=HybridCommuteClient(
                odsay=OdsayClient(api_key=os.getenv("ODSAY_API_KEY", "")),
                tmap=TmapClient(api_key=tmap_key),
            ),
```

- [ ] **Step 4: service.py 교체**

`src/modules/real_estate/service.py` 31번째 줄:
```python
# Before
from .commute.tmap_client import TmapClient

# After
from .commute.odsay_client import OdsayClient
from .commute.tmap_client import TmapClient
from .commute.hybrid_commute_client import HybridCommuteClient
```

109번째 줄:
```python
# Before
            tmap_client=TmapClient(api_key=tmap_key),

# After
            tmap_client=HybridCommuteClient(
                odsay=OdsayClient(api_key=os.getenv("ODSAY_API_KEY", "")),
                tmap=TmapClient(api_key=tmap_key),
            ),
```

- [ ] **Step 5: commute_server.py 교체**

16번째 줄:
```python
# Before
from modules.real_estate.commute.tmap_client import TmapClient

# After
from modules.real_estate.commute.odsay_client import OdsayClient
from modules.real_estate.commute.tmap_client import TmapClient
from modules.real_estate.commute.hybrid_commute_client import HybridCommuteClient
```

40번째 줄:
```python
# Before
    tmap_client=TmapClient(api_key=os.getenv("TMAP_API_KEY", "")),

# After
    tmap_client=HybridCommuteClient(
        odsay=OdsayClient(api_key=os.getenv("ODSAY_API_KEY", "")),
        tmap=TmapClient(api_key=os.getenv("TMAP_API_KEY", "")),
    ),
```

- [ ] **Step 6: Commit**

```bash
git add src/modules/real_estate/commute/commute_service.py \
        src/api/dependencies.py \
        src/api/routers/real_estate.py \
        src/modules/real_estate/service.py \
        src/mcp_servers/commute_server.py
git commit -m "feat(commute): 주입처 4곳 HybridCommuteClient로 교체 — transit=ODsay, car/walking=Tmap"
```

---

## Task 7: 전체 테스트 통과 확인

- [ ] **Step 1: commute 관련 테스트 전체 실행**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/commute/ -v
```

Expected: 모든 테스트 PASS (기존 tmap/commute_service/commute_repository 테스트 포함)

- [ ] **Step 2: 전체 단위 테스트 실행**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/ -v --ignore=tests/e2e
```

Expected: 기존 테스트 수 이상 PASS, 0 FAILED

- [ ] **Step 3: Commit (실패 시만)**

이미 각 Task에서 커밋했으므로, 추가 수정이 없으면 생략.

---

## 완료 기준

- [ ] `test_odsay_client.py` 11개 테스트 PASS
- [ ] `test_hybrid_commute_client.py` 5개 테스트 PASS
- [ ] 기존 `test_tmap_client.py`, `test_commute_service.py`, `test_commute_repository.py` 변경 없이 PASS
- [ ] `TmapClient` 직접 주입 코드가 코드베이스에 남아 있지 않음
- [ ] `.env`에 `ODSAY_API_KEY` 추가됨
