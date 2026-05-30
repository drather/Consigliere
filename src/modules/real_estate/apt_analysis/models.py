from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class AptAnalysisReport:
    complex_code: str
    apt_name: str
    generated_at: str               # ISO8601

    price_history: List[dict]       # {"date": str, "price": int, "area": float}
    jeonse_ratio: Optional[float]   # 전세가율 (%)
    supply_risk_summary: Optional[str]
    location_score: Optional[Dict[str, Any]]  # residential_total, investment_total, results
    commute_summary: Optional[Dict[str, int]] # mode → duration_minutes
    macro_snapshot: Dict[str, Any]

    llm_insight: str

    slack_text: str
    markdown_text: str
