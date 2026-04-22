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
