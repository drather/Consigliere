import os
import sys
import pytest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src"))

from modules.real_estate.commute.models import CommuteResult
from modules.real_estate.service import RealEstateAgent


def _make_agent_with_commute(commute_results: dict):
    """commute_service.get_all_modes가 commute_results를 반환하는 가짜 agent 생성."""
    agent = object.__new__(RealEstateAgent)

    mock_apt_repo = MagicMock()
    mock_apt_repo.get_by_name.return_value = None

    mock_apt_master_repo = MagicMock()
    mock_apt_master_repo.get_by_name.return_value = None

    mock_commute = MagicMock()
    mock_commute.get_all_modes.return_value = commute_results

    agent.apt_repo = mock_apt_repo
    agent.apt_master_repo = mock_apt_master_repo
    agent.commute_service = mock_commute
    return agent


def _make_tx(apt_name="테스트아파트", district_code="11710"):
    return {"apt_name": apt_name, "district_code": district_code, "price": 500_000_000}


class TestEnrichTransactionsCommute:
    def test_transit_minutes_attached_from_commute_service(self):
        """commute_service 결과가 commute_transit_minutes로 붙어야 한다."""
        results = {
            "transit": CommuteResult("k", "삼성역", "transit", 59, 1200),
            "car": CommuteResult("k", "삼성역", "car", 35, 15000),
            "walking": CommuteResult("k", "삼성역", "walking", 90, 5000),
        }
        agent = _make_agent_with_commute(results)
        enriched = agent._enrich_transactions([_make_tx()], area_intel={})

        tx = enriched[0]
        assert tx["commute_transit_minutes"] == 59
        assert tx["commute_car_minutes"] == 35
        assert tx["commute_walk_minutes"] == 90
        assert tx.get("commute_minutes") == 59  # 하위호환 fallback

    def test_partial_commute_result_no_crash(self):
        """일부 모드 실패(dict 키 없음)여도 enrich가 크래시 나지 않아야 한다."""
        results = {
            "transit": CommuteResult("k", "삼성역", "transit", 59, 0),
        }
        agent = _make_agent_with_commute(results)
        enriched = agent._enrich_transactions([_make_tx()], area_intel={})
        tx = enriched[0]
        assert tx["commute_transit_minutes"] == 59
        assert tx.get("commute_car_minutes") is None

    def test_commute_service_failure_sets_none(self):
        """commute_service가 빈 dict 반환 시 필드가 None으로 설정된다."""
        agent = _make_agent_with_commute({})
        enriched = agent._enrich_transactions([_make_tx()], area_intel={})
        tx = enriched[0]
        assert tx.get("commute_transit_minutes") is None
        assert tx.get("commute_minutes") is None
