import datetime as _dt
from typing import List
from modules.real_estate.location.dimensions.base import BaseDimension


class PricePotentialDimension(BaseDimension):
    @property
    def dimension_id(self) -> str:
        return "price_potential"

    @property
    def label(self) -> str:
        return "📈 가격상승가능성"

    def score(self, candidate: dict) -> int:
        recon_map = self._config.get("recon_score_map", {
            "HIGH": 100, "MEDIUM": 60, "LOW": 20, "COMPLETED": 50, "UNKNOWN": 50
        })
        recon_age = self._config.get("recon_age_years", 30)
        recon_far = self._config.get("recon_far_max", 200)
        neutral = self._config.get("data_absent_neutral", 50)

        far = candidate.get("floor_area_ratio")
        build_year = candidate.get("build_year")

        if far is not None and build_year is not None:
            age = _dt.date.today().year - int(build_year)
            is_old = age >= recon_age
            is_low_far = float(far) <= recon_far
            if is_old and is_low_far:
                base = 100
            elif is_old or is_low_far:
                base = 60
            else:
                base = 20
        else:
            potential = candidate.get("reconstruction_potential", "UNKNOWN")
            base = recon_map.get(potential, neutral)

        if candidate.get("gtx_benefit"):
            base = min(100, base + 30)

        return base

    def evidence(self, candidate: dict) -> List[str]:
        lines = []
        change = candidate.get("price_change_pct", 0)
        lines.append(f"전월比: {change:+.1f}%")
        build_year = candidate.get("build_year")
        if build_year:
            age = _dt.date.today().year - int(build_year)
            lines.append(f"건축연도: {build_year}년 (약 {age}년 경과)")
        return lines
