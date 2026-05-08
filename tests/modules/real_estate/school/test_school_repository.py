import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

from modules.real_estate.school.models import (
    SchoolInfo, SchoolStudentRecord, SchoolTeacherRecord, SchoolScore,
)

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
