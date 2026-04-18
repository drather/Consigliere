from dataclasses import dataclass
from typing import Optional


@dataclass
class MacroIndicatorDef:
    id: Optional[int]
    code: str
    item_code: str
    name: str
    unit: str
    frequency: str
    collect_every_days: int
    domain: str
    category: str
    is_active: bool
    last_collected_at: Optional[str]
    created_at: str


@dataclass
class MacroRecord:
    id: Optional[int]
    indicator_id: int
    period: str
    value: float
    collected_at: str
