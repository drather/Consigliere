import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

from modules.real_estate.location.dimensions.base import BaseDimension
from modules.real_estate.location.location_scorer import LocationScore


def test_base_dimension_is_abstract():
    import pytest
    with pytest.raises(TypeError):
        BaseDimension({})  # cannot instantiate abstract class


def test_location_score_fields():
    from modules.real_estate.location.dimension_result import DimensionResult
    dr = DimensionResult(id="transportation", label="🚇 교통", score=80, evidence=[])
    score = LocationScore(
        complex_code="A001",
        residential_total=75,
        residential_results=[dr],
        investment_total=65,
        investment_results=[],
        scored_at="2026-05-09T00:00:00+00:00",
    )
    assert score.residential_total == 75
    assert score.investment_total == 65


from modules.real_estate.location.location_repository import LocationRepository


def test_location_repository_upsert_and_get():
    from modules.real_estate.location.dimension_result import DimensionResult
    repo = LocationRepository(":memory:")
    score = LocationScore(
        complex_code="A001",
        residential_total=75,
        residential_results=[
            DimensionResult(id="transportation", label="🚇 교통", score=80, evidence=["20분"]),
            DimensionResult(id="education", label="🏫 교육환경", score=70, evidence=[]),
        ],
        investment_total=65,
        investment_results=[
            DimensionResult(id="commercial", label="🛍️ 상업활성도", score=60, evidence=[]),
            DimensionResult(id="liquidity", label="💧 환금성", score=70, evidence=[]),
        ],
        scored_at="2026-05-09T00:00:00+00:00",
    )
    repo.upsert_score(score)
    result = repo.get_score("A001")
    assert result.residential_total == 75
    assert result.residential_results[0].id == "transportation"
    assert result.residential_results[0].evidence == ["20분"]
    assert result.investment_results[0].id == "commercial"


def test_location_repository_get_missing_returns_none():
    repo = LocationRepository(":memory:")
    assert repo.get_score("NOTEXIST") is None


def test_location_repository_upsert_is_idempotent():
    repo = LocationRepository(":memory:")
    score = LocationScore("A001", 75, [], 65, [], "2026-05-09T00:00:00+00:00")
    repo.upsert_score(score)
    score2 = LocationScore("A001", 80, [], 70, [], "2026-05-09T01:00:00+00:00")
    repo.upsert_score(score2)
    result = repo.get_score("A001")
    assert result.residential_total == 80


from modules.real_estate.location.location_scorer import LocationScorer

_CONFIG = {
    "data_absent_neutral": 50,
    "residential_dimensions": [
        {"id": "transportation", "weight": 0.5},
        {"id": "education",      "weight": 0.5},
    ],
    "investment_dimensions": [
        {"id": "liquidity",       "weight": 0.5},
        {"id": "price_potential", "weight": 0.5},
    ],
    "thresholds": {
        "transportation": {"subway_close_min": 5, "commute_high_min": 20, "commute_medium_min": 35},
        "price_potential": {
            "recon_age_years": 30, "recon_far_max": 200,
            "recon_score_map": {"HIGH": 100, "MEDIUM": 60, "LOW": 20, "COMPLETED": 50, "UNKNOWN": 50},
        },
        "liquidity": {"high_households": 500, "medium_households": 300},
    },
}

def test_location_scorer_returns_location_score():
    scorer = LocationScorer(_CONFIG)
    candidate = {
        "complex_code": "A001",
        "poi_stations": [{"walk_minutes": 3}],
        "commute_transit_minutes": 15,
        "school_score": 80,
        "household_count": 600,
        "reconstruction_potential": "HIGH",
    }
    result = scorer.score(candidate)
    assert result.complex_code == "A001"
    assert 0 <= result.residential_total <= 100
    assert 0 <= result.investment_total <= 100
    ids = [dr.id for dr in result.residential_results]
    assert "transportation" in ids
    assert "education" in ids

def test_location_scorer_breakdown_matches_total():
    scorer = LocationScorer(_CONFIG)
    candidate = {
        "complex_code": "B002",
        "poi_stations": [{"walk_minutes": 3}],
        "commute_transit_minutes": 15,
        "school_score": 80,
        "household_count": 600,
        "reconstruction_potential": "HIGH",
    }
    result = scorer.score(candidate)
    r_map = {dr.id: dr.score for dr in result.residential_results}
    expected = round(r_map["transportation"] * 0.5 + r_map["education"] * 0.5)
    assert result.residential_total == expected

def test_location_scorer_weights_normalize():
    config = dict(_CONFIG)
    config["residential_dimensions"] = [
        {"id": "transportation", "weight": 2},
        {"id": "education",      "weight": 2},
    ]
    scorer = LocationScorer(config)
    candidate = {"complex_code": "C003", "school_score": 100,
                 "poi_stations": [{"walk_minutes": 3}], "commute_transit_minutes": 10}
    result = scorer.score(candidate)
    assert result.residential_total == 100


# ── DimensionResult ────────────────────────────────────────────
from modules.real_estate.location.dimension_result import DimensionResult

def test_dimension_result_fields():
    dr = DimensionResult(id="transportation", label="🚇 교통", score=80, evidence=["대중교통 20분"])
    assert dr.id == "transportation"
    assert dr.label == "🚇 교통"
    assert dr.score == 80
    assert dr.evidence == ["대중교통 20분"]

def test_dimension_result_default_evidence():
    dr = DimensionResult(id="foo", label="bar", score=50)
    assert dr.evidence == []


# ── LocationScore 새 구조 ──────────────────────────────────────

def test_location_score_has_results_not_breakdown():
    """LocationScore는 residential_results, investment_results를 List[DimensionResult]로 가진다."""
    dr = DimensionResult(id="transportation", label="🚇 교통", score=80, evidence=["20분"])
    score = LocationScore(
        complex_code="A001",
        residential_total=80,
        residential_results=[dr],
        investment_total=65,
        investment_results=[],
        scored_at="2026-05-10T00:00:00+00:00",
    )
    assert score.residential_results[0].id == "transportation"
    assert score.residential_results[0].label == "🚇 교통"
    assert score.residential_results[0].evidence == ["20분"]

def test_scorer_returns_dimension_results():
    """LocationScorer.score()가 residential_results에 DimensionResult 리스트를 반환한다."""
    scorer = LocationScorer(_CONFIG)
    candidate = {
        "complex_code": "A001",
        "poi_stations": [{"walk_minutes": 3}],
        "commute_transit_minutes": 15,
        "school_score": 80,
        "household_count": 600,
        "reconstruction_potential": "HIGH",
    }
    result = scorer.score(candidate)
    assert isinstance(result.residential_results, list)
    assert len(result.residential_results) == 2  # _CONFIG has transportation + education
    assert result.residential_results[0].id in ("transportation", "education")
    assert isinstance(result.residential_results[0].score, int)
    assert isinstance(result.residential_results[0].evidence, list)

def test_scorer_total_matches_weighted_results():
    """residential_total은 residential_results 점수의 가중 평균과 일치해야 한다."""
    scorer = LocationScorer(_CONFIG)
    candidate = {"complex_code": "B002", "poi_stations": [{"walk_minutes": 3}],
                 "commute_transit_minutes": 15, "school_score": 80}
    result = scorer.score(candidate)
    r_map = {dr.id: dr.score for dr in result.residential_results}
    expected = round(r_map["transportation"] * 0.5 + r_map["education"] * 0.5)
    assert result.residential_total == expected
