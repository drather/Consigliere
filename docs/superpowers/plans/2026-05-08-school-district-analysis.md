# 학군 분석 (School District Analysis) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 학교알리미 OpenAPI로 단지 인근 초/중/고교 데이터를 수집하여 학군 점수를 산출하고, 리포트·대시보드에 통합한다.

**Architecture:** `src/modules/real_estate/school/` 서브패키지로 구현 (building_master 패턴 동일). SchoolInfoClient → SchoolRepository (real_estate.db 통합) → SchoolService. 단지 좌표는 GeocoderService로 조회, 반경 1km 필터링 후 sgg_code 폴백.

**Tech Stack:** Python 3.12, SQLite, requests, pytest, Streamlit (대시보드), FastAPI (API)

---

## File Map

**Create:**
- `src/modules/real_estate/school/__init__.py`
- `src/modules/real_estate/school/models.py`
- `src/modules/real_estate/school/school_info_client.py`
- `src/modules/real_estate/school/school_repository.py`
- `src/modules/real_estate/school/school_service.py`
- `tests/modules/real_estate/school/__init__.py`
- `tests/modules/real_estate/school/test_school_repository.py`
- `tests/modules/real_estate/school/test_school_info_client.py`
- `tests/modules/real_estate/school/test_school_service.py`
- `tests/modules/real_estate/school/test_school_scoring.py`

**Modify:**
- `src/modules/real_estate/config.yaml` — school 섹션 추가
- `src/modules/real_estate/scoring.py` — `_score_school()` school_score 통합
- `src/api/dependencies.py` — SchoolService DI 추가
- `src/api/routers/real_estate.py` — 2개 엔드포인트 추가
- `src/dashboard/views/real_estate.py` — `_render_apt_detail_panel()` 학군 섹션 추가

---

## Task 1: 패키지 스캐폴드 + models.py

**Files:**
- Create: `src/modules/real_estate/school/__init__.py`
- Create: `src/modules/real_estate/school/models.py`
- Create: `tests/modules/real_estate/school/__init__.py`
- Test: `tests/modules/real_estate/school/test_school_repository.py` (모델 임포트 확인용)

- [ ] **Step 1: 디렉토리 및 빈 파일 생성**

```bash
mkdir -p src/modules/real_estate/school
touch src/modules/real_estate/school/__init__.py
mkdir -p tests/modules/real_estate/school
touch tests/modules/real_estate/school/__init__.py
```

- [ ] **Step 2: 실패하는 임포트 테스트 작성**

`tests/modules/real_estate/school/test_school_repository.py`:
```python
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
```

- [ ] **Step 3: 테스트 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/school/test_school_repository.py -v
```
Expected: `ModuleNotFoundError: No module named 'modules.real_estate.school.models'`

- [ ] **Step 4: models.py 작성**

`src/modules/real_estate/school/models.py`:
```python
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
    lat: Optional[float]
    lng: Optional[float]
    establishment_type: str     # 공립/사립
    founding_year: Optional[int]
    collected_at: str


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
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/school/test_school_repository.py::test_school_info_fields tests/modules/real_estate/school/test_school_repository.py::test_school_student_record_fields tests/modules/real_estate/school/test_school_repository.py::test_school_teacher_record_fields tests/modules/real_estate/school/test_school_repository.py::test_school_score_fields -v
```
Expected: 4 PASSED

- [ ] **Step 6: 커밋**

```bash
git add src/modules/real_estate/school/ tests/modules/real_estate/school/
git commit -m "feat(school): school 패키지 스캐폴드 + 데이터 모델 정의"
```

---

## Task 2: SchoolRepository (TDD)

**Files:**
- Create: `src/modules/real_estate/school/school_repository.py`
- Test: `tests/modules/real_estate/school/test_school_repository.py` (확장)

- [ ] **Step 1: 실패하는 Repository 테스트 추가**

`tests/modules/real_estate/school/test_school_repository.py`에 아래를 **추가**:
```python
from modules.real_estate.school.school_repository import SchoolRepository


