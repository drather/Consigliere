# tests/modules/real_estate/supply/test_supply_risk_analyzer.py
import sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

from unittest.mock import MagicMock
from modules.real_estate.supply.risk_analyzer import SupplyRiskAnalyzer
from modules.real_estate.supply.repository import SupplyRepository
from modules.real_estate.supply.models import SupplySchedule


def _make_supply_repo(lat=37.5120, lng=127.0986, units=500, expected="2026-10"):
    tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    repo = SupplyRepository(db_path=tf.name)
    if units > 0:
        repo.save(SupplySchedule(
            project_name="잠실파크원", sigungu_code="11710",
            lat=lat, lng=lng, household_count=units,
            expected_date=expected, supply_type="move_in"
        ))
    return repo


def _make_news_service(articles=None):
    svc = MagicMock()
    svc.get_categorized_news.return_value = articles or []
    return svc


def _make_llm(catalysts=None):
    llm = MagicMock()
    llm.generate_json.return_value = {"catalysts": catalysts or []}
    return llm


def _make_prompt_loader():
    loader = MagicMock()
    loader.load.return_value = ({}, "dummy prompt")
    return loader


def test_supply_nearby_units_counted():
    repo = _make_supply_repo(units=500)
    analyzer = SupplyRiskAnalyzer(
        supply_repo=repo, news_service=_make_news_service(),
        llm=_make_llm(), prompt_loader=_make_prompt_loader()
    )
    result = analyzer.analyze(lat=37.5133, lng=127.1001, apt_name="현대7", sigungu="송파구")
    assert result.nearby_units == 500


def test_no_supply_returns_zero():
    tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    empty_repo = SupplyRepository(db_path=tf.name)
    analyzer = SupplyRiskAnalyzer(
        supply_repo=empty_repo, news_service=_make_news_service(),
        llm=_make_llm(), prompt_loader=_make_prompt_loader()
    )
    result = analyzer.analyze(lat=37.5133, lng=127.1001, apt_name="현대7", sigungu="송파구")
    assert result.nearby_units == 0
    assert result.news_catalysts == []


def test_positive_catalyst_from_llm():
    repo = _make_supply_repo(units=0)
    articles = [{"title": "GTX-A 개통 확정", "description": "2027년 개통", "pub_date": "2026-05-10"}]
    catalysts = [{"type": "positive", "title": "GTX-A 개통 확정", "date": "2026-05-10"}]
    analyzer = SupplyRiskAnalyzer(
        supply_repo=repo, news_service=_make_news_service(articles),
        llm=_make_llm(catalysts), prompt_loader=_make_prompt_loader()
    )
    result = analyzer.analyze(lat=37.5133, lng=127.1001, apt_name="현대7", sigungu="송파구")
    assert len(result.news_catalysts) == 1
    assert result.news_catalysts[0]["type"] == "positive"


def test_no_news_returns_empty_catalysts():
    repo = _make_supply_repo(units=0)
    analyzer = SupplyRiskAnalyzer(
        supply_repo=repo, news_service=_make_news_service(articles=[]),
        llm=_make_llm(), prompt_loader=_make_prompt_loader()
    )
    result = analyzer.analyze(lat=37.5133, lng=127.1001, apt_name="현대7", sigungu="송파구")
    assert result.news_catalysts == []
    # 뉴스 없으면 LLM 호출 안 함
    analyzer._llm.generate_json.assert_not_called()
