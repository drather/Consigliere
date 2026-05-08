import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

from modules.real_estate.school.school_service import _calc_score

DEFAULT_CFG = dict(ideal=20, warning=28, high_count=3, mid_count=1, w_density=0.30, w_class=0.70)


def test_score_ideal_class_size_many_schools():
    score = _calc_score(nearby_count=5, avg_per_class=18, **DEFAULT_CFG)
    assert score == round(100 * 0.70 + 100 * 0.30)  # 100


def test_score_overcrowded_few_schools():
    score = _calc_score(nearby_count=0, avg_per_class=35, **DEFAULT_CFG)
    assert score == round(20 * 0.70 + 20 * 0.30)  # 20


def test_score_medium_class_medium_density():
    # nearby_count=2 >= mid_count=1 but < high_count=3 → density_score=60
    # avg_per_class=25 > ideal=20 but <= warning=28 → class_score=60
    score = _calc_score(nearby_count=2, avg_per_class=25, **DEFAULT_CFG)
    assert score == round(60 * 0.70 + 60 * 0.30)  # 60


def test_score_ideal_class_no_schools():
    score = _calc_score(nearby_count=0, avg_per_class=15, **DEFAULT_CFG)
    assert score == round(100 * 0.70 + 20 * 0.30)  # 76


def test_score_weight_sum_is_bounded():
    for nearby in range(0, 6):
        for avg in [15, 24, 32]:
            score = _calc_score(nearby_count=nearby, avg_per_class=avg, **DEFAULT_CFG)
            assert 0 <= score <= 100


def test_score_no_class_data_uses_neutral():
    score = _calc_score(nearby_count=3, avg_per_class=0.0, has_class_data=False, **DEFAULT_CFG)
    # class_score=50, density_score=100 → round(50*0.70 + 100*0.30) = round(35+30) = 65
    assert score == round(50 * 0.70 + 100 * 0.30)


def test_scoring_engine_uses_school_score_field():
    import sys, os as _os
    from modules.real_estate.scoring import ScoringEngine

    weights = {"commute": 20, "liquidity": 20, "school": 20, "living_convenience": 20, "price_potential": 20}
    config = {
        "commute_thresholds": [20, 35],
        "household_thresholds": [300, 500],
        "school_keywords": ["명문"],
        "reconstruction_score_map": {"UNKNOWN": 50},
        "data_absent_neutral": 50,
    }
    engine = ScoringEngine(weights=weights, config=config)
    candidate = {
        "apt_name": "반포자이",
        "commute_minutes": 25,
        "household_count": 500,
        "nearest_stations": [],
        "school_zone_notes": None,
        "reconstruction_potential": "UNKNOWN",
        "gtx_benefit": False,
        "school_score": 85,
    }
    result = engine.score_all([candidate])
    assert result[0]["scores"]["school"] == 85
