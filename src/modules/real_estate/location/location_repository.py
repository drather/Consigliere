import json
import sqlite3
from typing import List, Optional

from modules.real_estate.location.dimension_result import DimensionResult
from modules.real_estate.location.location_scorer import LocationScore

_DDL = """
CREATE TABLE IF NOT EXISTS location_scores (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    complex_code          TEXT NOT NULL UNIQUE,
    residential_total     INTEGER NOT NULL DEFAULT 50,
    residential_results   TEXT NOT NULL DEFAULT '[]',
    investment_total      INTEGER NOT NULL DEFAULT 50,
    investment_results    TEXT NOT NULL DEFAULT '[]',
    scored_at             TEXT NOT NULL
);
"""

_MIGRATE_SQL = [
    "ALTER TABLE location_scores ADD COLUMN residential_results TEXT NOT NULL DEFAULT '[]'",
    "ALTER TABLE location_scores ADD COLUMN investment_results TEXT NOT NULL DEFAULT '[]'",
]


def _results_to_json(results: List[DimensionResult]) -> str:
    return json.dumps(
        [{"id": dr.id, "label": dr.label, "score": dr.score, "evidence": dr.evidence}
         for dr in results],
        ensure_ascii=False,
    )


def _results_from_json(raw: str) -> List[DimensionResult]:
    items = json.loads(raw or "[]")
    return [DimensionResult(id=d["id"], label=d["label"], score=d["score"],
                            evidence=d.get("evidence", []))
            for d in items]


class LocationRepository:
    def __init__(self, db_path: str = "data/real_estate.db"):
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.executescript(_DDL)
        self._migrate()

    def _migrate(self) -> None:
        for sql in _MIGRATE_SQL:
            try:
                self._conn.execute(sql)
                self._conn.commit()
            except sqlite3.OperationalError:
                pass  # column already exists

    def _connect(self) -> sqlite3.Connection:
        return self._conn

    def upsert_score(self, score: LocationScore) -> None:
        conn = self._connect()
        conn.execute(
            """INSERT INTO location_scores
               (complex_code, residential_total, residential_results,
                investment_total, investment_results, scored_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(complex_code) DO UPDATE SET
               residential_total=excluded.residential_total,
               residential_results=excluded.residential_results,
               investment_total=excluded.investment_total,
               investment_results=excluded.investment_results,
               scored_at=excluded.scored_at""",
            (
                score.complex_code,
                score.residential_total,
                _results_to_json(score.residential_results),
                score.investment_total,
                _results_to_json(score.investment_results),
                score.scored_at,
            ),
        )
        conn.commit()

    def get_score(self, complex_code: str) -> Optional[LocationScore]:
        conn = self._connect()
        row = conn.execute(
            "SELECT complex_code, residential_total, residential_results,"
            "       investment_total, investment_results, scored_at"
            " FROM location_scores WHERE complex_code=?",
            (complex_code,),
        ).fetchone()
        if not row:
            return None
        return LocationScore(
            complex_code=row[0],
            residential_total=row[1],
            residential_results=_results_from_json(row[2]),
            investment_total=row[3],
            investment_results=_results_from_json(row[4]),
            scored_at=row[5],
        )
