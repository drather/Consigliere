from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

import yaml
import os

from core.llm import BaseLLMClient
from core.prompt_loader import PromptLoader
from core.logger import get_logger
from modules.real_estate.report_orchestrator import (
    _enrich_with_geocode,
    _enrich_with_poi,
    _enrich_with_building,
    _enrich_with_trend,
    _resolve_workplace_coords,
)
from modules.real_estate.location.location_scorer import LocationScorer
from modules.real_estate.trend_analyzer import TrendAnalyzer
from modules.real_estate.poi_collector import PoiCollector
from modules.real_estate.daily_report.report_formatter import build_markdown
from .models import DailyReport
from .transaction_aggregator import TransactionAggregator
from .daily_report_repository import DailyReportRepository

logger = get_logger(__name__)

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.yaml")


def _load_scorer() -> Optional[LocationScorer]:
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            full_cfg = yaml.safe_load(f) or {}
        return LocationScorer(config=full_cfg.get("scoring", {}))
    except Exception as e:
        logger.warning("[DailyOrchestrator] LocationScorer 초기화 실패, 점수 생략: %s", e)
        return None


def _format_candidate_for_llm(c: Dict) -> str:
    lines = [f"### {c.get('apt_name', '?')} ({c.get('sigungu', '')})"]
    lines.append(
        f"- 최근 거래: {c.get('recent_tx_count', 0)}건, "
        f"평균 {c.get('avg_recent_price', 0) / 10000:.0f}만원, "
        f"전월比 {c.get('price_change_pct', 0):+.1f}%"
    )
    lines.append(
        f"- 면적: {c.get('exclusive_area', 84):.0f}㎡, "
        f"세대수: {c.get('household_count', 0)}세대"
    )
    if c.get("build_year"):
        lines.append(
            f"- 준공: {c['build_year']}년, "
            f"용적률: {c.get('floor_area_ratio', '?')}%, "
            f"건폐율: {c.get('building_coverage_ratio', '?')}%"
        )
    commute = c.get("commute_transit_minutes")
    lines.append(f"- 출퇴근(대중교통): {'미수집' if commute is None else f'{commute}분'}")
    poi = c.get("_poi")
    if poi:
        stations = poi.subway_stations[:2] if hasattr(poi, "subway_stations") else []
        station_str = ", ".join(
            f"{s.get('name', '?')}({s.get('line', '?')})" for s in stations
        ) or "없음"
        lines.append(f"- 역세권: {station_str}")
        lines.append(
            f"- 학교 {poi.schools_count}개, 학원 {poi.academies_count}개, 마트 {poi.marts_count}개"
        )
    trend = c.get("_trend")
    if trend:
        lines.append(
            f"- 시세추세({c.get('_trend_area_sqm', 84):.0f}㎡): "
            f"평균 {trend.avg_price / 10000:.0f}만원, "
            f"변동 {trend.price_change_pct:+.1f}%, "
            f"월거래량 {trend.monthly_volume:.1f}건"
        )
    return "\n".join(lines)


