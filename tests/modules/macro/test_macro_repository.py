import pytest
from datetime import datetime, timezone
from modules.macro.models import MacroIndicatorDef, MacroRecord
from modules.macro.repository import MacroRepository


@pytest.fixture
def repo(tmp_path):
    db_path = str(tmp_path / "test_macro.db")
    return MacroRepository(db_path=db_path)


def _make_def(**kwargs) -> MacroIndicatorDef:
    defaults = dict(
        id=None,
        code="722Y001",
        item_code="0101000",
        name="한국은행 기준금리",
        unit="%",
        frequency="M",
        collect_every_days=30,
        domain="common",
        category="금리",
        is_active=True,
        last_collected_at=None,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    defaults.update(kwargs)
    return MacroIndicatorDef(**defaults)


def _make_record(indicator_id: int, period: str, value: float, collected_at: str) -> MacroRecord:
    return MacroRecord(id=None, indicator_id=indicator_id, period=period,
                       value=value, collected_at=collected_at)


class TestMacroRepository:
    def test_init_creates_tables(self, repo):
        import sqlite3
        conn = sqlite3.connect(repo.db_path)
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        conn.close()
        assert "macro_indicator_definitions" in tables
        assert "macro_records" in tables

    def test_insert_indicator_returns_id(self, repo):
        ind = _make_def()
        new_id = repo.insert_indicator(ind)
        assert isinstance(new_id, int)
        assert new_id > 0

    def test_get_active_indicators_all(self, repo):
        repo.insert_indicator(_make_def(code="722Y001", domain="common"))
        repo.insert_indicator(_make_def(code="121Y002", domain="real_estate",
                                        name="주담대금리", item_code="BEABAA2"))
        indicators = repo.get_active_indicators()
        assert len(indicators) == 2

    def test_get_active_indicators_by_domain(self, repo):
        repo.insert_indicator(_make_def(code="722Y001", domain="common"))
        repo.insert_indicator(_make_def(code="121Y002", domain="real_estate",
                                        name="주담대금리", item_code="BEABAA2"))
        result = repo.get_active_indicators(domain="real_estate")
        assert len(result) == 2  # real_estate + common
        domains = {r.domain for r in result}
        assert "real_estate" in domains
        assert "common" in domains

    def test_get_active_indicators_excludes_inactive(self, repo):
        ind = _make_def(is_active=False)
        repo.insert_indicator(ind)
        result = repo.get_active_indicators()
        assert len(result) == 0

    def test_update_last_collected(self, repo):
        new_id = repo.insert_indicator(_make_def())
        ts = "2026-04-18T10:00:00+00:00"
        repo.update_last_collected(new_id, ts)
        indicators = repo.get_active_indicators()
        assert indicators[0].last_collected_at == ts

    def test_insert_records_basic(self, repo):
        ind_id = repo.insert_indicator(_make_def())
        records = [
            _make_record(ind_id, "202503", 3.50, "2026-04-18T10:00:00+00:00"),
            _make_record(ind_id, "202502", 3.50, "2026-04-18T10:00:00+00:00"),
        ]
        repo.insert_records(records)
        history = repo.get_history(ind_id, months=12)
        assert len(history) == 2

    def test_insert_records_ignores_duplicate(self, repo):
        ind_id = repo.insert_indicator(_make_def())
        record = _make_record(ind_id, "202503", 3.50, "2026-04-18T10:00:00+00:00")
        repo.insert_records([record])
        repo.insert_records([record])
        history = repo.get_history(ind_id, months=12)
        assert len(history) == 1

    def test_insert_records_allows_revision(self, repo):
        ind_id = repo.insert_indicator(_make_def())
        repo.insert_records([_make_record(ind_id, "202503", 3.50, "2026-01-15T00:00:00+00:00")])
        repo.insert_records([_make_record(ind_id, "202503", 3.25, "2026-02-15T00:00:00+00:00")])
        import sqlite3
        conn = sqlite3.connect(repo.db_path)
        rows = conn.execute(
            "SELECT COUNT(*) FROM macro_records WHERE indicator_id=? AND period='202503'",
            (ind_id,)
        ).fetchone()[0]
        conn.close()
        assert rows == 2

    def test_get_history_returns_latest_per_period(self, repo):
        ind_id = repo.insert_indicator(_make_def())
        repo.insert_records([_make_record(ind_id, "202503", 3.50, "2026-01-15T00:00:00+00:00")])
        repo.insert_records([_make_record(ind_id, "202503", 3.25, "2026-02-15T00:00:00+00:00")])
        history = repo.get_history(ind_id, months=12)
        assert len(history) == 1
        assert history[0].value == 3.25

    def test_get_latest_returns_most_recent_period(self, repo):
        ind_id = repo.insert_indicator(_make_def())
        repo.insert_records([
            _make_record(ind_id, "202501", 3.50, "2026-02-01T00:00:00+00:00"),
            _make_record(ind_id, "202502", 3.25, "2026-03-01T00:00:00+00:00"),
            _make_record(ind_id, "202503", 3.00, "2026-04-01T00:00:00+00:00"),
        ])
        latest = repo.get_latest()
        assert len(latest) == 1
        assert latest[0]["period"] == "202503"
        assert latest[0]["value"] == 3.00

    def test_get_indicator_by_id(self, repo):
        new_id = repo.insert_indicator(_make_def())
        ind = repo.get_indicator_by_id(new_id)
        assert ind is not None
        assert ind.code == "722Y001"
