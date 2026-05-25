# src/modules/real_estate/supply/risk_analyzer.py
from dataclasses import dataclass, field
from typing import List, TYPE_CHECKING
from core.logger import get_logger

if TYPE_CHECKING:
    from modules.real_estate.supply.repository import SupplyRepository
    from modules.real_estate.news.service import NewsService
    from core.llm import BaseLLMClient
    from core.prompt_loader import PromptLoader

logger = get_logger(__name__)


@dataclass
class SupplyRiskResult:
    nearby_units: int
    supply_period: str          # e.g. "2026H2"
    news_catalysts: List[dict] = field(default_factory=list)


def _period_label(expected_dates: List[str]) -> str:
    if not expected_dates:
        return ""
    dates = sorted(expected_dates)
    first = dates[0]
    try:
        year, month = int(first[:4]), int(first[5:7])
        half = "H1" if month <= 6 else "H2"
        return f"{year}{half}"
    except (ValueError, IndexError):
        return first


class SupplyRiskAnalyzer:
    def __init__(
        self,
        supply_repo: "SupplyRepository",
        news_service: "NewsService",
        llm: "BaseLLMClient",
        prompt_loader: "PromptLoader",
        radius_km: float = 2.0,
        months_ahead: int = 12,
    ):
        self._supply_repo = supply_repo
        self._news_service = news_service
        self._llm = llm
        self._prompt_loader = prompt_loader
        self._radius_km = radius_km
        self._months_ahead = months_ahead

    def analyze(self, lat: float, lng: float, apt_name: str, sigungu: str) -> SupplyRiskResult:
        supply_items = self._supply_repo.get_within_radius(
            lat=lat, lng=lng,
            radius_km=self._radius_km,
            months_ahead=self._months_ahead,
        )
        nearby_units = sum(s.household_count for s in supply_items)
        period = _period_label([s.expected_date for s in supply_items])

        articles = self._news_service.get_categorized_news(
            query=f"{apt_name} {sigungu}", display=10
        )
        catalysts = self._classify_catalysts(articles, apt_name, sigungu)

        return SupplyRiskResult(
            nearby_units=nearby_units,
            supply_period=period,
            news_catalysts=catalysts,
        )

    def _classify_catalysts(
        self, articles: List[dict], apt_name: str, sigungu: str
    ) -> List[dict]:
        if not articles:
            return []

        news_list = "\n".join(
            f"{i+1}. [{a.get('pub_date','')}] {a.get('title','')} — {a.get('description','')[:80]}"
            for i, a in enumerate(articles)
        )
        try:
            _, prompt = self._prompt_loader.load(
                "news_catalyst_classifier",
                variables={"apt_name": apt_name, "sigungu": sigungu, "news_list": news_list},
            )
            result = self._llm.generate_json(prompt)
            return result.get("catalysts", [])
        except Exception as e:
            logger.warning("[SupplyRiskAnalyzer] LLM 분류 실패: %s", e)
            return []
