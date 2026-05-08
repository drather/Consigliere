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
