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
