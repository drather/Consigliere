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


from modules.real_estate.report_orchestrator import _resolve_workplace_coords, _enrich_with_commute
from modules.real_estate.commute.models import CommuteResult


class TestResolveWorkplaceCoords:
    def test_returns_station_and_coords_when_geocode_succeeds(self):
        mock_geocoder = MagicMock()
        mock_geocoder.geocode.return_value = (37.5088, 127.0633)
        persona = {"commute": {"workplace_station": "삼성역"}}

        name, lat, lng = _resolve_workplace_coords(persona, mock_geocoder)

        assert name == "삼성역"
        assert lat == pytest.approx(37.5088)
        assert lng == pytest.approx(127.0633)

    def test_returns_none_triple_when_geocode_fails(self):
        mock_geocoder = MagicMock()
        mock_geocoder.geocode.return_value = None
        persona = {"commute": {"workplace_station": "없는역"}}

        name, lat, lng = _resolve_workplace_coords(persona, mock_geocoder)

        assert name is None and lat is None and lng is None

    def test_returns_none_triple_when_no_workplace_station(self):
        mock_geocoder = MagicMock()
        persona = {"commute": {}}

        name, lat, lng = _resolve_workplace_coords(persona, mock_geocoder)

        assert name is None and lat is None and lng is None


class TestEnrichWithCommute:
    def test_fills_commute_transit_minutes(self):
        mock_svc = MagicMock()
        mock_svc.get.return_value = CommuteResult(
            origin_key="11680__래미안",
            destination="삼성역",
            mode="transit",
            duration_minutes=22,
            distance_meters=1500,
        )
        candidates = [{"apt_name": "래미안", "district_code": "11680", "road_address": "서울 강남구 역삼동 1"}]

        result = _enrich_with_commute(candidates, mock_svc, "삼성역", 37.5088, 127.0633)

        assert result[0]["commute_transit_minutes"] == 22

    def test_skips_when_no_road_address(self):
        mock_svc = MagicMock()
        candidates = [{"apt_name": "주소없는단지", "district_code": "11680", "road_address": ""}]

        result = _enrich_with_commute(candidates, mock_svc, "삼성역", 37.5088, 127.0633)

        assert result[0].get("commute_transit_minutes") is None
        mock_svc.get.assert_not_called()

    def test_handles_commute_service_exception_gracefully(self):
        mock_svc = MagicMock()
        mock_svc.get.side_effect = RuntimeError("T-map API 실패")
        candidates = [{"apt_name": "에러단지", "district_code": "11680", "road_address": "서울 강남구 1"}]

        result = _enrich_with_commute(candidates, mock_svc, "삼성역", 37.5088, 127.0633)

        assert result[0].get("commute_transit_minutes") is None  # 예외 삼켜짐


from modules.real_estate.report_orchestrator import _enrich_with_trend


class TestEnrichWithTrendMultiArea:
    def test_tries_first_area_and_returns_on_hit(self):
        """preferred_areas=[84, 99]일 때 84㎡ 데이터 있으면 84 기준 trend 반환."""
        mock_analyzer = MagicMock()
        mock_analyzer.get_trend.side_effect = lambda apt_master_id, area_sqm: (
            TrendData(apt_master_id=1, area_sqm=area_sqm, avg_price=2_800_000_000,
                      price_change_pct=1.5, monthly_volume=3.0,
                      price_min=2_700_000_000, price_max=2_900_000_000, sample_count=5)
            if area_sqm == 84.0 else None
        )
        candidates = [{"apt_name": "래미안", "id": 1}]

        result = _enrich_with_trend(candidates, mock_analyzer, preferred_areas=[84.0, 99.0])

        assert result[0]["_trend"].area_sqm == 84.0
        assert result[0]["_trend_area_sqm"] == 84.0
        # 84로 히트했으니 99는 시도 안 함
        assert mock_analyzer.get_trend.call_count == 1

    def test_falls_back_to_second_area_when_first_empty(self):
        """84㎡ 데이터 없고 99㎡ 데이터 있으면 99 기준 trend 반환."""
        mock_analyzer = MagicMock()
        mock_analyzer.get_trend.side_effect = lambda apt_master_id, area_sqm: (
            TrendData(apt_master_id=1, area_sqm=area_sqm, avg_price=3_200_000_000,
                      price_change_pct=0.5, monthly_volume=1.2,
                      price_min=3_100_000_000, price_max=3_300_000_000, sample_count=3)
            if area_sqm == 99.0 else None
        )
        candidates = [{"apt_name": "팰리스", "id": 1}]

        result = _enrich_with_trend(candidates, mock_analyzer, preferred_areas=[84.0, 99.0])

        assert result[0]["_trend"].area_sqm == 99.0
        assert result[0]["_trend_area_sqm"] == 99.0
        assert mock_analyzer.get_trend.call_count == 2  # 84 실패 후 99 시도

    def test_no_data_in_any_area_returns_no_trend(self):
        """모든 면적대에서 None이면 _trend 키 없음."""
        mock_analyzer = MagicMock()
        mock_analyzer.get_trend.return_value = None
        candidates = [{"apt_name": "미수집단지", "id": 1}]

        result = _enrich_with_trend(candidates, mock_analyzer, preferred_areas=[84.0, 99.0])

        assert result[0].get("_trend") is None