def _make_school(**kwargs) -> SchoolInfo:
    defaults = dict(
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
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/school/test_school_repository.py -v -k "TestSchoolRepository"
```
Expected: `ModuleNotFoundError: No module named 'modules.real_estate.school.school_repository'`

- [ ] **Step 3: school_repository.py 작성**

`src/modules/real_estate/school/school_repository.py`:
```python
import math
import sqlite3
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

    def _conn(self) -> sqlite3.Connection:
        if self._shared_conn is not None:
            return self._shared_conn
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        conn = self._conn()
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
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM school_info WHERE sgg_code=? AND school_kind=?",
                (sgg_code, school_kind),
            ).fetchall()
        return [_row_to_school(r) for r in rows]

    def get_all_schools_by_sgg(self, sgg_code: str) -> List[SchoolInfo]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM school_info WHERE sgg_code=?",
                (sgg_code,),
            ).fetchall()
        return [_row_to_school(r) for r in rows]

    def get_schools_near(
        self, lat: float, lng: float, radius_km: float
    ) -> List[SchoolInfo]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM school_info WHERE lat IS NOT NULL AND lng IS NOT NULL"
            ).fetchall()
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

    def get_student_records(self, school_code: str) -> List[SchoolStudentRecord]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM school_student_records WHERE school_code=?",
                (school_code,),
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

    def get_teacher_records(self, school_code: str) -> List[SchoolTeacherRecord]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM school_teacher_records WHERE school_code=?",
                (school_code,),
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
        lat=r["lat"],
        lng=r["lng"],
        establishment_type=r["establishment_type"],
        founding_year=r["founding_year"],
        collected_at=r["collected_at"],
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
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/school/test_school_repository.py -v
```
Expected: 전체 PASSED (4 모델 테스트 + 9 Repository 테스트 = 13 PASSED)

- [ ] **Step 5: 커밋**

```bash
git add src/modules/real_estate/school/school_repository.py tests/modules/real_estate/school/test_school_repository.py
git commit -m "feat(school): SchoolRepository SQLite CRUD 구현 (TDD)"
```

---

## Task 3: SchoolInfoClient (TDD)

**Files:**
- Create: `src/modules/real_estate/school/school_info_client.py`
- Test: `tests/modules/real_estate/school/test_school_info_client.py`

**⚠️ apiType 검증 주의:** 학교알리미 API의 실제 apiType 값은 API 키 발급 후 smoke test로 확인 필요.
현재 알려진 값: `0`=학교기본정보. 나머지는 구현 후 Step 5에서 실제 API로 검증.

- [ ] **Step 1: 실패하는 클라이언트 테스트 작성**

`tests/modules/real_estate/school/test_school_info_client.py`:
```python
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
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/school/test_school_info_client.py -v
```
Expected: `ModuleNotFoundError: No module named 'modules.real_estate.school.school_info_client'`

- [ ] **Step 3: school_info_client.py 작성**

`src/modules/real_estate/school/school_info_client.py`:
```python
import os
from typing import Any, Dict, List, Optional

import requests

try:
    from core.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

_BASE_URL = "https://www.schoolinfo.go.kr/openApi.do"

# apiType 값: 실제 API 응답으로 검증 필요 (Phase 3 smoke test)
_API_TYPE_SCHOOL_INFO = "0"       # 학교기본정보 (PDF 확인)
_API_TYPE_STUDENT_BY_GRADE = "2"  # 학년별·학급별 학생수 (요검증)
_API_TYPE_STUDENT_BY_GENDER = "1" # 성별 학생수 (요검증)
_API_TYPE_TEACHER = "5"           # 직위별 교원 현황 (요검증)


class SchoolInfoClient:
    """학교알리미 OpenAPI 클라이언트.

    API 키는 환경변수 SCHOOLINFO_API_KEY에서 읽는다.
    """

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or os.getenv("SCHOOLINFO_API_KEY", "")

    def _fetch(
        self, api_type: str, sido_code: str, sgg_code: str, school_kind: str
    ) -> List[Dict[str, Any]]:
        params = {
            "apiKey": self._api_key,
            "apiType": api_type,
            "sidoCode": sido_code,
            "sggCode": sgg_code,
            "schulKndCode": school_kind,
        }
        try:
            url = _BASE_URL
            query = "&".join(f"{k}={v}" for k, v in params.items())
            full_url = f"{url}?{query}"
            logger.info(f"[SchoolInfoClient] apiType={api_type} sido={sido_code} sgg={sgg_code} kind={school_kind}")
            resp = requests.get(full_url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if data.get("resultCode") != "success":
                logger.warning(f"[SchoolInfoClient] API 오류: {data.get('resultMsg')}")
                return []
            return data.get("list", [])
        except Exception as e:
            logger.error(f"[SchoolInfoClient] 요청 실패 apiType={api_type}: {e}")
            return []

    def get_school_list(
        self, sido_code: str, sgg_code: str, school_kind: str
    ) -> List[Dict[str, Any]]:
        return self._fetch(_API_TYPE_SCHOOL_INFO, sido_code, sgg_code, school_kind)

    def get_student_counts(
        self, sido_code: str, sgg_code: str, school_kind: str
    ) -> List[Dict[str, Any]]:
        return self._fetch(_API_TYPE_STUDENT_BY_GRADE, sido_code, sgg_code, school_kind)

    def get_gender_counts(
        self, sido_code: str, sgg_code: str, school_kind: str
    ) -> List[Dict[str, Any]]:
        return self._fetch(_API_TYPE_STUDENT_BY_GENDER, sido_code, sgg_code, school_kind)

    def get_teacher_counts(
        self, sido_code: str, sgg_code: str, school_kind: str
    ) -> List[Dict[str, Any]]:
        return self._fetch(_API_TYPE_TEACHER, sido_code, sgg_code, school_kind)
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/school/test_school_info_client.py -v
```
Expected: 6 PASSED

- [ ] **Step 5: apiType 실제 검증 (smoke test)**

아래 스크립트를 실행해 실제 API 응답을 확인하고, `school_info_client.py`의 apiType 상수를 수정한다:

```bash
arch -arm64 .venv/bin/python3.12 -c "
import os, json, requests
from dotenv import load_dotenv
load_dotenv()
key = os.getenv('SCHOOLINFO_API_KEY', '')
# 서울 종로구 초등학교 기본정보 조회 (apiType=0 확인)
for api_type in ['0', '1', '2', '3', '4', '5']:
    url = f'https://www.schoolinfo.go.kr/openApi.do?apiKey={key}&apiType={api_type}&sidoCode=11&sggCode=11110&schulKndCode=02'
    r = requests.get(url, timeout=15)
    data = r.json()
    code = data.get('resultCode', 'N/A')
    count = len(data.get('list', []))
    first_keys = list(data.get('list', [{}])[0].keys())[:5] if data.get('list') else []
    print(f'apiType={api_type}: code={code} count={count} keys={first_keys}')
"
```

결과 확인 후 `school_info_client.py`의 `_API_TYPE_*` 상수를 올바른 값으로 수정.

- [ ] **Step 6: 커밋**

```bash
git add src/modules/real_estate/school/school_info_client.py tests/modules/real_estate/school/test_school_info_client.py
git commit -m "feat(school): SchoolInfoClient 학교알리미 API 클라이언트 구현 (TDD)"
```

---

## Task 4: SchoolService — collect_by_district() (TDD)

**Files:**
- Create: `src/modules/real_estate/school/school_service.py`
- Test: `tests/modules/real_estate/school/test_school_service.py`

- [ ] **Step 1: 실패하는 서비스 테스트 작성**

`tests/modules/real_estate/school/test_school_service.py`:
```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

from unittest.mock import MagicMock, patch
from modules.real_estate.school.models import SchoolInfo, SchoolStudentRecord, SchoolTeacherRecord
from modules.real_estate.school.school_repository import SchoolRepository
from modules.real_estate.school.school_service import SchoolService

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
        "SCHUL_FOND_TYP_CODE": "공립",
        "FOND_YMD": "19700301",
    }
]

