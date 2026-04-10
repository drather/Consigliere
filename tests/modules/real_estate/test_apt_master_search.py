"""
TDD: 1-B — ApartmentMasterRepository.search() 메서드 검증
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src')))

from modules.real_estate.models import ApartmentMaster
from modules.real_estate.apartment_master.repository import ApartmentMasterRepository


@pytest.fixture
def repo(tmp_path):
    return ApartmentMasterRepository(db_path=str(tmp_path / "test.db"))


def _make_master(apt_name, district_code, household_count, constructor, approved_date, complex_code="X"):
    return ApartmentMaster(
        apt_name=apt_name,
        district_code=district_code,
        complex_code=complex_code,
        household_count=household_count,
        building_count=10,
        parking_count=0,
        constructor=constructor,
        approved_date=approved_date,
    )


@pytest.fixture
def populated_repo(repo):
    samples = [
        _make_master("래미안퍼스티지", "11650", 2444, "삼성물산", "20090101"),
        _make_master("힐스테이트", "11650", 800, "현대건설", "20151201"),
        _make_master("자이아파트", "11680", 350, "GS건설", "20031001"),
        _make_master("아이파크", "11680", 150, "HDC현대산업개발", "20001215"),
        _make_master("e편한세상", "11710", 1200, "DL이앤씨", "20180601"),
    ]
    for m in samples:
        repo.save(m)
    return repo


class TestApartmentMasterSearch:
    def test_search_all_returns_all_records(self, populated_repo):
        """필터 없이 호출 시 모든 레코드 반환."""
        results = populated_repo.search()
        assert len(results) == 5

    def test_search_by_apt_name_partial(self, populated_repo):
        """apt_name 부분일치 검색."""
        results = populated_repo.search(apt_name="래미안")
        assert len(results) == 1
        assert results[0].apt_name == "래미안퍼스티지"

    def test_search_by_district_code(self, populated_repo):
        """지구코드 필터."""
        results = populated_repo.search(district_code="11650")
        assert len(results) == 2
        names = {r.apt_name for r in results}
        assert "래미안퍼스티지" in names
        assert "힐스테이트" in names

    def test_search_by_min_household(self, populated_repo):
        """최소 세대수 필터."""
        results = populated_repo.search(min_household=500)
        assert all(r.household_count >= 500 for r in results)
        assert len(results) == 3

    def test_search_by_max_household(self, populated_repo):
        """최대 세대수 필터."""
        results = populated_repo.search(max_household=400)
        assert all(r.household_count <= 400 for r in results)
        assert len(results) == 2

    def test_search_by_constructor(self, populated_repo):
        """건설사 필터."""
        results = populated_repo.search(constructor="삼성물산")
        assert len(results) == 1
        assert results[0].constructor == "삼성물산"

    def test_search_by_constructor_partial(self, populated_repo):
        """건설사 부분일치."""
        results = populated_repo.search(constructor="현대")
        assert len(results) == 2  # 현대건설, HDC현대산업개발

    def test_search_by_approved_year_range(self, populated_repo):
        """준공연도 범위 필터."""
        results = populated_repo.search(approved_year_start=2010, approved_year_end=2020)
        assert all(2010 <= int(r.approved_date[:4]) <= 2020 for r in results)
        assert len(results) == 2  # 힐스테이트(2015), e편한세상(2018)

    def test_search_combined_filters(self, populated_repo):
        """복합 필터 — district + min_household."""
        results = populated_repo.search(district_code="11650", min_household=1000)
        assert len(results) == 1
        assert results[0].apt_name == "래미안퍼스티지"

    def test_search_no_match_returns_empty(self, populated_repo):
        """매칭 없으면 빈 리스트."""
        results = populated_repo.search(apt_name="존재하지않는아파트")
        assert results == []

    def test_search_limit_500(self, tmp_path):
        """결과 500건 제한 동작."""
        repo = ApartmentMasterRepository(db_path=str(tmp_path / "big.db"))
        for i in range(600):
            repo.save(_make_master(f"아파트{i:04d}", "11680", i * 2, "건설사A", "20100101", complex_code=f"C{i}"))
        results = repo.search()
        assert len(results) <= 500

    def test_search_returns_apartment_master_objects(self, populated_repo):
        """반환 타입이 ApartmentMaster 객체여야 한다."""
        results = populated_repo.search(apt_name="래미안")
        assert isinstance(results[0], ApartmentMaster)

    def test_search_empty_string_filters_ignored(self, populated_repo):
        """빈 문자열 필터는 무시된다."""
        results = populated_repo.search(apt_name="", constructor="", district_code="")
        assert len(results) == 5

    def test_get_distinct_constructors(self, populated_repo):
        """건설사 목록 조회 (드롭다운용)."""
        constructors = populated_repo.get_distinct_constructors()
        assert isinstance(constructors, list)
        assert "삼성물산" in constructors
        assert "현대건설" in constructors
        assert len(constructors) == len(set(constructors))  # 중복 없음
