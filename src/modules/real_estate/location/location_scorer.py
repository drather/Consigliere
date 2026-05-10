from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List

from modules.real_estate.location.dimension_result import DimensionResult
from modules.real_estate.location.dimensions.base import BaseDimension
from modules.real_estate.location.dimensions.transportation import TransportationDimension
from modules.real_estate.location.dimensions.education import EducationDimension
from modules.real_estate.location.dimensions.living_infra import LivingInfraDimension
from modules.real_estate.location.dimensions.medical import MedicalDimension
from modules.real_estate.location.dimensions.nature import NatureDimension
from modules.real_estate.location.dimensions.commercial import CommercialDimension
from modules.real_estate.location.dimensions.price_potential import PricePotentialDimension
from modules.real_estate.location.dimensions.liquidity import LiquidityDimension
from modules.real_estate.location.dimensions.school_premium import SchoolPremiumDimension
from modules.real_estate.location.dimensions.nuisance import NuisanceDimension


@dataclass
class LocationScore:
    complex_code: str
    residential_total: int
    residential_results: List[DimensionResult]
    investment_total: int
    investment_results: List[DimensionResult]
    scored_at: str


_DIMENSION_REGISTRY = {
    "transportation":  TransportationDimension,
    "education":       EducationDimension,
    "living_infra":    LivingInfraDimension,
    "medical":         MedicalDimension,
    "nature":          NatureDimension,
    "commercial":      CommercialDimension,
    "price_potential": PricePotentialDimension,
    "liquidity":       LiquidityDimension,
    "school_premium":  SchoolPremiumDimension,
    "nuisance":        NuisanceDimension,
}


class LocationScorer:
    def __init__(self, config: dict):
        neutral = config.get("data_absent_neutral", 50)
        thresholds = config.get("thresholds", {})

        self._residential = self._build_dims(
            config.get("residential_dimensions", []), thresholds, neutral
        )
        self._investment = self._build_dims(
            config.get("investment_dimensions", []), thresholds, neutral
        )

    def _build_dims(self, entries: list, thresholds: dict, neutral: int) -> List[dict]:
        result = []
        for entry in entries:
            dim_id = entry["id"]
            cls = _DIMENSION_REGISTRY[dim_id]
            dim_cfg = {**thresholds.get(dim_id, {}), "data_absent_neutral": neutral}
            result.append({"dim": cls(dim_cfg), "weight": entry["weight"]})
        return result

    def score(self, candidate: dict) -> LocationScore:
        r_total, r_results = self._compute(self._residential, candidate)
        i_total, i_results = self._compute(self._investment, candidate)
        return LocationScore(
            complex_code=candidate.get("complex_code", ""),
            residential_total=r_total,
            residential_results=r_results,
            investment_total=i_total,
            investment_results=i_results,
            scored_at=datetime.now(timezone.utc).isoformat(),
        )

    def _compute(self, dim_configs: list, candidate: dict):
        total_weight = sum(dc["weight"] for dc in dim_configs) or 1
        results = []
        for dc in dim_configs:
            dim = dc["dim"]
            s = dim.score(candidate)
            ev = dim.evidence(candidate)
            results.append(DimensionResult(
                id=dim.dimension_id,
                label=dim.label,
                score=s,
                evidence=ev,
            ))
        total = round(sum(
            dr.score * dc["weight"] / total_weight
            for dr, dc in zip(results, dim_configs)
        ))
        return total, results
