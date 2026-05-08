import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

from unittest.mock import patch, MagicMock
from modules.real_estate.school.school_info_client import SchoolInfoClient

BASE_SCHOOL_RESPONSE = {
    "resultCode": "success",
    "resultMsg": "성공",
    "list": [
        {
            "SCHUL_CODE": "S000001234",
            "SCHUL_NM": "반포초등학교",
            "SCHUL_KND_SC_CODE": "02",
            "LCTN_SC_CODE": "11",
            "ADRCD_CD": "11650",
            "ADRES": "서울 서초구 반포대로 1",
            "LTTUD": "37.5050",
            "LGTUD": "127.0010",
            "SCHUL_FOND_TYP_CODE": "공립",
            "FOND_YMD": "19700301",
        }
    ],
}

BASE_STUDENT_RESPONSE = {
    "resultCode": "success",
    "resultMsg": "성공",
    "list": [
        {
            "SCHUL_CODE": "S000001234",
            "SCHUL_NM": "반포초등학교",
            "ORD_SC_NM": "1학년",
            "CLRM_CNT": "4",
            "TOTSTUDN_CNT": "100",
            "MALE_STUDN_CNT": "52",
            "FEMALE_STUDN_CNT": "48",
            "DATA_YMD": "20250401",
        }
    ],
}

BASE_TEACHER_RESPONSE = {
    "resultCode": "success",
    "resultMsg": "성공",
    "list": [
        {
            "SCHUL_CODE": "S000001234",
            "SCHUL_NM": "반포초등학교",
            "TOTSTUDN_CNT": "300",
            "THING_CNT": "30",
            "DATA_YMD": "20250401",
        }
    ],
}


def _mock_get(response_body: dict):
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = response_body
    return mock


class TestSchoolInfoClient:
    def _client(self):
        return SchoolInfoClient(api_key="test_key")

    def test_get_school_list_returns_list(self):
        client = self._client()
        with patch("requests.get", return_value=_mock_get(BASE_SCHOOL_RESPONSE)):
            result = client.get_school_list("11", "11650", "02")
        assert len(result) == 1
        assert result[0]["SCHUL_CODE"] == "S000001234"

    def test_get_school_list_calls_correct_url(self):
        client = self._client()
        with patch("requests.get", return_value=_mock_get(BASE_SCHOOL_RESPONSE)) as mock_get:
            client.get_school_list("11", "11650", "02")
        call_url = mock_get.call_args[0][0]
        assert "schoolinfo.go.kr" in call_url
        assert "apiKey=test_key" in call_url
        assert "sidoCode=11" in call_url
        assert "sggCode=11650" in call_url
        assert "schulKndCode=02" in call_url

    def test_get_school_list_empty_on_api_error(self):
        client = self._client()
        with patch("requests.get", side_effect=Exception("timeout")):
            result = client.get_school_list("11", "11650", "02")
        assert result == []

    def test_get_student_counts_returns_list(self):
        client = self._client()
        with patch("requests.get", return_value=_mock_get(BASE_STUDENT_RESPONSE)):
            result = client.get_student_counts("11", "11650", "02")
        assert len(result) == 1
        assert result[0]["SCHUL_CODE"] == "S000001234"

    def test_get_teacher_counts_returns_list(self):
        client = self._client()
        with patch("requests.get", return_value=_mock_get(BASE_TEACHER_RESPONSE)):
            result = client.get_teacher_counts("11", "11650", "02")
        assert len(result) == 1

    def test_get_school_list_returns_empty_on_failure_result(self):
        client = self._client()
        fail_response = {"resultCode": "fail", "resultMsg": "인증키 오류", "list": []}
        with patch("requests.get", return_value=_mock_get(fail_response)):
            result = client.get_school_list("11", "11650", "02")
        assert result == []
