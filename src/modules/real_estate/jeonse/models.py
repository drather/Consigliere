from dataclasses import dataclass
from typing import Optional


@dataclass
class JeonseTransaction:
    apt_name: str
    district_code: str
    deal_date: str          # YYYY-MM-DD
    exclusive_area: float
    deposit: int            # 만원
    monthly_rent: int       # 만원, 전세=0
    contract_type: str      # 'jeonse' | 'monthly'
    floor: int
    complex_code: Optional[str] = None
    id: Optional[int] = None
