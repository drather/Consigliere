import sys, os
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src"))

from modules.real_estate.service import RealEstateAgent, _area_matches, _make_dedup_key
from modules.real_estate.apartment_repository import ApartmentRepository
from modules.real_estate.apt_master_repository import AptMasterRepository
from modules.real_estate.models import ApartmentMaster, AptMasterEntry
from datetime import timezone, datetime


def _make_agent(apt_repo=None, apt_master_repo=None):
    agent = object.__new__(RealEstateAgent)
    agent.apt_repo = apt_repo or ApartmentRepository(db_path=":memory:")
    agent.apt_master_repo = apt_master_repo or AptMasterRepository(db_path=":memory:")
    return agent


# ── ISSUE-01: dedup key normalize ──────────────────────────────────────────

def test_dedup_key_same_for_normalized_names():
    """이매촌(청구)와 이매촌청구는 dedup 후 1건만 남아야 한다."""
    tx1 = {"apt_name": "이매촌청구",  "exclusive_area": 84.0, "deal_date": "2026-04-15", "floor": 5, "price": 80000}
    tx2 = {"apt_name": "이매촌(청구)", "exclusive_area": 84.0, "deal_date": "2026-04-15", "floor": 5, "price": 80000}
    assert _make_dedup_key(tx1) == _make_dedup_key(tx2)


# ── ISSUE-02: _lookup_apt_details normalize ─────────────────────────────────

def test_lookup_normalizes_parenthesized_name():
    """이매촌(청구) 조회 시 내부적으로 이매촌청구로 normalize하여 조회한다."""
    apt_repo = ApartmentRepository(db_path=":memory:")
    apt_master_repo = AptMasterRepository(db_path=":memory:")

    apt_repo.save(ApartmentMaster(
        apt_name="이매촌청구", district_code="41135", complex_code="K100",
        household_count=800, building_count=10, parking_count=0,
        constructor="현대건설", approved_date="19990101",
    ))
    apt_master_repo.upsert(AptMasterEntry(
        apt_name="이매촌청구", district_code="41135", complex_code="K100",
        created_at=datetime.now(timezone.utc).isoformat(),
    ))

    agent = _make_agent(apt_repo, apt_master_repo)
    result = agent._lookup_apt_details("이매촌(청구)", "41135")

    assert result is not None
    assert result.household_count == 800


def test_lookup_returns_none_for_truly_missing():
    """실제로 없는 아파트는 None 반환."""
    agent = _make_agent()
    assert agent._lookup_apt_details("없는아파트(12)", "11680") is None


# ── ISSUE-03-A: _area_matches compound name ─────────────────────────────────

def test_area_matches_full_name():
    assert _area_matches("강남구", "강남구 재건축 허가") is True


def test_area_matches_partial_token_in_compound_name():
    """'성남시 분당구' → 뉴스에 '분당구'만 있어도 매칭해야 한다."""
    assert _area_matches("성남시 분당구", "분당구 재건축 추진") is True


def test_area_matches_another_token():
    assert _area_matches("성남시 분당구", "성남시 개발 호재") is True


def test_area_matches_no_match():
    assert _area_matches("성남시 분당구", "강남 GTX 착공") is False


def test_extract_horea_data_compound_area():
    """복합 지명 '성남시 분당구'가 '분당구'로만 나온 뉴스에서도 매칭된다."""
    agent = _make_agent()
    news = "분당구 재건축 사업이 인허가를 받았다. 2026년 착공 예정."
    result = agent._extract_horea_data(news, ["성남시 분당구"])
    assert "성남시 분당구" in result
    assert len(result["성남시 분당구"]["items"]) > 0


def test_dedup_key_none_fields_not_equal():
    """exclusive_area 또는 deal_date가 None이면 uuid를 반환해 dedup되지 않는다."""
    tx1 = {"apt_name": "아파트A", "exclusive_area": None, "deal_date": None, "floor": 5, "price": 80000}
    tx2 = {"apt_name": "아파트A", "exclusive_area": None, "deal_date": None, "floor": 5, "price": 80000}
    # 불완전 레코드는 동일해 보여도 별개 키로 처리
    assert _make_dedup_key(tx1) != _make_dedup_key(tx2)


def test_area_matches_excludes_single_char_token():
    """1자 토큰(예: '구')은 필터링되어 잘못 매칭되지 않는다."""
    # "마 구"에서 "구"는 1자라서 제외 → "강남구"와 매칭 안 됨
    assert _area_matches("마 구", "강남구 재건축") is False
