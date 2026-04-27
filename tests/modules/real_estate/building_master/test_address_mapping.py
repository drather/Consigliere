import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

import sqlite3
from unittest.mock import MagicMock, patch

from modules.real_estate.building_master.building_master_service import (
    BuildingMasterService,
    _normalize_addr,
)
from modules.real_estate.building_master.building_master_repository import BuildingMasterRepository
from modules.real_estate.building_master.building_register_client import BuildingRegisterClient
from modules.real_estate.building_master.models import BuildingMaster
from modules.real_estate.apt_master_repository import AptMasterRepository
from modules.real_estate.models import AptMasterEntry
from datetime import datetime, timezone


def _make_bm(mgm_pk, name, sigungu, road_addr):
    return BuildingMaster(
        mgm_pk=mgm_pk,
        building_name=name,
        sigungu_code=sigungu,
        road_address=road_addr,
        collected_at=datetime.now(timezone.utc).isoformat(),
    )


def _make_apt(id_, name, district, complex_code=None):
    return AptMasterEntry(
        id=id_,
        apt_name=name,
        district_code=district,
        sido="서울특별시",
        sigungu="강남구",
        complex_code=complex_code,
        tx_count=10,
        first_traded="202301",
        last_traded="202312",
        created_at=datetime.now(timezone.utc).isoformat(),
    )


# ── _normalize_addr ─────────────────────────────────────────────────────────

def test_normalize_addr_strips_parens():
    assert _normalize_addr("서울특별시 서초구 반포대로 333 (반포동)") == "반포대로 333"


def test_normalize_addr_no_parens():
    assert _normalize_addr("서울특별시 종로구 새문안로3길 23") == "새문안로3길 23"


def test_normalize_addr_empty():
    assert _normalize_addr("") == ""
    assert _normalize_addr(None) == ""


def test_normalize_addr_single_token():
    assert _normalize_addr("반포대로") == "반포대로"


# ── map_by_address ───────────────────────────────────────────────────────────

def _setup_db_with_apartments(db_path, apt_entry, road_address):
    """apt_master + apartments 테이블에 테스트 데이터 삽입."""
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS apartments (
                complex_code TEXT PRIMARY KEY,
                apt_name TEXT NOT NULL,
                district_code TEXT NOT NULL DEFAULT '',
                sido TEXT NOT NULL DEFAULT '',
                sigungu TEXT NOT NULL DEFAULT '',
                eupmyeondong TEXT NOT NULL DEFAULT '',
                ri TEXT NOT NULL DEFAULT '',
                road_address TEXT NOT NULL DEFAULT '',
                legal_address TEXT NOT NULL DEFAULT '',
                household_count INTEGER NOT NULL DEFAULT 0,
                building_count INTEGER NOT NULL DEFAULT 0,
                parking_count INTEGER NOT NULL DEFAULT 0,
                constructor TEXT NOT NULL DEFAULT '',
                developer TEXT NOT NULL DEFAULT '',
                approved_date TEXT NOT NULL DEFAULT '',
                top_floor INTEGER NOT NULL DEFAULT 0,
                base_floor INTEGER NOT NULL DEFAULT 0,
                total_area REAL NOT NULL DEFAULT 0.0,
                heat_type TEXT NOT NULL DEFAULT '',
                elevator_count INTEGER NOT NULL DEFAULT 0,
                units_60 INTEGER NOT NULL DEFAULT 0,
                units_85 INTEGER NOT NULL DEFAULT 0,
                units_135 INTEGER NOT NULL DEFAULT 0,
                units_136_plus INTEGER NOT NULL DEFAULT 0,
                fetched_at TEXT NOT NULL DEFAULT ''
            )
        """)
        conn.execute(
            "INSERT OR IGNORE INTO apartments (complex_code, apt_name, district_code, road_address, fetched_at) VALUES (?,?,?,?,?)",
            (apt_entry.complex_code, apt_entry.apt_name, apt_entry.district_code, road_address, "2024-01-01"),
        )
        conn.commit()


def test_map_by_address_matches_exact_road():
    bm_repo = BuildingMasterRepository(db_path=":memory:")
    apt_repo = AptMasterRepository(db_path=":memory:")
    svc = BuildingMasterService(BuildingRegisterClient(api_key="x"), bm_repo, apt_repo)

    # building_master: 반포자이, 반포대로 333
    bm_repo.upsert(_make_bm("BM001", "반포자이", "11650", "서울특별시 서초구 반포대로 333 (반포동)"))

    # apt_master: 반포자이 (미매핑, complex_code 있음)
    entry = _make_apt(1, "반포자이", "11650", complex_code="12345")
    apt_repo.upsert(entry)

    # apartments 테이블에 동일 주소 삽입 (in-memory DB에 직접)
    with apt_repo._conn() as conn:
        _setup_db_with_apartments.__wrapped__(conn, entry, "서울특별시 서초구 반포대로 333") \
            if hasattr(_setup_db_with_apartments, "__wrapped__") else None

    # 직접 apartments 테이블 삽입
    with apt_repo._conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS apartments (
                complex_code TEXT PRIMARY KEY, apt_name TEXT NOT NULL,
                district_code TEXT NOT NULL DEFAULT '', sido TEXT NOT NULL DEFAULT '',
                sigungu TEXT NOT NULL DEFAULT '', eupmyeondong TEXT NOT NULL DEFAULT '',
                ri TEXT NOT NULL DEFAULT '', road_address TEXT NOT NULL DEFAULT '',
                legal_address TEXT NOT NULL DEFAULT '', household_count INTEGER NOT NULL DEFAULT 0,
                building_count INTEGER NOT NULL DEFAULT 0, parking_count INTEGER NOT NULL DEFAULT 0,
                constructor TEXT NOT NULL DEFAULT '', developer TEXT NOT NULL DEFAULT '',
                approved_date TEXT NOT NULL DEFAULT '', top_floor INTEGER NOT NULL DEFAULT 0,
                base_floor INTEGER NOT NULL DEFAULT 0, total_area REAL NOT NULL DEFAULT 0.0,
                heat_type TEXT NOT NULL DEFAULT '', elevator_count INTEGER NOT NULL DEFAULT 0,
                units_60 INTEGER NOT NULL DEFAULT 0, units_85 INTEGER NOT NULL DEFAULT 0,
                units_135 INTEGER NOT NULL DEFAULT 0, units_136_plus INTEGER NOT NULL DEFAULT 0,
                fetched_at TEXT NOT NULL DEFAULT ''
            )
        """)
        conn.execute(
            "INSERT INTO apartments (complex_code, apt_name, district_code, road_address, fetched_at) VALUES (?,?,?,?,?)",
            ("12345", "반포자이", "11650", "서울특별시 서초구 반포대로 333", "2024-01-01"),
        )

    result = svc.map_by_address()
    assert result["mapped"] == 1
    assert result["no_address"] == 0

    mapped_entry = apt_repo.get_by_id(1)
    assert mapped_entry.pnu == "BM001"
    assert mapped_entry.mapping_score >= 0.6


