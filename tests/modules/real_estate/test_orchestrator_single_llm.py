import pytest
import sys, os
from datetime import date
from unittest.mock import MagicMock, patch
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src"))

from modules.real_estate.insight_orchestrator import InsightOrchestrator
from modules.real_estate.calculator import BudgetPlan


def _make_orchestrator():
    llm = MagicMock()
    llm.generate_json.return_value = {"blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "테스트"}}]}
    prompt_loader = MagicMock()
    prompt_loader.load.return_value = ({"task_type": "synthesis"}, "test prompt")
    return InsightOrchestrator(llm=llm, prompt_loader=prompt_loader), llm


def _make_budget_plan():
    return BudgetPlan(
        available_cash=274_000_000, max_price_ltv=874_000_000, max_price_dsr=950_000_000,
        final_max_price=874_000_000, estimated_loan=600_000_000, estimated_taxes=26_000_000,
        reasoning="테스트 예산 근거",
    )


def test_generate_strategy_calls_llm_exactly_once():
    """LLM은 정확히 1번만 호출된다 (horea_analyst 제거 확인)."""
    orch, llm = _make_orchestrator()
    candidates = [{"apt_name": "테스트아파트", "price": 800_000_000, "district_code": "11680",
                   "exclusive_area": 84.0, "deal_date": "2026-04-15", "floor": 10}]

    orch.generate_strategy(
        target_date=date(2026, 4, 19),
        candidates=candidates,
        budget_plan=_make_budget_plan(),
        persona_data={"priority_weights": {"commute": 3, "liquidity": 2, "price_potential": 2,
                                           "living_convenience": 2, "school": 1}},
        preference_rules=[],
        scoring_config={},
        report_config={"top_n": 5},
        horea_data={},
        macro_summary="- 기준금리: 3.0%\n- 주담대금리: 4.2%",
        horea_text="호재 정보 없음",
    )

    assert llm.generate_json.call_count == 1


def test_generate_strategy_prompt_includes_macro_summary():
    """LLM 호출 시 프롬프트에 macro_summary가 전달된다."""
    orch, llm = _make_orchestrator()
    candidates = [{"apt_name": "테스트아파트", "price": 800_000_000, "district_code": "11680",
                   "exclusive_area": 84.0, "deal_date": "2026-04-15", "floor": 10}]

    orch.generate_strategy(
        target_date=date(2026, 4, 19),
        candidates=candidates,
        budget_plan=_make_budget_plan(),
        persona_data={"priority_weights": {"commute": 3, "liquidity": 2, "price_potential": 2,
                                           "living_convenience": 2, "school": 1}},
        preference_rules=[],
        scoring_config={},
        report_config={"top_n": 5},
        horea_data={},
        macro_summary="기준금리 3.0%",
        horea_text="호재 없음",
    )

    call_args = orch.prompt_loader.load.call_args
    variables = call_args.kwargs.get("variables", {})
    assert "macro_summary" in variables
    assert "기준금리 3.0%" in variables["macro_summary"]


def test_generate_strategy_empty_candidates_returns_empty_report():
    orch, llm = _make_orchestrator()
    result = orch.generate_strategy(
        target_date=date(2026, 4, 19),
        candidates=[],
        budget_plan=_make_budget_plan(),
        persona_data={"priority_weights": {}},
        preference_rules=[],
        scoring_config={},
        report_config={"top_n": 5},
        horea_data={},
        macro_summary="",
        horea_text="",
    )
    assert "blocks" in result
    llm.generate_json.assert_not_called()
