from datetime import date
from unittest.mock import MagicMock, patch
import pytest

from modules.real_estate.daily_report.daily_report_orchestrator import DailyReportOrchestrator
from modules.real_estate.daily_report.models import AggregatedTransaction, DailyReport


def _make_aggregated(name: str = "래미안", score: float = 0.8) -> AggregatedTransaction:
    return AggregatedTransaction(
        apt_master_id=1,
        apt_name=name,
        district_code="11680",
        sigungu="강남구",
        complex_code="CC001",
        recent_tx_count=3,
        avg_recent_price=280_000_000,
        price_change_pct=2.5,
        exclusive_area=84.0,
        household_count=1200,
        composite_score=score,
    )


def _make_orchestrator(tmp_path) -> DailyReportOrchestrator:
    mock_llm = MagicMock()
    mock_llm.generate_json.return_value = {
        "market_summary": "오늘 강남권 거래가 활발했습니다.",
        "candidate_insights": [
            {
                "apt_name": "래미안",
                "trading_comment": "3건 거래, 전월비 +2.5%",
                "characteristics_comment": "1200세대, 2002년 준공",
                "strategy_comment": "삼성역 22분, 예산 범위 내"
            }
        ],
    }
    mock_prompt_loader = MagicMock()
    mock_prompt_loader.load.return_value = ({"task_type": "REAL_ESTATE_ANALYSIS"}, "prompt text")
    mock_aggregator = MagicMock()
    mock_aggregator.aggregate.return_value = [_make_aggregated()]
    mock_repo = MagicMock()
    mock_repo.save.return_value = str(tmp_path / "daily_2026-05-03.md")

    return DailyReportOrchestrator(
        llm=mock_llm,
        prompt_loader=mock_prompt_loader,
        aggregator=mock_aggregator,
        report_repo=mock_repo,
        db_path=str(tmp_path / "re.db"),
    )


class TestGenerate:
    def test_returns_daily_report(self, tmp_path):
        orch = _make_orchestrator(tmp_path)
        result = orch.generate(
            target_date=date(2026, 5, 3),
            days=3,
            top_k=5,
            persona={},
            macro_summary="기준금리: 3.5%",
        )
        assert isinstance(result, DailyReport)
        assert result.date == "2026-05-03"
        assert result.market_summary == "오늘 강남권 거래가 활발했습니다."

    def test_aggregator_called_with_correct_params(self, tmp_path):
        orch = _make_orchestrator(tmp_path)
        orch.generate(
            target_date=date(2026, 5, 3),
            days=3,
            top_k=5,
            persona={},
            macro_summary="",
        )
        orch._aggregator.aggregate.assert_called_once()
        call_kwargs = orch._aggregator.aggregate.call_args
        # Check days=3 was passed (either as positional or keyword arg)
        args, kwargs = call_kwargs
        assert kwargs.get("days", args[0] if args else None) == 3

    def test_llm_called_with_prompt(self, tmp_path):
        orch = _make_orchestrator(tmp_path)
        orch.generate(
            target_date=date(2026, 5, 3),
            days=3,
            top_k=5,
            persona={},
            macro_summary="기준금리: 3.5%",
        )
        orch._llm.generate_json.assert_called_once()

    def test_report_repo_save_called(self, tmp_path):
        orch = _make_orchestrator(tmp_path)
        orch.generate(
            target_date=date(2026, 5, 3),
            days=3,
            top_k=5,
            persona={},
            macro_summary="",
        )
        orch._repo.save.assert_called_once()
        saved = orch._repo.save.call_args.args[0]
        assert isinstance(saved, DailyReport)

    def test_empty_aggregation_returns_report_with_empty_candidates(self, tmp_path):
        orch = _make_orchestrator(tmp_path)
        orch._aggregator.aggregate.return_value = []
        result = orch.generate(
            target_date=date(2026, 5, 3),
            days=3,
            top_k=5,
            persona={},
            macro_summary="",
        )
        assert isinstance(result, DailyReport)
        assert result.candidates == []


class TestBuildMarkdown:
    def test_markdown_contains_date_and_apt_name(self, tmp_path):
        orch = _make_orchestrator(tmp_path)
        result = orch.generate(
            target_date=date(2026, 5, 3),
            days=3,
            top_k=5,
            persona={},
            macro_summary="기준금리: 3.5%",
        )
        assert "2026-05-03" in result.markdown
        assert "래미안" in result.markdown

    def test_markdown_contains_market_summary(self, tmp_path):
        orch = _make_orchestrator(tmp_path)
        result = orch.generate(
            target_date=date(2026, 5, 3),
            days=3,
            top_k=5,
            persona={},
            macro_summary="",
        )
        assert "오늘 강남권 거래가 활발했습니다." in result.markdown


class TestCommuteQuota:
    def test_cached_commute_does_not_consume_quota(self, tmp_path):
        from modules.real_estate.commute.models import CommuteResult

        mock_repo = MagicMock()
        mock_repo.get.return_value = CommuteResult(
            origin_key="11680__래미안", destination="삼성역", mode="transit",
            duration_minutes=18, distance_meters=900,
        )
        mock_svc = MagicMock()
        mock_svc._repo = mock_repo

        orch = _make_orchestrator(tmp_path)
        orch._commute_svc = mock_svc

        candidates = [{"apt_name": "래미안", "district_code": "11680", "road_address": "서울 강남구 역삼 1"}]
        result = orch._enrich_with_commute_quota(candidates, "삼성역", 37.5088, 127.0633, max_new_calls=0)

        assert result[0]["commute_transit_minutes"] == 18
        mock_svc.get.assert_not_called()

    def test_quota_zero_skips_uncached_candidates(self, tmp_path):
        mock_repo = MagicMock()
        mock_repo.get.return_value = None
        mock_svc = MagicMock()
        mock_svc._repo = mock_repo

        orch = _make_orchestrator(tmp_path)
        orch._commute_svc = mock_svc

        candidates = [{"apt_name": "신규단지", "district_code": "11680", "road_address": "서울 강남구 1"}]
        result = orch._enrich_with_commute_quota(candidates, "삼성역", 37.5088, 127.0633, max_new_calls=0)

        assert result[0].get("commute_transit_minutes") is None
        mock_svc.get.assert_not_called()

    def test_quota_limits_new_api_calls(self, tmp_path):
        from modules.real_estate.commute.models import CommuteResult

        mock_repo = MagicMock()
        mock_repo.get.return_value = None
        mock_svc = MagicMock()
        mock_svc._repo = mock_repo
        mock_svc.get.return_value = CommuteResult(
            origin_key="x", destination="삼성역", mode="transit",
            duration_minutes=25, distance_meters=1200,
        )

        orch = _make_orchestrator(tmp_path)
        orch._commute_svc = mock_svc

        candidates = [
            {"apt_name": f"단지{i}", "district_code": "11680", "road_address": f"서울 강남구 {i}"}
            for i in range(5)
        ]
        orch._enrich_with_commute_quota(candidates, "삼성역", 37.5088, 127.0633, max_new_calls=2)

        assert mock_svc.get.call_count == 2