_STUDENT_LIST = [
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
]

_TEACHER_LIST = [
    {
        "SCHUL_CODE": "S000001234",
        "SCHUL_NM": "반포초등학교",
        "TOTSTUDN_CNT": "300",
        "THING_CNT": "30",
        "DATA_YMD": "20250401",
    }
]


def _make_client(schools=None, students=None, genders=None, teachers=None):
    client = MagicMock()
    client.get_school_list.return_value = schools if schools is not None else _SCHOOL_LIST
    client.get_student_counts.return_value = students if students is not None else _STUDENT_LIST
    client.get_gender_counts.return_value = genders if genders is not None else []
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
        # 초/중/고 각각 3회 school_list 호출
        assert client.get_school_list.call_count == 3

    def test_collect_saves_student_records(self):
        svc = self._svc()
        svc.collect_by_district("11", "11650")
        repo = svc._repo
        records = repo.get_student_records("S000001234")
        assert len(records) >= 1
        assert records[0].grade == "1학년"

    def test_collect_saves_teacher_records(self):
        svc = self._svc()
        svc.collect_by_district("11", "11650")
        repo = svc._repo
        records = repo.get_teacher_records("S000001234")
        assert len(records) >= 1
        assert records[0].total_teachers == 30

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
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/school/test_school_service.py -v -k "TestCollectByDistrict"
```
Expected: `ModuleNotFoundError: No module named 'modules.real_estate.school.school_service'`

- [ ] **Step 3: school_service.py 작성 (collect_by_district 부분)**

`src/modules/real_estate/school/school_service.py`:
```python
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from core.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from modules.real_estate.school.models import (
    SchoolInfo, SchoolStudentRecord, SchoolTeacherRecord, SchoolScore,
)
from modules.real_estate.school.school_info_client import SchoolInfoClient
from modules.real_estate.school.school_repository import SchoolRepository

_SCHOOL_KINDS = [
    ("02", "elementary"),
    ("03", "middle"),
    ("04", "high"),
]


