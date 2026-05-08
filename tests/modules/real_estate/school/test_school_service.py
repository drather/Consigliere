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
        # grade key must be the full suffix, not just the last digit
        # (avoids collision between elementary "21" and middle "11")
        assert records[0].grade == "21"

    def test_collect_saves_teacher_records(self):
        svc = self._svc()
        svc.collect_by_district("11", "11650")
        records = svc._repo.get_teacher_records("S000001234")  # no year = all records
        assert len(records) >= 1
        # students_per_teacher must be > 0 (student total looked up from student rows)
        assert records[0].students_per_teacher > 0

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


class TestCalculateScore:
    def _svc_with_data(self):
        repo = SchoolRepository(db_path=":memory:")
        svc = SchoolService(
            client=_make_client(),
            repo=repo,
            geocoder=None,
            config={
                "radius_km": 1.0,
                "students_per_class_ideal": 20,
                "students_per_class_warning": 28,
                "nearby_school_high": 3,
                "nearby_school_mid": 1,
                "score_weight_density": 0.30,
                "score_weight_class_size": 0.70,
            },
        )
        svc.collect_by_district("11", "11650")
        return svc

    def test_calculate_score_returns_school_score(self):
        svc = self._svc_with_data()
        score = svc.calculate_score("1234567890", "반포초등학교", "11650")
        assert score.complex_code == "1234567890"
        assert 0 <= score.score <= 100

    def test_calculate_score_saved_to_repo(self):
        svc = self._svc_with_data()
        svc.calculate_score("1234567890", "반포초등학교", "11650")
        saved = svc._repo.get_score("1234567890", "total")
        assert saved is not None

    def test_calculate_score_no_schools_returns_neutral(self):
        repo = SchoolRepository(db_path=":memory:")
        svc = SchoolService(client=_make_client(schools=[]), repo=repo, geocoder=None)
        score = svc.calculate_score("9999", "없는단지", "99999")
        assert score.score == 50
        assert score.nearby_school_count == 0

    def test_get_cached_score_returns_none_when_missing(self):
        svc = self._svc_with_data()
        result = svc.get_cached_score("NOTEXIST", "total")
        assert result is None

    def test_get_cached_score_returns_saved_score(self):
        svc = self._svc_with_data()
        svc.calculate_score("1234567890", "반포초등학교", "11650")
        result = svc.get_cached_score("1234567890", "total")
        assert result is not None
        assert 0 <= result.score <= 100

    def test_calculate_score_with_geocoder(self):
        from unittest.mock import MagicMock
        geocoder = MagicMock()
        geocoder.geocode.return_value = (37.505, 127.001)
        repo = SchoolRepository(db_path=":memory:")
        svc = SchoolService(
            client=_make_client(),
            repo=repo,
            geocoder=geocoder,
            config={
                "radius_km": 5.0,  # large radius to catch mock school at 37.5050, 127.0010
                "students_per_class_ideal": 20,
                "students_per_class_warning": 28,
                "nearby_school_high": 3,
                "nearby_school_mid": 1,
                "score_weight_density": 0.30,
                "score_weight_class_size": 0.70,
            },
        )
        svc.collect_by_district("11", "11650")
        score = svc.calculate_score("1234567890", "반포초등학교", "11650")
        geocoder.geocode.assert_called_once_with("반포초등학교", "11650")
        assert score.complex_code == "1234567890"
