"""
candidate_filter.py 단위 테스트
preference_rules.yaml 규칙을 Python 코드로 실행하는 엔진 검증
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src')))


def make_tx(**kwargs):
    base = {
        "apt_name": "테스트아파트",
        "exclusive_area": 84.0,
        "household_count": 600,
        "building_type": "아파트",
        "commute_minutes": 25,
        "price": 800_000_000,
    }
    base.update(kwargs)
    return base


class TestCandidateFilter:
    def _filter(self, candidates, rules):
        from modules.real_estate.candidate_filter import CandidateFilter
        return CandidateFilter(rules).apply(candidates)

    def test_apartment_only_removes_officetel(self):
        rules = [{"id": "apartment_only", "enabled": True}]
        candidates = [
            make_tx(apt_name="오피스텔A", building_type="오피스텔"),
            make_tx(apt_name="아파트B", building_type="아파트"),
        ]
        result = self._filter(candidates, rules)
        assert len(result) == 1
        assert result[0]["apt_name"] == "아파트B"

    def test_min_exclusive_area_removes_small(self):
        rules = [{"id": "min_exclusive_area", "enabled": True, "min_area_sqm": 59}]
        candidates = [
            make_tx(apt_name="소형", exclusive_area=42.0),
            make_tx(apt_name="적정", exclusive_area=59.0),
            make_tx(apt_name="대형", exclusive_area=84.0),
        ]
        result = self._filter(candidates, rules)
        assert len(result) == 2
        assert all(tx["exclusive_area"] >= 59 for tx in result)

    def test_min_household_count_removes_small_complex(self):
        rules = [{"id": "min_household_count", "enabled": True, "min_households": 500}]
        candidates = [
            make_tx(apt_name="소단지", household_count=200),
            make_tx(apt_name="대단지", household_count=600),
        ]
        result = self._filter(candidates, rules)
        assert len(result) == 1
        assert result[0]["apt_name"] == "대단지"

    def test_within_commute_removes_far(self):
        rules = [{"id": "within_30min_commute", "enabled": True, "max_commute_minutes": 30}]
        candidates = [
            make_tx(apt_name="원거리", commute_minutes=45),
            make_tx(apt_name="근거리", commute_minutes=20),
        ]
        result = self._filter(candidates, rules)
        assert len(result) == 1
        assert result[0]["apt_name"] == "근거리"

    def test_disabled_rule_is_ignored(self):
        rules = [{"id": "min_household_count", "enabled": False, "min_households": 500}]
        candidates = [make_tx(household_count=100), make_tx(household_count=800)]
        result = self._filter(candidates, rules)
        assert len(result) == 2

    def test_multiple_rules_applied_in_sequence(self):
        rules = [
            {"id": "apartment_only", "enabled": True},
            {"id": "min_exclusive_area", "enabled": True, "min_area_sqm": 59},
        ]
        candidates = [
            make_tx(apt_name="오피스텔소형", building_type="오피스텔", exclusive_area=33.0),
            make_tx(apt_name="아파트소형", building_type="아파트", exclusive_area=42.0),
            make_tx(apt_name="아파트적정", building_type="아파트", exclusive_area=84.0),
        ]
        result = self._filter(candidates, rules)
        assert len(result) == 1
        assert result[0]["apt_name"] == "아파트적정"

    def test_empty_candidates_returns_empty(self):
        rules = [{"id": "apartment_only", "enabled": True}]
        result = self._filter([], rules)
        assert result == []
