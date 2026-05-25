# src/modules/real_estate/jeonse/client.py
import os
import requests
import xml.etree.ElementTree as ET
from typing import List
from core.logger import get_logger
from .models import JeonseTransaction

logger = get_logger(__name__)

_BASE_URL = "http://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent"


def _text(item: ET.Element, tag: str, default: str = "") -> str:
    el = item.find(tag)
    return el.text.strip() if el is not None and el.text else default


def _parse_date(year: str, month: str, day: str) -> str:
    try:
        m = month.strip().zfill(2)
        d = day.strip().zfill(2)
        return f"{year}-{m}-{d}"
    except Exception:
        return ""


class JeonseClient:
    def __init__(self):
        self._service_key = os.getenv("MOLIT_API_KEY", "")

    def fetch(self, district_code: str, year_month: str) -> List[JeonseTransaction]:
        """district_code: 5자리 법정동 코드, year_month: YYYYMM"""
        params = {
            "serviceKey": self._service_key,
            "pageNo": "1",
            "numOfRows": "1000",
            "LAWD_CD": district_code,
            "DEAL_YMD": year_month,
        }
        try:
            resp = requests.get(_BASE_URL, params=params, timeout=15)
            resp.raise_for_status()
            return self._parse(resp.text, district_code)
        except Exception as e:
            logger.error("[JeonseClient] fetch 실패 %s %s: %s", district_code, year_month, e)
            return []

    def _parse(self, xml_text: str, district_code: str) -> List[JeonseTransaction]:
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            logger.error("[JeonseClient] XML 파싱 실패: %s", e)
            return []

        results = []
        for item in root.iter("item"):
            apt_name = _text(item, "아파트")
            deposit_raw = _text(item, "보증금액").replace(",", "")
            monthly_raw = _text(item, "월세금액").replace(",", "")
            area_raw = _text(item, "전용면적")
            year = _text(item, "년")
            month = _text(item, "월")
            day = _text(item, "일")
            floor_raw = _text(item, "층")

            try:
                deposit = int(deposit_raw) if deposit_raw else 0
                monthly_rent = int(monthly_raw) if monthly_raw else 0
                area = float(area_raw) if area_raw else 0.0
                floor = int(floor_raw) if floor_raw else 0
                deal_date = _parse_date(year, month, day)
                contract_type = "jeonse" if monthly_rent == 0 else "monthly"
            except (ValueError, TypeError):
                continue

            if not apt_name or deposit == 0 or area == 0.0 or not deal_date:
                continue

            results.append(JeonseTransaction(
                apt_name=apt_name,
                district_code=district_code,
                deal_date=deal_date,
                exclusive_area=area,
                deposit=deposit,
                monthly_rent=monthly_rent,
                contract_type=contract_type,
                floor=floor,
            ))
        logger.info("[JeonseClient] %s → %d건 파싱", district_code, len(results))
        return results
