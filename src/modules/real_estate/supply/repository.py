import math
import sqlite3
import threading
from datetime import date
from typing import List
from .models import SupplySchedule

_DDL = """
CREATE TABLE IF NOT EXISTS supply_schedule (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_name    TEXT NOT NULL,
    sigungu_code    TEXT NOT NULL,
    lat             REAL NOT NULL,
    lng             REAL NOT NULL,
    household_count INTEGER NOT NULL,
    expected_date   TEXT NOT NULL,
    supply_type     TEXT NOT NULL DEFAULT 'move_in',
    collected_at    TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(project_name, expected_date)
);
"""


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


class SupplyRepository:
    def __init__(self, db_path: str):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_DDL)
        self._conn.commit()
        self._lock = threading.Lock()

    def save(self, s: SupplySchedule) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT OR IGNORE INTO supply_schedule
                   (project_name, sigungu_code, lat, lng, household_count, expected_date, supply_type)
                   VALUES (?,?,?,?,?,?,?)""",
                (s.project_name, s.sigungu_code, s.lat, s.lng, s.household_count, s.expected_date, s.supply_type)
            )
            self._conn.commit()

    def save_bulk(self, items: List[SupplySchedule]) -> int:
        saved = 0
        with self._lock:
            for s in items:
                cur = self._conn.execute(
                    """INSERT OR IGNORE INTO supply_schedule
                       (project_name, sigungu_code, lat, lng, household_count, expected_date, supply_type)
                       VALUES (?,?,?,?,?,?,?)""",
                    (s.project_name, s.sigungu_code, s.lat, s.lng, s.household_count, s.expected_date, s.supply_type)
                )
                saved += cur.rowcount
            self._conn.commit()
        return saved

    def get_within_radius(
        self, lat: float, lng: float, radius_km: float = 2.0, months_ahead: int = 12
    ) -> List[SupplySchedule]:
        today = date.today()
        # Accurate month arithmetic
        cutoff_year = today.year + (today.month + months_ahead - 1) // 12
        cutoff_month = (today.month + months_ahead - 1) % 12 + 1
        cutoff = f"{cutoff_year:04d}-{cutoff_month:02d}"
        today_str = today.strftime("%Y-%m")

        rows = self._conn.execute(
            "SELECT * FROM supply_schedule WHERE expected_date >= ? AND expected_date <= ?",
            (today_str, cutoff)
        ).fetchall()

        return [
            SupplySchedule(
                id=r["id"], project_name=r["project_name"], sigungu_code=r["sigungu_code"],
                lat=r["lat"], lng=r["lng"], household_count=r["household_count"],
                expected_date=r["expected_date"], supply_type=r["supply_type"]
            )
            for r in rows
            if _haversine_km(lat, lng, r["lat"], r["lng"]) <= radius_km
        ]
