import os
from datetime import datetime, timezone
from typing import Optional

from .formatter import format_slack, format_markdown
from .models import AptAnalysisReport

try:
    from core.logger import get_logger
except ImportError:
    import logging
    def get_logger(name): return logging.getLogger(name)

logger = get_logger(__name__)


class AptAnalysisOrchestrator:
    def __init__(
        self,
        apt_master_repo,
        apt_details_repo,
        tx_repo,
        jeonse_repo,
        supply_repo,
        location_service,
        macro_svc,
        commute_repo,
        llm,
        geocoder=None,
        news_service=None,
        prompt_loader=None,
    ):
        self._apt_master_repo = apt_master_repo
        self._apt_details_repo = apt_details_repo
        self._tx_repo = tx_repo
        self._jeonse_repo = jeonse_repo
        self._supply_repo = supply_repo
        self._location_service = location_service
        self._macro_svc = macro_svc
        self._commute_repo = commute_repo
        self._llm = llm
        self._geocoder = geocoder
        self._news_service = news_service
        self._prompt_loader = prompt_loader

    def analyze(self, complex_code: str) -> AptAnalysisReport:
        apt_entry = self._apt_master_repo.get_by_complex_code(complex_code)
        if apt_entry is None:
            raise ValueError(f"단지 코드 없음: {complex_code}")

        apt_name = apt_entry.apt_name
        district_code = apt_entry.district_code

        price_history = self._collect_price_history(complex_code)
        jeonse_ratio = self._calc_jeonse_ratio(apt_name, district_code, price_history)
        supply_risk_summary = self._get_supply_risk(apt_entry)
        commute_summary = self._get_commute_summary(district_code, apt_name)
        location_score = self._get_location_score(complex_code, apt_entry, commute_summary)
        macro_snapshot = self._macro_svc.fetch_latest_macro_data()

        prompt = self._build_prompt(
            apt_name=apt_name,
            price_history=price_history,
            jeonse_ratio=jeonse_ratio,
            supply_risk_summary=supply_risk_summary,
            location_score=location_score,
            commute_summary=commute_summary,
            macro_snapshot=macro_snapshot,
        )
        llm_insight = self._llm.generate(prompt)

        generated_at = datetime.now(timezone.utc).isoformat()

        report = AptAnalysisReport(
            complex_code=complex_code,
            apt_name=apt_name,
            generated_at=generated_at,
            price_history=price_history,
            jeonse_ratio=jeonse_ratio,
            supply_risk_summary=supply_risk_summary,
            location_score=location_score,
            commute_summary=commute_summary,
            macro_snapshot=macro_snapshot,
            llm_insight=llm_insight,
            slack_text="",
            markdown_text="",
        )
        report.slack_text = format_slack(report)
        report.markdown_text = format_markdown(report)
        return report

    def _collect_price_history(self, complex_code: str) -> list:
        txs = self._tx_repo.get_by_complex(complex_code)
        return [
            {"date": t.deal_date, "price": t.price, "area": t.exclusive_area}
            for t in txs
        ]

    def _calc_jeonse_ratio(self, apt_name: str, district_code: str, price_history: list) -> Optional[float]:
        if not price_history:
            return None
        # jeonse_transactions.complex_code는 항상 NULL (JeonseClient 미설정) → apt_name+district_code로 매칭
        jeonse_txs = self._jeonse_repo.get_by_apt_name(apt_name, district_code)
        jeonse_only = [t for t in jeonse_txs if getattr(t, "contract_type", "jeonse") == "jeonse"]
        if not jeonse_only:
            return None
        avg_sale_man = sum(p["price"] for p in price_history) / len(price_history) / 10000  # 원 → 만원
        avg_jeonse_man = sum(t.deposit for t in jeonse_only) / len(jeonse_only)
        if avg_sale_man == 0:
            return None
        return round(avg_jeonse_man / avg_sale_man * 100, 1)

    def _get_supply_risk(self, apt_entry) -> Optional[str]:
        try:
            from modules.real_estate.supply.risk_analyzer import SupplyRiskAnalyzer
        except ImportError:
            try:
                from src.modules.real_estate.supply.risk_analyzer import SupplyRiskAnalyzer
            except ImportError:
                return None

        apt_details = self._apt_details_repo.get(getattr(apt_entry, "complex_code", None))
        if apt_details is None:
            return None

        road_address = getattr(apt_details, "road_address", "") or ""
        sigungu = getattr(apt_details, "sigungu", "") or ""
        apt_name = getattr(apt_entry, "apt_name", "")

        try:
            from modules.real_estate.geocoder import GeocoderService
            geocoder = self._geocoder
            if geocoder is None:
                geocoder = GeocoderService(
                    api_key=os.getenv("KAKAO_API_KEY", ""),
                    cache_path=os.getenv("GEOCODE_CACHE_PATH", "data/geocode_cache.db"),
                )
            coords = geocoder.geocode(apt_name, getattr(apt_entry, "district_code", ""), address=road_address)
            if coords is None:
                return None
            lat, lng = coords
            analyzer = SupplyRiskAnalyzer(
                supply_repo=self._supply_repo,
                news_service=self._news_service,
                llm=self._llm,
                prompt_loader=self._prompt_loader,
            )
            result = analyzer.analyze(lat=lat, lng=lng, apt_name=apt_name, sigungu=sigungu)
            return f"반경 3km 공급 {result.nearby_units:,}세대 ({result.supply_period}) — {self._risk_level(result.nearby_units)}"
        except Exception as e:
            logger.warning("[AptAnalysisOrchestrator] supply_risk 계산 실패 (None 반환): %s", e)
            return None

    @staticmethod
    def _risk_level(units: int) -> str:
        if units >= 5000:
            return "위험"
        if units >= 2000:
            return "주의"
        return "안전"

    def _get_location_score(self, complex_code: str, apt_entry, commute_summary: Optional[dict]):
        score = self._location_service.get_score(complex_code)
        if score is None:
            candidate = self._build_location_candidate(complex_code, apt_entry, commute_summary)
            try:
                score = self._location_service.enrich_and_save(complex_code, candidate)
            except Exception as e:
                logger.warning("[AptAnalysis] 입지 점수 계산 실패 %s: %s", complex_code, e)
                return None
        return {
            "residential_total": score.residential_total,
            "investment_total": score.investment_total,
            "results": {
                "residential": [{"label": dr.label, "score": dr.score} for dr in score.residential_results],
                "investment": [{"label": dr.label, "score": dr.score} for dr in score.investment_results],
            },
        }

    def _build_location_candidate(self, complex_code: str, apt_entry, commute_summary: Optional[dict]) -> dict:
        """POI 캐시 + 통근 데이터 + 단지 정보로 LocationScorer 입력 candidate를 구성한다."""
        candidate: dict = {"complex_code": complex_code}
        if apt_entry.household_count is not None:
            candidate["household_count"] = apt_entry.household_count

        poi = self._location_service.get_poi_cached(complex_code)
        if poi is not None:
            candidate.update({
                "poi_stations": poi.subway_stations,
                "poi_schools_count": poi.schools_count,
                "poi_academies_count": poi.academies_count,
                "poi_marts_count": poi.marts_count,
                "poi_convenience_count": poi.convenience_count,
                "poi_pharmacy_count": poi.pharmacy_count,
                "poi_medical_count": poi.medical_count,
                "poi_park_nearest_m": poi.park_nearest_m,
                "poi_restaurant_count": poi.restaurant_count,
                "poi_cafe_count": poi.cafe_count,
            })

        if commute_summary and commute_summary.get("transit") is not None:
            candidate["commute_transit_minutes"] = commute_summary["transit"]

        return candidate

    def _get_commute_summary(self, district_code: str, apt_name: str) -> Optional[dict]:
        origin_key = f"{district_code}__{apt_name}"
        cached = self._commute_repo.get_all_by_origin(origin_key)
        if not cached:
            return None
        return {r.mode: r.duration_minutes for r in cached}

    def _build_prompt(self, apt_name, price_history, jeonse_ratio, supply_risk_summary,
                      location_score, commute_summary, macro_snapshot) -> str:
        lines = [
            f"## 단지: {apt_name}",
            "",
            "### 실거래가 히스토리 (최근 거래 기준)",
        ]
        for p in price_history[:10]:
            lines.append(f"- {p['date']}: {p['price']:,}원 ({p['area']}㎡)")

        lines += [
            "",
            f"### 전세가율: {jeonse_ratio:.1f}%" if jeonse_ratio else "### 전세가율: 데이터 없음",
            "",
            f"### 공급 리스크: {supply_risk_summary}" if supply_risk_summary else "### 공급 리스크: 데이터 없음",
            "",
        ]

        if location_score:
            lines.append(f"### 입지 점수: 실거주 {location_score['residential_total']}점 / 투자 {location_score['investment_total']}점")

        if commute_summary:
            commute_str = " | ".join(f"{k}: {v}분" for k, v in commute_summary.items())
            lines.append(f"### 출퇴근(삼성역 기준): {commute_str}")

        rate = macro_snapshot.get("base_rate", {})
        if rate:
            lines.append(f"### 기준금리: {rate.get('value', '-')}%")

        lines += [
            "",
            "위 데이터를 종합하여 이 아파트 단지의 실거주·투자 가치를 한국어로 심층 분석하세요.",
            "강점, 약점, 매수 타이밍, 리스크 요인을 포함한 종합 의견을 작성하세요.",
        ]
        return "\n".join(lines)
