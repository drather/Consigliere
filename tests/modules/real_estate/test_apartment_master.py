"""
TDD: ApartmentMaster — Repository / Client / Service 테스트
"""
import os
import sys
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src')))


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_db(tmp_path):
    return str(tmp_path / "test_apartment_master.db")


@pytest.fixture
def sample_master():
    from modules.real_estate.models import ApartmentMaster
    return ApartmentMaster(
        apt_name="래미안퍼스티지",
        district_code="11650",
        complex_code="A12345",
        household_count=2444,
        building_count=36,
        parking_count=3200,
        constructor="삼성물산",
        approved_date="20090101",
    )


# ── Repository Tests ───────────────────────────────────────────────────────────

class TestApartmentMasterRepository:
    def test_get_returns_none_for_unknown(self, tmp_db):
        from modules.real_estate.apartment_master.repository import ApartmentMasterRepository
        repo = ApartmentMasterRepository(db_path=tmp_db)
        result = repo.get("없는아파트", "11680")
        assert result is None

    def test_save_and_get_roundtrip(self, tmp_db, sample_master):
        from modules.real_estate.apartment_master.repository import ApartmentMasterRepository
        repo = ApartmentMasterRepository(db_path=tmp_db)
        repo.save(sample_master)

        result = repo.get("래미안퍼스티지", "11650")
        assert result is not None
        assert result.household_count == 2444
        assert result.building_count == 36
        assert result.constructor == "삼성물산"
        assert result.complex_code == "A12345"

    def test_save_overwrites_existing(self, tmp_db, sample_master):
        from modules.real_estate.apartment_master.repository import ApartmentMasterRepository
        from modules.real_estate.models import ApartmentMaster
        repo = ApartmentMasterRepository(db_path=tmp_db)
        repo.save(sample_master)

        updated = ApartmentMaster(
            apt_name="래미안퍼스티지",
            district_code="11650",
            complex_code="A12345",
            household_count=9999,
            building_count=36,
            parking_count=3200,
            constructor="삼성물산",
            approved_date="20090101",
        )
        repo.save(updated)

        result = repo.get("래미안퍼스티지", "11650")
        assert result.household_count == 9999

    def test_get_all_complex_codes(self, tmp_db, sample_master):
        from modules.real_estate.apartment_master.repository import ApartmentMasterRepository
        repo = ApartmentMasterRepository(db_path=tmp_db)
        repo.save(sample_master)

        codes = repo.get_all_complex_codes()
        assert "A12345" in codes

    def test_empty_db_returns_empty_list(self, tmp_db):
        from modules.real_estate.apartment_master.repository import ApartmentMasterRepository
        repo = ApartmentMasterRepository(db_path=tmp_db)
        assert repo.get_all_complex_codes() == []

    def test_get_count(self, tmp_db, sample_master):
        from modules.real_estate.apartment_master.repository import ApartmentMasterRepository
        repo = ApartmentMasterRepository(db_path=tmp_db)
        assert repo.count() == 0
        repo.save(sample_master)
        assert repo.count() == 1


# ── Client Tests (mock HTTP) ───────────────────────────────────────────────────

