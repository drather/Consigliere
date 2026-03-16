from pydantic import BaseModel
from typing import List, Optional

class MacroIndicator(BaseModel):
    name: str
    code: str
    value: float
    unit: str
    date: str

class MacroData(BaseModel):
    base_rate: Optional[MacroIndicator] = None
    m2_growth: Optional[MacroIndicator] = None
    loan_rate: Optional[MacroIndicator] = None
    updated_at: str
