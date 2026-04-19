import sys, os, pytest, json
from datetime import date
from unittest.mock import MagicMock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src"))

from modules.real_estate.insight_orchestrator import InsightOrchestrator
from modules.real_estate.calculator import BudgetPlan


def _make_orchestrator(horea_response=None):
    llm = MagicMock()
    horea_result = horea_response or {
        "horea_assessments": {
            "강남구": {"score": 75, "verdict": "ACTIVE", "reasoning": "재건축 인허가"}
        }
    }
    synth_result = {"blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "리포트"}}]}
    llm.generate_json.side_effect = [horea_result, synth_result]

    prompt_loader = MagicMock()
    prompt_loader.load.return_value = ({"task_type": "test"}, "test prompt")
    return InsightOrchestrator(llm=llm, prompt_loader=prompt_loader), llm


def _make_budget():
    return BudgetPlan(
        available_cash=274_000_000, max_price_ltv=874_000_000,
        max_price_dsr=950_000_000, final_max_price=874_000_000,
        estimated_loan=600_000_000, estimated_taxes=26_000_000,
        reasoning="테스트",
    )


SAMPLE_ARTICLES = [
    {"title": "강남구 재건축 인허가", "url": "http://a.com", "description": "강남구 일대...", "pub_date": "Sat, 19 Apr 2026 09:00:00 +0900"}
]

SAMPLE_CANDIDATES = [
    {"apt_name": "강남아파트", "price": 800_000_000, "district_code": "11680",
     "district_name": "강남구", "exclusive_area": 84.0, "deal_date": "2026-04-15", "floor": 10,
     "reconstruction_potential": "UNKNOWN"}
]


def test_validate_horea_called_when_articles_provided():
    """news_articles가 있으면 horea_validator LLM이 호출된다."""
    orch, llm = _make_orchestrator()
    orch.generate_strategy(
        target_date=date(2026, 4, 19),
        candidates=SAMPLE_CANDIDATES,
        budget_plan=_make_budget(),
        persona_data={"priority_weights": {"commute": 3, "liquidity": 2, "price_potential": 2,
                                           "living_convenience": 2, "school": 1},
                      "user": {"interest_areas": ["강남구"]}},
        preference_rules=[],
        scoring_config={"data_absent_neutral": 50, "reconstruction_score_map": {"UNKNOWN": 50}},
        report_config={"top_n": 5},
        horea_data={},
        macro_summary="",
        horea_text="",
        news_articles=SAMPLE_ARTICLES,
    )
    assert llm.generate_json.call_count == 2  # horea_validator + synthesizer


def test_validate_horea_skipped_when_no_articles():
    """news_articles=None이면 horea_validator를 건너뛰고 LLM 1회만 호출."""
    orch, llm = _make_orchestrator()
    synth_result = {"blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "리포트"}}]}
    llm.generate_json.side_effect = [synth_result]

    orch.generate_strategy(
        target_date=date(2026, 4, 19),
        candidates=SAMPLE_CANDIDATES,
        budget_plan=_make_budget(),
        persona_data={"priority_weights": {"commute": 3, "liquidity": 2, "price_potential": 2,
                                           "living_convenience": 2, "school": 1},
                      "user": {"interest_areas": ["강남구"]}},
        preference_rules=[],
        scoring_config={"data_absent_neutral": 50, "reconstruction_score_map": {"UNKNOWN": 50}},
        report_config={"top_n": 5},
        horea_data={},
        macro_summary="",
        horea_text="",
        news_articles=None,
    )
    assert llm.generate_json.call_count == 1  # synthesizer only


def test_horea_scores_affect_price_potential():
    """horea_validator 결과가 price_potential 점수에 반영된다."""
    orch, llm = _make_orchestrator(horea_response={
        "horea_assessments": {"강남구": {"score": 100, "verdict": "ACTIVE", "reasoning": "GTX"}}
    })
    result = orch.generate_strategy(
        target_date=date(2026, 4, 19),
        candidates=SAMPLE_CANDIDATES,
        budget_plan=_make_budget(),
        persona_data={"priority_weights": {"commute": 1, "liquidity": 1, "price_potential": 10,
                                           "living_convenience": 1, "school": 1},
                      "user": {"interest_areas": ["강남구"]}},
        preference_rules=[],
        scoring_config={"data_absent_neutral": 50, "reconstruction_score_map": {"UNKNOWN": 50}},
        report_config={"top_n": 5},
        horea_data={},
        macro_summary="",
        horea_text="",
        news_articles=SAMPLE_ARTICLES,
    )
    assert "blocks" in result
    # synthesizer가 2번째 호출됨을 확인
    assert llm.generate_json.call_count == 2


def test_horea_validator_failure_falls_back_gracefully():
    """horea_validator LLM 실패 시 synthesizer는 여전히 호출된다."""
    llm = MagicMock()
    synth_result = {"blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "리포트"}}]}
    llm.generate_json.side_effect = [Exception("LLM 오류"), synth_result]

    prompt_loader = MagicMock()
    prompt_loader.load.return_value = ({"task_type": "test"}, "test prompt")
    orch = InsightOrchestrator(llm=llm, prompt_loader=prompt_loader)

    result = orch.generate_strategy(
        target_date=date(2026, 4, 19),
        candidates=SAMPLE_CANDIDATES,
        budget_plan=_make_budget(),
        persona_data={"priority_weights": {"commute": 1, "liquidity": 1, "price_potential": 1,
                                           "living_convenience": 1, "school": 1},
                      "user": {"interest_areas": ["강남구"]}},
        preference_rules=[],
        scoring_config={"data_absent_neutral": 50, "reconstruction_score_map": {"UNKNOWN": 50}},
        report_config={"top_n": 5},
        horea_data={},
        macro_summary="",
        horea_text="",
        news_articles=SAMPLE_ARTICLES,
    )
    assert "blocks" in result
