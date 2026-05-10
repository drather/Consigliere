from typing import List
from modules.real_estate.location.dimensions.base import BaseDimension


class TransportationDimension(BaseDimension):
    @property
    def dimension_id(self) -> str:
        return "transportation"

    @property
    def label(self) -> str:
        return "🚇 교통"

    def score(self, candidate: dict) -> int:
        neutral = self._config.get("data_absent_neutral", 50)
        close_min = self._config.get("subway_close_min", 5)
        commute_high = self._config.get("commute_high_min", 20)
        commute_medium = self._config.get("commute_medium_min", 35)

        stations = candidate.get("poi_stations") or candidate.get("nearest_stations")
        if stations:
            closest = min(s.get("walk_minutes", 99) for s in stations)
            if closest <= close_min:
                station_score = 100
            elif closest <= close_min * 2:
                station_score = 60
            else:
                station_score = 20
        else:
            station_score = neutral

        minutes = candidate.get("commute_transit_minutes") or candidate.get("commute_minutes")
        if minutes is not None:
            if minutes <= commute_high:
                commute_score = 100
            elif minutes <= commute_medium:
                commute_score = 60
            else:
                commute_score = 20
        else:
            commute_score = neutral

        return round((station_score + commute_score) / 2)

    def evidence(self, candidate: dict) -> List[str]:
        lines = []
        commute = candidate.get("commute_transit_minutes") or candidate.get("commute_minutes")
        if commute is not None:
            lines.append(f"대중교통 {commute}분")
        route = candidate.get("_commute_route_summary", "")
        if route:
            lines.append(f"경로: {route}")
        poi = candidate.get("_poi")
        if poi and hasattr(poi, "subway_stations") and poi.subway_stations:
            for s in poi.subway_stations[:2]:
                lines.append(f"인근역: {s.get('name', '?')} 도보 {s.get('walk_minutes', '?')}분")
        return lines
