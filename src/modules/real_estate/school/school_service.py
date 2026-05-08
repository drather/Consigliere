"""SchoolService — collects and scores school district data.

Field mapping (discovered via smoke test 2026-05-09):

apiType=0 (학교기본정보):
  SCHUL_CODE, SCHUL_NM, SCHUL_KND_SC_CODE, LCTN_SC_CODE, ADRCD_CD,
  ADRES, LTTUD, LGTUD, FOND_SC_CODE, FOND_YMD

apiType=10 (학생현황) — one row per school, year-level aggregation:
  SCHUL_CODE, STDNT_SUM (total), STDNT_SUM_21..26 (grade 1-6 totals),
  COL_2G1/COL_2G2 pattern = COL_{2}{grade}{1=male/2=female} class counts
  e.g. COL_211=grade1 male classes, COL_212=grade1 female classes

apiType=17 (교원현황):
  SCHUL_CODE, COL_1 (total teachers), ML_TOI_FGR (male), FML_TOI_FGR (female)
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from core.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from modules.real_estate.school.models import (
    SchoolInfo,
    SchoolStudentRecord,
    SchoolTeacherRecord,
)
from modules.real_estate.school.school_repository import SchoolRepository

# School kind codes used by the API
_SCHOOL_KINDS = ["02", "03", "04"]  # 초등, 중등, 고등

# Grade suffixes in apiType=10: COL_2{grade}{sex} — elementary has grades 1-6 (21..26)
# Middle/high grades: grade 1=1, 2=2, 3=3 (11..13 for middle, 11..13 for high)
# We use the STDNT_SUM_XX keys to detect which grades exist in each row.
_ELEMENTARY_GRADE_SUFFIXES = ["21", "22", "23", "24", "25", "26"]
_SECONDARY_GRADE_SUFFIXES = ["11", "12", "13"]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_int(val: Any, default: int = 0) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


class SchoolService:
    """Handles collection and scoring of school district data."""

    def __init__(
        self,
        client,
        repo: SchoolRepository,
        geocoder=None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self._client = client
        self._repo = repo
        self._geocoder = geocoder
        self._config = config or {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def collect_by_district(self, sido_code: str, sgg_code: str) -> Dict[str, int]:
        """Collect school info, student records, and teacher records for a district.

        Iterates over 초/중/고 (kinds 02/03/04), fetches from API, and persists to DB.

        Returns:
            dict with keys: schools_saved, student_records_saved, teacher_records_saved
        """
        year = datetime.now(timezone.utc).year
        pban_yr = str(year)
        now = _now_iso()

        schools_saved = 0
        student_records_saved = 0
        teacher_records_saved = 0

        for kind in _SCHOOL_KINDS:
            # 1. Collect school basic info
            school_rows = self._client.get_school_list(sido_code, sgg_code, kind)
            school_map: Dict[str, SchoolInfo] = {}
            for raw in school_rows:
                school = self._parse_school(raw, now)
                self._repo.upsert_school(school)
                school_map[school.school_code] = school
                schools_saved += 1

            if not school_map:
                continue

            # 2. Collect student counts
            raw_students = self._client.get_student_counts(sido_code, sgg_code, kind, pban_yr)
            # Build school_code → total_students map for teacher ratio calculation.
            # STDNT_SUM exists in apiType=10 (student) rows, not in apiType=17 (teacher) rows.
            student_total_map: Dict[str, int] = {}
            for raw in raw_students:
                code = raw.get("SCHUL_CODE", "")
                total = _safe_int(raw.get("STDNT_SUM", 0))
                if code and total:
                    student_total_map[code] = total
                records = self._parse_student_records(raw, year, now)
                for rec in records:
                    self._repo.upsert_student_record(rec)
                    student_records_saved += 1

            # 3. Collect teacher counts
            raw_teachers = self._client.get_teacher_counts(sido_code, sgg_code, kind, pban_yr)
            for raw in raw_teachers:
                # Look up total_students from student rows (STDNT_SUM is not in apiType=17)
                code = raw.get("SCHUL_CODE", "")
                total_students = student_total_map.get(code, 0)
                rec = self._parse_teacher_record(raw, year, total_students, now)
                if rec is not None:
                    self._repo.upsert_teacher_record(rec)
                    teacher_records_saved += 1

        return {
            "schools_saved": schools_saved,
            "student_records_saved": student_records_saved,
            "teacher_records_saved": teacher_records_saved,
        }

    def calculate_score(self, complex_code: str, lat: float, lng: float) -> None:
        """Calculate school district score for a complex. (Task 5 — not yet implemented)"""
        raise NotImplementedError("calculate_score() will be implemented in Task 5")

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    def _parse_school(self, raw: Dict[str, Any], now: str) -> SchoolInfo:
        """Parse SchoolInfo from apiType=0 response row."""
        lat = _safe_float(raw.get("LTTUD")) or None
        lng = _safe_float(raw.get("LGTUD")) or None

        fond_ymd = raw.get("FOND_YMD", "")
        founding_year: Optional[int] = None
        if fond_ymd and len(fond_ymd) >= 4:
            try:
                founding_year = int(fond_ymd[:4])
            except ValueError:
                pass

        # ADRCD_CD may be a 10-digit full code; extract 5-digit sgg portion
        adrcd_cd = str(raw.get("ADRCD_CD", ""))
        sgg_code = adrcd_cd[:5] if len(adrcd_cd) >= 5 else adrcd_cd

        return SchoolInfo(
            school_code=raw.get("SCHUL_CODE", ""),
            school_name=raw.get("SCHUL_NM", ""),
            school_kind=raw.get("SCHUL_KND_SC_CODE", ""),
            sido_code=raw.get("LCTN_SC_CODE", ""),
            sgg_code=sgg_code,
            address=raw.get("ADRES", ""),
            establishment_type=raw.get("FOND_SC_CODE", ""),
            lat=lat,
            lng=lng,
            founding_year=founding_year,
            collected_at=now,
        )

    def _parse_student_records(
        self, raw: Dict[str, Any], year: int, now: str
    ) -> List[SchoolStudentRecord]:
        """Parse per-grade SchoolStudentRecord list from apiType=10 response row.

        apiType=10 returns one row per school with all grades aggregated.
        Grade keys follow the pattern:
          STDNT_SUM_{suffix}  — student count for that grade
          COL_{suffix}1       — male class count for that grade
          COL_{suffix}2       — female class count for that grade

        Elementary (02): suffixes 21..26 (grade 1-6)
        Middle/High (03/04): suffixes 11..13 (grade 1-3)
        """
        school_code = raw.get("SCHUL_CODE", "")
        records: List[SchoolStudentRecord] = []

        # Determine which grade suffixes to try
        # Try elementary suffixes first; if none found try secondary
        all_suffixes = _ELEMENTARY_GRADE_SUFFIXES + _SECONDARY_GRADE_SUFFIXES

        for suffix in all_suffixes:
            stdnt_key = f"STDNT_SUM_{suffix}"
            if stdnt_key not in raw:
                continue

            student_count = _safe_int(raw.get(stdnt_key, 0))
            male_classes = _safe_int(raw.get(f"COL_{suffix}1", 0))
            female_classes = _safe_int(raw.get(f"COL_{suffix}2", 0))
            class_count = male_classes + female_classes

            # use the full suffix as the opaque grade key (e.g. "21", "22", "11", "12")
            # avoids collision: suffix[-1] would map both "21" and "11" to "1"
            grade = suffix

            students_per_class = (
                round(student_count / class_count, 2) if class_count > 0 else 0.0
            )

            records.append(
                SchoolStudentRecord(
                    school_code=school_code,
                    year=year,
                    grade=grade,
                    class_count=class_count,
                    student_count=student_count,
                    students_per_class=students_per_class,
                    male_count=0,   # apiType=10 does not provide per-grade gender breakdown
                    female_count=0,
                    collected_at=now,
                )
            )

        return records

    def _parse_teacher_record(
        self,
        raw: Dict[str, Any],
        year: int,
        total_students: int,
        now: str,
    ) -> Optional[SchoolTeacherRecord]:
        """Parse SchoolTeacherRecord from apiType=17 response row.

        Real fields (from smoke test):
          COL_1         — total teacher headcount
          ML_TOI_FGR    — male teacher count
          FML_TOI_FGR   — female teacher count
        """
        school_code = raw.get("SCHUL_CODE", "")
        if not school_code:
            return None

        total_teachers = _safe_int(raw.get("COL_1", 0))
        if total_teachers == 0:
            # Try summing male+female as fallback
            total_teachers = (
                _safe_int(raw.get("ML_TOI_FGR", 0))
                + _safe_int(raw.get("FML_TOI_FGR", 0))
            )

        students_per_teacher = (
            round(total_students / total_teachers, 2) if total_teachers > 0 else 0.0
        )

        return SchoolTeacherRecord(
            school_code=school_code,
            year=year,
            total_teachers=total_teachers,
            students_per_teacher=students_per_teacher,
            collected_at=now,
        )
