import json
import sqlite3
from typing import Optional

from modules.real_estate.location.location_scorer import LocationScore

_DDL = """
CREATE TABLE IF NOT EXISTS location_scores (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    complex_code          TEXT NOT NULL UNIQUE,
    residential_total     INTEGER NOT NULL DEFAULT 50,
    residential_breakdown TEXT NOT NULL DEFAULT '{}',
    investment_total      INTEGER NOT NULL DEFAULT 50,
    investment_breakdown  TEXT NOT NULL DEFAULT '{}',
    scored_at             TEXT NOT NULL
);
"""


class LocationRepository:
    def __init__(self, db_path: str = "data/real_estate.db"):
        self._db_path = db_path
        # Keep a persistent connection for :memory: databases; reuse for file DBs too.
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.executescript(_DDL)

    def _connect(self) -> sqlite3.Connection:
        return self._conn

    def upsert_score(self, score: LocationScore) -> None:
        conn = self._connect()
        conn.execute(
            """INSERT INTO location_scores
               (complex_code, residential_total, residential_breakdown,
                investment_total, investment_breakdown, scored_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(complex_code) DO UPDATE SET
               residential_total=excluded.residential_total,
               residential_breakdown=excluded.residential_breakdown,
               investment_total=excluded.investment_total,
               investment_breakdown=excluded.investment_breakdown,
               scored_at=excluded.scored_at""",
            (
                score.complex_code,
                score.residential_total,
                json.dumps(score.residential_breakdown, ensure_ascii=False),
                score.investment_total,
                json.dumps(score.investment_breakdown, ensure_ascii=False),
                score.scored_at,
            ),
        )
        conn.commit()

    def get_score(self, complex_code: str) -> Optional[LocationScore]:
        conn = self._connect()
        row = conn.execute(
            "SELECT complex_code, residential_total, residential_breakdown,"
            "       investment_total, investment_breakdown, scored_at"
            " FROM location_scores WHERE complex_code=?",
            (complex_code,),
        ).fetchone()
        if not row:
            return None
        return LocationScore(
            complex_code=row[0],
            residential_total=row[1],
            residential_breakdown=json.loads(row[2]),
            investment_total=row[3],
            investment_breakdown=json.loads(row[4]),
            scored_at=row[5],
        )