class TestApartmentMasterClient:
    def _make_list_response(self):
        """공동주택 단지 목록 API mock 응답."""
        return {
            "response": {
                "body": {
                    "items": {
                        "item": [
                            {"kaptCode": "A12345", "kaptName": "래미안퍼스티지", "bjdCode": "1165010100"},
                            {"kaptCode": "B67890", "kaptName": "반포자이", "bjdCode": "1165010200"},
                        ]
                    },
                    "totalCount": 2,
                }
            }
        }

    def _make_info_response(self):
        """공동주택 기본정보 API mock 응답."""
        return {
            "response": {
                "body": {
                    "item": {
                        "kaptCode": "A12345",
                        "kaptName": "래미안퍼스티지",
                        "hhldCnt": "2444",
                        "bdNum": "36",
                        "kaptTarea": "3200",
                        "kaptBcompany": "삼성물산",
                        "useAprDay": "20090101",
                    }
                }
            }
        }

    def test_fetch_complex_list_returns_items(self):
        from modules.real_estate.apartment_master.client import ApartmentMasterClient
        client = ApartmentMasterClient(api_key="test-key")

        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = self._make_list_response()
            items = client.fetch_complex_list("11650")

        assert len(items) == 2
        assert items[0]["kaptCode"] == "A12345"
        assert items[0]["kaptName"] == "래미안퍼스티지"

    def test_fetch_complex_list_returns_empty_on_error(self):
        from modules.real_estate.apartment_master.client import ApartmentMasterClient
        client = ApartmentMasterClient(api_key="test-key")

        with patch("requests.get") as mock_get:
            mock_get.side_effect = Exception("network error")
            items = client.fetch_complex_list("11650")

        assert items == []

    def test_fetch_complex_info_returns_dict(self):
        from modules.real_estate.apartment_master.client import ApartmentMasterClient
        client = ApartmentMasterClient(api_key="test-key")

        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = self._make_info_response()
            info = client.fetch_complex_info("A12345")

        assert info is not None
        assert info["hhldCnt"] == "2444"
        assert info["bdNum"] == "36"
        assert info["kaptBcompany"] == "삼성물산"

    def test_fetch_complex_info_returns_none_on_error(self):
        from modules.real_estate.apartment_master.client import ApartmentMasterClient
        client = ApartmentMasterClient(api_key="test-key")

        with patch("requests.get") as mock_get:
            mock_get.side_effect = Exception("timeout")
            info = client.fetch_complex_info("A12345")

        assert info is None

    def test_fetch_complex_list_single_item_coerced_to_list(self):
        """API가 item 1건일 때 dict로 반환하는 케이스 처리."""
        from modules.real_estate.apartment_master.client import ApartmentMasterClient
        client = ApartmentMasterClient(api_key="test-key")

        single_item_resp = {
            "response": {
                "body": {
                    "items": {
                        "item": {"kaptCode": "A12345", "kaptName": "래미안퍼스티지", "bjdCode": "1165010100"}
                    },
                    "totalCount": 1,
                }
            }
        }
        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = single_item_resp
            items = client.fetch_complex_list("11650")

        assert len(items) == 1
        assert items[0]["kaptCode"] == "A12345"


# ── Service Tests ──────────────────────────────────────────────────────────────

