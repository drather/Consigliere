import math
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import List, Optional

from modules.real_estate.school.models import (
    SchoolInfo, SchoolStudentRecord, SchoolTeacherRecord, SchoolScore,
)

_DDL = """
CREATE TABLE IF NOT EXISTS school_info (
    school_code         TEXT PRIMARY KEY,
    school_name         TEXT NOT NULL,
    school_kind         TEXT NOT NULL,
    sido_code           TEXT NOT NULL,
    sgg_code            TEXT NOT NULL,
    address             TEXT NOT NULL DEFAULT '',
    lat                 REAL,
    lng                 REAL,
    establishment_type  TEXT NOT NULL DEFAULT '',
    founding_year       INTEGER,
    collected_at        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_school_sgg ON school_info(sgg_code, school_kind);

CREATE TABLE IF NOT EXISTS school_student_records (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    school_code     TEXT NOT NULL,
    year            INTEGER NOT NULL,
    grade           TEXT NOT NULL,
    class_count     INTEGER NOT NULL DEFAULT 0,
    student_count   INTEGER NOT NULL DEFAULT 0,
    students_per_class REAL NOT NULL DEFAULT 0,
    male_count      INTEGER NOT NULL DEFAULT 0,
    female_count    INTEGER NOT NULL DEFAULT 0,
    collected_at    TEXT NOT NULL,
    UNIQUE(school_code, year, grade)
);
CREATE INDEX IF NOT EXISTS idx_ssr_school ON school_student_records(school_code);

CREATE TABLE IF NOT EXISTS school_teacher_records (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    school_code             TEXT NOT NULL,
    year                    INTEGER NOT NULL,
    total_teachers          INTEGER NOT NULL DEFAULT 0,
    students_per_teacher    REAL NOT NULL DEFAULT 0,
    collected_at            TEXT NOT NULL,
    UNIQUE(school_code, year)
);
CREATE INDEX IF NOT EXISTS idx_str_school ON school_teacher_records(school_code);

CREATE TABLE IF NOT EXISTS school_scores (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    complex_code                TEXT NOT NULL,
    school_kind                 TEXT NOT NULL,
    nearby_school_count         INTEGER NOT NULL DEFAULT 0,
    avg_students_per_class      REAL NOT NULL DEFAULT 0,
    avg_students_per_teacher    REAL NOT NULL DEFAULT 0,
    score                       INTEGER NOT NULL DEFAULT 50,
    collected_at                TEXT NOT NULL,
    UNIQUE(complex_code, school_kind)
);
CREATE INDEX IF NOT EXISTS idx_ss_complex ON school_scores(complex_code);
"""


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlng / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(max(0.0, a)))


