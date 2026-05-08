import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

from unittest.mock import MagicMock
from modules.real_estate.school.models import SchoolInfo, SchoolStudentRecord, SchoolTeacherRecord
from modules.real_estate.school.school_repository import SchoolRepository
from modules.real_estate.school.school_service import SchoolService

# Real field names discovered from smoke test against schoolinfo.go.kr (2026-05-09)
# apiType=0 (school list) fields:
_SCHOOL_LIST = [
    {
        "SCHUL_CODE": "S000001234",
        "SCHUL_NM": "반포초등학교",
        "SCHUL_KND_SC_CODE": "02",
        "LCTN_SC_CODE": "11",
        "ADRCD_CD": "11650",
        "ADRES": "서울 서초구 반포대로 1",
        "LTTUD": "37.5050",
        "LGTUD": "127.0010",
        "FOND_SC_CODE": "공립",
        "FOND_YMD": "19700301",
    }
]

# apiType=10 (student counts) real fields:
# SCHUL_CODE, STDNT_SUM (total), STDNT_SUM_21..26 (by grade),
# COL_211/COL_212 (grade1 male/female class count), etc.
_STUDENT_LIST = [
    {
        "SCHUL_CODE": "S000001234",
        "SCHUL_NM": "반포초등학교",
        "SCHUL_KND_SC_CODE": "02",
        "LCTN_SC_CODE": "11",
        "ADRCD_CD": "1165000000",
        "ADRCD_NM": "서울특별시 서초구",
        "STDNT_SUM": 595,
        "STDNT_SUM_21": 100,
        "STDNT_SUM_22": 105,
        "STDNT_SUM_23": 102,
        "STDNT_SUM_24": 106,
        "STDNT_SUM_25": 98,
        "STDNT_SUM_26": 84,
        "COL_211": 2,
        "COL_212": 2,
        "COL_221": 3,
        "COL_222": 3,
        "COL_231": 3,
        "COL_232": 2,
        "COL_241": 3,
        "COL_242": 3,
        "COL_251": 3,
        "COL_252": 2,
        "COL_261": 2,
        "COL_262": 2,
        "FOND_SC_CODE": "공립",
        "PBAN_EXCP_YN": "N",
    }
]

# apiType=17 (teacher counts) real fields:
# SCHUL_CODE, COL_1 (total teachers), ML_TOI_FGR (male), FML_TOI_FGR (female)
_TEACHER_LIST = [
    {
        "SCHUL_CODE": "S000001234",
        "SCHUL_NM": "반포초등학교",
        "SCHUL_KND_SC_CODE": "02",
        "LCTN_SC_CODE": "11",
        "ADRCD_CD": "1165000000",
        "ADRCD_NM": "서울특별시 서초구",
        "COL_1": 33,
        "ML_TOI_FGR": 11,
        "FML_TOI_FGR": 10,
        "COM_CCCLA_FGR": 2,
        "CURR_CCCLA_FGR": 1,
        "FOND_SC_CODE": "공립",
        "PBAN_EXCP_YN": "N",
    }
]


def _make_client(schools=None, students=None, teachers=None):
    client = MagicMock()
    client.get_school_list.return_value = schools if schools is not None else _SCHOOL_LIST
    client.get_student_counts.return_value = students if students is not None else _STUDENT_LIST
    client.get_teacher_counts.return_value = teachers if teachers is not None else _TEACHER_LIST
    return client


class TestCollectByDistrict:
    def _svc(self, client=None):
        repo = SchoolRepository(db_path=":memory:")
        return SchoolService(client=client or _make_client(), repo=repo, geocoder=None)

    def test_collect_saves_schools(self):
        svc = self._svc()
        result = svc.collect_by_district("11", "11650")
        assert result["schools_saved"] >= 1

    def test_collect_all_three_kinds(self):
        client = _make_client()
        svc = self._svc(client=client)
        svc.collect_by_district("11", "11650")
        assert client.get_school_list.call_count == 3

    def test_collect_saves_student_records(self):
        svc = self._svc()
        svc.collect_by_district("11", "11650")
        records = svc._repo.get_student_records("S000001234")  # no year = all records
        assert len(records) >= 1

    def test_collect_saves_teacher_records(self):
        svc = self._svc()
        svc.collect_by_district("11", "11650")
        records = svc._repo.get_teacher_records("S000001234")  # no year = all records
        assert len(records) >= 1

    def test_collect_handles_api_empty_gracefully(self):
        client = _make_client(schools=[], students=[], teachers=[])
        svc = self._svc(client=client)
        result = svc.collect_by_district("11", "11650")
        assert result["schools_saved"] == 0

    def test_collect_returns_result_dict(self):
        svc = self._svc()
        result = svc.collect_by_district("11", "11650")
        assert "schools_saved" in result
        assert "student_records_saved" in result
        assert "teacher_records_saved" in result
