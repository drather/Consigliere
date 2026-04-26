import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

import json
from unittest.mock import MagicMock, patch

from modules.real_estate.building_master.models import BuildingMaster
from modules.real_estate.building_master.building_register_client import (
    BuildingRegisterClient,
)


def test_building_master_construction():
    bm = BuildingMaster(
        mgm_pk="1234567890123456789012",
        building_name="래미안아파트",
        sigungu_code="11650",
    )
    assert bm.mgm_pk == "1234567890123456789012"
    assert bm.building_name == "래미안아파트"
    assert bm.sigungu_code == "11650"
    assert bm.bjdong_code == ""
    assert bm.total_units is None


def test_building_master_full_fields():
    bm = BuildingMaster(
        mgm_pk="9999999999999999999999",
        building_name="아크로리버파크",
        sigungu_code="11650",
        bjdong_code="10800",
        parcel_pnu="1165010800",
        completion_year=2016,
        total_units=1612,
        total_buildings=7,
        floor_area_ratio=299.9,
        building_coverage_ratio=19.9,
    )
    assert bm.parcel_pnu == "1165010800"
    assert bm.completion_year == 2016
    assert bm.total_units == 1612


# 총괄표제부 기준 샘플 응답 (etcPurps 필드 사용)
_SAMPLE_RESPONSE = {
    "response": {
        "body": {
            "totalCount": 2,
            "items": {
                "item": [
                    {
                        "mgmBldrgstPk": "1100000000000001000001",
                        "bldNm": "래미안아파트",
                        "sigunguCd": "11650",
                        "bjdongCd": "10100",
                        "newPlatPlc": "서울특별시 서초구 반포대로 23",
                        "platPlc": "서울특별시 서초구 반포동 10-1",
                        "useAprDay": "20050320",
                        "hhldCnt": "1000",
                        "mainBldCnt": "5",
                        "vlRat": "250.0",
                        "bcRat": "20.0",
                        "mainPurpsCdNm": "공동주택",
                        "etcPurps": "공동주택(아파트)",
                    },
                    {
                        "mgmBldrgstPk": "1100000000000001000002",
                        "bldNm": "상가건물",
                        "sigunguCd": "11650",
                        "bjdongCd": "10100",
                        "newPlatPlc": "서울특별시 서초구 어딘가 1",
                        "platPlc": "서울특별시 서초구 반포동 20",
                        "useAprDay": "20100101",
                        "hhldCnt": "0",
                        "mainBldCnt": "1",
                        "vlRat": "400.0",
                        "bcRat": "60.0",
                        "mainPurpsCdNm": "제2종근린생활시설",
                        "etcPurps": "근린생활시설",
                    },
                ]
            },
        }
    }
}


def test_fetch_page_calls_correct_url():
    client = BuildingRegisterClient(api_key="testkey")
    mock_resp = MagicMock()
    mock_resp.json.return_value = _SAMPLE_RESPONSE
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_resp) as mock_get:
        result = client.fetch_page("11650", page_no=1)

    call_kwargs = mock_get.call_args
    assert call_kwargs[1]["params"]["sigunguCd"] == "11650"
    assert call_kwargs[1]["params"]["serviceKey"] == "testkey"
    assert call_kwargs[1]["params"]["_type"] == "json"
    assert result == _SAMPLE_RESPONSE


def test_fetch_page_includes_bjdong_when_provided():
    client = BuildingRegisterClient(api_key="testkey")
    mock_resp = MagicMock()
    mock_resp.json.return_value = _SAMPLE_RESPONSE
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_resp) as mock_get:
        client.fetch_page("11650", bjdong_cd="10100", page_no=1)

    params = mock_get.call_args[1]["params"]
    assert params["bjdongCd"] == "10100"


def test_fetch_page_omits_bjdong_when_empty():
    client = BuildingRegisterClient(api_key="testkey")
    mock_resp = MagicMock()
    mock_resp.json.return_value = _SAMPLE_RESPONSE
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_resp) as mock_get:
        client.fetch_page("11650", page_no=1)

    params = mock_get.call_args[1]["params"]
    assert "bjdongCd" not in params


def test_fetch_apartments_filters_non_apt():
    client = BuildingRegisterClient(api_key="testkey")
    mock_resp = MagicMock()
    mock_resp.json.return_value = _SAMPLE_RESPONSE
    mock_resp.raise_for_status = MagicMock()

    with patch.object(client, "discover_bjdong_codes", return_value=["10100"]):
        with patch("requests.get", return_value=mock_resp):
            items = client.fetch_apartments_by_sigungu("11650")

    assert len(items) == 1
    assert items[0]["bldNm"] == "래미안아파트"


def test_fetch_apartments_returns_empty_when_no_bjdong():
    client = BuildingRegisterClient(api_key="testkey")
    with patch.object(client, "discover_bjdong_codes", return_value=[]):
        items = client.fetch_apartments_by_sigungu("11650")
    assert items == []


def test_parse_item_extracts_fields():
    raw = {
        "mgmBldrgstPk": "1100000000000001000001",
        "bldNm": "래미안아파트",
        "sigunguCd": "11650",
        "bjdongCd": "10100",
        "newPlatPlc": "서울특별시 서초구 반포대로 23",
        "platPlc": "서울특별시 서초구 반포동 10-1",
        "useAprDay": "20050320",
        "hhldCnt": "1000",
        "mainBldCnt": "5",
        "vlRat": "250.0",
        "bcRat": "20.0",
        "etcPurps": "공동주택(아파트)",
    }
    parsed = BuildingRegisterClient.parse_item(raw)
    assert parsed["mgm_pk"] == "1100000000000001000001"
    assert parsed["building_name"] == "래미안아파트"
    assert parsed["sigungu_code"] == "11650"
    assert parsed["bjdong_code"] == "10100"
    assert parsed["completion_year"] == 2005
    assert parsed["total_units"] == 1000
    assert parsed["total_buildings"] == 5
    assert parsed["floor_area_ratio"] == 250.0
    assert parsed["building_coverage_ratio"] == 20.0


def test_parse_item_handles_missing_fields():
    raw = {"mgmBldrgstPk": "9999", "bldNm": "테스트", "sigunguCd": "11110"}
    parsed = BuildingRegisterClient.parse_item(raw)
    assert parsed["completion_year"] is None
    assert parsed["total_units"] is None
    assert parsed["bjdong_code"] == ""


def test_parse_item_falls_back_to_dongcnt():
    """구버전 호환: mainBldCnt 없으면 dongCnt 사용."""
    raw = {"mgmBldrgstPk": "1", "bldNm": "테스트", "sigunguCd": "11110", "dongCnt": "3"}
    parsed = BuildingRegisterClient.parse_item(raw)
    assert parsed["total_buildings"] == 3


def test_extract_items_handles_single_dict():
    data = {
        "response": {
            "body": {
                "totalCount": 1,
                "items": {
                    "item": {
                        "mgmBldrgstPk": "001",
                        "bldNm": "단독",
                        "etcPurps": "공동주택(아파트)",
                    }
                },
            }
        }
    }
    items = BuildingRegisterClient._extract_items(data)
    assert len(items) == 1
    assert items[0]["mgmBldrgstPk"] == "001"


def test_extract_items_handles_empty():
    data = {"response": {"body": {"totalCount": 0, "items": {"item": None}}}}
    assert BuildingRegisterClient._extract_items(data) == []
