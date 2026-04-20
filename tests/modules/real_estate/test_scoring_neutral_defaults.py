import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src"))

from modules.real_estate.scoring import ScoringEngine

NEUTRAL = 50

CONFIG_WITH_NEUTRAL = {
    "commute_thresholds": [20, 35],
    "household_thresholds": [300, 500],
    "school_keywords": ["학원가", "명문"],
    "reconstruction_score_map": {
        "HIGH": 100, "MEDIUM": 60, "LOW": 20, "COMPLETED": 50, "UNKNOWN": 50
    },
    "data_absent_neutral": NEUTRAL,
}

WEIGHTS = {"commute": 25, "liquidity": 25, "price_potential": 25, "living_convenience": 17, "school": 8}


def make_engine():
    return ScoringEngine(weights=WEIGHTS, config=CONFIG_WITH_NEUTRAL)


def test_liquidity_neutral_when_household_count_absent():
    """household_count 키 자체가 없으면 중립값(50)을 반환한다."""
    engine = make_engine()
    assert engine._score_liquidity({"apt_name": "테스트"}) == NEUTRAL


def test_liquidity_low_when_household_count_zero():
    """household_count=0은 실제 0 → LOW(20)."""
    engine = make_engine()
    assert engine._score_liquidity({"household_count": 0}) == 20


def test_liquidity_high_when_above_threshold():
    engine = make_engine()
    assert engine._score_liquidity({"household_count": 600}) == 100


def test_commute_neutral_when_minutes_absent():
    engine = make_engine()
    assert engine._score_commute({"apt_name": "테스트"}) == NEUTRAL


def test_school_neutral_when_notes_absent():
    engine = make_engine()
    assert engine._score_school({"apt_name": "테스트"}) == NEUTRAL


def test_school_low_when_notes_empty_string():
    """빈 문자열 = 데이터 있지만 해당 없음 → LOW(20)."""
    engine = make_engine()
    assert engine._score_school({"school_zone_notes": "", "elementary_schools": []}) == 20


def test_living_convenience_neutral_when_stations_absent():
    engine = make_engine()
    assert engine._score_living_convenience({"apt_name": "테스트"}) == NEUTRAL


def test_living_convenience_low_when_stations_empty_list():
    """[] = area_intel에 역 없음 → LOW(20)."""
    engine = make_engine()
    assert engine._score_living_convenience({"nearest_stations": []}) == 20


def test_price_potential_neutral_for_unknown_without_horea():
    """UNKNOWN + horea_scores 없음 → 중립값(50)."""
    engine = make_engine()
    c = {"reconstruction_potential": "UNKNOWN"}
    assert engine._score_price_potential(c, horea_scores=None) == NEUTRAL


def test_price_potential_high_from_reconstruction():
    """재건축 HIGH는 중립값 무관하게 100."""
    engine = make_engine()
    c = {"reconstruction_potential": "HIGH"}
    assert engine._score_price_potential(c, horea_scores=None) == 100


def test_price_potential_boosted_by_active_horea():
    """ACTIVE horea score=80 → boost=32 → base(50)+32=82."""
    engine = make_engine()
    c = {"reconstruction_potential": "UNKNOWN", "district_name": "강남구"}
    horea_scores = {"강남구": {"score": 80, "verdict": "ACTIVE", "reasoning": "재건축 인허가"}}
    result = engine._score_price_potential(c, horea_scores=horea_scores)
    assert result == min(100, NEUTRAL + int(80 * 0.4))  # 50 + 32 = 82


def test_price_potential_no_boost_for_none_verdict():
    """score=0(NONE) → boost=0 → base(50)."""
    engine = make_engine()
    c = {"reconstruction_potential": "UNKNOWN", "district_name": "강남구"}
    horea_scores = {"강남구": {"score": 0, "verdict": "NONE", "reasoning": "없음"}}
    result = engine._score_price_potential(c, horea_scores=horea_scores)
    assert result == NEUTRAL


def test_price_potential_no_district_match_stays_neutral():
    """district_name이 horea_scores 키와 불일치 → 중립값 유지."""
    engine = make_engine()
    c = {"reconstruction_potential": "UNKNOWN", "district_name": "관악구"}
    horea_scores = {"강남구": {"score": 80, "verdict": "ACTIVE", "reasoning": "..."}}
    assert engine._score_price_potential(c, horea_scores=horea_scores) == NEUTRAL


def test_score_all_uses_horea_scores_param():
    """score_all에 horea_scores 전달 시 price_potential에 반영된다."""
    engine = make_engine()
    c = {
        "apt_name": "강남아파트", "district_name": "강남구",
        "reconstruction_potential": "UNKNOWN",
    }
    horea_scores = {"강남구": {"score": 100, "verdict": "ACTIVE", "reasoning": "GTX"}}
    results = engine.score_all([c], horea_scores=horea_scores)
    assert results[0]["scores"]["price_potential"] == min(100, NEUTRAL + int(100 * 0.4))
