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
        parking_count=0,
        constructor="삼성물산",
        approved_date="20090101",
        road_address="서울특별시 서초구 반포대로 201",
        legal_address="서울 서초구 반포동 1",
        top_floor=25,
        base_floor=3,
        total_area=312000.5,
        heat_type="지역난방",
        developer="삼성물산개발",
        elevator_count=36,
        units_60=0,
        units_85=1200,
        units_135=1000,
        units_136_plus=244,
        sido="서울특별시",
        sigungu="서초구",
        eupmyeondong="반포동",
        ri="",
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

    def test_save_and_get_new_fields(self, tmp_db, sample_master):
        """신규 필드(API 2 + API 1 as1~as4)가 저장·조회된다."""
        from modules.real_estate.apartment_master.repository import ApartmentMasterRepository
        repo = ApartmentMasterRepository(db_path=tmp_db)
        repo.save(sample_master)

        result = repo.get("래미안퍼스티지", "11650")
        assert result.road_address == "서울특별시 서초구 반포대로 201"
        assert result.legal_address == "서울 서초구 반포동 1"
        assert result.top_floor == 25
        assert result.base_floor == 3
        assert result.total_area == 312000.5
        assert result.heat_type == "지역난방"
        assert result.developer == "삼성물산개발"
        assert result.elevator_count == 36
        assert result.units_60 == 0
        assert result.units_85 == 1200
        assert result.units_135 == 1000
        assert result.units_136_plus == 244
        assert result.sido == "서울특별시"
        assert result.sigungu == "서초구"
        assert result.eupmyeondong == "반포동"
        assert result.ri == ""

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
            parking_count=0,
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

    def test_migration_adds_new_columns_to_existing_db(self, tmp_path):
        """기존 DB에 신규 컬럼이 없어도 _init_db()가 자동으로 추가한다 (마이그레이션)."""
        import sqlite3
        db_path = str(tmp_path / "old_schema.db")

        # 구버전 스키마로 DB 생성
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                CREATE TABLE apartment_master (
                    cache_key TEXT PRIMARY KEY,
                    complex_code TEXT DEFAULT '',
                    household_count INTEGER DEFAULT 0,
                    building_count INTEGER DEFAULT 0,
                    parking_count INTEGER DEFAULT 0,
                    constructor TEXT DEFAULT '',
                    approved_date TEXT DEFAULT '',
                    fetched_at TEXT
                )
            """)
            conn.execute(
                "INSERT INTO apartment_master (cache_key, household_count, constructor) "
                "VALUES ('11650__래미안퍼스티지', 2444, '삼성물산')"
            )
            conn.commit()

        # 신버전 Repository 초기화 시 신규 컬럼 자동 추가
        from modules.real_estate.apartment_master.repository import ApartmentMasterRepository
        repo = ApartmentMasterRepository(db_path=db_path)  # _init_db() 호출

        # 기존 레코드가 보존되고 신규 컬럼은 기본값으로
        result = repo.get("래미안퍼스티지", "11650")
        assert result is not None
        assert result.household_count == 2444
        assert result.road_address == ""   # 신규 컬럼 기본값
        assert result.top_floor == 0


# ── Client Tests (mock HTTP) ───────────────────────────────────────────────────

class TestApartmentMasterClient:
    def _make_list_response(self):
        """공동주택 전체 목록 API mock 응답 (items가 list 직접 반환)."""
        return {
            "response": {
                "body": {
                    "items": [
                        {"kaptCode": "A12345", "kaptName": "래미안퍼스티지", "bjdCode": "1165010100"},
                        {"kaptCode": "B67890", "kaptName": "반포자이", "bjdCode": "1165010200"},
                    ],
                    "totalCount": 2,
                    "numOfRows": 10000,
                    "pageNo": 1,
                }
            }
        }

    def _make_info_response(self):
        """공동주택 기본정보 API mock 응답 — 실제 API 전체 필드 반영."""
        return {
            "response": {
                "body": {
                    "item": {
                        "kaptCode": "A12345",
                        "kaptName": "래미안퍼스티지",
                        "kaptAddr": "서울 서초구 반포동 1",
                        "doroJuso": "서울특별시 서초구 반포대로 201",
                        "hoCnt": 2444,
                        "kaptdaCnt": "2444",
                        "kaptDongCnt": "36",
                        "kaptBcompany": "삼성물산",
                        "kaptAcompany": "삼성물산개발",
                        "kaptUsedate": "20090101",
                        "kaptTarea": "312000.5",
                        "kaptTopFloor": "25",
                        "kaptBaseFloor": "3",
                        "codeHeatNm": "지역난방",
                        "kaptdEcntp": "36",
                        "kaptMparea60": "0",
                        "kaptMparea85": "1200",
                        "kaptMparea135": "1000",
                        "kaptMparea136": "244",
                        "privArea": "220000",
                        "codeSaleNm": "분양",
                        "codeHallNm": "계단식",
                        "bjdCode": "1165010100",
                        "zipcode": "06523",
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

    def test_fetch_complex_list_filters_by_sigungu(self):
        """bjdCode prefix로 시군구 필터링 확인."""
        from modules.real_estate.apartment_master.client import ApartmentMasterClient
        client = ApartmentMasterClient(api_key="test-key")

        resp = {
            "response": {
                "body": {
                    "items": [
                        {"kaptCode": "A12345", "kaptName": "래미안퍼스티지", "bjdCode": "1165010100"},
                        {"kaptCode": "C99999", "kaptName": "강남래미안", "bjdCode": "1168010100"},
                    ],
                    "totalCount": 2, "numOfRows": 10000, "pageNo": 1,
                }
            }
        }
        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = resp
            items = client.fetch_complex_list("11650")

        assert len(items) == 1
        assert items[0]["kaptCode"] == "A12345"

    def test_fetch_complex_info_returns_dict(self):
        from modules.real_estate.apartment_master.client import ApartmentMasterClient
        client = ApartmentMasterClient(api_key="test-key")

        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = self._make_info_response()
            info = client.fetch_complex_info("A12345")

        assert info is not None
        assert info["hoCnt"] == 2444
        assert info["kaptDongCnt"] == "36"
        assert info["kaptBcompany"] == "삼성물산"
        assert info["kaptUsedate"] == "20090101"
        assert info["doroJuso"] == "서울특별시 서초구 반포대로 201"
        assert info["codeHeatNm"] == "지역난방"

    def test_fetch_complex_info_returns_none_on_error(self):
        from modules.real_estate.apartment_master.client import ApartmentMasterClient
        client = ApartmentMasterClient(api_key="test-key")

        with patch("requests.get") as mock_get:
            mock_get.side_effect = Exception("timeout")
            info = client.fetch_complex_info("A12345")

        assert info is None

    def test_fetch_complex_list_legacy_dict_items_handled(self):
        """하위 호환: 구버전 API가 items를 {'item': [...]} 형태로 반환하는 경우."""
        from modules.real_estate.apartment_master.client import ApartmentMasterClient
        client = ApartmentMasterClient(api_key="test-key")

        legacy_resp = {
            "response": {
                "body": {
                    "items": {
                        "item": {"kaptCode": "A12345", "kaptName": "래미안퍼스티지", "bjdCode": "1165010100"}
                    },
                    "totalCount": 1, "numOfRows": 10000, "pageNo": 1,
                }
            }
        }
        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = legacy_resp
            items = client.fetch_complex_list("11650")

        assert len(items) == 1
        assert items[0]["kaptCode"] == "A12345"


# ── Service Tests ──────────────────────────────────────────────────────────────

class TestApartmentMasterService:
    def _make_mock_client(self):
        client = MagicMock()
        client.fetch_complex_list.return_value = [
            {
                "kaptCode": "A12345", "kaptName": "래미안퍼스티지", "bjdCode": "1165010100",
                "as1": "서울특별시", "as2": "서초구", "as3": "반포동", "as4": "",
            },
        ]
        client.fetch_complex_info.return_value = {
            "kaptCode": "A12345",
            "kaptName": "래미안퍼스티지",
            "kaptAddr": "서울 서초구 반포동 1",
            "doroJuso": "서울특별시 서초구 반포대로 201",
            "hoCnt": 2444,
            "kaptDongCnt": "36",
            "kaptBcompany": "삼성물산",
            "kaptAcompany": "삼성물산개발",
            "kaptUsedate": "20090101",
            "kaptTarea": "312000.5",
            "kaptTopFloor": "25",
            "kaptBaseFloor": "3",
            "codeHeatNm": "지역난방",
            "kaptdEcntp": "36",
            "kaptMparea60": "0",
            "kaptMparea85": "1200",
            "kaptMparea135": "1000",
            "kaptMparea136": "244",
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
        assert result.road_address == "서울특별시 서초구 반포대로 201"
        assert result.heat_type == "지역난방"
        assert result.top_floor == 25
        assert result.units_85 == 1200
        # as1~as4 (API 1 목록 필드)
        assert result.sido == "서울특별시"
        assert result.sigungu == "서초구"
        assert result.eupmyeondong == "반포동"
        client.fetch_complex_list.assert_called_once_with("11650")

    def test_get_or_fetch_cache_miss_saves_to_db(self, tmp_db):
        from modules.real_estate.apartment_master.repository import ApartmentMasterRepository
        from modules.real_estate.apartment_master.service import ApartmentMasterService
        repo = ApartmentMasterRepository(db_path=tmp_db)
        client = self._make_mock_client()

        svc = ApartmentMasterService(client=client, repository=repo)
        svc.get_or_fetch("래미안퍼스티지", "11650")

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

    def test_parse_info_extracts_all_fields(self, tmp_db):
        """_parse_info()가 API 1(list_item) + API 2(info) 전체 필드를 ApartmentMaster로 변환한다."""
        from modules.real_estate.apartment_master.service import ApartmentMasterService
        from modules.real_estate.apartment_master.repository import ApartmentMasterRepository
        repo = ApartmentMasterRepository(db_path=tmp_db)
        svc = ApartmentMasterService(client=MagicMock(), repository=repo)

        list_item = {
            "kaptCode": "A12345", "kaptName": "래미안퍼스티지", "bjdCode": "1165010100",
            "as1": "서울특별시", "as2": "서초구", "as3": "반포동", "as4": "",
        }
        info = {
            "kaptAddr": "서울 서초구 반포동 1",
            "doroJuso": "서울특별시 서초구 반포대로 201",
            "hoCnt": 2444,
            "kaptDongCnt": "36",
            "kaptBcompany": "삼성물산",
            "kaptAcompany": "삼성물산개발",
            "kaptUsedate": "20090101",
            "kaptTarea": "312000.5",
            "kaptTopFloor": "25",
            "kaptBaseFloor": "3",
            "codeHeatNm": "지역난방",
            "kaptdEcntp": "36",
            "kaptMparea60": "0",
            "kaptMparea85": "1200",
            "kaptMparea135": "1000",
            "kaptMparea136": "244",
        }
        master = svc._parse_info("래미안퍼스티지", "11650", "A12345", info, list_item=list_item)

        assert master.road_address == "서울특별시 서초구 반포대로 201"
        assert master.legal_address == "서울 서초구 반포동 1"
        assert master.top_floor == 25
        assert master.base_floor == 3
        assert master.total_area == 312000.5
        assert master.heat_type == "지역난방"
        assert master.developer == "삼성물산개발"
        assert master.elevator_count == 36
        assert master.units_60 == 0
        assert master.units_85 == 1200
        assert master.units_135 == 1000
        assert master.units_136_plus == 244
        assert master.sido == "서울특별시"
        assert master.sigungu == "서초구"
        assert master.eupmyeondong == "반포동"
        assert master.ri == ""

    def test_parse_info_handles_missing_fields_gracefully(self, tmp_db):
        """필드가 없거나 빈 값이어도 오류 없이 기본값으로 처리된다."""
        from modules.real_estate.apartment_master.service import ApartmentMasterService
        from modules.real_estate.apartment_master.repository import ApartmentMasterRepository
        repo = ApartmentMasterRepository(db_path=tmp_db)
        svc = ApartmentMasterService(client=MagicMock(), repository=repo)

        info = {"hoCnt": 500, "kaptDongCnt": "10", "kaptBcompany": "GS건설", "kaptUsedate": "20101001"}
        master = svc._parse_info("자이아파트", "11680", "B99", info)

        assert master.road_address == ""
        assert master.top_floor == 0
        assert master.total_area == 0.0
        assert master.heat_type == ""
        assert master.units_85 == 0
        assert master.sido == ""
        assert master.sigungu == ""
        assert master.eupmyeondong == ""

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
        repo.save(sample_master)
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
