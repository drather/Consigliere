"""
TDD: 1-A — _enrich_transactions()에서 constructor/approved_date가 후보 dict에 포함되는지 검증
"""
import os
import sys
import pytest
from unittest.mock import MagicMock
from datetime import timezone, datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src')))

from modules.real_estate.models import ApartmentMaster, AptMasterEntry
from modules.real_estate.apartment_repository import ApartmentRepository
from modules.real_estate.apt_master_repository import AptMasterRepository


def _make_agent_with_master(master: ApartmentMaster):
    """RealEstateAgent를 최소한으로 stub해서 apt_repo / apt_master_repo 제어."""
    from modules.real_estate.service import RealEstateAgent

    apt_repo = ApartmentRepository(db_path=":memory:")
    apt_master_repo = AptMasterRepository(db_path=":memory:")

    if master is not None:
        apt_repo.save(master)
        apt_master_repo.upsert(AptMasterEntry(
            apt_name=master.apt_name,
            district_code=master.district_code,
            complex_code=master.complex_code,
            created_at=datetime.now(timezone.utc).isoformat(),
        ))

    agent = object.__new__(RealEstateAgent)
    agent.apt_repo = apt_repo
    agent.apt_master_repo = apt_master_repo
    return agent


def _sample_master(household_count=2444, constructor="삼성물산", approved_date="20090101"):
    return ApartmentMaster(
        apt_name="래미안퍼스티지",
        district_code="11650",
        complex_code="A12345",
        household_count=household_count,
        building_count=36,
        parking_count=0,
        constructor=constructor,
        approved_date=approved_date,
    )


def _sample_tx(apt_name="래미안퍼스티지", district_code="11650"):
    return {
        "apt_name": apt_name,
        "district_code": district_code,
        "price": 2_000_000_000,
        "deal_date": "2026-04-01",
        "floor": 10,
    }


class TestEnrichConstructor:
    def test_constructor_attached_to_tx(self):
        """마스터 조회 성공 시 constructor 필드가 tx에 부착된다."""
        agent = _make_agent_with_master(_sample_master(constructor="삼성물산"))
        result = agent._enrich_transactions([_sample_tx()], area_intel={})
        assert result[0]["constructor"] == "삼성물산"

    def test_approved_date_attached_to_tx(self):
        """마스터 조회 성공 시 approved_date 필드가 tx에 부착된다."""
        agent = _make_agent_with_master(_sample_master(approved_date="20090101"))
        result = agent._enrich_transactions([_sample_tx()], area_intel={})
        assert result[0]["approved_date"] == "20090101"

    def test_household_count_attached_to_tx(self):
        """마스터 조회 성공 시 household_count 실값이 tx에 부착된다."""
        agent = _make_agent_with_master(_sample_master(household_count=2444))
        result = agent._enrich_transactions([_sample_tx()], area_intel={})
        assert result[0]["household_count"] == 2444

    def test_building_count_attached_to_tx(self):
        """마스터 조회 성공 시 building_count가 tx에 부착된다."""
        agent = _make_agent_with_master(_sample_master())
        result = agent._enrich_transactions([_sample_tx()], area_intel={})
        assert result[0]["building_count"] == 36

    def test_master_not_found_keeps_tx_intact(self):
        """마스터 조회 실패(None) 시 tx가 그대로 반환된다 (KeyError/AttributeError 없음)."""
        agent = _make_agent_with_master(None)
        tx = _sample_tx()
        result = agent._enrich_transactions([tx], area_intel={})
        assert result[0]["apt_name"] == "래미안퍼스티지"
        assert "constructor" not in result[0]  # 마스터 없으면 필드 미부착

    def test_master_exception_keeps_tx_intact(self):
        """마스터 서비스 예외 발생 시 tx가 그대로 반환된다."""
        from modules.real_estate.service import RealEstateAgent

        agent = object.__new__(RealEstateAgent)
        # apt_master_repo.get_by_name_district raises an exception
        mock_repo = MagicMock()
        mock_repo.get_by_name_district.side_effect = Exception("DB error")
        agent.apt_master_repo = mock_repo
        agent.apt_repo = ApartmentRepository(db_path=":memory:")

        result = agent._enrich_transactions([_sample_tx()], area_intel={})
        assert len(result) == 1
        assert result[0]["apt_name"] == "래미안퍼스티지"

    def test_multiple_txs_all_enriched(self):
        """여러 tx에 대해 모두 constructor/approved_date가 부착된다."""
        agent = _make_agent_with_master(_sample_master())
        # 모두 마스터 DB에 저장된 apt_name과 동일하게 사용
        txs = [_sample_tx(apt_name="래미안퍼스티지") for _ in range(3)]
        result = agent._enrich_transactions(txs, area_intel={})
        for r in result:
            assert "constructor" in r
            assert "approved_date" in r
