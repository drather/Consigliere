from datetime import date
from typing import List, Optional
from .api_client import MOLITClient
from ..models import RealEstateTransaction

class TransactionMonitorService:
    """
    Orchestrates fetching transactions from API and converting them to domain models.
    """

    def __init__(self, client: Optional[MOLITClient] = None):
        self.client = client or MOLITClient()

    def get_daily_transactions(self, district_code: str, year_month: str) -> List[RealEstateTransaction]:
        """
        Main entry point to get cleaned transaction objects.
        """
        raw_xml = self.client.fetch_raw_transactions(district_code, year_month)
        if not raw_xml:
            return []

        dict_items = self.client.parse_xml_to_dict_list(raw_xml)
        transactions = []

        for item in dict_items:
            try:
                # Map API tags (English based on latest version observation)
                # dealAmount: "    82,500" (10k KRW unit)
                price_str = item.get("dealAmount", "0").replace(",", "").strip()
                price_krw = int(price_str) * 10000

                deal_date = date(
                    year=int(item.get("dealYear")),
                    month=int(item.get("dealMonth")),
                    day=int(item.get("dealDay"))
                )

                transaction = RealEstateTransaction(
                    deal_date=deal_date,
                    district_code=item.get("sggCd", district_code), # sggCd or bonbun? Usually sggCd for district
                    apt_name=item.get("aptNm", "Unknown"),
                    exclusive_area=float(item.get("excluUseAr", 0)),
                    floor=int(item.get("floor", 0)),
                    price=price_krw,
                    build_year=int(item.get("buildYear", 0)),
                    road_name=item.get("roadNm"),
                )
                transactions.append(transaction)
            except Exception as e:
                # Fallback for Korean tags just in case (older API version compatibility)
                if not transactions and "아파트" in item:
                    try:
                        price_str = item.get("거래금액", "0").replace(",", "").strip()
                        price_krw = int(price_str) * 10000
                        deal_date = date(int(item.get("년")), int(item.get("월")), int(item.get("일")))
                        transaction = RealEstateTransaction(
                            deal_date=deal_date,
                            district_code=item.get("법정동시군구코드", district_code),
                            apt_name=item.get("아파트", "Unknown"),
                            exclusive_area=float(item.get("전용면적", 0)),
                            floor=int(item.get("층", 0)),
                            price=price_krw,
                            build_year=int(item.get("건축년도", 0)),
                            road_name=item.get("도로명"),
                        )
                        transactions.append(transaction)
                    except:
                        print(f"⚠️ [Monitor] Skipping item due to parsing error: {e}")
                        continue
                else:
                    print(f"⚠️ [Monitor] Skipping item due to parsing error: {e}")
                    continue

        print(f"✅ [Monitor] Successfully parsed {len(transactions)} transactions.")
        return transactions
