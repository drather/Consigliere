import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src"))

from modules.real_estate.apartment_repository import ApartmentRepository
from modules.real_estate.apt_master_repository import AptMasterRepository
from modules.real_estate.models import ApartmentMaster, AptMasterEntry
from modules.real_estate.service import RealEstateAgent
from datetime import timezone, datetime


def _make_agent(apt_repo, apt_master_repo):
    agent = object.__new__(RealEstateAgent)
    agent.apt_repo = apt_repo
    agent.apt_master_repo = apt_master_repo
    return agent


def _make_apt_master(complex_code="K001", apt_name="테스트아파트", district_code="11680",
                     household_count=600, constructor="현대건설", approved_date="20100101"):
    return ApartmentMaster(
        complex_code=complex_code,
        apt_name=apt_name,
        district_code=district_code,
        household_count=household_count,
        building_count=5,
        parking_count=0,
        constructor=constructor,
        approved_date=approved_date,
    )


def test_lookup_apt_details_via_complex_code():
    apt_repo = ApartmentRepository(db_path=":memory:")
    apt_master_repo = AptMasterRepository(db_path=":memory:")

    apt_repo.save(_make_apt_master())
    apt_master_repo.upsert(AptMasterEntry(
        apt_name="테스트아파트",
        district_code="11680",
        complex_code="K001",
        created_at=datetime.now(timezone.utc).isoformat(),
    ))

    agent = _make_agent(apt_repo, apt_master_repo)
    result = agent._lookup_apt_details("테스트아파트", "11680")

    assert result is not None
    assert result.household_count == 600
    assert result.constructor == "현대건설"


def test_lookup_apt_details_fallback_search():
    apt_repo = ApartmentRepository(db_path=":memory:")
    apt_master_repo = AptMasterRepository(db_path=":memory:")

    apt_repo.save(_make_apt_master(apt_name="래미안아파트"))
    apt_master_repo.upsert(AptMasterEntry(
        apt_name="래미안아파트",
        district_code="11680",
        complex_code=None,
        created_at=datetime.now(timezone.utc).isoformat(),
    ))

    agent = _make_agent(apt_repo, apt_master_repo)
    result = agent._lookup_apt_details("래미안아파트", "11680")

    assert result is not None
    assert result.household_count == 600


def test_lookup_apt_details_returns_none_when_missing():
    apt_repo = ApartmentRepository(db_path=":memory:")
    apt_master_repo = AptMasterRepository(db_path=":memory:")
    agent = _make_agent(apt_repo, apt_master_repo)

    result = agent._lookup_apt_details("없는아파트", "11680")
    assert result is None


def test_enrich_transactions_sets_household_count():
    apt_repo = ApartmentRepository(db_path=":memory:")
    apt_master_repo = AptMasterRepository(db_path=":memory:")

    apt_repo.save(_make_apt_master())
    apt_master_repo.upsert(AptMasterEntry(
        apt_name="테스트아파트",
        district_code="11680",
        complex_code="K001",
        created_at=datetime.now(timezone.utc).isoformat(),
    ))

    agent = _make_agent(apt_repo, apt_master_repo)
    txs = [{"apt_name": "테스트아파트", "district_code": "11680", "price": 500_000_000}]
    enriched = agent._enrich_transactions(txs, {})

    assert enriched[0]["household_count"] == 600
    assert enriched[0]["constructor"] == "현대건설"
