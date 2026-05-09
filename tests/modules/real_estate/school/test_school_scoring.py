import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

from modules.real_estate.school.school_service import _calc_score

DEFAULT_CFG = dict(
    transfer_high=0.06,
    transfer_medium=0.03,
    high_count=3, mid_count=1,
    w_density=0.30, w_quality=0.70,
)


def test_score_high_transfer_many_schools():
    score = _calc_score(nearby_count=5, avg_transfer_rate=0.08, **DEFAULT_CFG)
    assert score == round(100 * 0.70 + 100 * 0.30)  # 100


def test_score_low_transfer_few_schools():
    score = _calc_score(nearby_count=0, avg_transfer_rate=0.01, **DEFAULT_CFG)
    assert score == round(20 * 0.70 + 20 * 0.30)  # 20


def test_score_medium_transfer_medium_density():
    # nearby_count=2 >= mid_count=1 but < high_count=3 → density_score=60
    # avg_transfer_rate=0.04 >= medium=0.03 but < high=0.06 → quality_score=60
    score = _calc_score(nearby_count=2, avg_transfer_rate=0.04, **DEFAULT_CFG)
    assert score == round(60 * 0.70 + 60 * 0.30)  # 60


def test_score_high_transfer_no_schools():
    score = _calc_score(nearby_count=0, avg_transfer_rate=0.08, **DEFAULT_CFG)
    assert score == round(100 * 0.70 + 20 * 0.30)  # 76


def test_score_weight_sum_is_bounded():
    for nearby in range(0, 6):
        for rate in [0.01, 0.04, 0.08]:
            score = _calc_score(nearby_count=nearby, avg_transfer_rate=rate, **DEFAULT_CFG)
            assert 0 <= score <= 100


def test_score_no_quality_data_uses_neutral():
    score = _calc_score(nearby_count=3, avg_transfer_rate=0.0, has_quality_data=False, **DEFAULT_CFG)
    # quality_score=50, density_score=100 → round(50*0.70 + 100*0.30) = 65
    assert score == round(50 * 0.70 + 100 * 0.30)
