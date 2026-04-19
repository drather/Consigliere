"""
TDD: 1-A 실거래가 분석 품질 향상 — household_count 실값 반영 점수 검증
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src')))

from modules.real_estate.scoring import ScoringEngine


DEFAULT_WEIGHTS = {
    "commute": 20,
    "liquidity": 20,
    "price_potential": 20,
    "living_convenience": 20,
    "school": 20,
}

DEFAULT_CONFIG = {
    "commute_thresholds": [20, 35],
    "household_thresholds": [300, 500],
    "school_keywords": ["학원가", "명문"],
    "reconstruction_score_map": {
        "HIGH": 100, "MEDIUM": 60, "LOW": 20, "COMPLETED": 50, "UNKNOWN": 10
    },
}


def make_candidate(**kwargs):
    base = {
        "apt_name": "테스트아파트",
        "commute_minutes": 25,
        "household_count": 0,
        "nearest_stations": [],
        "school_zone_notes": "",
        "reconstruction_potential": "UNKNOWN",
        "gtx_benefit": False,
        "price": 800_000_000,
    }
    base.update(kwargs)
    return base


class TestLiquidityScore:
    def setup_method(self):
        self.engine = ScoringEngine(DEFAULT_WEIGHTS, DEFAULT_CONFIG)

    def test_household_count_zero_returns_low(self):
        """household_count=0 이면 _LOW(20) 반환 — 마스터 미조회 케이스."""
        c = make_candidate(household_count=0)
        score = self.engine._score_liquidity(c)
        assert score == 20  # _LOW

    def test_household_count_small_returns_low(self):
        """세대수 300 미만 → LOW."""
        c = make_candidate(household_count=150)
        score = self.engine._score_liquidity(c)
        assert score == 20

    def test_household_count_medium_returns_medium(self):
        """세대수 300~500 → MEDIUM(60)."""
        c = make_candidate(household_count=400)
        score = self.engine._score_liquidity(c)
        assert score == 60

    def test_household_count_large_returns_high(self):
        """세대수 500 이상 → HIGH(100)."""
        c = make_candidate(household_count=2444)
        score = self.engine._score_liquidity(c)
        assert score == 100

    def test_household_count_exactly_threshold(self):
        """임계값 경계: 300 → MEDIUM (low_t 이상이므로)."""
        c = make_candidate(household_count=300)
        score = self.engine._score_liquidity(c)
        assert score == 60

    def test_household_count_exactly_high_threshold(self):
        """임계값 경계: 500 → HIGH."""
        c = make_candidate(household_count=500)
        score = self.engine._score_liquidity(c)
        assert score == 100

    def test_score_all_uses_real_household_count(self):
        """score_all()에서 실제 household_count가 총점에 반영된다."""
        low_c = make_candidate(apt_name="소형단지", household_count=100)
        high_c = make_candidate(apt_name="대형단지", household_count=1000)
        results = self.engine.score_all([low_c, high_c])
        # 대형단지(liquidity HIGH)가 소형단지(liquidity LOW)보다 총점 높아야 한다
        names = [r["apt_name"] for r in results]
        assert names[0] == "대형단지", "세대수 많은 단지가 더 높은 점수를 받아야 한다"

    def test_missing_household_count_defaults_to_zero(self):
        """household_count 키 없을 때 기본값 0 처리 — KeyError 없어야 한다."""
        c = {"apt_name": "키없는아파트"}
        score = self.engine._score_liquidity(c)
        assert score == 50  # data_absent_neutral (세대수 없음 → 중립값)
