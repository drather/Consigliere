"""
ReportOrchestrator — 전문 컨설턴트 리포트 생성 파이프라인.

흐름:
  1. Python: DSR 기반 예산 계산
  2. Python: GeocoderService — road_address → lat/lng (캐시 우선)
  3. Python: PoiCollector — 각 단지 POI 수집 (lat/lng 필수)
  4. Python: BuildingMaster JOIN — 용적률·건폐율·준공연도
  5. Python: CommuteService — TMAP 출퇴근 실측
  6. Python: TrendAnalyzer — 실거래가 추세 집계
  7. Python: ScoringEngine(POI 반영) — 점수 계산
  8. LLM: LocationAgent — 입지 분석 (Top 5 배치)
  9. LLM: SchoolAgent — 학군 분석 (Top 5 배치)
  10. LLM: StrategyAgent — 투자 전략 + 액션 플랜
  11. Markdown 리포트 조립 → ReportRepository 저장
"""
import json
import sqlite3
from datetime import date
from typing import Any, Dict, List, Optional

from core.llm import BaseLLMClient
from core.prompt_loader import PromptLoader
from core.logger import get_logger
from .config import RealEstateConfig
from .poi_collector import PoiCollector, PoiData
from .trend_analyzer import TrendAnalyzer, TrendData
from .scoring import ScoringEngine
from .report_repository import ReportRepository, ProfessionalReport

logger = get_logger(__name__)

def _calc_budget(
    persona_data: Dict,
    macro_summary: str,
    dsr_rate: float = 0.40,
    loan_term_months: int = 360,
) -> int:
    import re
    user = persona_data.get("user", {})
    assets = user.get("assets", {}).get("total", 0)
    annual_income = user.get("income", {}).get("total", 0)

    rate_match = re.search(r"주담대[^\d]*([\d.]+)%", macro_summary)
    annual_rate = float(rate_match.group(1)) / 100 if rate_match else 0.045
    monthly_rate = annual_rate / 12
    monthly_income = annual_income / 12
    max_monthly_payment = monthly_income * dsr_rate

    if monthly_rate > 0:
        loan_limit = max_monthly_payment * (1 - (1 + monthly_rate) ** -loan_term_months) / monthly_rate
    else:
        loan_limit = max_monthly_payment * loan_term_months

    return int(assets + loan_limit)


def _enrich_with_geocode(candidates: List[Dict], geocoder) -> List[Dict]:
    """road_address → GeocoderService → lat/lng 채움.
    이미 lat/lng가 있으면 스킵. geocoder가 None이면 no-op."""
    if geocoder is None:
        return candidates

    hit = skip = miss = 0
    enriched = []
    for c in candidates:
        result = dict(c)
        if c.get("lat") and c.get("lng"):
            skip += 1
            enriched.append(result)
            continue
        road_address = c.get("road_address") or ""
        apt_name = c.get("apt_name", "")
        district_code = c.get("district_code", "")
        if road_address:
            try:
                coords = geocoder.geocode(apt_name, district_code, address=road_address)
                if coords:
                    result["lat"], result["lng"] = coords
                    hit += 1
                else:
                    logger.warning("[Geocode] 좌표 없음: %s / %s", apt_name, road_address)
                    miss += 1
            except Exception as e:
                logger.warning("[Geocode] 실패 %s: %s", apt_name, e)
                miss += 1
        else:
            logger.debug("[Geocode] road_address 없음, 스킵: %s", apt_name)
            miss += 1
        enriched.append(result)

    logger.info("[Geocode] 좌표 수집 완료 — 성공 %d, 기존보유 %d, 실패 %d (전체 %d)", hit, skip, miss, len(candidates))
    return enriched


def _enrich_with_poi(candidates: List[Dict], poi_collector: PoiCollector) -> List[Dict]:
    enriched = []
    hit = skip = 0
    for c in candidates:
        result = dict(c)
        complex_code = c.get("complex_code") or c.get("apt_name", "unknown")
        lat = c.get("lat")
        lng = c.get("lng")
        if lat and lng:
            try:
                poi = poi_collector.collect(complex_code=complex_code, lat=lat, lng=lng)
                result["poi_stations"] = poi.subway_stations
                result["poi_academies_count"] = poi.academies_count
                result["_poi"] = poi
                hit += 1
            except Exception as e:
                logger.warning("[POI] 수집 실패 %s: %s", c.get("apt_name"), e)
                skip += 1
        else:
            logger.debug("[POI] lat/lng 없어 스킵: %s", c.get("apt_name"))
            skip += 1
        enriched.append(result)
    logger.info("[POI] 수집 완료 — 성공 %d, 스킵 %d", hit, skip)
    return enriched


