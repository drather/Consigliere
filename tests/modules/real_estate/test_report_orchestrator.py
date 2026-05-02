import os
import sys
import pytest
from datetime import date
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src')))

from modules.real_estate.report_orchestrator import ReportOrchestrator
from modules.real_estate.report_repository import ProfessionalReport
from modules.real_estate.poi_collector import PoiData
from modules.real_estate.trend_analyzer import TrendData


def _make_mock_candidate():
    return {
        "apt_name": "래미안원베일리",
        "apt_master_id": 1,
        "district_code": "11650",
        "district_name": "서초구",
        "complex_code": "1234567890",
        "road_address": "서울시 서초구 반포대로 201",
        "household_count": 2990,
        "build_year": 1994,
        "floor_area_ratio": 198.0,
        "building_coverage_ratio": 18.0,
        "price": 1_500_000_000,
        "exclusive_area": 84.0,
        "commute_transit_minutes": 23,
        "reconstruction_potential": "UNKNOWN",
        "lat": 37.5072,
        "lng": 126.9959,
    }


def _make_scoring_config():
    return {
        "commute_thresholds": [20, 35],
        "household_thresholds": [300, 500],
        "school_keywords": ["학원가"],
        "reconstruction_score_map": {"HIGH": 100, "MEDIUM": 60, "LOW": 20, "COMPLETED": 50, "UNKNOWN": 50},
        "data_absent_neutral": 50,
        "poi_close_station_walk_minutes": 5,
        "poi_academy_high_threshold": 30,
        "poi_academy_medium_threshold": 15,
        "reconstruction_age_years": 30,
        "reconstruction_far_max": 200,
    }


def _make_persona_data():
    return {
        "user": {
            "assets": {"total": 300_000_000},
            "income": {"total": 160_000_000},
            "plans": {"primary_goal": "실거주 및 투자 가치"},
        },
        "priority_weights": {
            "commute": 25, "liquidity": 25, "price_potential": 25,
            "living_convenience": 17, "school": 8,
        },
    }


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.generate_json.side_effect = [
        # LocationAgent
        {"analyses": [{"apt_name": "래미안원베일리", "text": "강남역 도보 5분 초역세권"}]},
        # SchoolAgent
        {"analyses": [{"apt_name": "래미안원베일리", "text": "학원 52개 최상위 학군"}]},
        # StrategyAgent
        {"market_diagnosis": "관망 유리", "strategy": "임장 후 결정", "action_short": "OO 임장", "action_mid": "금리 하락 시 매수", "risks": ["금리 인상", "규제 강화"]},
    ]
    return llm


@pytest.fixture
def mock_prompt_loader():
    loader = MagicMock()
    loader.load_with_cache_split.return_value = ("시스템 프롬프트", "유저 프롬프트 {{candidates_poi_json}} {{candidates_school_json}} {{macro_summary}} {{budget_summary}} {{user_goals}} {{ranked_candidates_summary}}")
    return loader


@pytest.fixture
def mock_poi_collector():
    collector = MagicMock()
    collector.collect.return_value = PoiData(
        complex_code="1234567890",
        subway_stations=[{"name": "강남역", "walk_minutes": 5}],
        schools_count=2,
        academies_count=47,
        marts_count=3,
    )
    return collector


@pytest.fixture
def mock_trend_analyzer():
    analyzer = MagicMock()
    analyzer.get_trend.return_value = TrendData(
        apt_master_id=1, area_sqm=84.0,
        avg_price=1_500_000_000, price_change_pct=2.1,
        monthly_volume=8.0, price_min=1_400_000_000,
        price_max=1_600_000_000, sample_count=10,
    )
    return analyzer


@pytest.fixture
def orchestrator(mock_llm, mock_prompt_loader, mock_poi_collector, mock_trend_analyzer, tmp_path):
    from modules.real_estate.report_repository import ReportRepository
    report_repo = ReportRepository(storage_path=str(tmp_path))
    return ReportOrchestrator(
        llm=mock_llm,
        prompt_loader=mock_prompt_loader,
        poi_collector=mock_poi_collector,
        trend_analyzer=mock_trend_analyzer,
        report_repository=report_repo,
        re_db_path=str(tmp_path / "re.db"),  # ← 추가
    )


