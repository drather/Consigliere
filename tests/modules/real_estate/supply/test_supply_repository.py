# tests/modules/real_estate/supply/test_supply_repository.py
import sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

from modules.real_estate.supply.repository import SupplyRepository
from modules.real_estate.supply.models import SupplySchedule


def _make_repo():
    tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    return SupplyRepository(db_path=tf.name)


def _supply(**kwargs):
    defaults = dict(
        project_name="잠실 파크원", sigungu_code="11710",
        lat=37.5120, lng=127.0986,
        household_count=500, expected_date="2026-10",
        supply_type="move_in"
    )
    defaults.update(kwargs)
    return SupplySchedule(**defaults)


def test_save_and_get_within_radius():
    repo = _make_repo()
    repo.save(_supply())
    # 잠실역 (37.5133, 127.1001) 기준 반경 2km
    results = repo.get_within_radius(lat=37.5133, lng=127.1001, radius_km=2.0, months_ahead=12)
    assert len(results) == 1
    assert results[0].household_count == 500


def test_outside_radius_excluded():
    repo = _make_repo()
    repo.save(_supply(lat=37.4500, lng=127.0000))  # 약 10km 떨어진 위치
    results = repo.get_within_radius(lat=37.5133, lng=127.1001, radius_km=2.0, months_ahead=12)
    assert len(results) == 0


def test_expired_date_excluded():
    repo = _make_repo()
    repo.save(_supply(expected_date="2025-01"))  # 이미 지난 날짜
    results = repo.get_within_radius(lat=37.5133, lng=127.1001, radius_km=2.0, months_ahead=12)
    assert len(results) == 0


def test_sum_nearby_units():
    repo = _make_repo()
    repo.save(_supply(household_count=300))
    repo.save(_supply(project_name="잠실 롯데캐슬", household_count=700))
    results = repo.get_within_radius(lat=37.5133, lng=127.1001, radius_km=2.0, months_ahead=12)
    total = sum(r.household_count for r in results)
    assert total == 1000