class SchoolService:
    def __init__(
        self,
        client: SchoolInfoClient,
        repo: SchoolRepository,
        geocoder=None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self._client = client
        self._repo = repo
        self._geocoder = geocoder
        self._config = config or {}

    def collect_by_district(self, sido_code: str, sgg_code: str) -> Dict[str, int]:
        result = {"schools_saved": 0, "student_records_saved": 0, "teacher_records_saved": 0}
        now = datetime.now(timezone.utc).isoformat()
        year = datetime.now().year

        for kind_code, _ in _SCHOOL_KINDS:
            # 학교기본정보
            raw_schools = self._client.get_school_list(sido_code, sgg_code, kind_code)
            for raw in raw_schools:
                try:
                    school = _parse_school(raw, now)
                    self._repo.upsert_school(school)
                    result["schools_saved"] += 1
                except Exception as e:
                    logger.warning(f"[SchoolService] school parse error: {e}")

            # 학년별·학급별 학생수 (성별 학생수 포함)
            raw_students = self._client.get_student_counts(sido_code, sgg_code, kind_code)
            gender_map = _build_gender_map(
                self._client.get_gender_counts(sido_code, sgg_code, kind_code)
            )
            for raw in raw_students:
                try:
                    record = _parse_student_record(raw, year, gender_map, now)
                    self._repo.upsert_student_record(record)
                    result["student_records_saved"] += 1
                except Exception as e:
                    logger.warning(f"[SchoolService] student record parse error: {e}")

            # 직위별 교원 현황
            raw_teachers = self._client.get_teacher_counts(sido_code, sgg_code, kind_code)
            teacher_student_map = _build_student_total_map(raw_students)
            for raw in raw_teachers:
                try:
                    record = _parse_teacher_record(raw, year, teacher_student_map, now)
                    self._repo.upsert_teacher_record(record)
                    result["teacher_records_saved"] += 1
                except Exception as e:
                    logger.warning(f"[SchoolService] teacher record parse error: {e}")

        return result

    def calculate_score(
        self,
        complex_code: str,
        apt_name: str,
        district_code: str,
        radius_km: Optional[float] = None,
    ) -> SchoolScore:
        cfg = self._config
        radius = radius_km or float(cfg.get("radius_km", 1.0))
        ideal = int(cfg.get("students_per_class_ideal", 20))
        warning = int(cfg.get("students_per_class_warning", 28))
        high_count = int(cfg.get("nearby_school_high", 3))
        mid_count = int(cfg.get("nearby_school_mid", 1))
        w_density = float(cfg.get("score_weight_density", 0.30))
        w_class = float(cfg.get("score_weight_class_size", 0.70))

        sido_code = district_code[:2]
        sgg_code = district_code

        lat, lng = None, None
        if self._geocoder:
            try:
                coords = self._geocoder.geocode(apt_name, district_code)
                if coords:
                    lat, lng = coords
            except Exception:
                pass

        if lat is not None and lng is not None:
            nearby = self._repo.get_schools_near(lat, lng, radius)
        else:
            nearby = self._repo.get_all_schools_by_sgg(sgg_code)

        now = datetime.now(timezone.utc).isoformat()

        if not nearby:
            score = SchoolScore(
                complex_code=complex_code,
                school_kind="total",
                nearby_school_count=0,
                avg_students_per_class=0.0,
                avg_students_per_teacher=0.0,
                score=50,
                collected_at=now,
            )
            self._repo.upsert_school_score(score)
            return score

        all_per_class: List[float] = []
        all_per_teacher: List[float] = []
        for school in nearby:
            records = self._repo.get_student_records(school.school_code)
            if records:
                avg = sum(r.students_per_class for r in records) / len(records)
                all_per_class.append(avg)
            t_records = self._repo.get_teacher_records(school.school_code)
            if t_records:
                all_per_teacher.append(t_records[-1].students_per_teacher)

        avg_per_class = sum(all_per_class) / len(all_per_class) if all_per_class else 0.0
        avg_per_teacher = sum(all_per_teacher) / len(all_per_teacher) if all_per_teacher else 0.0

        score_val = _calc_score(
            nearby_count=len(nearby),
            avg_per_class=avg_per_class,
            ideal=ideal,
            warning=warning,
            high_count=high_count,
            mid_count=mid_count,
            w_density=w_density,
            w_class=w_class,
        )

        score = SchoolScore(
            complex_code=complex_code,
            school_kind="total",
            nearby_school_count=len(nearby),
            avg_students_per_class=round(avg_per_class, 1),
            avg_students_per_teacher=round(avg_per_teacher, 1),
            score=score_val,
            collected_at=now,
        )
        self._repo.upsert_school_score(score)
        return score


def _calc_score(
    nearby_count: int,
    avg_per_class: float,
    ideal: int,
    warning: int,
    high_count: int,
    mid_count: int,
    w_density: float,
    w_class: float,
) -> int:
    if avg_per_class <= ideal:
        class_score = 100
    elif avg_per_class <= warning:
        class_score = 60
    else:
        class_score = 20

    if nearby_count >= high_count:
        density_score = 100
    elif nearby_count >= mid_count:
        density_score = 60
    else:
        density_score = 20

    return round(class_score * w_class + density_score * w_density)


def _parse_school(raw: Dict, now: str) -> SchoolInfo:
    founding_str = raw.get("FOND_YMD", "")
    founding_year = int(founding_str[:4]) if len(founding_str) >= 4 else None
    lat_str = raw.get("LTTUD") or raw.get("LAT") or ""
    lng_str = raw.get("LGTUD") or raw.get("LNG") or ""
    return SchoolInfo(
        school_code=raw.get("SCHUL_CODE", ""),
        school_name=raw.get("SCHUL_NM", ""),
        school_kind=raw.get("SCHUL_KND_SC_CODE", ""),
        sido_code=raw.get("LCTN_SC_CODE", ""),
        sgg_code=raw.get("ADRCD_CD", ""),
        address=raw.get("ADRES", ""),
        lat=float(lat_str) if lat_str else None,
        lng=float(lng_str) if lng_str else None,
        establishment_type=raw.get("SCHUL_FOND_TYP_CODE", ""),
        founding_year=founding_year,
        collected_at=now,
    )


def _build_gender_map(raw_genders: List[Dict]) -> Dict[str, Dict]:
    result: Dict[str, Dict] = {}
    for raw in raw_genders:
        code = raw.get("SCHUL_CODE", "")
        result[code] = raw
    return result


def _build_student_total_map(raw_students: List[Dict]) -> Dict[str, int]:
    totals: Dict[str, int] = {}
    for raw in raw_students:
        code = raw.get("SCHUL_CODE", "")
        cnt = int(raw.get("TOTSTUDN_CNT", 0) or 0)
        totals[code] = totals.get(code, 0) + cnt
    return totals


def _parse_student_record(
    raw: Dict, year: int, gender_map: Dict, now: str
) -> SchoolStudentRecord:
    school_code = raw.get("SCHUL_CODE", "")
    class_count = int(raw.get("CLRM_CNT", 0) or 0)
    student_count = int(raw.get("TOTSTUDN_CNT", 0) or 0)
    per_class = round(student_count / class_count, 1) if class_count > 0 else 0.0
    gender = gender_map.get(school_code, {})
    return SchoolStudentRecord(
        school_code=school_code,
        year=year,
        grade=raw.get("ORD_SC_NM", ""),
        class_count=class_count,
        student_count=student_count,
        students_per_class=per_class,
        male_count=int(raw.get("MALE_STUDN_CNT", 0) or gender.get("MALE_STUDN_CNT", 0) or 0),
        female_count=int(raw.get("FEMALE_STUDN_CNT", 0) or gender.get("FEMALE_STUDN_CNT", 0) or 0),
        collected_at=now,
    )


def _parse_teacher_record(
    raw: Dict, year: int, student_total_map: Dict, now: str
) -> SchoolTeacherRecord:
    school_code = raw.get("SCHUL_CODE", "")
    total_teachers = int(raw.get("THING_CNT", 0) or 0)
    total_students = student_total_map.get(school_code, 0)
    per_teacher = round(total_students / total_teachers, 1) if total_teachers > 0 else 0.0
    return SchoolTeacherRecord(
        school_code=school_code,
        year=year,
        total_teachers=total_teachers,
        students_per_teacher=per_teacher,
        collected_at=now,
    )
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/school/test_school_service.py -v -k "TestCollectByDistrict"
```
Expected: 6 PASSED

- [ ] **Step 5: 커밋**

```bash
git add src/modules/real_estate/school/school_service.py tests/modules/real_estate/school/test_school_service.py
git commit -m "feat(school): SchoolService.collect_by_district() 구현 (TDD)"
```

---

## Task 5: SchoolService — calculate_score() (TDD)

**Files:**
- Test: `tests/modules/real_estate/school/test_school_service.py` (확장)
- Test: `tests/modules/real_estate/school/test_school_scoring.py`

- [ ] **Step 1: 점수 계산 단위 테스트 작성**

`tests/modules/real_estate/school/test_school_scoring.py`:
```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

from modules.real_estate.school.school_service import _calc_score

DEFAULT_CFG = dict(ideal=20, warning=28, high_count=3, mid_count=1, w_density=0.30, w_class=0.70)


def test_score_ideal_class_size_many_schools():
    score = _calc_score(nearby_count=5, avg_per_class=18, **DEFAULT_CFG)
    assert score == round(100 * 0.70 + 100 * 0.30)  # 100


def test_score_overcrowded_few_schools():
    score = _calc_score(nearby_count=0, avg_per_class=35, **DEFAULT_CFG)
    assert score == round(20 * 0.70 + 20 * 0.30)  # 20


def test_score_medium_class_medium_density():
    score = _calc_score(nearby_count=2, avg_per_class=25, **DEFAULT_CFG)
    assert score == round(60 * 0.70 + 100 * 0.30)  # 72


def test_score_ideal_class_no_schools():
    score = _calc_score(nearby_count=0, avg_per_class=15, **DEFAULT_CFG)
    assert score == round(100 * 0.70 + 20 * 0.30)  # 76


def test_score_weight_sum_is_bounded():
    for nearby in range(0, 6):
        for avg in [15, 24, 32]:
            score = _calc_score(nearby_count=nearby, avg_per_class=avg, **DEFAULT_CFG)
            assert 0 <= score <= 100
```

- [ ] **Step 2: calculate_score() 통합 테스트 추가**

`tests/modules/real_estate/school/test_school_service.py`에 아래 클래스를 **추가**:
```python
from modules.real_estate.school.school_service import _calc_score


class TestCalculateScore:
    def _svc_with_data(self):
        from modules.real_estate.school.school_repository import SchoolRepository
        from modules.real_estate.school.school_service import SchoolService
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
        # 데이터 사전 수집
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
        from modules.real_estate.school.school_repository import SchoolRepository
        from modules.real_estate.school.school_service import SchoolService
        repo = SchoolRepository(db_path=":memory:")
        svc = SchoolService(client=_make_client(schools=[]), repo=repo, geocoder=None)
        score = svc.calculate_score("9999", "없는단지", "99999")
        assert score.score == 50
        assert score.nearby_school_count == 0

    def test_calculate_score_with_lat_lng_via_geocoder(self):
        geocoder = MagicMock()
        geocoder.geocode.return_value = (37.505, 127.001)
        from modules.real_estate.school.school_repository import SchoolRepository
        from modules.real_estate.school.school_service import SchoolService
        repo = SchoolRepository(db_path=":memory:")
        svc = SchoolService(
            client=_make_client(), repo=repo, geocoder=geocoder,
            config={"radius_km": 1.0, "students_per_class_ideal": 20,
                    "students_per_class_warning": 28, "nearby_school_high": 3,
                    "nearby_school_mid": 1, "score_weight_density": 0.30,
                    "score_weight_class_size": 0.70}
        )
        svc.collect_by_district("11", "11650")
        score = svc.calculate_score("1234567890", "반포초등학교", "11650")
        geocoder.geocode.assert_called_once_with("반포초등학교", "11650")
        assert score.complex_code == "1234567890"
```

- [ ] **Step 3: 테스트 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/school/test_school_scoring.py tests/modules/real_estate/school/test_school_service.py -v -k "TestCalculateScore or test_score"
```
Expected: `test_school_scoring.py` PASSED (이미 구현), `test_school_service.py` TestCalculateScore PASSED

- [ ] **Step 4: 전체 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/school/ -v
```
Expected: 전체 PASSED

- [ ] **Step 5: 커밋**

```bash
git add tests/modules/real_estate/school/test_school_scoring.py tests/modules/real_estate/school/test_school_service.py
git commit -m "test(school): calculate_score() 점수 계산 단위 테스트 추가"
```

---

## Task 6: config.yaml + scoring.py 통합

**Files:**
- Modify: `src/modules/real_estate/config.yaml`
- Modify: `src/modules/real_estate/scoring.py`

- [ ] **Step 1: 실패하는 scoring 통합 테스트 작성**

`tests/modules/real_estate/school/test_school_scoring.py`에 아래를 **추가**:
```python
def test_scoring_engine_uses_school_score_field():
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))
    from modules.real_estate.scoring import ScoringEngine

    weights = {"commute": 20, "liquidity": 20, "school": 20, "living_convenience": 20, "price_potential": 20}
    config = {
        "commute_thresholds": [20, 35],
        "household_thresholds": [300, 500],
        "school_keywords": ["명문"],
        "reconstruction_score_map": {"UNKNOWN": 50},
        "data_absent_neutral": 50,
    }
    engine = ScoringEngine(weights=weights, config=config)
    candidate = {
        "apt_name": "반포자이",
        "commute_minutes": 25,
        "household_count": 500,
        "nearest_stations": [],
        "school_zone_notes": None,
        "reconstruction_potential": "UNKNOWN",
        "gtx_benefit": False,
        "school_score": 85,  # SchoolService로 계산된 점수
    }
    result = engine.score_all([candidate])
    assert result[0]["scores"]["school"] == 85
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/school/test_school_scoring.py::test_scoring_engine_uses_school_score_field -v
```
Expected: FAILED (school_score 필드 미지원)

- [ ] **Step 3: config.yaml에 school 섹션 추가**

`src/modules/real_estate/config.yaml`의 `poi:` 섹션 아래에 추가:
```yaml
school:
  radius_km: 1.0
  students_per_class_ideal: 20
  students_per_class_warning: 28
  nearby_school_high: 3
  nearby_school_mid: 1
  score_weight_density: 0.30
  score_weight_class_size: 0.70
