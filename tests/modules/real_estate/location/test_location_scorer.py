import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

from modules.real_estate.location.dimensions.base import BaseDimension
from modules.real_estate.location.location_scorer import LocationScore


def test_base_dimension_is_abstract():
    import pytest
    with pytest.raises(TypeError):
        BaseDimension({})  # cannot instantiate abstract class


def test_location_score_fields():
    score = LocationScore(
        complex_code="A001",
        residential_total=75,
        residential_breakdown={"transportation": 80},
        investment_total=65,
        investment_breakdown={"commercial": 60},
        scored_at="2026-05-09T00:00:00+00:00",
    )
    assert score.residential_total == 75
    assert score.investment_total == 65


from modules.real_estate.location.location_repository import LocationRepository


def test_location_repository_upsert_and_get():
    repo = LocationRepository(":memory:")
    score = LocationScore(
        complex_code="A001",
        residential_total=75,
        residential_breakdown={"transportation": 80, "education": 70},
        investment_total=65,
        investment_breakdown={"commercial": 60, "liquidity": 70},
        scored_at="2026-05-09T00:00:00+00:00",
    )
    repo.upsert_score(score)
    result = repo.get_score("A001")
    assert result.residential_total == 75
    assert result.investment_breakdown["commercial"] == 60


def test_location_repository_get_missing_returns_none():
    repo = LocationRepository(":memory:")
    assert repo.get_score("NOTEXIST") is None


def test_location_repository_upsert_is_idempotent():
    repo = LocationRepository(":memory:")
    score = LocationScore("A001", 75, {}, 65, {}, "2026-05-09T00:00:00+00:00")
    repo.upsert_score(score)
    score2 = LocationScore("A001", 80, {}, 70, {}, "2026-05-09T01:00:00+00:00")
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
        "commute_minutes": 15,
        "school_score": 80,
        "household_count": 600,
        "reconstruction_potential": "HIGH",
    }
    result = scorer.score(candidate)
    assert result.complex_code == "A001"
    assert 0 <= result.residential_total <= 100
    assert 0 <= result.investment_total <= 100
    assert "transportation" in result.residential_breakdown
    assert "education" in result.residential_breakdown

def test_location_scorer_breakdown_matches_total():
    scorer = LocationScorer(_CONFIG)
    candidate = {
        "complex_code": "B002",
        "poi_stations": [{"walk_minutes": 3}],
        "commute_minutes": 15,
        "school_score": 80,
        "household_count": 600,
        "reconstruction_potential": "HIGH",
    }
    result = scorer.score(candidate)
    expected_residential = round(
        result.residential_breakdown["transportation"] * 0.5
        + result.residential_breakdown["education"] * 0.5
    )
    assert result.residential_total == expected_residential

def test_location_scorer_weights_normalize():
    config = dict(_CONFIG)
    config["residential_dimensions"] = [
        {"id": "transportation", "weight": 2},
        {"id": "education",      "weight": 2},
    ]
    scorer = LocationScorer(config)
    candidate = {"complex_code": "C003", "school_score": 100,
                 "poi_stations": [{"walk_minutes": 3}], "commute_minutes": 10}
    result = scorer.score(candidate)
    assert result.residential_total == 100
