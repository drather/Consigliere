import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

from unittest.mock import MagicMock
from modules.real_estate.building_master.building_master_service import (
    BuildingMasterService,
)
from modules.real_estate.building_master.models import BuildingMaster
from modules.real_estate.building_master.building_master_repository import (
    BuildingMasterRepository,
)
from modules.real_estate.apt_master_repository import AptMasterRepository
from modules.real_estate.models import AptMasterEntry
from datetime import datetime, timezone as tz


def _make_client_stub(items_by_code: dict):
    client = MagicMock()
    def _fetch(code):
        return items_by_code.get(code, [])
    client.fetch_apartments_by_sigungu.side_effect = _fetch
    client.parse_item.side_effect = lambda item: item  # passthrough
    return client


def test_collect_inserts_items():
    bm_repo = BuildingMasterRepository(db_path=":memory:")
    apt_repo = AptMasterRepository(db_path=":memory:")

    raw_item = {
        "mgm_pk": "1100000000000001000001",
        "building_name": "래미안아파트",
        "sigungu_code": "11650",
        "bjdong_code": "10100",
        "parcel_pnu": "1165010100",
        "road_address": "서울 서초구 반포대로 23",
        "jibun_address": "서울 서초구 반포동 10",
        "completion_year": 2005,
        "total_units": 1000,
        "total_buildings": 5,
        "floor_area_ratio": 250.0,
        "building_coverage_ratio": 20.0,
    }
    client = _make_client_stub({"11650": [raw_item]})
    svc = BuildingMasterService(client, bm_repo, apt_repo)

    result = svc.collect(sigungu_codes=["11650"])
    assert result["collected"] == 1
    assert result["failed"] == []
    assert bm_repo.count() == 1


def test_collect_skips_already_collected():
    bm_repo = BuildingMasterRepository(db_path=":memory:")
    apt_repo = AptMasterRepository(db_path=":memory:")
    bm_repo.upsert(BuildingMaster(
        mgm_pk="EXISTING", building_name="기존아파트",
        sigungu_code="11650", collected_at="2026-01-01T00:00:00+00:00",
    ))
    client = _make_client_stub({"11650": []})
    svc = BuildingMasterService(client, bm_repo, apt_repo)

    result = svc.collect(sigungu_codes=["11650"])
    assert result["skipped"] == 1
    assert result["collected"] == 0
    client.fetch_apartments_by_sigungu.assert_not_called()


def test_collect_isolates_failed_sigungu():
    bm_repo = BuildingMasterRepository(db_path=":memory:")
    apt_repo = AptMasterRepository(db_path=":memory:")
    client = MagicMock()
    client.fetch_apartments_by_sigungu.side_effect = Exception("API error")
    svc = BuildingMasterService(client, bm_repo, apt_repo)

    result = svc.collect(sigungu_codes=["11650", "11680"])
    assert "11650" in result["failed"]
    assert "11680" in result["failed"]
    assert result["collected"] == 0


def test_collect_skips_items_missing_mgm_pk():
    bm_repo = BuildingMasterRepository(db_path=":memory:")
    apt_repo = AptMasterRepository(db_path=":memory:")
    raw_item = {
        "mgm_pk": "",
        "building_name": "이름없는아파트",
        "sigungu_code": "11650",
        "bjdong_code": "",
        "parcel_pnu": "",
        "road_address": None,
        "jibun_address": None,
        "completion_year": None,
        "total_units": None,
        "total_buildings": None,
        "floor_area_ratio": None,
        "building_coverage_ratio": None,
    }
    client = _make_client_stub({"11650": [raw_item]})
    svc = BuildingMasterService(client, bm_repo, apt_repo)

    result = svc.collect(sigungu_codes=["11650"])
    assert result["collected"] == 0
    assert bm_repo.count() == 0


def _seed_apt_master(repo, name: str, district_code: str) -> AptMasterEntry:
    now = datetime.now(tz.utc).isoformat()
    entry = AptMasterEntry(apt_name=name, district_code=district_code, created_at=now)
    repo.upsert(entry)
    return repo.get_by_name_district(name, district_code)


def _seed_building(repo, mgm_pk: str, name: str, sigungu_code: str) -> None:
    repo.upsert(BuildingMaster(
        mgm_pk=mgm_pk, building_name=name, sigungu_code=sigungu_code,
        collected_at=datetime.now(tz.utc).isoformat(),
    ))


def test_map_high_similarity_sets_pnu():
    bm_repo = BuildingMasterRepository(db_path=":memory:")
    apt_repo = AptMasterRepository(db_path=":memory:")
    _seed_apt_master(apt_repo, "래미안아파트", "11650")
    _seed_building(bm_repo, "MGM001", "래미안아파트", "11650")

    svc = BuildingMasterService(MagicMock(), bm_repo, apt_repo)
    result = svc.map_to_apt_master()

    assert result["mapped"] == 1
    mapped = apt_repo.get_by_name_district("래미안아파트", "11650")
    assert mapped.pnu == "MGM001"
    assert mapped.mapping_score >= 0.8


def test_map_low_similarity_leaves_pnu_null():
    bm_repo = BuildingMasterRepository(db_path=":memory:")
    apt_repo = AptMasterRepository(db_path=":memory:")
    _seed_apt_master(apt_repo, "래미안아파트", "11650")
    _seed_building(bm_repo, "MGM002", "현대아이파크", "11650")

    svc = BuildingMasterService(MagicMock(), bm_repo, apt_repo)
    result = svc.map_to_apt_master()

    assert result["mapped"] == 0
    assert result["below_threshold"] == 1
    entry = apt_repo.get_by_name_district("래미안아파트", "11650")
    assert entry.pnu is None


def test_map_no_candidates_in_sigungu():
    bm_repo = BuildingMasterRepository(db_path=":memory:")
    apt_repo = AptMasterRepository(db_path=":memory:")
    _seed_apt_master(apt_repo, "래미안아파트", "11650")
    _seed_building(bm_repo, "MGM003", "래미안아파트", "11680")

    svc = BuildingMasterService(MagicMock(), bm_repo, apt_repo)
    result = svc.map_to_apt_master()

    assert result["no_candidates"] == 1
    assert result["mapped"] == 0


def test_map_skips_already_mapped():
    bm_repo = BuildingMasterRepository(db_path=":memory:")
    apt_repo = AptMasterRepository(db_path=":memory:")
    entry = _seed_apt_master(apt_repo, "래미안아파트", "11650")
    apt_repo.update_building_mapping(entry.id, "EXISTING_MGM", 0.95)
    _seed_building(bm_repo, "MGM004", "래미안아파트", "11650")

    svc = BuildingMasterService(MagicMock(), bm_repo, apt_repo)
    result = svc.map_to_apt_master()

    assert result["total"] == 0
    assert result["mapped"] == 0
