import os
import sys
import pytest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

from modules.real_estate.commute.models import CommuteResult


def make_result(origin_key="11680__래미안", mode="transit", minutes=25, meters=3000):
    return CommuteResult(
        origin_key=origin_key,
        destination="삼성역",
        mode=mode,
        duration_minutes=minutes,
        distance_meters=meters,
    )


class TestCommuteRepository:
    def _repo(self, ttl_days=90):
        from modules.real_estate.commute.commute_repository import CommuteRepository
        return CommuteRepository(db_path=":memory:", ttl_days=ttl_days)

    def test_get_returns_none_when_empty(self):
        repo = self._repo()
        result = repo.get("11680__없는단지", "삼성역", "transit")
        assert result is None

    def test_upsert_and_get(self):
        repo = self._repo()
        r = make_result()
        repo.upsert(r)
        got = repo.get("11680__래미안", "삼성역", "transit")
        assert got is not None
        assert got.duration_minutes == 25
        assert got.cached is True

    def test_expired_cache_returns_none(self):
        repo = self._repo(ttl_days=0)  # 즉시 만료
        r = make_result()
        repo.upsert(r)
        got = repo.get("11680__래미안", "삼성역", "transit")
        assert got is None

    def test_upsert_updates_existing(self):
        repo = self._repo()
        repo.upsert(make_result(minutes=25))
        repo.upsert(make_result(minutes=59))  # 갱신
        got = repo.get("11680__래미안", "삼성역", "transit")
        assert got.duration_minutes == 59

    def test_different_modes_stored_independently(self):
        repo = self._repo()
        repo.upsert(make_result(mode="transit", minutes=59))
        repo.upsert(make_result(mode="car", minutes=30))
        repo.upsert(make_result(mode="walking", minutes=90))

        assert repo.get("11680__래미안", "삼성역", "transit").duration_minutes == 59
        assert repo.get("11680__래미안", "삼성역", "car").duration_minutes == 30
        assert repo.get("11680__래미안", "삼성역", "walking").duration_minutes == 90

    def test_different_origins_stored_independently(self):
        repo = self._repo()
        repo.upsert(make_result(origin_key="11680__A단지", minutes=20))
        repo.upsert(make_result(origin_key="11710__B단지", minutes=59))

        assert repo.get("11680__A단지", "삼성역", "transit").duration_minutes == 20
        assert repo.get("11710__B단지", "삼성역", "transit").duration_minutes == 59

    def test_upsert_and_get_preserves_legs(self):
        """legs와 route_summary가 저장 후 복원돼야 한다."""
        repo = self._repo()
        legs = [
            {"mode": "WALK", "from_name": "출발지", "to_name": "정류장", "duration_minutes": 5},
            {"mode": "BUS", "route": "302", "from_name": "가락시장", "to_name": "잠실역",
             "duration_minutes": 12, "stop_count": 4},
        ]
        r = CommuteResult(
            origin_key="11710__파크데일", destination="삼성역", mode="transit",
            duration_minutes=59, distance_meters=1200,
            legs=legs, route_summary="도보 5분 → 302번 버스 → 잠실역",
        )
        repo.upsert(r)
        got = repo.get("11710__파크데일", "삼성역", "transit")
        assert got is not None
        assert len(got.legs) == 2
        assert got.legs[1]["route"] == "302"
        assert got.route_summary == "도보 5분 → 302번 버스 → 잠실역"

    def test_migration_adds_columns_to_old_db(self):
        """route_json 컬럼 없는 구형 DB에서도 정상 동작해야 한다."""
        import sqlite3
        from modules.real_estate.commute.commute_repository import CommuteRepository

        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)

        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            tmp_path = f.name
        try:
            conn2 = sqlite3.connect(tmp_path)
            conn2.executescript("""
                CREATE TABLE commute_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    origin_key TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    duration_minutes INTEGER NOT NULL,
                    distance_meters INTEGER NOT NULL DEFAULT 0,
                    cached_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    UNIQUE(origin_key, destination, mode)
                )
            """)
            conn2.execute(
                "INSERT INTO commute_cache (origin_key, destination, mode, duration_minutes, "
                "distance_meters, cached_at, expires_at) VALUES (?,?,?,?,?,?,?)",
                ("k", "삼성역", "transit", 59, 0, now.isoformat(), (now + timedelta(days=90)).isoformat()),
            )
            conn2.commit()
            conn2.close()

            repo = CommuteRepository(db_path=tmp_path, ttl_days=90)
            got = repo.get("k", "삼성역", "transit")
            assert got is not None
            assert got.duration_minutes == 59
            assert got.legs == []
            assert got.route_summary == ""
        finally:
            os.unlink(tmp_path)


class TestCommuteResultModel:
    def test_legs_defaults_to_empty_list(self):
        from modules.real_estate.commute.models import CommuteResult
        r = CommuteResult("k", "삼성역", "transit", 59, 1200)
        assert r.legs == []
        assert r.route_summary == ""

    def test_legs_can_be_set(self):
        from modules.real_estate.commute.models import CommuteResult
        legs = [{"mode": "BUS", "route": "302", "from_name": "가락시장", "to_name": "잠실역",
                 "duration_minutes": 12, "stop_count": 4}]
        r = CommuteResult("k", "삼성역", "transit", 59, 1200, legs=legs, route_summary="302번 → 잠실역 → 2호선 → 삼성역")
        assert r.legs[0]["route"] == "302"
        assert r.route_summary == "302번 → 잠실역 → 2호선 → 삼성역"
