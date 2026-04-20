import sqlite3
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from .models import CommuteResult

logger = logging.getLogger(__name__)

_DDL = """
CREATE TABLE IF NOT EXISTS commute_cache (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    origin_key       TEXT NOT NULL,
    destination      TEXT NOT NULL,
    mode             TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL,
    distance_meters  INTEGER NOT NULL DEFAULT 0,
    cached_at        TEXT NOT NULL,
    expires_at       TEXT NOT NULL,
    UNIQUE(origin_key, destination, mode)
)
"""


class CommuteRepository:
    def __init__(self, db_path: str, ttl_days: int = 90):
        self._db_path = db_path
        self._ttl_days = ttl_days
        # Keep a persistent connection for :memory: databases; for file-based
        # DBs this is also fine since SQLite supports shared-cache reuse.
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        self._conn.executescript(_DDL)
        self._conn.commit()

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def get(self, origin_key: str, destination: str, mode: str) -> Optional[CommuteResult]:
        """유효한 캐시가 있으면 CommuteResult(cached=True) 반환, 없거나 만료시 None."""
        row = self._conn.execute(
            "SELECT * FROM commute_cache WHERE origin_key=? AND destination=? AND mode=?",
            (origin_key, destination, mode),
        ).fetchone()

        if row is None:
            return None

        expires_at = datetime.fromisoformat(row["expires_at"])
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if self._now() > expires_at:
            return None

        return CommuteResult(
            origin_key=row["origin_key"],
            destination=row["destination"],
            mode=row["mode"],
            duration_minutes=row["duration_minutes"],
            distance_meters=row["distance_meters"],
            cached=True,
        )

    def upsert(self, result: CommuteResult):
        """캐시 저장 또는 갱신."""
        now = self._now()
        expires_at = now + timedelta(days=self._ttl_days)
        self._conn.execute(
            """
            INSERT INTO commute_cache
                (origin_key, destination, mode, duration_minutes, distance_meters, cached_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(origin_key, destination, mode) DO UPDATE SET
                duration_minutes = excluded.duration_minutes,
                distance_meters  = excluded.distance_meters,
                cached_at        = excluded.cached_at,
                expires_at       = excluded.expires_at
            """,
            (
                result.origin_key, result.destination, result.mode,
                result.duration_minutes, result.distance_meters,
                now.isoformat(), expires_at.isoformat(),
            ),
        )
        self._conn.commit()