def _enrich_with_building(candidates: List[Dict], db_path: str) -> List[Dict]:
    """pnu → building_master JOIN으로 용적률·건폐율·준공연도를 채운다.
    pnu 없으면 approved_date 앞 4자리에서 build_year를 파생한다."""
    bm_map: Dict[str, Dict] = {}
    if db_path:
        mgm_pk_list = [c.get("pnu") for c in candidates if c.get("pnu")]
        if mgm_pk_list:
            try:
                placeholders = ",".join("?" * len(mgm_pk_list))
                with sqlite3.connect(db_path) as conn:
                    rows = conn.execute(
                        f"SELECT mgm_pk, floor_area_ratio, building_coverage_ratio, completion_year "
                        f"FROM building_master WHERE mgm_pk IN ({placeholders})",
                        mgm_pk_list,
                    ).fetchall()
                bm_map = {
                    r[0]: {
                        "floor_area_ratio": r[1],
                        "building_coverage_ratio": r[2],
                        "build_year": r[3],
                    }
                    for r in rows
                }
                logger.info("[Building] building_master 조회 %d건 → 매칭 %d건", len(mgm_pk_list), len(bm_map))
            except sqlite3.OperationalError as e:
                logger.warning("[Building] building_master 조회 실패 (테이블 없음): %s", e)
            except sqlite3.Error as e:
                logger.error("[Building] building_master DB 오류: %s", e)

    enriched = []
    for c in candidates:
        result = dict(c)
        pnu = c.get("pnu")
        if pnu and pnu in bm_map:
            result.update(bm_map[pnu])
        if not result.get("build_year") and result.get("approved_date"):
            try:
                result["build_year"] = int(str(result["approved_date"])[:4])
            except (ValueError, TypeError):
                pass
        enriched.append(result)
    return enriched


def _resolve_workplace_coords(persona_data: Dict, geocoder) -> tuple:
    """persona의 commute.workplace_station을 lat/lng로 변환.
    실패하면 (None, None, None) 반환."""
    station = persona_data.get("commute", {}).get("workplace_station", "")
    if not station:
        return None, None, None
    try:
        coords = geocoder.geocode(apt_name=station, district_code="", address=station)
    except Exception as e:
        logger.warning("[Orchestrator] workplace_station 좌표 변환 실패 (%s): %s", station, e)
        return None, None, None
    if coords:
        logger.info("[Orchestrator] workplace 좌표: %s → %.4f, %.4f", station, coords[0], coords[1])
        return station, coords[0], coords[1]
    logger.warning("[Orchestrator] workplace_station 좌표 없음: %s — config 기본 목적지 사용", station)
    return None, None, None


def _enrich_with_commute(
    candidates: List[Dict],
    commute_svc,
    dest: Optional[str],
    dest_lat: Optional[float],
    dest_lng: Optional[float],
) -> List[Dict]:
    """각 candidate에 commute_transit_minutes 를 채운다.
    road_address 없어도 geocoder 캐시로 좌표 조회 가능하므로 시도한다.
    CommuteService 예외는 로그 후 무시."""
    enriched = []
    hit = skip = 0
    for c in candidates:
        result = dict(c)
        if commute_svc is not None:
            apt_name = c.get("apt_name", "")
            district_code = c.get("district_code", "")
            road_address = c.get("road_address") or ""
            origin_key = f"{district_code}__{apt_name}"
            try:
                cr = commute_svc.get(
                    origin_key=origin_key,
                    road_address=road_address,
                    apt_name=apt_name,
                    district_code=district_code,
                    mode="transit",
                    dest_override=dest,
                    dest_lat_override=dest_lat,
                    dest_lng_override=dest_lng,
                )
                if cr:
                    result["commute_transit_minutes"] = cr.duration_minutes
                    hit += 1
                else:
                    skip += 1
            except Exception as e:
                logger.warning("[Commute] 실패 %s: %s", c.get("apt_name"), e)
                skip += 1
        else:
            skip += 1
        enriched.append(result)
    logger.info("[Commute] 출퇴근 수집 완료 — 성공 %d, 스킵 %d", hit, skip)
    return enriched


