from datetime import date
from typing import List, Optional
from .api_client import MOLITClient
from ..models import RealEstateTransaction
from core.logger import get_logger

logger = get_logger(__name__)


def _parse_item_to_transaction(item: dict, district_code: str) -> Optional[RealEstateTransaction]:
    """MOLIT XML item dict → RealEstateTransaction. None if parsing fails."""
    try:
        price_str = item.get("dealAmount", "0").replace(",", "").strip()
        price_krw = int(price_str) * 10000
        deal_date = date(int(item.get("dealYear")), int(item.get("dealMonth")), int(item.get("dealDay")))
        return RealEstateTransaction(
            deal_date=deal_date,
            district_code=item.get("sggCd", district_code),
            apt_name=item.get("aptNm", "Unknown"),
            exclusive_area=float(item.get("excluUseAr", 0)),
            floor=int(item.get("floor", 0)),
            price=price_krw,
            build_year=int(item.get("buildYear", 0)),
            road_name=item.get("roadNm"),
        )
    except Exception:
        try:  # Korean tag fallback (older API version)
            price_krw = int(item.get("거래금액", "0").replace(",", "").strip()) * 10000
            deal_date = date(int(item.get("년")), int(item.get("월")), int(item.get("일")))
            return RealEstateTransaction(
                deal_date=deal_date,
                district_code=item.get("법정동시군구코드", district_code),
                apt_name=item.get("아파트", "Unknown"),
                exclusive_area=float(item.get("전용면적", 0)),
                floor=int(item.get("층", 0)),
                price=price_krw,
                build_year=int(item.get("건축년도", 0)),
                road_name=item.get("도로명"),
            )
        except Exception as e:
            logger.warning(f"[Monitor] Skipping item: {e}")
            return None


class TransactionMonitorService:
    """
    Orchestrates fetching transactions from API and converting them to domain models.
    """

    def __init__(self, client: Optional[MOLITClient] = None):
        self.client = client or MOLITClient()

    def get_daily_transactions(self, district_code: str, year_month: str) -> List[RealEstateTransaction]:
        """Main entry point to get cleaned transaction objects."""
        raw_xml = self.client.fetch_raw_transactions(district_code, year_month)
        if not raw_xml:
            return []
        dict_items = self.client.parse_xml_to_dict_list(raw_xml)
        txs = [t for item in dict_items if (t := _parse_item_to_transaction(item, district_code)) is not None]
        logger.info(f"[Monitor] Parsed {len(txs)} transactions.")
        return txs