class DailyReportOrchestrator:
    def __init__(
        self,
        llm: BaseLLMClient,
        prompt_loader: PromptLoader,
        aggregator: TransactionAggregator,
        report_repo: DailyReportRepository,
        db_path: str = "data/real_estate.db",
        poi_collector: Optional[PoiCollector] = None,
        trend_analyzer: Optional[TrendAnalyzer] = None,
        commute_svc=None,
        geocoder=None,
        max_new_commute_api_calls: int = 5,
    ):
        self._llm = llm
        self._prompt_loader = prompt_loader
        self._aggregator = aggregator
        self._repo = report_repo
        self._db_path = db_path
        self._poi_collector = poi_collector
        self._trend_analyzer = trend_analyzer
        self._commute_svc = commute_svc
        self._geocoder = geocoder
        self._max_new_commute_api_calls = max_new_commute_api_calls

    def generate(
        self,
        target_date: date,
        days: int = 3,
        top_k: int = 5,
        persona: Optional[Dict] = None,
        macro_summary: str = "",
        budget_available: int = 0,
    ) -> DailyReport:
        persona = persona or {}
        date_str = target_date.isoformat()

        # Step 1. 거래 집계
        candidates = self._aggregator.aggregate(
            days=days, top_k=top_k * 3, persona=persona, budget_available=budget_available
        )

        if not candidates:
            logger.warning("[DailyOrchestrator] 최근 %d일 거래 없음", days)
            return self._empty_report(date_str, days, macro_summary)

        logger.info("[DailyOrchestrator] 집계 완료 — %d개 단지", len(candidates))

        # Step 3. Enrich pipeline
        candidates = _enrich_with_geocode(candidates, self._geocoder)
        if self._poi_collector:
            candidates = _enrich_with_poi(candidates, self._poi_collector)
        candidates = _enrich_with_building(candidates, self._db_path)
        if self._commute_svc and self._geocoder:
            dest, dest_lat, dest_lng = _resolve_workplace_coords(persona, self._geocoder)
            candidates = self._enrich_with_commute_quota(
                candidates, dest, dest_lat, dest_lng, self._max_new_commute_api_calls
            )
        if self._trend_analyzer:
            preferred_areas = (
                persona.get("apartment_preferences", {}).get("preferred_area_sqm", [84.0])
            )
            candidates = _enrich_with_trend(candidates, self._trend_analyzer, preferred_areas=preferred_areas)

        # Step 4. LocationScorer 실행 — evidence 포함 DimensionResult 생성
        scorer = _load_scorer()
        if scorer:
            for c in candidates:
                try:
                    c["_location_score"] = scorer.score(c)
                except Exception as e:
                    logger.warning("[DailyOrchestrator] scorer.score 실패 %s: %s", c.get("apt_name"), e)

        # Step 5. LLM 분석
        candidates_text = "\n\n".join(_format_candidate_for_llm(c) for c in candidates)
        budget_str = f"{budget_available / 10000:.0f}만원" if budget_available > 0 else "미설정"
        preferred_area = persona.get("apartment_preferences", {}).get("preferred_area_sqm", [84])[0]
        date_from = (target_date - timedelta(days=days)).isoformat()
        date_range = f"{date_from} ~ {date_str}"

        metadata, prompt = self._prompt_loader.load(
            "daily_strategy",
            variables={
                "date_range": date_range,
                "budget_str": budget_str,
                "workplace_station": persona.get("commute", {}).get("workplace_station", "미설정"),
                "preferred_area": preferred_area,
                "investment_style": persona.get("investment_style", "미설정"),
                "macro_summary": macro_summary or "거시경제 데이터 없음",
                "candidate_count": len(candidates),
                "candidates_text": candidates_text,
            },
        )
        try:
            llm_result = self._llm.generate_json(prompt, metadata=metadata)
            market_bullets = llm_result.get("market_bullets", [])
            market_summary = "\n".join(f"- {b}" for b in market_bullets) if market_bullets else ""
            candidate_insights = llm_result.get("candidate_insights", [])
        except Exception as e:
            logger.warning("[DailyOrchestrator] LLM 실패: %s", e)
            market_summary = ""
            candidate_insights = []

        # Step 6. Markdown 조립 — report_formatter에 완전 위임
        insights_map = {i.get("apt_name", ""): i for i in candidate_insights}
        markdown = build_markdown(
            date_str=date_str,
            date_range=date_range,
            macro_summary=macro_summary,
            market_summary=market_summary,
            candidates=candidates,
            insights_map=insights_map,
        )

        # Step 7. 직렬화 가능한 candidates
        serializable_candidates = [
            {k: v for k, v in c.items() if not k.startswith("_")}
            for c in candidates
        ]

        report = DailyReport(
            date=date_str,
            analysis_period=date_range,
            total_transactions=sum(c.get("recent_tx_count", 0) for c in candidates),
            top_k=len(candidates),
            macro_summary=macro_summary,
            market_summary=market_summary,
            candidates=serializable_candidates,
            markdown=markdown,
            generated_at=datetime.now().isoformat(),
        )

        self._repo.save(report)
        return report

    def _enrich_with_commute_quota(
        self,
        candidates: List[Dict],
        dest: Optional[str],
        dest_lat: Optional[float],
        dest_lng: Optional[float],
        max_new_calls: int,
    ) -> List[Dict]:
        """TMAP API 신규 호출을 max_new_calls 이내로 제한한다."""
        if not self._commute_svc or dest is None:
            return candidates

        new_calls_used = 0
        enriched = []
        for c in candidates:
            result = dict(c)
            road_address = c.get("road_address") or ""
            if not road_address:
                enriched.append(result)
                continue

            apt_name = c.get("apt_name", "")
            district_code = c.get("district_code", "")
            origin_key = f"{district_code}__{apt_name}"

            cached = self._commute_svc.get_cached(origin_key, dest, "transit")
            if cached is not None:
                result["commute_transit_minutes"] = cached.duration_minutes
                result["_commute_route_summary"] = cached.route_summary
                logger.debug("[DailyOrchestrator] 출퇴근 캐시 히트: %s", apt_name)
            elif new_calls_used < max_new_calls:
                try:
                    cr = self._commute_svc.get(
                        origin_key=origin_key,
                        road_address=road_address,
                        apt_name=apt_name,
                        district_code=district_code,
                        mode="transit",
                        dest_override=dest,
                        dest_lat_override=dest_lat,
                        dest_lng_override=dest_lng,
                    )
                    new_calls_used += 1
                    if cr:
                        result["commute_transit_minutes"] = cr.duration_minutes
                        result["_commute_route_summary"] = cr.route_summary
                    else:
                        logger.warning(
                            "[DailyOrchestrator] 출퇴근 결과 없음 (quota 소모됨): %s", apt_name
                        )
                    logger.info(
                        "[DailyOrchestrator] 출퇴근 API 호출 %d/%d: %s",
                        new_calls_used, max_new_calls, apt_name,
                    )
                except Exception as e:
                    logger.warning("[DailyOrchestrator] Commute 실패 %s: %s", apt_name, e)
            else:
                logger.info(
                    "[DailyOrchestrator] 출퇴근 quota 소진 (%d/%d), 스킵: %s",
                    new_calls_used, max_new_calls, apt_name,
                )

            enriched.append(result)
        return enriched

    def _empty_report(self, date_str: str, days: int, macro_summary: str) -> DailyReport:
        markdown = (
            f"# 데일리 부동산 브리핑 — {date_str}\n\n"
            f"최근 {days}일 간 분석 가능한 실거래 데이터가 없습니다.\n"
        )
        report = DailyReport(
            date=date_str,
            analysis_period=f"최근 {days}일",
            total_transactions=0,
            top_k=0,
            macro_summary=macro_summary,
            market_summary="",
            candidates=[],
            markdown=markdown,
            generated_at=datetime.now().isoformat(),
        )
        self._repo.save(report)
        return report
