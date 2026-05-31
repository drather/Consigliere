import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

import pytest
from unittest.mock import MagicMock
from modules.real_estate.location.location_service import LocationService


def _make_service(score=None, poi=None):
    loc_repo = MagicMock()
    loc_repo.get_score.return_value = score
    poi_collector = MagicMock()
    poi_collector.get_cached.return_value = poi
    poi_collector.collect.return_value = poi or MagicMock()
    scorer = MagicMock()
    mock_score = MagicMock()
    mock_score.complex_code = "CC001"
    scorer.score.return_value = mock_score
    svc = LocationService(loc_repo=loc_repo, poi_collector=poi_collector, scorer=scorer)
    return svc, loc_repo, poi_collector, scorer, mock_score


class TestLocationService:
    def test_get_score_returns_from_repo(self):
        expected = MagicMock()
        svc, loc_repo, *_ = _make_service(score=expected)
        assert svc.get_score("CC001") is expected
        loc_repo.get_score.assert_called_once_with("CC001")

    def test_get_score_returns_none_when_missing(self):
        svc, *_ = _make_service(score=None)
        assert svc.get_score("NOTEXIST") is None

    def test_get_poi_cached_returns_from_collector(self):
        mock_poi = MagicMock()
        svc, _, poi_collector, *_ = _make_service(poi=mock_poi)
        result = svc.get_poi_cached("CC001")
        assert result is mock_poi
        poi_collector.get_cached.assert_called_once_with("CC001")

    def test_get_poi_cached_returns_none_when_missing(self):
        svc, *_ = _make_service(poi=None)
        assert svc.get_poi_cached("NOTEXIST") is None

    def test_enrich_and_save_scores_then_persists(self):
        svc, loc_repo, _, scorer, mock_score = _make_service()
        candidate = {"complex_code": "CC001", "_poi": MagicMock()}
        result = svc.enrich_and_save("CC001", candidate)
        scorer.score.assert_called_once_with(candidate)
        loc_repo.upsert_score.assert_called_once_with(mock_score)
        assert result is mock_score

    def test_collect_poi_delegates_to_poi_collector(self):
        svc, _, poi_collector, *_ = _make_service()
        svc.collect_poi("CC001", 37.5, 127.0)
        poi_collector.collect.assert_called_once_with("CC001", 37.5, 127.0)

    def test_get_stale_complex_codes_returns_difference(self):
        svc, _, poi_collector, *_ = _make_service()
        poi_collector.get_fresh_complex_codes.return_value = {"CC001"}
        result = svc.get_stale_complex_codes(["CC001", "CC002"])
        assert result == {"CC002"}
        poi_collector.get_fresh_complex_codes.assert_called_once_with(["CC001", "CC002"])