def _enrich_with_trend(
    candidates: List[Dict],
    trend_analyzer: TrendAnalyzer,
    preferred_areas: Optional[List[float]] = None,
) -> List[Dict]:
    """preferred_areas 순서대로 면적대를 시도해 실거래 추세를 채운다.
    preferred_areas 미제공 시 기존 동작(84㎡ 단일) 유지."""
    if preferred_areas is None:
        preferred_areas = [84.0]

    enriched = []
    for c in candidates:
        result = dict(c)
        apt_master_id = c.get("id") or c.get("apt_master_id")

        if apt_master_id:
            try:
                trend = None
                for area in preferred_areas:
                    trend = trend_analyzer.get_trend(apt_master_id=apt_master_id, area_sqm=area)
                    if trend:
                        result["_trend_area_sqm"] = area
                        break
                if trend:
                    result["_trend"] = trend
            except Exception as e:
                logger.warning("[Trend] 추세 실패 %s: %s", c.get("apt_name"), e)
        enriched.append(result)
    return enriched


def _call_location_agent(llm: BaseLLMClient, prompt_loader: PromptLoader, candidates: List[Dict]) -> Dict[str, str]:
    poi_input = [
        {
            "apt_name": c.get("apt_name"),
            "subway_stations": (c.get("_poi") or PoiData()).subway_stations,
            "marts_count": (c.get("_poi") or PoiData()).marts_count,
        }
        for c in candidates
    ]
    poi_json = json.dumps(poi_input, ensure_ascii=False)
    logger.info("[LocationAgent] 입력 단지 수: %d, POI 데이터 있음: %d",
                len(poi_input), sum(1 for c in candidates if c.get("_poi")))
    metadata, prompt = prompt_loader.load("location_analyst", variables={"candidates_poi_json": poi_json})
    try:
        result = llm.generate_json(prompt, metadata=metadata)
        analyses = result.get("analyses", [])
        logger.info("[LocationAgent] 분석 결과 %d건 반환", len(analyses))
        return {a["apt_name"]: a["text"] for a in analyses}
    except Exception as e:
        logger.warning("[LocationAgent] 실패: %s", e)
        return {}


def _call_school_agent(llm: BaseLLMClient, prompt_loader: PromptLoader, candidates: List[Dict]) -> Dict[str, str]:
    school_input = [
        {
            "apt_name": c.get("apt_name"),
            "schools_count": (c.get("_poi") or PoiData()).schools_count,
            "academies_count": (c.get("_poi") or PoiData()).academies_count,
        }
        for c in candidates
    ]
    school_json = json.dumps(school_input, ensure_ascii=False)
    logger.info("[SchoolAgent] 입력 단지 수: %d", len(school_input))
    metadata, prompt = prompt_loader.load("school_analyst", variables={"candidates_school_json": school_json})
    try:
        result = llm.generate_json(prompt, metadata=metadata)
        analyses = result.get("analyses", [])
        logger.info("[SchoolAgent] 분석 결과 %d건 반환", len(analyses))
        return {a["apt_name"]: a["text"] for a in analyses}
    except Exception as e:
        logger.warning("[SchoolAgent] 실패: %s", e)
        return {}


def _call_strategy_agent(
    llm: BaseLLMClient,
    prompt_loader: PromptLoader,
    candidates: List[Dict],
    macro_summary: str,
    budget_available: int,
    persona_data: Dict,
) -> Dict:
    candidates_summary = "\n".join(
        f"- {c.get('apt_name')}: 총점 {c.get('total_score', 0):.1f}점, "
        f"출퇴근 {c.get('commute_transit_minutes', '?')}분"
        for c in candidates[:5]
    )
    budget_str = f"{budget_available / 100_000_000:.1f}억원"
    user_goals = persona_data.get("user", {}).get("plans", {}).get("primary_goal", "실거주 및 투자 가치")

    metadata, prompt = prompt_loader.load("strategy_analyst", variables={
        "macro_summary": macro_summary,
        "budget_summary": f"구매 가능 예산: {budget_str}",
        "user_goals": user_goals,
        "ranked_candidates_summary": candidates_summary,
    })
    try:
        result = llm.generate_json(prompt, metadata=metadata)
        logger.info("[StrategyAgent] 전략 생성 완료 (keys: %s)", list(result.keys()))
        return result
    except Exception as e:
        logger.warning("[StrategyAgent] 실패: %s", e)
        return {"market_diagnosis": "", "strategy": "", "action_short": "", "action_mid": "", "risks": []}


