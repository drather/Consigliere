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
