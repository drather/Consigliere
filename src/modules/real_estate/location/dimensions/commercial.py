from modules.real_estate.location.dimensions.base import BaseDimension


class CommercialDimension(BaseDimension):
    @property
    def dimension_id(self) -> str:
        return "commercial"

    @property
    def label(self) -> str:
        return "commercial"  # TODO(task2): replace with emoji label

    def score(self, candidate: dict) -> int:
        restaurant = candidate.get("poi_restaurant_count", 0) or 0
        cafe = candidate.get("poi_cafe_count", 0) or 0
        convenience = candidate.get("poi_convenience_count", 0) or 0
        pharmacy = candidate.get("poi_pharmacy_count", 0) or 0
        medical = candidate.get("poi_medical_count", 0) or 0
        mart = candidate.get("poi_marts_count", 0) or 0

        cfg = self._config
        high = cfg.get("high_count", 30)
        mid = cfg.get("medium_count", 10)

        total = restaurant + cafe
        volume_score = 100 if total >= high else (60 if total >= mid else 20)

        min_c = cfg.get("diversity_min_count", {})
        checks = [
            (restaurant, min_c.get("restaurant", 3)),
            (cafe, min_c.get("cafe", 2)),
            (convenience, min_c.get("convenience", 1)),
            (pharmacy, min_c.get("pharmacy", 1)),
            (medical, min_c.get("medical", 1)),
            (mart, min_c.get("mart", 1)),
        ]
        present = sum(1 for count, threshold in checks if count >= threshold)
        diversity_score = round(present / len(checks) * 100)

        return int(volume_score * 0.5 + diversity_score * 0.5 + 0.5)