def _build_markdown(
    target_date: date,
    budget_available: int,
    macro_summary: str,
    candidates: List[Dict],
    location_analyses: Dict[str, str],
    school_analyses: Dict[str, str],
    strategy: Dict,
) -> str:
    import datetime as _dt
    lines = []
    date_str = target_date.strftime("%Y-%m-%d")
    budget_str = f"{budget_available / 100_000_000:.1f}억"

    lines.append(f"# Consigliere 부동산 전략 리포트 — {date_str}\n")

    lines.append("## 1. Executive Summary\n")
    lines.append(f"- **구매 가능 예산:** {budget_str}")
    lines.append(f"- **시장 현황:** {macro_summary}")
    top3 = candidates[:3]
    lines.append(f"- **추천 Top 3:** " + " / ".join(f"{c['apt_name']}({c.get('total_score', 0):.0f}점)" for c in top3))
    if strategy.get("action_short"):
        lines.append(f"- **지금 당장 할 일:** {strategy['action_short']}")
    lines.append("")

    lines.append("## 2. 거시경제 컨텍스트\n")
    lines.append(macro_summary or "(거시경제 데이터 없음)")
    if strategy.get("market_diagnosis"):
        lines.append(f"\n{strategy['market_diagnosis']}")
    lines.append("")

    lines.append("## 3. 추천 단지 상세 분석\n")
    for i, c in enumerate(candidates[:5], 1):
        name = c.get("apt_name", "")
        score = c.get("total_score", 0)
        trend: Optional[TrendData] = c.get("_trend")
        poi: Optional[PoiData] = c.get("_poi")

        lines.append(f"### {i}위. {name} — 총점 {score:.0f}/100\n")

        lines.append("**입지 분석**")
        if poi and poi.subway_stations:
            stations_str = ", ".join(f"{s['name']} 도보 {s['walk_minutes']}분" for s in poi.subway_stations[:3])
            lines.append(f"- 역세권: {stations_str}")
            lines.append(f"- 생활편의: 반경 1km 내 대형마트/백화점 {poi.marts_count}개")
        loc_text = location_analyses.get(name, "")
        if loc_text:
            lines.append(f"- {loc_text}")
        lines.append("")

        lines.append("**학군 분석**")
        if poi:
            lines.append(f"- 반경 1km 내 학교 {poi.schools_count}개, 학원 {poi.academies_count}개")
        school_text = school_analyses.get(name, "")
        if school_text:
            lines.append(f"- {school_text}")
        lines.append("")

        lines.append("**실거래가 추세**")
        if trend:
            area_label = f"{c.get('_trend_area_sqm', 84):.0f}㎡"
            lines.append(f"- 6개월 평균가: {trend.avg_price_eok()} ({area_label} 기준)")
            lines.append(f"- 3개월 전 대비: {trend.price_change_str()} / 월 평균 거래량 {trend.monthly_volume:.1f}건")
        else:
            lines.append("- 실거래가 데이터 미수집")
        lines.append("")

        lines.append("**재건축/투자 잠재력**")
        far = c.get("floor_area_ratio")
        build_year = c.get("build_year")
        if far and build_year:
            age = _dt.date.today().year - int(build_year)
            bcr = c.get("building_coverage_ratio", 0)
            lines.append(f"- 건축연도: {build_year}년 ({age}년), 용적률: {far:.0f}%, 건폐율: {bcr:.0f}%")
        scores = c.get("scores", {})
        lines.append(f"- 가격잠재력 점수: {scores.get('price_potential', '-')}점")
        lines.append("")

        commute = c.get("commute_transit_minutes") or c.get("commute_minutes")
        lines.append("**출퇴근** (직장 기준, 캐시)")
        lines.append(f"- 대중교통 {commute or '?'}분")
        lines.append("")

        lines.append("**예산 적합성**")
        if trend and trend.avg_price > 0:
            budget_ok = budget_available >= trend.avg_price
            area_label = f"{c.get('_trend_area_sqm', 84):.0f}㎡"
            lines.append(f"- 최근 실거래가: {trend.avg_price_eok()} ({area_label} 기준) vs 구매 가능 {budget_str}")
            lines.append(f"- {'예산 범위 내' if budget_ok else '예산 초과 — 추가 조달 필요'}")
        else:
            lines.append(f"- 최근 실거래가: 미수집 vs 구매 가능 {budget_str}")
        lines.append("")

    lines.append("## 4. 투자 전략 및 액션 플랜\n")
    if strategy.get("strategy"):
        lines.append(f"**전략:** {strategy['strategy']}\n")
    if strategy.get("action_short"):
        lines.append(f"**단기(3개월):** {strategy['action_short']}\n")
    if strategy.get("action_mid"):
        lines.append(f"**중기(1년):** {strategy['action_mid']}\n")
    if strategy.get("risks"):
        lines.append("**리스크 요인:**")
        for r in strategy["risks"]:
            lines.append(f"- {r}")

    return "\n".join(lines)


