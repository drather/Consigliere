import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

from modules.real_estate.building_master.models import BuildingMaster


def test_building_master_construction():
    bm = BuildingMaster(
        mgm_pk="1234567890123456789012",
        building_name="래미안아파트",
        sigungu_code="11650",
    )
    assert bm.mgm_pk == "1234567890123456789012"
    assert bm.building_name == "래미안아파트"
    assert bm.sigungu_code == "11650"
    assert bm.bjdong_code == ""
    assert bm.total_units is None


def test_building_master_full_fields():
    bm = BuildingMaster(
        mgm_pk="9999999999999999999999",
        building_name="아크로리버파크",
        sigungu_code="11650",
        bjdong_code="10800",
        parcel_pnu="1165010800",
        completion_year=2016,
        total_units=1612,
        total_buildings=7,
        floor_area_ratio=299.9,
        building_coverage_ratio=19.9,
    )
    assert bm.parcel_pnu == "1165010800"
    assert bm.completion_year == 2016
    assert bm.total_units == 1612
