import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

from unittest.mock import MagicMock
from modules.real_estate.daily_report.daily_report_orchestrator import DailyReportOrchestrator
from modules.real_estate.school.models import SchoolScore


def _make_orchestrator(tmp_path, school_repo):
    mock_llm = MagicMock()
    mock_llm.generate_json.return_value = {
        "market_bullets": [],
        "candidate_insights": [],
    }
    mock_prompt_loader = MagicMock()
    mock_prompt_loader.load.return_value = ({"task_type": "REAL_ESTATE_ANALYSIS"}, "prompt")
    mock_aggregator = MagicMock()
    mock_aggregator.aggregate.return_value = []
    mock_repo = MagicMock()
    mock_repo.save.return_value = None

    return DailyReportOrchestrator(
        llm=mock_llm,
        prompt_loader=mock_prompt_loader,
        aggregator=mock_aggregator,
        report_repo=mock_repo,
        db_path=str(tmp_path / "re.db"),
        school_repo=school_repo,
    )


def _make_school_score(complex_code="CC001", score=78, nearby=4,
                       per_teacher=15.2, transfer=0.065):
    return SchoolScore(
        complex_code=complex_code,
        school_kind="total",
        nearby_school_count=nearby,
        avg_students_per_class=0.0,
        avg_students_per_teacher=per_teacher,
        score=score,
        collected_at="2026-05-18T00:00:00+00:00",
        avg_transfer_rate=transfer,
    )


class TestEnrichWithSchool:
    def test_cache_hit_injects_school_fields(self, tmp_path):
        mock_repo = MagicMock()
        mock_repo.get_score.return_value = _make_school_score()
        orch = _make_orchestrator(tmp_path, mock_repo)

        candidates = [{"complex_code": "CC001", "apt_name": "래미안"}]
        result = orch._enrich_with_school(candidates)

        assert result[0]["school_score"] == 78
        assert result[0]["school_nearby_count"] == 4
        assert result[0]["school_avg_per_teacher"] == 15.2
        assert result[0]["school_transfer_rate"] == 0.065

    def test_no_school_repo_returns_unchanged(self, tmp_path):
        orch = _make_orchestrator(tmp_path, None)
        candidates = [{"complex_code": "CC001", "apt_name": "래미안"}]
        result = orch._enrich_with_school(candidates)
        assert "school_score" not in result[0]

    def test_cache_miss_no_school_fields(self, tmp_path):
        mock_repo = MagicMock()
        mock_repo.get_score.return_value = None
        orch = _make_orchestrator(tmp_path, mock_repo)

        candidates = [{"complex_code": "UNKNOWN", "apt_name": "미등록"}]
        result = orch._enrich_with_school(candidates)
        assert "school_score" not in result[0]

    def test_missing_complex_code_skipped(self, tmp_path):
        mock_repo = MagicMock()
        orch = _make_orchestrator(tmp_path, mock_repo)

        candidates = [{"apt_name": "코드없음"}]
        result = orch._enrich_with_school(candidates)
        mock_repo.get_score.assert_not_called()
        assert "school_score" not in result[0]

    def test_repo_exception_does_not_raise(self, tmp_path):
        mock_repo = MagicMock()
        mock_repo.get_score.side_effect = Exception("DB 연결 실패")
        orch = _make_orchestrator(tmp_path, mock_repo)

        candidates = [{"complex_code": "CC001", "apt_name": "래미안"}]
        result = orch._enrich_with_school(candidates)
        assert result[0]["apt_name"] == "래미안"
        assert "school_score" not in result[0]

    def test_multiple_candidates_all_enriched(self, tmp_path):
        mock_repo = MagicMock()
        mock_repo.get_score.side_effect = lambda code, kind: (
            _make_school_score(code, score=80) if code == "CC001"
            else _make_school_score(code, score=60) if code == "CC002"
            else None
        )
        orch = _make_orchestrator(tmp_path, mock_repo)

        candidates = [
            {"complex_code": "CC001", "apt_name": "래미안"},
            {"complex_code": "CC002", "apt_name": "힐스테이트"},
            {"complex_code": "NONE", "apt_name": "미수집"},
        ]
        result = orch._enrich_with_school(candidates)
        assert result[0]["school_score"] == 80
        assert result[1]["school_score"] == 60
        assert "school_score" not in result[2]

    def test_orchestrator_accepts_school_repo_in_init(self, tmp_path):
        mock_repo = MagicMock()
        orch = _make_orchestrator(tmp_path, mock_repo)
        assert orch._school_repo is mock_repo