class ReportOrchestrator:
    def __init__(
        self,
        llm: BaseLLMClient,
        prompt_loader: PromptLoader,
        poi_collector: PoiCollector,
        trend_analyzer: TrendAnalyzer,
        report_repository: ReportRepository,
        re_db_path: str = "",
        commute_svc=None,
        geocoder=None,
    ):
        self._llm = llm
        self._prompt_loader = prompt_loader
        self._poi_collector = poi_collector
        self._trend_analyzer = trend_analyzer
        self._repo = report_repository
        self._re_db_path = re_db_path
        self._commute_svc = commute_svc
        self._geocoder = geocoder

    def generate(
        self,
        target_date: date,
        candidates: List[Dict[str, Any]],
        persona_data: Dict[str, Any],
        scoring_config: Dict[str, Any],
        macro_summary: str = "",
    ) -> ProfessionalReport:
        financial_cfg = RealEstateConfig().get("financial_defaults", {})
        dsr_rate = financial_cfg.get("dsr_rate", 0.40)
        loan_term_months = int(financial_cfg.get("loan_term_years", 30)) * 12
        budget_available = _calc_budget(persona_data, macro_summary, dsr_rate=dsr_rate, loan_term_months=loan_term_months)
        logger.info("[ReportOrchestrator] 구매 가능 예산: %.1f억, 후보 %d건",
                    budget_available / 100_000_000, len(candidates))

        # road_address → lat/lng (POI 수집 전처리)
        enriched = _enrich_with_geocode(candidates, self._geocoder)
        enriched = _enrich_with_poi(enriched, self._poi_collector)
        enriched = _enrich_with_building(enriched, self._re_db_path)

        if self._commute_svc and self._geocoder:
            dest, dest_lat, dest_lng = _resolve_workplace_coords(persona_data, self._geocoder)
            enriched = _enrich_with_commute(enriched, self._commute_svc, dest, dest_lat, dest_lng)

        preferred_areas = persona_data.get("apartment_preferences", {}).get("preferred_area_sqm", [84.0])
        enriched = _enrich_with_trend(enriched, self._trend_analyzer, preferred_areas=preferred_areas)

        weights = persona_data.get("priority_weights", {})
        scored = ScoringEngine(weights, scoring_config).score_all(enriched)
        top5 = scored[:5]
        logger.info("[ReportOrchestrator] 점수 Top5: %s",
                    [(c.get("apt_name"), c.get("total_score")) for c in top5])

        location_analyses = _call_location_agent(self._llm, self._prompt_loader, top5)
        school_analyses = _call_school_agent(self._llm, self._prompt_loader, top5)
        strategy = _call_strategy_agent(
            self._llm, self._prompt_loader, top5,
            macro_summary, budget_available, persona_data,
        )

        markdown = _build_markdown(
            target_date, budget_available, macro_summary,
            top5, location_analyses, school_analyses, strategy,
        )

        report = ProfessionalReport(
            date=target_date.strftime("%Y-%m-%d"),
            budget_available=budget_available,
            macro_summary=macro_summary,
            candidates_summary=[
                {"apt_name": c["apt_name"], "total_score": c.get("total_score", 0), "scores": c.get("scores", {})}
                for c in top5
            ],
            location_analyses=[{"apt_name": k, "text": v} for k, v in location_analyses.items()],
            school_analyses=[{"apt_name": k, "text": v} for k, v in school_analyses.items()],
            strategy=strategy,
            markdown=markdown,
        )
        self._repo.save(report)
        return report
