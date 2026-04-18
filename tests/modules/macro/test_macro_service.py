import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
from modules.macro.models import MacroIndicatorDef
from modules.macro.service import MacroCollectionService


def _make_def(ind_id=1, collect_every_days=30, last_collected_at=None, **kwargs) -> MacroIndicatorDef:
    defaults = dict(
        id=ind_id,
        code="722Y001",
        item_code="0101000",
        name="한국은행 기준금리",
        unit="%",
        frequency="M",
        collect_every_days=collect_every_days,
        domain="common",
        category="금리",
        is_active=True,
        last_collected_at=last_collected_at,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    defaults.update(kwargs)
    return MacroIndicatorDef(**defaults)


class TestMacroCollectionService:
    @pytest.fixture
    def service(self, tmp_path):
        return MacroCollectionService(db_path=str(tmp_path / "test.db"))

    def test_collect_due_skips_recent(self, service):
        recent = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        ind = _make_def(collect_every_days=30, last_collected_at=recent)
        service.repo.get_active_indicators = MagicMock(return_value=[ind])
        result = service.collect_due_indicators()
        assert "한국은행 기준금리" in result["skipped"]
        assert result["collected"] == []

    def test_collect_due_collects_overdue(self, service):
        old = (datetime.now(timezone.utc) - timedelta(days=45)).isoformat()
        ind = _make_def(collect_every_days=30, last_collected_at=old)
        service.repo.get_active_indicators = MagicMock(return_value=[ind])
        service.client.get_statistic_series = MagicMock(return_value=[
            {"TIME": "202503", "DATA_VALUE": "3.50"},
            {"TIME": "202502", "DATA_VALUE": "3.50"},
        ])
        service.repo.insert_records = MagicMock()
        service.repo.update_last_collected = MagicMock()
        result = service.collect_due_indicators()
        assert "한국은행 기준금리" in result["collected"]
        service.repo.insert_records.assert_called_once()
        service.repo.update_last_collected.assert_called_once()

    def test_collect_due_collects_never_collected(self, service):
        ind = _make_def(last_collected_at=None)
        service.repo.get_active_indicators = MagicMock(return_value=[ind])
        service.client.get_statistic_series = MagicMock(return_value=[
            {"TIME": "202503", "DATA_VALUE": "3.50"},
        ])
        service.repo.insert_records = MagicMock()
        service.repo.update_last_collected = MagicMock()
        result = service.collect_due_indicators()
        assert "한국은행 기준금리" in result["collected"]

    def test_collect_due_handles_bok_error(self, service):
        ind = _make_def(last_collected_at=None)
        service.repo.get_active_indicators = MagicMock(return_value=[ind])
        service.client.get_statistic_series = MagicMock(return_value=[])
        service.repo.insert_records = MagicMock()
        service.repo.update_last_collected = MagicMock()
        result = service.collect_due_indicators()
        assert result["errors"] == []
        service.repo.update_last_collected.assert_called_once()

    def test_collect_all_ignores_due_check(self, service):
        recent = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        ind = _make_def(collect_every_days=30, last_collected_at=recent)
        service.repo.get_active_indicators = MagicMock(return_value=[ind])
        service.client.get_statistic_series = MagicMock(return_value=[])
        service.repo.insert_records = MagicMock()
        service.repo.update_last_collected = MagicMock()
        result = service.collect_all()
        assert "한국은행 기준금리" in result["collected"]

    def test_collect_domain_filter_passed_to_repo(self, service):
        service.repo.get_active_indicators = MagicMock(return_value=[])
        service.collect_due_indicators(domain="real_estate")
        service.repo.get_active_indicators.assert_called_once_with(domain="real_estate")

    def test_get_latest_delegates_to_repo(self, service):
        service.repo.get_latest = MagicMock(return_value=[{"name": "기준금리", "value": 3.5}])
        result = service.get_latest(domain="common")
        service.repo.get_latest.assert_called_once_with(domain="common")
        assert result[0]["name"] == "기준금리"

    def test_get_history_delegates_to_repo(self, service):
        service.repo.get_history = MagicMock(return_value=[])
        service.get_history(indicator_id=1, months=12)
        service.repo.get_history.assert_called_once_with(1, 12)
