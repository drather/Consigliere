from dataclasses import dataclass
from typing import Optional


@dataclass
class SchoolInfo:
    school_code: str
    school_name: str
    school_kind: str            # "02"=초등 "03"=중등 "04"=고등
    sido_code: str
    sgg_code: str
    address: str
    establishment_type: str     # 공립/사립
    collected_at: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    founding_year: Optional[int] = None


@dataclass
class SchoolStudentRecord:
    school_code: str
    year: int
    grade: str
    class_count: int
    student_count: int
    students_per_class: float
    male_count: int
    female_count: int
    collected_at: str


@dataclass
class SchoolTeacherRecord:
    school_code: str
    year: int
    total_teachers: int
    students_per_teacher: float
    collected_at: str


@dataclass
class SchoolScore:
    complex_code: str
    school_kind: str            # "elementary" / "middle" / "high" / "total"
    nearby_school_count: int
    avg_students_per_class: float
    avg_students_per_teacher: float
    score: int                  # 0~100
    collected_at: str