def test_map_by_address_skips_no_complex_code():
    bm_repo = BuildingMasterRepository(db_path=":memory:")
    apt_repo = AptMasterRepository(db_path=":memory:")
    svc = BuildingMasterService(BuildingRegisterClient(api_key="x"), bm_repo, apt_repo)

    bm_repo.upsert(_make_bm("BM001", "래미안아파트", "11650", "서울특별시 서초구 반포대로 333 (반포동)"))
    entry = _make_apt(1, "래미안아파트", "11650", complex_code=None)
    apt_repo.upsert(entry)

    result = svc.map_by_address()
    assert result["no_address"] == 1
    assert result["mapped"] == 0


def test_map_by_address_skips_address_mismatch():
    bm_repo = BuildingMasterRepository(db_path=":memory:")
    apt_repo = AptMasterRepository(db_path=":memory:")
    svc = BuildingMasterService(BuildingRegisterClient(api_key="x"), bm_repo, apt_repo)

    bm_repo.upsert(_make_bm("BM001", "래미안아파트", "11650", "서울특별시 서초구 영동대로 508 (대치동)"))
    entry = _make_apt(1, "래미안아파트", "11650", complex_code="99999")
    apt_repo.upsert(entry)

    with apt_repo._conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS apartments (
                complex_code TEXT PRIMARY KEY, apt_name TEXT NOT NULL,
                district_code TEXT NOT NULL DEFAULT '', sido TEXT NOT NULL DEFAULT '',
                sigungu TEXT NOT NULL DEFAULT '', eupmyeondong TEXT NOT NULL DEFAULT '',
                ri TEXT NOT NULL DEFAULT '', road_address TEXT NOT NULL DEFAULT '',
                legal_address TEXT NOT NULL DEFAULT '', household_count INTEGER NOT NULL DEFAULT 0,
                building_count INTEGER NOT NULL DEFAULT 0, parking_count INTEGER NOT NULL DEFAULT 0,
                constructor TEXT NOT NULL DEFAULT '', developer TEXT NOT NULL DEFAULT '',
                approved_date TEXT NOT NULL DEFAULT '', top_floor INTEGER NOT NULL DEFAULT 0,
                base_floor INTEGER NOT NULL DEFAULT 0, total_area REAL NOT NULL DEFAULT 0.0,
                heat_type TEXT NOT NULL DEFAULT '', elevator_count INTEGER NOT NULL DEFAULT 0,
                units_60 INTEGER NOT NULL DEFAULT 0, units_85 INTEGER NOT NULL DEFAULT 0,
                units_135 INTEGER NOT NULL DEFAULT 0, units_136_plus INTEGER NOT NULL DEFAULT 0,
                fetched_at TEXT NOT NULL DEFAULT ''
            )
        """)
        conn.execute(
            "INSERT INTO apartments (complex_code, apt_name, district_code, road_address, fetched_at) VALUES (?,?,?,?,?)",
            ("99999", "래미안아파트", "11650", "서울특별시 서초구 반포대로 10", "2024-01-01"),
        )

    result = svc.map_by_address()
    assert result["no_match"] == 1
    assert result["mapped"] == 0


def test_map_by_address_skips_already_mapped():
    bm_repo = BuildingMasterRepository(db_path=":memory:")
    apt_repo = AptMasterRepository(db_path=":memory:")
    svc = BuildingMasterService(BuildingRegisterClient(api_key="x"), bm_repo, apt_repo)

    # apt_master 항목에 pnu 이미 설정 → get_all_for_mapping() 반환 안 함
    entry = _make_apt(1, "반포자이", "11650", complex_code="12345")
    apt_repo.upsert(entry)
    apt_repo.update_building_mapping(1, "BM_EXISTING", 0.9)

    result = svc.map_by_address()
    assert result["total"] == 0