```

- [ ] **Step 4: scoring.py의 `_score_school()` 수정**

`src/modules/real_estate/scoring.py`의 `_score_school()` 메서드를:
```python
    def _score_school(self, c: Dict) -> int:
        """SchoolService 학군 점수 우선, 없으면 POI 학원수/키워드 fallback."""
        school_score = c.get("school_score")
        if school_score is not None:
            return int(school_score)

        poi_academies = c.get("poi_academies_count")
        if poi_academies is not None:
            if poi_academies >= self.poi_academy_high:
                return _HIGH
            if poi_academies >= self.poi_academy_mid:
                return _MEDIUM
            return _LOW

        notes = c.get("school_zone_notes")
        if notes is None:
            return self.neutral
        if any(kw in notes for kw in self.school_keywords):
            return _HIGH
        schools = c.get("elementary_schools", [])
        if schools:
            return _MEDIUM
        return _LOW
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/school/test_school_scoring.py -v
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_scoring.py -v
```
Expected: 전체 PASSED (기존 scoring 테스트 포함)

- [ ] **Step 6: 커밋**

```bash
git add src/modules/real_estate/config.yaml src/modules/real_estate/scoring.py tests/modules/real_estate/school/test_school_scoring.py
git commit -m "feat(school): config.yaml school 섹션 추가 + scoring.py school_score 통합"
```

---

## Task 7: API 통합 (dependencies.py + router)

**Files:**
- Modify: `src/api/dependencies.py`
- Modify: `src/api/routers/real_estate.py`

- [ ] **Step 1: dependencies.py에 SchoolService 추가**

`src/api/dependencies.py` 파일 끝에 추가 (`GeocoderService`는 이미 파일 내 commute 섹션에서 임포트됨):
```python
from modules.real_estate.school.school_info_client import SchoolInfoClient
from modules.real_estate.school.school_repository import SchoolRepository
from modules.real_estate.school.school_service import SchoolService

