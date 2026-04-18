import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src"))

from modules.real_estate.service import RealEstateAgent


def _make_agent():
    agent = object.__new__(RealEstateAgent)
    return agent


MACRO_DATA = {
    "base_rate": {"name": "기준금리", "value": 3.0, "unit": "%", "date": "2026-04"},
    "loan_rate": {"name": "주담대금리", "value": 4.2, "unit": "%", "date": "2026-04"},
    "m2_growth": {"name": "M2", "value": 4200000, "unit": "십억원", "date": "2026-04"},
}


def test_format_macro_summary_contains_base_rate():
    agent = _make_agent()
    summary = agent._format_macro_summary(MACRO_DATA)
    assert "3.0" in summary
    assert "기준금리" in summary


def test_format_macro_summary_contains_loan_rate():
    agent = _make_agent()
    summary = agent._format_macro_summary(MACRO_DATA)
    assert "4.2" in summary
    assert "주담대" in summary


def test_format_macro_summary_empty_returns_empty():
    agent = _make_agent()
    assert agent._format_macro_summary({}) == ""
    assert agent._format_macro_summary(None) == ""


def test_extract_horea_data_finds_gtx():
    agent = _make_agent()
    news = "GTX-A 수서역 착공 소식이 전해졌다. 송파구 잠실 일대 수혜 예상."
    result = agent._extract_horea_data(news, ["송파구"])
    assert "송파구" in result
    assert result["송파구"]["gtx"] is True
    assert len(result["송파구"]["items"]) > 0


def test_extract_horea_data_finds_reconstruction():
    agent = _make_agent()
    news = "서초구 반포주공 재건축 사업 인허가 완료. 2030년 완공 예정."
    result = agent._extract_horea_data(news, ["서초구"])
    assert "서초구" in result
    assert len(result["서초구"]["items"]) > 0


def test_extract_horea_data_no_match_returns_empty():
    agent = _make_agent()
    news = "코스피가 하락했다."
    result = agent._extract_horea_data(news, ["송파구"])
    assert result == {}


def test_extract_horea_data_formats_for_prompt():
    agent = _make_agent()
    news = "GTX-A 수서역 착공 확정. 송파구 수혜 기대."
    result = agent._extract_horea_data(news, ["송파구"])
    text = agent._horea_data_to_text(result)
    assert "송파구" in text
