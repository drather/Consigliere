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