_school_cfg_raw = _re_config.get("school", {})
_school_repo = SchoolRepository(db_path=_re_db_path)
_school_service = SchoolService(
    client=SchoolInfoClient(api_key=os.getenv("SCHOOLINFO_API_KEY", "")),
    repo=_school_repo,
    geocoder=GeocoderService(api_key=os.getenv("KAKAO_API_KEY", "")),
    config=_school_cfg_raw,
)


def get_school_service() -> SchoolService:
    return _school_service
```

- [ ] **Step 2: real_estate.py router에 엔드포인트 추가**

`src/api/routers/real_estate.py`에서 import에 아래를 추가:
```python
from api.dependencies import get_school_service
from modules.real_estate.school.school_service import SchoolService
```

그리고 파일 끝(`router` 정의 아래)에 엔드포인트 추가:
```python
class SchoolCollectRequest(BaseModel):
    sido_code: str = Field("11", description="시도코드 (예: 11=서울)")
    sgg_code: str = Field(..., description="시군구코드 5자리 (예: 11650=서초구)")


@router.post("/jobs/school/collect")
def collect_school_data(
    request: SchoolCollectRequest,
    school_service: SchoolService = Depends(get_school_service),
):
    """시군구 단위로 초/중/고 학교 데이터 수집."""
    try:
        result = school_service.collect_by_district(request.sido_code, request.sgg_code)
        return {"status": "success", **result}
    except Exception as e:
        logger.error(f"[School Collect] {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/real-estate/school/{complex_code}")