class TestReportOrchestrator:
    def test_generate_returns_professional_report(self, orchestrator):
        report = orchestrator.generate(
            target_date=date(2026, 5, 1),
            candidates=[_make_mock_candidate()],
            persona_data=_make_persona_data(),
            scoring_config=_make_scoring_config(),
            macro_summary="기준금리 3.5%, 주담대 4.2%",
        )
        assert isinstance(report, ProfessionalReport)
        assert report.date == "2026-05-01"
        assert report.budget_available > 0
        assert len(report.candidates_summary) >= 1
        assert report.markdown != ""

    def test_generate_saves_to_repository(self, orchestrator, tmp_path):
        orchestrator.generate(
            target_date=date(2026, 5, 1),
            candidates=[_make_mock_candidate()],
            persona_data=_make_persona_data(),
            scoring_config=_make_scoring_config(),
            macro_summary="",
        )
        assert (tmp_path / "2026-05-01.json").exists()
        assert (tmp_path / "2026-05-01.md").exists()

    def test_poi_failure_does_not_break_pipeline(self, orchestrator, mock_poi_collector):
        mock_poi_collector.collect.side_effect = Exception("API 실패")
        report = orchestrator.generate(
            target_date=date(2026, 5, 1),
            candidates=[_make_mock_candidate()],
            persona_data=_make_persona_data(),
            scoring_config=_make_scoring_config(),
            macro_summary="",
        )
        assert isinstance(report, ProfessionalReport)


import sqlite3 as _sqlite3
from modules.real_estate.report_orchestrator import _enrich_with_building


def _setup_building_db(db_path: str):
    """테스트용 building_master 테이블 생성."""
    with _sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS building_master (
                mgm_pk TEXT PRIMARY KEY,
                building_name TEXT,
                sigungu_code TEXT,
                floor_area_ratio REAL,
                building_coverage_ratio REAL,
                completion_year INTEGER,
                collected_at TEXT
            )
        """)
        conn.execute(
            "INSERT INTO building_master VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("BM001", "래미안테스트", "11650", 247.3, 21.8, 2002, "2026-01-01"),
        )


class TestEnrichWithBuilding:
    def test_pnu_match_fills_far_bcr_build_year(self, tmp_path):
        """pnu가 있고 building_master에 매칭되면 FAR·BCR·build_year가 채워진다."""
        db_path = str(tmp_path / "re.db")
        _setup_building_db(db_path)
        candidates = [{"apt_name": "래미안", "pnu": "BM001"}]

        result = _enrich_with_building(candidates, db_path)

        assert result[0]["floor_area_ratio"] == pytest.approx(247.3)
        assert result[0]["building_coverage_ratio"] == pytest.approx(21.8)
        assert result[0]["build_year"] == 2002

    def test_no_pnu_uses_approved_date_fallback(self, tmp_path):
        """pnu 없고 approved_date가 있으면 앞 4자리로 build_year 파생."""
        db_path = str(tmp_path / "re.db")
        _setup_building_db(db_path)
        candidates = [{"apt_name": "기타단지", "pnu": None, "approved_date": "20050315"}]

        result = _enrich_with_building(candidates, db_path)

        assert result[0]["build_year"] == 2005
        assert result[0].get("floor_area_ratio") is None

    def test_no_match_returns_candidate_unchanged(self, tmp_path):
        """pnu가 있지만 building_master에 없으면 원본 그대로 반환."""
        db_path = str(tmp_path / "re.db")
        _setup_building_db(db_path)
        candidates = [{"apt_name": "미매핑단지", "pnu": "UNKNOWN_PNU"}]

        result = _enrich_with_building(candidates, db_path)

        assert result[0].get("floor_area_ratio") is None

    def test_empty_db_path_returns_candidates_unchanged(self):
        """db_path가 빈 문자열이면 DB 조회 없이 원본 반환."""
        candidates = [{"apt_name": "테스트", "pnu": "BM001"}]
        result = _enrich_with_building(candidates, "")
        assert result[0].get("floor_area_ratio") is None
        assert result[0]["apt_name"] == "테스트"
