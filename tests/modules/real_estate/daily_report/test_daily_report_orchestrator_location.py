import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

from datetime import date
from unittest.mock import MagicMock, patch

from modules.real_estate.daily_report.daily_report_orchestrator import DailyReportOrchestrator


def _make_candidate(name: str = "래미안") -> dict:
    return {
        "apt_master_id": 1,
        "apt_name": name,
        "district_code": "11680",
        "sigungu": "강남구",
        "complex_code": "CC001",
        "recent_tx_count": 3,
        "avg_recent_price": 280_000_000,
        "price_change_pct": 2.5,
        "exclusive_area": 84.0,
        "household_count": 1200,
        "composite_score": 0.8,
        "road_address": None,
        "pnu": None,
        "_recent_tx_points": [],
    }


def _make_orchestrator(tmp_path) -> DailyReportOrchestrator:
    mock_llm = MagicMock()
    mock_llm.generate_json.return_value = {
        "market_bullets": ["강남권 거래 활발"],
        "candidate_insights": [
            {
                "apt_name": "래미안",
                "trading_bullets": [],
                "characteristics_bullets": [],
                "strategy_bullets": [],
            }
        ],
    }
    mock_prompt_loader = MagicMock()
    mock_prompt_loader.load.return_value = ({"task_type": "REAL_ESTATE_ANALYSIS"}, "prompt text")
    mock_aggregator = MagicMock()
    mock_aggregator.aggregate.return_value = [_make_candidate()]
    mock_repo = MagicMock()
    mock_repo.save.return_value = str(tmp_path / "daily.md")

    return DailyReportOrchestrator(
        llm=mock_llm,
        prompt_loader=mock_prompt_loader,
        aggregator=mock_aggregator,
        report_repo=mock_repo,
        db_path=str(tmp_path / "re.db"),
    )


class TestLocationScorePersistence:
    def test_upsert_score_called_after_scoring(self, tmp_path):
        """generate() 실행 후 LocationRepository.upsert_score가 최소 1회 호출되어야 한다."""
        from modules.real_estate.location.location_scorer import LocationScore, LocationScorer
        from unittest.mock import patch

        orch = _make_orchestrator(tmp_path)
        mock_loc_repo = MagicMock()
        orch._loc_repo = mock_loc_repo

        mock_scorer = MagicMock(spec=LocationScorer)
        mock_scorer.score.return_value = LocationScore(
            complex_code="CC001",
            residential_total=75,
            residential_results=[],
            investment_total=65,
            investment_results=[],
            scored_at="2026-05-27T00:00:00+00:00",
        )
        with patch(
            "modules.real_estate.daily_report.daily_report_orchestrator._load_scorer",
            return_value=mock_scorer,
        ):
            orch.generate(
                target_date=date(2026, 5, 27),
                days=3,
                top_k=5,
                persona={},
                macro_summary="기준금리: 3.5%",
            )

        mock_loc_repo.upsert_score.assert_called()

    def test_upsert_score_called_once_per_candidate(self, tmp_path):
        """후보 단지 수만큼 upsert_score가 호출되어야 한다."""
        from modules.real_estate.location.location_scorer import LocationScore, LocationScorer
        from unittest.mock import patch

        orch = _make_orchestrator(tmp_path)
        orch._aggregator.aggregate.return_value = [
            _make_candidate("래미안"),
            _make_candidate("자이"),
            _make_candidate("힐스테이트"),
        ]
        mock_loc_repo = MagicMock()
        orch._loc_repo = mock_loc_repo

        mock_scorer = MagicMock(spec=LocationScorer)
        mock_scorer.score.return_value = LocationScore(
            complex_code="CC001",
            residential_total=75,
            residential_results=[],
            investment_total=65,
            investment_results=[],
            scored_at="2026-05-27T00:00:00+00:00",
        )
        with patch(
            "modules.real_estate.daily_report.daily_report_orchestrator._load_scorer",
            return_value=mock_scorer,
        ):
            orch.generate(
                target_date=date(2026, 5, 27),
                days=3,
                top_k=5,
                persona={},
                macro_summary="",
            )

        assert mock_loc_repo.upsert_score.call_count == 3

    def test_upsert_score_receives_location_score_object(self, tmp_path):
        """upsert_score에 전달되는 인자가 complex_code 속성을 가진 LocationScore여야 한다."""
        from modules.real_estate.location.location_scorer import LocationScore, LocationScorer
        from unittest.mock import patch

        orch = _make_orchestrator(tmp_path)
        mock_loc_repo = MagicMock()
        orch._loc_repo = mock_loc_repo

        # Guarantee scorer always runs by patching _load_scorer
        mock_scorer = MagicMock(spec=LocationScorer)
        mock_scorer.score.return_value = LocationScore(
            complex_code="CC001",
            residential_total=75,
            residential_results=[],
            investment_total=65,
            investment_results=[],
            scored_at="2026-05-27T00:00:00+00:00",
        )
        with patch(
            "modules.real_estate.daily_report.daily_report_orchestrator._load_scorer",
            return_value=mock_scorer,
        ):
            orch.generate(
                target_date=date(2026, 5, 27),
                days=3,
                top_k=5,
                persona={},
                macro_summary="",
            )

        mock_loc_repo.upsert_score.assert_called()
        arg = mock_loc_repo.upsert_score.call_args_list[0].args[0]
        assert isinstance(arg, LocationScore)
        assert hasattr(arg, "complex_code")
        assert hasattr(arg, "residential_total")
        assert hasattr(arg, "investment_total")

    def test_loc_repo_initialized_in_constructor(self, tmp_path):
        """DailyReportOrchestrator가 생성될 때 _loc_repo 속성이 존재해야 한다."""
        orch = _make_orchestrator(tmp_path)
        assert hasattr(orch, "_loc_repo")

    def test_upsert_failure_does_not_break_report(self, tmp_path):
        """upsert_score가 예외를 던져도 generate()는 DailyReport를 정상 반환해야 한다."""
        from modules.real_estate.daily_report.models import DailyReport

        orch = _make_orchestrator(tmp_path)
        mock_loc_repo = MagicMock()
        mock_loc_repo.upsert_score.side_effect = Exception("DB 오류")
        orch._loc_repo = mock_loc_repo

        result = orch.generate(
            target_date=date(2026, 5, 27),
            days=3,
            top_k=5,
            persona={},
            macro_summary="",
        )

        assert isinstance(result, DailyReport)