def get_school_score(
    complex_code: str,
    apt_name: str = "",
    district_code: str = "",
    school_service: SchoolService = Depends(get_school_service),
):
    """단지 학군 점수 조회. 미계산 시 즉시 계산 후 반환."""
    try:
        cached = school_service._repo.get_score(complex_code, "total")
        if cached:
            return {
                "complex_code": cached.complex_code,
                "school_kind": cached.school_kind,
                "nearby_school_count": cached.nearby_school_count,
                "avg_students_per_class": cached.avg_students_per_class,
                "avg_students_per_teacher": cached.avg_students_per_teacher,
                "score": cached.score,
                "collected_at": cached.collected_at,
            }
        if apt_name and district_code:
            score = school_service.calculate_score(complex_code, apt_name, district_code)
            return {
                "complex_code": score.complex_code,
                "school_kind": score.school_kind,
                "nearby_school_count": score.nearby_school_count,
                "avg_students_per_class": score.avg_students_per_class,
                "avg_students_per_teacher": score.avg_students_per_teacher,
                "score": score.score,
                "collected_at": score.collected_at,
            }
        return {"complex_code": complex_code, "score": 50, "message": "데이터 미수집"}
    except Exception as e:
        logger.error(f"[School Score] {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 3: FastAPI 서버 기동 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000 &
sleep 3
curl -s http://localhost:8000/docs | grep -o "school" | head -5
```
Expected: `school` 텍스트 포함 (Swagger UI에 엔드포인트 등록 확인)

- [ ] **Step 4: 커밋**

```bash
git add src/api/dependencies.py src/api/routers/real_estate.py
git commit -m "feat(school): API 엔드포인트 추가 — /jobs/school/collect + /dashboard/real-estate/school/{complex_code}"
```

---

## Task 8: 대시보드 학군 섹션 추가

**Files:**
- Modify: `src/dashboard/views/real_estate.py`

- [ ] **Step 1: `_render_apt_detail_panel()`에 학군 섹션 추가**

시그니처는 변경 없음 — 학군 데이터는 commute와 동일하게 FastAPI 엔드포인트 직접 호출 방식.

`src/dashboard/views/real_estate.py`에서 출퇴근 expander(`with st.expander("🗺️ 출퇴근 경로 상세"...`) 블록 아래, 건물정보 섹션(`# ── 건물 정보`) 위에 아래 블록을 삽입:
```python
        # 학군 분석 카드
        with st.expander("📚 학군 분석", expanded=False):
            try:
                import requests as _req
                _district = entry.district_code or ""
                _ccode = getattr(entry, "complex_code", None) or ""
                _apt_nm = entry.apt_name or ""
                school_resp = _req.get(
                    f"http://localhost:8000/dashboard/real-estate/school/{_ccode}",
                    params={"apt_name": _apt_nm, "district_code": _district},
                    timeout=15,
                )
                if school_resp.status_code == 200:
                    sd = school_resp.json()
                    sc1, sc2, sc3, sc4 = st.columns(4)
                    with sc1:
                        st.metric("반경 1km 학교 수", f"{sd.get('nearby_school_count', '-')}개")
                    with sc2:
                        avg_cls = sd.get('avg_students_per_class', 0)
                        st.metric("학급당 평균 학생수", f"{avg_cls:.1f}명" if avg_cls else "-")
                    with sc3:
                        avg_tch = sd.get('avg_students_per_teacher', 0)
                        st.metric("교사 1인당 학생수", f"{avg_tch:.1f}명" if avg_tch else "-")
                    with sc4:
                        st.metric("학군 점수", f"{sd.get('score', '-')}/100")
                    if sd.get("message"):
                        st.caption(sd["message"])
                else:
                    st.caption("학군 정보 조회 실패")
            except Exception:
                st.caption("서버 연결 실패 — FastAPI 서버가 실행 중인지 확인하세요")
```

- [ ] **Step 2: 기존 `_render_apt_detail_panel()` 호출부 변경 없음 확인**

`src/dashboard/views/real_estate.py` 호출부(line ~455) 확인:
```python
_render_apt_detail_panel(
    results[_sel_idx],
    apt_repo=_apt_detail_repo,
    bm_repo=_bm_repo,
    tx_limit=_tx_limit,
)
```
시그니처 변경 없으므로 이 호출부는 수정 불필요.

- [ ] **Step 3: 전체 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/school/ -v
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_scoring.py -v
```
Expected: 전체 PASSED

- [ ] **Step 4: 커밋**

```bash
git add src/dashboard/views/real_estate.py
git commit -m "feat(school): 대시보드 단지 상세 패널에 학군 분석 섹션 추가"
```

---

## Task 9: 실데이터 검증 + context 업데이트

**Files:**
- Modify: `docs/context/active_state.md`
- Modify: `docs/context/history.md`

- [ ] **Step 1: 실데이터 수집 테스트 (서초구 초등학교)**

```bash
arch -arm64 .venv/bin/python3.12 -c "
import os
from dotenv import load_dotenv
load_dotenv()
from modules.real_estate.school.school_info_client import SchoolInfoClient
from modules.real_estate.school.school_repository import SchoolRepository
from modules.real_estate.school.school_service import SchoolService

client = SchoolInfoClient()
repo = SchoolRepository(db_path=':memory:')
svc = SchoolService(client=client, repo=repo, geocoder=None)
result = svc.collect_by_district('11', '11650')
print('결과:', result)
schools = repo.get_schools_by_sgg('11650', '02')
print(f'초등학교 {len(schools)}개 수집')
if schools:
    print('예시:', schools[0].school_name, schools[0].lat, schools[0].lng)
"
```
Expected: `schools_saved > 0`, 학교명·좌표 출력

- [ ] **Step 2: apiType 오류 발생 시 수정**

실데이터 검증에서 학생수/교원 데이터가 0이면 Task 3 Step 5의 smoke test로 올바른 apiType 확인 후 `school_info_client.py` 상수 수정.

- [ ] **Step 3: active_state.md 업데이트**

`docs/context/active_state.md`에서 현재 포커스를 아래로 갱신:
```markdown
**Current Active Feature:** 학교알리미 학군 분석 완료 (2026-05-08)
- SchoolInfoClient + SchoolRepository + SchoolService 구현
- scoring.py school_score 통합
- API 엔드포인트 2개: POST /jobs/school/collect, GET /dashboard/real-estate/school/{complex_code}
- 대시보드 Tab1 학군 섹션 추가
```

- [ ] **Step 4: history.md 업데이트**

`docs/context/history.md` 상단에 새 섹션 추가:
```markdown
## 2026-05-08: 학교알리미 기반 학군 분석 구현

- **Feature:** `feature/school-district-analysis` → master 머지
- **신규 패키지:** `src/modules/real_estate/school/`
  - `SchoolInfoClient` — 학교알리미 OpenAPI (apiType=0/1/2/5)
  - `SchoolRepository` — school_info/school_student_records/school_teacher_records/school_scores 테이블
  - `SchoolService` — collect_by_district() + calculate_score()
- **학군 점수:** 학급당 학생수(70%) + 반경 1km 학교 수(30%), data_absent_neutral=50
- **통합:** scoring.py `_score_school()` school_score 필드 우선 처리
- **API:** POST /jobs/school/collect, GET /dashboard/real-estate/school/{complex_code}
- **대시보드:** Tab1 단지 상세 패널 📚 학군 분석 expander
- **핵심 학습:** 실제 apiType 값은 smoke test 필수 (문서 미기재)
```

- [ ] **Step 5: 최종 커밋**

```bash
git add docs/context/active_state.md docs/context/history.md
git commit -m "docs(context): 학군 분석 구현 완료 — active_state + history 업데이트"
```
