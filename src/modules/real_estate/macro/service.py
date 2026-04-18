"""
Real Estate 도메인 전용 거시경제 조회 어댑터.
실제 수집/저장은 modules.macro.service.MacroCollectionService에 위임한다.
"""
from typing import Dict, Any, List, Optional

try:
    from modules.macro.service import MacroCollectionService
    from modules.real_estate.config import RealEstateConfig
except ImportError:
    from src.modules.macro.service import MacroCollectionService
    from src.modules.real_estate.config import RealEstateConfig

try:
    from core.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class MacroService:
    """
    RealEstateAgent가 직접 참조하는 어댑터.
    MacroCollectionService에 위임하고, 기존 응답 포맷(MacroData 호환)을 유지한다.
    """

    def __init__(self, api_key: Optional[str] = None):
        config = RealEstateConfig()
        db_path = config.get("macro_db_path", "data/macro.db")
        self._svc = MacroCollectionService(db_path=db_path, api_key=api_key)

    def fetch_latest_macro_data(self) -> Dict[str, Any]:
        """DB에서 real_estate + common 도메인 최신값 조회."""
        latest = self._svc.get_latest(domain="real_estate")
        result: Dict[str, Any] = {"updated_at": None}

        for item in latest:
            name = item.get("name", "")
            collected_at = item.get("collected_at")
            if not result["updated_at"] or collected_at > result["updated_at"]:
                result["updated_at"] = collected_at

            entry = {
                "name": name,
                "code": str(item.get("id")),
                "value": item.get("value"),
                "unit": item.get("unit"),
                "date": item.get("period"),
            }

            if "기준금리" in name:
                result["base_rate"] = entry
            elif "주택담보대출" in name or "주담대" in name:
                result["loan_rate"] = entry
            elif "M2" in name:
                result["m2_growth"] = entry

        return result

    def fetch_macro_history(self, months: int = 24) -> Dict[str, List[Dict[str, Any]]]:
        """기준금리·주담대 시계열 반환 (기존 응답 포맷 유지)."""
        latest_list = self._svc.get_latest(domain="real_estate")
        base_id = next((i["id"] for i in latest_list if "기준금리" in i["name"]), None)
        loan_id = next((i["id"] for i in latest_list if "주택담보대출" in i["name"]), None)

        def _to_series(indicator_id, label):
            if not indicator_id:
                return []
            records = self._svc.get_history(indicator_id, months=months)
            return [
                {"date": f"{r.period[:4]}-{r.period[4:]}", "value": r.value, "name": label}
                for r in sorted(records, key=lambda x: x.period)
            ]

        return {
            "base_rate": _to_series(base_id, "한국은행 기준금리(%)"),
            "loan_rate":  _to_series(loan_id, "주담대금리(%)"),
        }

    def collect_real_estate_indicators(self) -> Dict[str, Any]:
        """real_estate + common 지표 수집 (기한 도래분만)."""
        return self._svc.collect_due_indicators(domain="real_estate")
