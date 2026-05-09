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
