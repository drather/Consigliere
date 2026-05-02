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
        dest_override: Optional[str] = None,
        dest_lat_override: Optional[float] = None,
        dest_lng_override: Optional[float] = None,
    ) -> Optional[CommuteResult]:
        """단일 모드 출퇴근 시간 반환. 실패 시 None.

        dest_override 제공 시 초기화 destination 대신 사용.
        캐시 키는 (origin_key, destination, mode) 복합키.
        """
        dest = dest_override or self._dest
        dest_lat = dest_lat_override if dest_lat_override is not None else self._dest_lat
        dest_lng = dest_lng_override if dest_lng_override is not None else self._dest_lng

        cached = self._repo.get(origin_key, dest, mode)
        if cached is not None:
            return cached

        coords = self._geocoder.geocode(apt_name, district_code, address=road_address)
        if coords is None:
            logger.warning("[CommuteService] geocode 실패: %s / %s", apt_name, road_address)
            return None

        origin_lat, origin_lng = coords
        try:
            duration, distance, legs, route_summary = self._client.route_with_legs(
                origin_lat, origin_lng, dest_lat, dest_lng, mode=mode
            )
        except Exception as exc:
            logger.warning("[CommuteService] T-map %s 실패 (%s): %s", mode, apt_name, exc)
            return None

        result = CommuteResult(
            origin_key=origin_key,
            destination=dest,
            mode=mode,
            duration_minutes=duration,
            distance_meters=distance,
            cached=False,
            legs=legs,
            route_summary=route_summary,
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
