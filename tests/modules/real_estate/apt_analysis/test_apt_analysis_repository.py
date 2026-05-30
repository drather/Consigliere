import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

import pytest
from modules.real_estate.apt_analysis.models import AptAnalysisReport
from modules.real_estate.apt_analysis.repository import AptAnalysisRepository


@pytest.fixture
def repo(tmp_path):
    return AptAnalysisRepository(db_path=str(tmp_path / "re.db"))


def _make_report(complex_code: str = "CC001", generated_at: str = "2026-05-30T12:00:00", llm_insight: str = "이 단지는 입지가 우수합니다.") -> AptAnalysisReport:
    return AptAnalysisReport(
        complex_code=complex_code,
        apt_name="래미안블레스티지",
        generated_at=generated_at,
        price_history=[{"date": "2026-05-01", "price": 1_500_000_000, "area": 84.0}],
        jeonse_ratio=60.5,
        supply_risk_summary="반경 3km 공급 3,500세대 — 위험",
        location_score={"residential_total": 72, "investment_total": 68, "results": {}},
        commute_summary={"transit": 32, "car": 25},
        macro_snapshot={"base_rate": {"value": 3.0}, "updated_at": "2026-05-30"},
        llm_insight=llm_insight,
        slack_text="*래미안블레스티지* 분석 완료",
        markdown_text="# 래미안블레스티지\n\n분석 결과...",
    )


class TestAptAnalysisRepository:
    def test_save_and_get_latest(self, repo):
        report = _make_report()
        repo.save(report)
        latest = repo.get_latest("CC001")
        assert latest is not None
        assert latest.complex_code == "CC001"
        assert latest.apt_name == "래미안블레스티지"
        assert latest.llm_insight == "이 단지는 입지가 우수합니다."

    def test_get_latest_returns_none_when_no_data(self, repo):
        assert repo.get_latest("NONEXISTENT") is None

    def test_get_history_returns_multiple_sorted(self, repo):
        r1 = _make_report(generated_at="2026-05-29T10:00:00", llm_insight="분석1")
        r2 = _make_report(generated_at="2026-05-30T12:00:00", llm_insight="분석2")
        repo.save(r1)
        repo.save(r2)
        history = repo.get_history("CC001", limit=10)
        assert len(history) == 2
        assert history[0].generated_at == "2026-05-30T12:00:00"

    def test_get_history_respects_limit(self, repo):
        for i in range(5):
            r = _make_report(generated_at=f"2026-05-{i+1:02d}T00:00:00")
            repo.save(r)
        history = repo.get_history("CC001", limit=3)
        assert len(history) == 3

    def test_save_preserves_optional_none_fields(self, repo):
        report = _make_report()
        report.jeonse_ratio = None
        report.supply_risk_summary = None
        report.location_score = None
        report.commute_summary = None
        repo.save(report)
        latest = repo.get_latest("CC001")
        assert latest.jeonse_ratio is None
        assert latest.supply_risk_summary is None
