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