class TestApartmentMasterService:
    def _make_mock_client(self):
        client = MagicMock()
        client.fetch_complex_list.return_value = [
            {"kaptCode": "A12345", "kaptName": "래미안퍼스티지", "bjdCode": "1165010100"},
        ]
        client.fetch_complex_info.return_value = {
            "kaptCode": "A12345",
            "kaptName": "래미안퍼스티지",
            "hhldCnt": "2444",
            "bdNum": "36",
            "kaptTarea": "3200",
            "kaptBcompany": "삼성물산",
            "useAprDay": "20090101",
        }
        return client

    def test_get_or_fetch_cache_hit(self, tmp_db, sample_master):
        from modules.real_estate.apartment_master.repository import ApartmentMasterRepository
        from modules.real_estate.apartment_master.service import ApartmentMasterService
        repo = ApartmentMasterRepository(db_path=tmp_db)
        repo.save(sample_master)

        client = MagicMock()
        svc = ApartmentMasterService(client=client, repository=repo)
        result = svc.get_or_fetch("래미안퍼스티지", "11650")

        assert result is not None
        assert result.household_count == 2444
        client.fetch_complex_list.assert_not_called()

    def test_get_or_fetch_cache_miss_fetches_api(self, tmp_db):
        from modules.real_estate.apartment_master.repository import ApartmentMasterRepository
        from modules.real_estate.apartment_master.service import ApartmentMasterService
        repo = ApartmentMasterRepository(db_path=tmp_db)
        client = self._make_mock_client()

        svc = ApartmentMasterService(client=client, repository=repo)
        result = svc.get_or_fetch("래미안퍼스티지", "11650")

        assert result is not None
        assert result.household_count == 2444
        assert result.constructor == "삼성물산"
        client.fetch_complex_list.assert_called_once_with("11650")

    def test_get_or_fetch_cache_miss_saves_to_db(self, tmp_db):
        from modules.real_estate.apartment_master.repository import ApartmentMasterRepository
        from modules.real_estate.apartment_master.service import ApartmentMasterService
        repo = ApartmentMasterRepository(db_path=tmp_db)
        client = self._make_mock_client()

        svc = ApartmentMasterService(client=client, repository=repo)
        svc.get_or_fetch("래미안퍼스티지", "11650")

        # 두 번째 조회는 DB에서 가져와야 함
        client.fetch_complex_list.reset_mock()
        result = svc.get_or_fetch("래미안퍼스티지", "11650")
        client.fetch_complex_list.assert_not_called()
        assert result.household_count == 2444

    def test_get_or_fetch_no_match_returns_none(self, tmp_db):
        from modules.real_estate.apartment_master.repository import ApartmentMasterRepository
        from modules.real_estate.apartment_master.service import ApartmentMasterService
        repo = ApartmentMasterRepository(db_path=tmp_db)
        client = MagicMock()
        client.fetch_complex_list.return_value = []

        svc = ApartmentMasterService(client=client, repository=repo)
        result = svc.get_or_fetch("존재하지않는아파트", "11650")
        assert result is None

    def test_build_initial_saves_all(self, tmp_db):
        from modules.real_estate.apartment_master.repository import ApartmentMasterRepository
        from modules.real_estate.apartment_master.service import ApartmentMasterService
        repo = ApartmentMasterRepository(db_path=tmp_db)
        client = self._make_mock_client()

        districts = [{"code": "11650", "name": "서초구"}]
        svc = ApartmentMasterService(client=client, repository=repo)
        stats = svc.build_initial(districts)

        assert stats["saved"] >= 1
        assert repo.count() >= 1

    def test_build_initial_skips_existing(self, tmp_db, sample_master):
        from modules.real_estate.apartment_master.repository import ApartmentMasterRepository
        from modules.real_estate.apartment_master.service import ApartmentMasterService
        repo = ApartmentMasterRepository(db_path=tmp_db)
        repo.save(sample_master)  # A12345 already saved
        client = self._make_mock_client()

        districts = [{"code": "11650", "name": "서초구"}]
        svc = ApartmentMasterService(client=client, repository=repo)
        stats = svc.build_initial(districts)

        assert stats["skipped"] >= 1
        client.fetch_complex_info.assert_not_called()

    def test_match_name_exact(self, tmp_db):
        from modules.real_estate.apartment_master.repository import ApartmentMasterRepository
        from modules.real_estate.apartment_master.service import ApartmentMasterService
        repo = ApartmentMasterRepository(db_path=tmp_db)
        svc = ApartmentMasterService(client=MagicMock(), repository=repo)

        candidates = [
            {"kaptCode": "A1", "kaptName": "래미안퍼스티지"},
            {"kaptCode": "A2", "kaptName": "반포자이"},
        ]
        matched = svc._match_name("래미안퍼스티지", candidates)
        assert matched == "A1"

    def test_match_name_partial(self, tmp_db):
        from modules.real_estate.apartment_master.repository import ApartmentMasterRepository
        from modules.real_estate.apartment_master.service import ApartmentMasterService
        repo = ApartmentMasterRepository(db_path=tmp_db)
        svc = ApartmentMasterService(client=MagicMock(), repository=repo)

        candidates = [
            {"kaptCode": "A1", "kaptName": "래미안퍼스티지아파트"},
        ]
        matched = svc._match_name("래미안퍼스티지", candidates)
        assert matched == "A1"

    def test_match_name_no_match_returns_none(self, tmp_db):
        from modules.real_estate.apartment_master.repository import ApartmentMasterRepository
        from modules.real_estate.apartment_master.service import ApartmentMasterService
        repo = ApartmentMasterRepository(db_path=tmp_db)
        svc = ApartmentMasterService(client=MagicMock(), repository=repo)

        candidates = [{"kaptCode": "A1", "kaptName": "전혀다른아파트"}]
        matched = svc._match_name("래미안퍼스티지", candidates)
        assert matched is None
