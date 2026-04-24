import sqlite3
from datetime import datetime, timezone
from typing import List, Optional

from modules.real_estate.building_master.models import BuildingMaster

_DDL = """
CREATE TABLE IF NOT EXISTS building_master (
    mgm_pk                  TEXT PRIMARY KEY,
    building_name           TEXT NOT NULL,
    sigungu_code            TEXT NOT NULL,
    bjdong_code             TEXT NOT NULL DEFAULT '',
    parcel_pnu              TEXT NOT NULL DEFAULT '',
    road_address            TEXT,
    jibun_address           TEXT,
    completion_year         INTEGER,
    total_units             INTEGER,
    total_buildings         INTEGER,
    floor_area_ratio        REAL,
    building_coverage_ratio REAL,
    collected_at            TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_bm_sigungu ON building_master(sigungu_code);
CREATE INDEX IF NOT EXISTS idx_bm_parcel  ON building_master(parcel_pnu);
CREATE INDEX IF NOT EXISTS idx_bm_name    ON building_master(building_name);
"""

_UPSERT_SQL = """
INSERT INTO building_master
    (mgm_pk, building_name, sigungu_code, bjdong_code, parcel_pnu,
     road_address, jibun_address, completion_year, total_units,
     total_buildings, floor_area_ratio, building_coverage_ratio, collected_at)
VALUES
    (:mgm_pk, :building_name, :sigungu_code, :bjdong_code, :parcel_pnu,
     :road_address, :jibun_address, :completion_year, :total_units,
     :total_buildings, :floor_area_ratio, :building_coverage_ratio, :collected_at)
ON CONFLICT(mgm_pk) DO UPDATE SET
    -- sigungu_code / bjdong_code / parcel_pnu 는 최초 등록 값을 보존
    building_name           = excluded.building_name,
    completion_year         = excluded.completion_year,
    total_units             = excluded.total_units,
    total_buildings         = excluded.total_buildings,
    floor_area_ratio        = excluded.floor_area_ratio,
    building_coverage_ratio = excluded.building_coverage_ratio,
    road_address            = excluded.road_address,
    jibun_address           = excluded.jibun_address,
    collected_at            = excluded.collected_at
"""


class BuildingMasterRepository:
    def __init__(self, db_path: str = "data/real_estate.db"):
        self._db_path = db_path
        if db_path == ":memory:":
            self._shared_conn: Optional[sqlite3.Connection] = sqlite3.connect(":memory:")
            self._shared_conn.row_factory = sqlite3.Row
        else:
            self._shared_conn = None
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        if self._shared_conn is not None:
            return self._shared_conn
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        conn = self._conn()
        conn.executescript(_DDL)  # executescript issues implicit COMMIT

    def upsert(self, bm: BuildingMaster) -> None:
        params = {
            "mgm_pk": bm.mgm_pk,
            "building_name": bm.building_name,
            "sigungu_code": bm.sigungu_code,
            "bjdong_code": bm.bjdong_code,
            "parcel_pnu": bm.parcel_pnu,
            "road_address": bm.road_address,
            "jibun_address": bm.jibun_address,
            "completion_year": bm.completion_year,
            "total_units": bm.total_units,
            "total_buildings": bm.total_buildings,
            "floor_area_ratio": bm.floor_area_ratio,
            "building_coverage_ratio": bm.building_coverage_ratio,
            "collected_at": bm.collected_at or datetime.now(timezone.utc).isoformat(),
        }
        with self._conn() as conn:
            conn.execute(_UPSERT_SQL, params)

    def get_by_sigungu(self, sigungu_code: str) -> List[BuildingMaster]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM building_master WHERE sigungu_code = ?",
                (sigungu_code,),
            ).fetchall()
        return [_row_to_bm(r) for r in rows]

    def count_by_sigungu(self, sigungu_code: str) -> int:
        with self._conn() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM building_master WHERE sigungu_code = ?",
                (sigungu_code,),
            ).fetchone()[0]

    def count(self) -> int:
        with self._conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM building_master").fetchone()[0]


def _row_to_bm(row: sqlite3.Row) -> BuildingMaster:
    return BuildingMaster(
        mgm_pk=row["mgm_pk"],
        building_name=row["building_name"],
        sigungu_code=row["sigungu_code"],
        bjdong_code=row["bjdong_code"],
        parcel_pnu=row["parcel_pnu"],
        road_address=row["road_address"],
        jibun_address=row["jibun_address"],
        completion_year=row["completion_year"],
        total_units=row["total_units"],
        total_buildings=row["total_buildings"],
        floor_area_ratio=row["floor_area_ratio"],
        building_coverage_ratio=row["building_coverage_ratio"],
        collected_at=row["collected_at"],
    )
