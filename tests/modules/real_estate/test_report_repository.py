import os
import sys
import json
import pytest
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src')))

from modules.real_estate.report_repository import ReportRepository, ProfessionalReport


def _make_report(d: str = "2026-05-01") -> ProfessionalReport:
    return ProfessionalReport(
        date=d,
        budget_available=820_000_000,
        macro_summary="기준금리 3.5%, 주담대 4.2%",
        candidates_summary=[{"apt_name": "래미안원베일리", "total_score": 87.0}],
        location_analyses=[{"apt_name": "래미안원베일리", "text": "강남역 도보 5분 초역세권"}],
        school_analyses=[{"apt_name": "래미안원베일리", "text": "학원 52개 최상위 학군"}],
        strategy={"market_diagnosis": "관망 유리", "strategy": "임장 후 결정", "action_short": "OO 임장", "action_mid": "금리 하락 시 매수", "risks": ["금리 인상", "규제 강화"]},
        markdown="# 테스트 리포트\n내용",
    )


@pytest.fixture
def repo(tmp_path):
    return ReportRepository(storage_path=str(tmp_path))


class TestReportRepository:
    def test_save_and_load(self, repo):
        report = _make_report("2026-05-01")
        repo.save(report)
        loaded = repo.load("2026-05-01")
        assert loaded is not None
        assert loaded.date == "2026-05-01"
        assert loaded.budget_available == 820_000_000
        assert loaded.macro_summary == "기준금리 3.5%, 주담대 4.2%"

    def test_save_creates_markdown_and_json(self, tmp_path):
        repo = ReportRepository(storage_path=str(tmp_path))
        repo.save(_make_report("2026-05-02"))
        assert (tmp_path / "2026-05-02.md").exists()
        assert (tmp_path / "2026-05-02.json").exists()

    def test_load_returns_none_for_missing(self, repo):
        result = repo.load("1999-01-01")
        assert result is None

    def test_list_dates_returns_sorted(self, repo):
        repo.save(_make_report("2026-05-01"))
        repo.save(_make_report("2026-04-30"))
        repo.save(_make_report("2026-04-29"))
        dates = repo.list_dates()
        assert dates == ["2026-05-01", "2026-04-30", "2026-04-29"]

    def test_list_dates_empty(self, repo):
        assert repo.list_dates() == []

    def test_json_is_valid(self, tmp_path):
        repo = ReportRepository(storage_path=str(tmp_path))
        repo.save(_make_report("2026-05-03"))
        raw = (tmp_path / "2026-05-03.json").read_text(encoding="utf-8")
        data = json.loads(raw)
        assert data["date"] == "2026-05-03"
        assert "candidates_summary" in data
