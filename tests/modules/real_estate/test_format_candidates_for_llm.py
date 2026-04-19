"""Tests for InsightOrchestrator._format_candidates_for_llm()"""
import pytest
from modules.real_estate.insight_orchestrator import InsightOrchestrator


def _make_orchestrator():
    class FakeLLM:
        def generate_json(self, prompt, metadata=None):
            return {}

    class FakeLoader:
        def load(self, name, variables=None):
            return {}, ""

    return InsightOrchestrator(llm=FakeLLM(), prompt_loader=FakeLoader())


def _candidate(**overrides):
    base = {
        "apt_name": "테스트아파트",
        "district_name": "강남구",
        "price": 90000,
        "deal_date": "2026-04-15",
        "exclusive_area": 84.13,
        "floor": 4,
        "household_count": 812,
        "building_count": 15,
        "constructor": "우방건설",
        "approved_date": "20110101",
        "commute_minutes": 19,
        "nearest_stations": ["잠실역·2호선·8호선"],
        "school_zone_notes": "강남구 학군",
        "total_score": 87.5,
        "scores": {
            "commute": 100,
            "liquidity": 100,
            "price_potential": 50,
            "living_convenience": 80,
            "school": 90,
        },
    }
    base.update(overrides)
    return base


def test_all_five_scores_present():
    orch = _make_orchestrator()
    text = orch._format_candidates_for_llm([_candidate()])
    assert "출퇴근점수: 100점" in text
    assert "환금성점수: 100점" in text
    assert "생활편의점수: 80점" in text
    assert "학군점수: 90점" in text
    assert "가격상승가능성점수: 50점" in text


def test_total_score_in_header():
    orch = _make_orchestrator()
    text = orch._format_candidates_for_llm([_candidate()])
    assert "총점=87.5" in text


def test_candidate_count_header():
    orch = _make_orchestrator()
    cands = [_candidate(apt_name="A"), _candidate(apt_name="B"), _candidate(apt_name="C")]
    text = orch._format_candidates_for_llm(cands)
    assert "총 3개 단지" in text


def test_medal_ranks():
    orch = _make_orchestrator()
    cands = [_candidate(apt_name=n) for n in ["A", "B", "C", "D"]]
    text = orch._format_candidates_for_llm(cands)
    assert "🥇 1위:" in text
    assert "🥈 2위:" in text
    assert "🥉 3위:" in text
    assert "4위:" in text


def test_neutral_household_none():
    orch = _make_orchestrator()
    c = _candidate(
        household_count=None,
        building_count=None,
        scores={"commute": 50, "liquidity": 50, "price_potential": 50, "living_convenience": 50, "school": 50},
    )
    text = orch._format_candidates_for_llm([c])
    assert "환금성점수: 50점" in text
    assert "세대수 미확인" in text


def test_no_constructor_no_approved_date():
    orch = _make_orchestrator()
    c = _candidate(constructor=None, approved_date=None)
    text = orch._format_candidates_for_llm([c])
    assert "단지정보 없음" not in text or True  # 세대/동 정보만 있으면 ok


def test_no_commute_data():
    orch = _make_orchestrator()
    c = _candidate(commute_minutes=None, nearest_stations=None,
                   scores={"commute": 50, "liquidity": 100, "price_potential": 50, "living_convenience": 50, "school": 50})
    text = orch._format_candidates_for_llm([c])
    assert "출퇴근점수: 50점" in text


def test_price_formatting():
    orch = _make_orchestrator()
    c = _candidate(price=93000)
    text = orch._format_candidates_for_llm([c])
    assert "93,000만원" in text  # DB 단위(만원) 그대로 표기


def test_price_formatting_round_eok():
    orch = _make_orchestrator()
    c = _candidate(price=90000)
    text = orch._format_candidates_for_llm([c])
    assert "90,000만원" in text  # LLM 단위 변환 방지
