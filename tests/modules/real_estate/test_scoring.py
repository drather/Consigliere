"""
scoring.py 단위 테스트
5개 기준 가중치 점수 계산 엔진 검증
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src')))


def make_candidate(**kwargs):
    base = {
        "apt_name": "테스트아파트",
        "commute_minutes": 25,
        "household_count": 500,
        "nearest_stations": [{"name": "역삼역", "line": "2호선", "walk_minutes": 5}],
        "school_zone_notes": "역삼초 배정권.",
        "reconstruction_potential": "MEDIUM",
        "gtx_benefit": False,
        "price": 800_000_000,
    }
    base.update(kwargs)
    return base


DEFAULT_WEIGHTS = {
    "commute": 25,
    "liquidity": 25,
    "price_potential": 25,
    "living_convenience": 17,
    "school": 8,
}

DEFAULT_CONFIG = {
    "commute_thresholds": [20, 35],
    "household_thresholds": [300, 500],
    "school_keywords": ["학원가", "명문", "특목고", "자사고"],
    "reconstruction_score_map": {
        "HIGH": 100, "MEDIUM": 60, "LOW": 20, "COMPLETED": 50, "UNKNOWN": 10
    },
}


class TestScoringEngine:
    def _score(self, candidates, weights=None, config=None, horea=None):
        from modules.real_estate.scoring import ScoringEngine
        engine = ScoringEngine(
            weights=weights or DEFAULT_WEIGHTS,
            config=config or DEFAULT_CONFIG,
        )
        return engine.score_all(candidates, horea_data=horea or {})

    def test_commute_high_score(self):
        c = make_candidate(commute_minutes=15)
        results = self._score([c])
        assert results[0]["scores"]["commute"] == 100

    def test_commute_medium_score(self):
        c = make_candidate(commute_minutes=28)
        results = self._score([c])
        assert results[0]["scores"]["commute"] == 60

    def test_commute_low_score(self):
        c = make_candidate(commute_minutes=50)
        results = self._score([c])
        assert results[0]["scores"]["commute"] == 20

    def test_liquidity_high_score(self):
        c = make_candidate(household_count=600)
        results = self._score([c])
        assert results[0]["scores"]["liquidity"] == 100

    def test_liquidity_medium_score(self):
        c = make_candidate(household_count=400)
        results = self._score([c])
        assert results[0]["scores"]["liquidity"] == 60

    def test_liquidity_low_score(self):
        c = make_candidate(household_count=150)
        results = self._score([c])
        assert results[0]["scores"]["liquidity"] == 20

    def test_school_high_with_keyword(self):
        c = make_candidate(school_zone_notes="대치 학원가 핵심 학군.")
        results = self._score([c])
        assert results[0]["scores"]["school"] == 100

    def test_school_low_without_keyword(self):
        c = make_candidate(school_zone_notes="일반초 배정권.")
        results = self._score([c])
        assert results[0]["scores"]["school"] == 20

    def test_price_potential_high_from_reconstruction(self):
        c = make_candidate(reconstruction_potential="HIGH")
        results = self._score([c])
        assert results[0]["scores"]["price_potential"] == 100

    def test_price_potential_boosted_by_horea(self):
        c = make_candidate(
            reconstruction_potential="LOW",
            apt_name="인덕원현대",
            district_name="안양시 동안구",
        )
        horea = {"안양시 동안구": {"gtx": True, "items": ["GTX-C 인덕원역 착공"]}}
        results = self._score([c], horea=horea)
        # LOW(20) + gtx horea boost(+40) = 60
        assert results[0]["scores"]["price_potential"] >= 60

    def test_total_score_is_weighted_sum(self):
        c = make_candidate(
            commute_minutes=15,        # HIGH=100
            household_count=600,       # HIGH=100
            school_zone_notes="학원가", # HIGH=100
            reconstruction_potential="HIGH",  # HIGH=100
            nearest_stations=[
                {"name": "역삼역", "walk_minutes": 5},
                {"name": "선릉역", "walk_minutes": 4},
            ],  # 2개 도보5분 이내 → living_convenience HIGH=100
        )
        weights = {"commute": 25, "liquidity": 25, "price_potential": 25, "living_convenience": 17, "school": 8}
        results = self._score([c], weights=weights)
        # 모든 항목 HIGH(100점)이면 총점도 100
        assert results[0]["total_score"] == 100.0

    def test_results_sorted_by_total_score_descending(self):
        candidates = [
            make_candidate(apt_name="하위", commute_minutes=60, household_count=100),
            make_candidate(apt_name="상위", commute_minutes=10, household_count=800),
        ]
        results = self._score(candidates)
        assert results[0]["apt_name"] == "상위"
        assert results[1]["apt_name"] == "하위"

    def test_missing_fields_use_defaults(self):
        c = {"apt_name": "필드없음", "price": 500_000_000}
        results = self._score([c])
        assert "total_score" in results[0]
        assert 0 <= results[0]["total_score"] <= 100
