from dataclasses import dataclass
from typing import Optional


@dataclass
class SupplySchedule:
    project_name: str
    sigungu_code: str
    lat: float
    lng: float
    household_count: int
    expected_date: str      # YYYY-MM
    supply_type: str        # 'sale' | 'move_in'
    id: Optional[int] = None