class SchoolRepository:
    def __init__(self, db_path: str = "data/real_estate.db"):
        self._db_path = db_path
        if db_path == ":memory:":
            self._shared_conn: Optional[sqlite3.Connection] = sqlite3.connect(":memory:")
            self._shared_conn.row_factory = sqlite3.Row
        else:
            self._shared_conn = None
        self._init_db()

    @contextmanager
    def _conn(self):
        if self._shared_conn is not None:
            yield self._shared_conn
        else:
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript(_DDL)

    def upsert_school(self, s: SchoolInfo) -> None:
        sql = """
        INSERT INTO school_info
            (school_code, school_name, school_kind, sido_code, sgg_code,
             address, lat, lng, establishment_type, founding_year, collected_at)
        VALUES
            (:school_code, :school_name, :school_kind, :sido_code, :sgg_code,
             :address, :lat, :lng, :establishment_type, :founding_year, :collected_at)
        ON CONFLICT(school_code) DO UPDATE SET
            school_name=excluded.school_name,
            address=excluded.address,
            lat=excluded.lat,
            lng=excluded.lng,
            establishment_type=excluded.establishment_type,
            founding_year=excluded.founding_year,
            collected_at=excluded.collected_at
        """
        with self._conn() as conn:
            conn.execute(sql, {
                "school_code": s.school_code,
                "school_name": s.school_name,
                "school_kind": s.school_kind,
                "sido_code": s.sido_code,
                "sgg_code": s.sgg_code,
                "address": s.address,
                "lat": s.lat,
                "lng": s.lng,
                "establishment_type": s.establishment_type,
                "founding_year": s.founding_year,
                "collected_at": s.collected_at or datetime.now(timezone.utc).isoformat(),
            })

    def get_schools_by_sgg(self, sgg_code: str, school_kind: str) -> List[SchoolInfo]:
        """Return schools that have at least one student record (for scoring use)."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM school_info WHERE sgg_code=? AND school_kind=?"
                " AND school_code IN (SELECT DISTINCT school_code FROM school_student_records)",
                (sgg_code, school_kind),
            ).fetchall()
        return [_row_to_school(r) for r in rows]

    def get_all_schools_by_sgg(self, sgg_code: str, school_kind: str) -> List[SchoolInfo]:
        """Return all schools in the SGG for the given kind (no student-record filter)."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM school_info WHERE sgg_code=? AND school_kind=?",
                (sgg_code, school_kind),
            ).fetchall()
        return [_row_to_school(r) for r in rows]

    def get_schools_near(
        self, lat: float, lng: float, radius_km: float,
        sgg_code: str | None = None,
    ) -> List[SchoolInfo]:
        if sgg_code is not None:
            sql = ("SELECT * FROM school_info"
                   " WHERE lat IS NOT NULL AND lng IS NOT NULL AND sgg_code = ?")
            params: tuple = (sgg_code,)
        else:
            sql = "SELECT * FROM school_info WHERE lat IS NOT NULL AND lng IS NOT NULL"
            params = ()
        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [
            _row_to_school(r) for r in rows
            if _haversine_km(lat, lng, r["lat"], r["lng"]) <= radius_km
        ]

    def upsert_student_record(self, r: SchoolStudentRecord) -> None:
        sql = """
        INSERT INTO school_student_records
            (school_code, year, grade, class_count, student_count,
             students_per_class, male_count, female_count, collected_at)
        VALUES
            (:school_code, :year, :grade, :class_count, :student_count,
             :students_per_class, :male_count, :female_count, :collected_at)
        ON CONFLICT(school_code, year, grade) DO UPDATE SET
            class_count=excluded.class_count,
            student_count=excluded.student_count,
            students_per_class=excluded.students_per_class,
            male_count=excluded.male_count,
            female_count=excluded.female_count,
            collected_at=excluded.collected_at
        """
        with self._conn() as conn:
            conn.execute(sql, {
                "school_code": r.school_code,
                "year": r.year,
                "grade": r.grade,
                "class_count": r.class_count,
                "student_count": r.student_count,
                "students_per_class": r.students_per_class,
                "male_count": r.male_count,
                "female_count": r.female_count,
                "collected_at": r.collected_at or datetime.now(timezone.utc).isoformat(),
            })

    def get_student_records(
        self, school_code: str, year: Optional[int] = None
    ) -> List[SchoolStudentRecord]:
        with self._conn() as conn:
            if year is None:
                rows = conn.execute(
                    "SELECT * FROM school_student_records WHERE school_code=?",
                    (school_code,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM school_student_records WHERE school_code=? AND year=?",
                    (school_code, year),
                ).fetchall()
        return [_row_to_student(r) for r in rows]

    def upsert_teacher_record(self, r: SchoolTeacherRecord) -> None:
        sql = """
        INSERT INTO school_teacher_records
            (school_code, year, total_teachers, students_per_teacher, collected_at)
        VALUES
            (:school_code, :year, :total_teachers, :students_per_teacher, :collected_at)
        ON CONFLICT(school_code, year) DO UPDATE SET
            total_teachers=excluded.total_teachers,
            students_per_teacher=excluded.students_per_teacher,
            collected_at=excluded.collected_at
        """
        with self._conn() as conn:
            conn.execute(sql, {
                "school_code": r.school_code,
                "year": r.year,
                "total_teachers": r.total_teachers,
                "students_per_teacher": r.students_per_teacher,
                "collected_at": r.collected_at or datetime.now(timezone.utc).isoformat(),
            })

    def get_teacher_records(
        self, school_code: str, year: Optional[int] = None
    ) -> List[SchoolTeacherRecord]:
        with self._conn() as conn:
            if year is None:
                rows = conn.execute(
                    "SELECT * FROM school_teacher_records WHERE school_code=?",
                    (school_code,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM school_teacher_records WHERE school_code=? AND year=?",
                    (school_code, year),
                ).fetchall()
        return [_row_to_teacher(r) for r in rows]

    def upsert_school_score(self, sc: SchoolScore) -> None:
        sql = """
        INSERT INTO school_scores
            (complex_code, school_kind, nearby_school_count,
             avg_students_per_class, avg_students_per_teacher, score, collected_at)
        VALUES
            (:complex_code, :school_kind, :nearby_school_count,
             :avg_students_per_class, :avg_students_per_teacher, :score, :collected_at)
        ON CONFLICT(complex_code, school_kind) DO UPDATE SET
            nearby_school_count=excluded.nearby_school_count,
            avg_students_per_class=excluded.avg_students_per_class,
            avg_students_per_teacher=excluded.avg_students_per_teacher,
            score=excluded.score,
            collected_at=excluded.collected_at
        """
        with self._conn() as conn:
            conn.execute(sql, {
                "complex_code": sc.complex_code,
                "school_kind": sc.school_kind,
                "nearby_school_count": sc.nearby_school_count,
                "avg_students_per_class": sc.avg_students_per_class,
                "avg_students_per_teacher": sc.avg_students_per_teacher,
                "score": sc.score,
                "collected_at": sc.collected_at or datetime.now(timezone.utc).isoformat(),
            })

    def get_score(self, complex_code: str, school_kind: str) -> Optional[SchoolScore]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM school_scores WHERE complex_code=? AND school_kind=?",
                (complex_code, school_kind),
            ).fetchone()
        return _row_to_score(row) if row else None


def _row_to_school(r: sqlite3.Row) -> SchoolInfo:
    return SchoolInfo(
        school_code=r["school_code"],
        school_name=r["school_name"],
        school_kind=r["school_kind"],
        sido_code=r["sido_code"],
        sgg_code=r["sgg_code"],
        address=r["address"],
        establishment_type=r["establishment_type"],
        collected_at=r["collected_at"],
        lat=r["lat"],
        lng=r["lng"],
        founding_year=r["founding_year"],
    )


def _row_to_student(r: sqlite3.Row) -> SchoolStudentRecord:
    return SchoolStudentRecord(
        school_code=r["school_code"],
        year=r["year"],
        grade=r["grade"],
        class_count=r["class_count"],
        student_count=r["student_count"],
        students_per_class=r["students_per_class"],
        male_count=r["male_count"],
        female_count=r["female_count"],
        collected_at=r["collected_at"],
    )


def _row_to_teacher(r: sqlite3.Row) -> SchoolTeacherRecord:
    return SchoolTeacherRecord(
        school_code=r["school_code"],
        year=r["year"],
        total_teachers=r["total_teachers"],
        students_per_teacher=r["students_per_teacher"],
        collected_at=r["collected_at"],
    )


def _row_to_score(r: sqlite3.Row) -> SchoolScore:
    return SchoolScore(
        complex_code=r["complex_code"],
        school_kind=r["school_kind"],
        nearby_school_count=r["nearby_school_count"],
        avg_students_per_class=r["avg_students_per_class"],
        avg_students_per_teacher=r["avg_students_per_teacher"],
        score=r["score"],
        collected_at=r["collected_at"],
    )
