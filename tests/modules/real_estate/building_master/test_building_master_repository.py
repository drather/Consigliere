import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

from modules.real_estate.building_master.models import BuildingMaster
from modules.real_estate.building_master.building_master_repository import (
    BuildingMasterRepository,
)


def _make_bm(**kwargs) -> BuildingMaster:
    defaults = dict(
        mgm_pk="1100000000000001000001",
        building_name="래미안아파트",
        sigungu_code="11650",
        bjdong_code="10100",
        parcel_pnu="1165010100",
        road_address="서울 서초구 반포대로 23",
        jibun_address="서울 서초구 반포동 10",
        completion_year=2005,
        total_units=1000,
        total_buildings=5,
        floor_area_ratio=250.0,
        building_coverage_ratio=20.0,
        collected_at="2026-04-23T00:00:00+00:00",
    )
    defaults.update(kwargs)
    return BuildingMaster(**defaults)


def test_upsert_and_count():
    repo = BuildingMasterRepository(db_path=":memory:")
    assert repo.count() == 0
    repo.upsert(_make_bm())
    assert repo.count() == 1


def test_upsert_idempotent():
    repo = BuildingMasterRepository(db_path=":memory:")
    bm = _make_bm()
    repo.upsert(bm)
    repo.upsert(bm)  # 두 번 upsert → 1건 유지
    assert repo.count() == 1


def test_upsert_updates_fields():
    repo = BuildingMasterRepository(db_path=":memory:")
    repo.upsert(_make_bm(total_units=1000))
    repo.upsert(_make_bm(total_units=1200))  # 갱신
    results = repo.get_by_sigungu("11650")
    assert results[0].total_units == 1200


def test_get_by_sigungu_returns_only_matching():
    repo = BuildingMasterRepository(db_path=":memory:")
    repo.upsert(_make_bm(mgm_pk="A001", sigungu_code="11650"))
    repo.upsert(_make_bm(mgm_pk="A002", sigungu_code="11680"))
    results = repo.get_by_sigungu("11650")
    assert len(results) == 1
    assert results[0].mgm_pk == "A001"


def test_count_by_sigungu():
    repo = BuildingMasterRepository(db_path=":memory:")
    repo.upsert(_make_bm(mgm_pk="A001", sigungu_code="11650"))
    repo.upsert(_make_bm(mgm_pk="A002", sigungu_code="11650"))
    assert repo.count_by_sigungu("11650") == 2
    assert repo.count_by_sigungu("11680") == 0


def test_get_by_sigungu_returns_all_fields():
    repo = BuildingMasterRepository(db_path=":memory:")
    bm = _make_bm()
    repo.upsert(bm)
    results = repo.get_by_sigungu("11650")
    r = results[0]
    assert r.building_name == "래미안아파트"
    assert r.completion_year == 2005
    assert r.total_units == 1000
    assert r.floor_area_ratio == 250.0
