"""SchoolService — collects and scores school district data.

Field mapping (discovered via smoke test 2026-05-09):

apiType=0 (학교기본정보):
  SCHUL_CODE, SCHUL_NM, SCHUL_KND_SC_CODE, LCTN_SC_CODE, ADRCD_CD,
  ADRES, LTTUD, LGTUD, FOND_SC_CODE, FOND_YMD

apiType=10 (학생현황) — one row per school, year-level aggregation:
  SCHUL_CODE, STDNT_SUM (total students),
  STDNT_SUM_21..26 (grade 1-6 totals for elementary),
  STDNT_SUM_11..13 (grade 1-3 for middle/high),
  MVIN_SUM (전입생), MVT_SUM (전출생),
  COL_2XX1/COL_2XX2 = per-grade 전입/전출 student counts (NOT class counts)
  NOTE: class count data is NOT available via this API.

apiType=17 (교원현황):
  SCHUL_CODE, COL_1 (total teachers), ML_TOI_FGR (male), FML_TOI_FGR (female)
  students_per_teacher = STDNT_SUM (from apiType=10) / COL_1
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
    SchoolScore,
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


def _calc_score(
    nearby_count: int,
    avg_transfer_rate: float,
    transfer_high: float,
    transfer_medium: float,
    high_count: int,
    mid_count: int,
    w_density: float,
    w_quality: float,
    has_quality_data: bool = True,
) -> int:
    """Calculate a 0-100 school district score from transfer-rate and density sub-scores.

    transfer_rate = MVIN_SUM / STDNT_SUM — 전입생 비율이 높을수록 학군 수요가 높음.
    """
    if not has_quality_data:
        quality_score = 50
    elif avg_transfer_rate >= transfer_high:
        quality_score = 100
    elif avg_transfer_rate >= transfer_medium:
        quality_score = 60
    else:
        quality_score = 20

    if nearby_count >= high_count:
        density_score = 100
    elif nearby_count >= mid_count:
        density_score = 60
    else:
        density_score = 20

    return round(quality_score * w_quality + density_score * w_density)


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
        now_year = datetime.now(timezone.utc).year
        now = _now_iso()
        # Try current year first; fall back to previous year if API hasn't published yet
        # (e.g. 2026 data published 2026-05-30, so early 2026 runs get 0 records)
        _pban_candidates = [str(now_year), str(now_year - 1)]

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

            # 2. Collect student counts (try current year, fall back to previous if unpublished)
            raw_students: List[Dict] = []
            data_year = now_year
            for pban_yr in _pban_candidates:
                raw_students = self._client.get_student_counts(sido_code, sgg_code, kind, pban_yr)
                if raw_students:
                    data_year = int(pban_yr)
                    break

            # Build school_code → total_students and mvin_count maps.
            # STDNT_SUM / MVIN_SUM exist in apiType=10 rows, not in apiType=17 (teacher) rows.
            student_total_map: Dict[str, int] = {}
            mvin_sum_map: Dict[str, int] = {}
            for raw in raw_students:
                code = raw.get("SCHUL_CODE", "")
                total = _safe_int(raw.get("STDNT_SUM", 0))
                mvin = _safe_int(raw.get("MVIN_SUM", 0))
                if code and total:
                    student_total_map[code] = total
                if code and mvin:
                    mvin_sum_map[code] = mvin
                records = self._parse_student_records(raw, data_year, now)
                for rec in records:
                    self._repo.upsert_student_record(rec)
                    student_records_saved += 1

            # 3. Collect teacher counts (use same pban_yr as student data)
            teacher_pban_yr = str(data_year)
            raw_teachers = self._client.get_teacher_counts(sido_code, sgg_code, kind, teacher_pban_yr)
            for raw in raw_teachers:
                code = raw.get("SCHUL_CODE", "")
                total_students = student_total_map.get(code, 0)
                mvin_count = mvin_sum_map.get(code, 0)
                rec = self._parse_teacher_record(raw, data_year, total_students, mvin_count, now)
                if rec is not None:
                    self._repo.upsert_teacher_record(rec)
                    teacher_records_saved += 1

        return {
            "schools_saved": schools_saved,
            "student_records_saved": student_records_saved,
            "teacher_records_saved": teacher_records_saved,
        }

    def calculate_score(
        self,
        complex_code: str,
        apt_name: str,
        district_code: str,
        radius_km: Optional[float] = None,
    ) -> SchoolScore:
        """Calculate school district score for a real-estate complex.

        Resolves nearby schools via geocoding (if geocoder is available) or falls back
        to all schools in the district. Computes a weighted score from class-size and
        density sub-scores, persists the result, and returns a SchoolScore.
        """
        # 1. Read config values with defaults
        transfer_high = float(self._config.get("transfer_rate_high", 0.06))
        transfer_medium = float(self._config.get("transfer_rate_medium", 0.03))
        high_count = int(self._config.get("nearby_school_high", 3))
        mid_count = int(self._config.get("nearby_school_mid", 1))
        w_density = float(self._config.get("score_weight_density", 0.30))
        w_quality = float(self._config.get("score_weight_quality", 0.70))
        cfg_radius = float(self._config.get("radius_km", 1.0))
        effective_radius = radius_km if radius_km is not None else cfg_radius

        now = _now_iso()

        # 2. Resolve lat/lng via geocoder
        lat: Optional[float] = None
        lng: Optional[float] = None
        if self._geocoder is not None:
            coords = self._geocoder.geocode(apt_name, district_code)
            if coords:
                lat, lng = coords

        # 3. Find nearby schools
        if lat is not None and lng is not None:
            nearby = self._repo.get_schools_near(lat, lng, effective_radius, sgg_code=district_code)
        else:
            # Fallback: aggregate all kinds across the district
            nearby = []
            for kind in _SCHOOL_KINDS:
                nearby.extend(self._repo.get_all_schools_by_sgg(district_code, kind))

        # 4. No schools found → neutral score
        if not nearby:
            result = SchoolScore(
                complex_code=complex_code,
                school_kind="total",
                nearby_school_count=0,
                avg_students_per_class=0.0,
                avg_students_per_teacher=0.0,
                score=50,
                collected_at=now,
            )
            self._repo.upsert_school_score(result)
            return result

        # 5. Collect teacher records — gather both per_teacher (display) and transfer_rate (scoring)
        all_per_teacher: list[float] = []
        all_transfer_rates: list[float] = []
        for school in nearby:
            teacher_records = self._repo.get_teacher_records(school.school_code)
            for trec in teacher_records:
                if trec.students_per_teacher > 0:
                    all_per_teacher.append(trec.students_per_teacher)
                if trec.transfer_in_rate > 0:
                    all_transfer_rates.append(trec.transfer_in_rate)

        avg_per_teacher = (
            round(sum(all_per_teacher) / len(all_per_teacher), 2) if all_per_teacher else 0.0
        )
        avg_transfer_rate = (
            round(sum(all_transfer_rates) / len(all_transfer_rates), 4) if all_transfer_rates else 0.0
        )

        # 6. Calculate composite score using transfer_rate as quality signal
        score = _calc_score(
            nearby_count=len(nearby),
            avg_transfer_rate=avg_transfer_rate,
            transfer_high=transfer_high,
            transfer_medium=transfer_medium,
            high_count=high_count,
            mid_count=mid_count,
            w_density=w_density,
            w_quality=w_quality,
            has_quality_data=bool(all_transfer_rates),
        )

        # 7. Persist and return
        result = SchoolScore(
            complex_code=complex_code,
            school_kind="total",
            nearby_school_count=len(nearby),
            avg_students_per_class=0.0,
            avg_students_per_teacher=avg_per_teacher,
            score=score,
            collected_at=now,
        )
        self._repo.upsert_school_score(result)
        return result

    def get_cached_score(
        self, complex_code: str, school_kind: str = "total"
    ) -> Optional[SchoolScore]:
        return self._repo.get_score(complex_code, school_kind)

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
          COL_{suffix}1/2     — 전입/전출 student counts (NOT class counts)

        class_count and students_per_class are not available from this API.
        Elementary (02): suffixes 21..26 (grade 1-6)
        Middle/High (03/04): suffixes 11..13 (grade 1-3)
        """
        school_code = raw.get("SCHUL_CODE", "")
        records: List[SchoolStudentRecord] = []

        all_suffixes = _ELEMENTARY_GRADE_SUFFIXES + _SECONDARY_GRADE_SUFFIXES

        for suffix in all_suffixes:
            stdnt_key = f"STDNT_SUM_{suffix}"
            if stdnt_key not in raw:
                continue

            student_count = _safe_int(raw.get(stdnt_key, 0))
            # use the full suffix as the opaque grade key (e.g. "21", "22", "11", "12")
            # avoids collision: suffix[-1] would map both "21" and "11" to "1"
            grade = suffix

            records.append(
                SchoolStudentRecord(
                    school_code=school_code,
                    year=year,
                    grade=grade,
                    class_count=0,           # not available via schoolinfo API
                    student_count=student_count,
                    students_per_class=0.0,  # not available via schoolinfo API
                    male_count=0,
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
        mvin_count: int,
        now: str,
    ) -> Optional[SchoolTeacherRecord]:
        """Parse SchoolTeacherRecord from apiType=17 response row.

        Real fields (from smoke test):
          COL_1         — total teacher headcount
          ML_TOI_FGR    — male teacher count
          FML_TOI_FGR   — female teacher count
        mvin_count comes from MVIN_SUM in the apiType=10 row (looked up by school_code).
        """
        school_code = raw.get("SCHUL_CODE", "")
        if not school_code:
            return None

        total_teachers = _safe_int(raw.get("COL_1", 0))
        if total_teachers == 0:
            total_teachers = (
                _safe_int(raw.get("ML_TOI_FGR", 0))
                + _safe_int(raw.get("FML_TOI_FGR", 0))
            )

        students_per_teacher = (
            round(total_students / total_teachers, 2) if total_teachers > 0 else 0.0
        )
        transfer_in_rate = (
            round(mvin_count / total_students, 4) if total_students > 0 else 0.0
        )

        return SchoolTeacherRecord(
            school_code=school_code,
            year=year,
            total_teachers=total_teachers,
            students_per_teacher=students_per_teacher,
            collected_at=now,
            transfer_in_rate=transfer_in_rate,
        )
