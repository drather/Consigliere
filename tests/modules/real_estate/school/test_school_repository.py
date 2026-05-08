import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

from modules.real_estate.school.models import (
    SchoolInfo, SchoolStudentRecord, SchoolTeacherRecord, SchoolScore,
)
from modules.real_estate.school.school_repository import SchoolRepository


def test_school_info_fields():
    s = SchoolInfo(
        school_code="S000001234",
        school_name="반포초등학교",
        school_kind="02",
        sido_code="11",
        sgg_code="11650",
        address="서울 서초구 반포대로 1",
        lat=37.505,
        lng=127.001,
        establishment_type="공립",
        founding_year=1970,
        collected_at="2026-05-08T00:00:00+00:00",
    )
    assert s.school_code == "S000001234"
    assert s.school_kind == "02"

def test_school_student_record_fields():
    r = SchoolStudentRecord(
        school_code="S000001234",
        year=2025,
        grade="1",
        class_count=4,
        student_count=100,
        students_per_class=25.0,
        male_count=52,
        female_count=48,
        collected_at="2026-05-08T00:00:00+00:00",
    )
    assert r.students_per_class == 25.0

def test_school_teacher_record_fields():
    r = SchoolTeacherRecord(
        school_code="S000001234",
        year=2025,
        total_teachers=30,
        students_per_teacher=8.3,
        collected_at="2026-05-08T00:00:00+00:00",
    )
    assert r.total_teachers == 30

def test_school_score_fields():
    sc = SchoolScore(
        complex_code="1234567890",
        school_kind="total",
        nearby_school_count=5,
        avg_students_per_class=23.5,
        avg_students_per_teacher=10.2,
        score=72,
        collected_at="2026-05-08T00:00:00+00:00",
    )
    assert sc.score == 72


def _make_school(**kwargs) -> SchoolInfo:
    defaults = dict(
        school_code="S000001234",
        school_name="반포초등학교",
        school_kind="02",
        sido_code="11",
        sgg_code="11650",
        address="서울 서초구 반포대로 1",
        establishment_type="공립",
        collected_at="2026-05-08T00:00:00+00:00",
        lat=37.505,
        lng=127.001,
        founding_year=1970,
    )
    defaults.update(kwargs)
    return SchoolInfo(**defaults)


def _make_student_record(**kwargs) -> SchoolStudentRecord:
    defaults = dict(
        school_code="S000001234",
        year=2025,
        grade="1",
        class_count=4,
        student_count=100,
        students_per_class=25.0,
        male_count=52,
        female_count=48,
        collected_at="2026-05-08T00:00:00+00:00",
    )
    defaults.update(kwargs)
    return SchoolStudentRecord(**defaults)


def _make_teacher_record(**kwargs) -> SchoolTeacherRecord:
    defaults = dict(
        school_code="S000001234",
        year=2025,
        total_teachers=30,
        students_per_teacher=8.3,
        collected_at="2026-05-08T00:00:00+00:00",
    )
    defaults.update(kwargs)
    return SchoolTeacherRecord(**defaults)


def _make_score(**kwargs) -> SchoolScore:
    defaults = dict(
        complex_code="1234567890",
        school_kind="total",
        nearby_school_count=5,
        avg_students_per_class=23.5,
        avg_students_per_teacher=10.2,
        score=72,
        collected_at="2026-05-08T00:00:00+00:00",
    )
    defaults.update(kwargs)
    return SchoolScore(**defaults)


class TestSchoolRepository:
    def _repo(self):
        return SchoolRepository(db_path=":memory:")

    def test_upsert_and_get_school(self):
        repo = self._repo()
        repo.upsert_school(_make_school())
        results = repo.get_schools_by_sgg("11650", "02")
        assert len(results) == 1
        assert results[0].school_name == "반포초등학교"

    def test_upsert_school_idempotent(self):
        repo = self._repo()
        repo.upsert_school(_make_school())
        repo.upsert_school(_make_school(school_name="반포초등학교(수정)"))
        results = repo.get_schools_by_sgg("11650", "02")
        assert len(results) == 1
        assert results[0].school_name == "반포초등학교(수정)"

    def test_get_schools_by_sgg_filters_kind(self):
        repo = self._repo()
        repo.upsert_school(_make_school(school_code="A001", school_kind="02"))
        repo.upsert_school(_make_school(school_code="A002", school_kind="03"))
        assert len(repo.get_schools_by_sgg("11650", "02")) == 1
        assert len(repo.get_schools_by_sgg("11650", "03")) == 1

    def test_get_schools_near_radius(self):
        repo = self._repo()
        # 반포대교 근처 (약 0.5km)
        repo.upsert_school(_make_school(school_code="NEAR", lat=37.510, lng=127.005))
        # 강남역 근처 (약 3km)
        repo.upsert_school(_make_school(school_code="FAR", lat=37.498, lng=127.027))
        near = repo.get_schools_near(lat=37.510, lng=127.005, radius_km=1.0)
        assert len(near) == 1
        assert near[0].school_code == "NEAR"

    def test_get_schools_near_no_coords_returns_empty(self):
        repo = self._repo()
        repo.upsert_school(_make_school(lat=None, lng=None))
        result = repo.get_schools_near(lat=37.510, lng=127.005, radius_km=1.0)
        assert result == []

    def test_upsert_student_record(self):
        repo = self._repo()
        repo.upsert_school(_make_school())
        repo.upsert_student_record(_make_student_record())
        records = repo.get_student_records("S000001234")
        assert len(records) == 1
        assert records[0].students_per_class == 25.0

    def test_upsert_teacher_record(self):
        repo = self._repo()
        repo.upsert_school(_make_school())
        repo.upsert_teacher_record(_make_teacher_record())
        records = repo.get_teacher_records("S000001234")
        assert len(records) == 1
        assert records[0].total_teachers == 30

    def test_upsert_and_get_score(self):
        repo = self._repo()
        repo.upsert_school_score(_make_score())
        result = repo.get_score("1234567890", "total")
        assert result is not None
        assert result.score == 72

    def test_get_score_not_found_returns_none(self):
        repo = self._repo()
        assert repo.get_score("NOTEXIST", "total") is None
