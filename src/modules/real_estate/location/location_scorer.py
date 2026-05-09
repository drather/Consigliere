from dataclasses import dataclass


@dataclass
class LocationScore:
    complex_code: str
    residential_total: int
    residential_breakdown: dict
    investment_total: int
    investment_breakdown: dict
    scored_at: str
