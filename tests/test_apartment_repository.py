"""
ApartmentRepository (real_estate.db / apartments 테이블) 단위 테스트.
in-memory SQLite 사용 → 파일 의존성 없음.
"""
import pytest
from datetime import datetime

try:
    from modules.real_estate.apartment_repository import ApartmentRepository
    from modules.real_estate.models import ApartmentMaster
except ImportError:
    from src.modules.real_estate.apartment_repository import ApartmentRepository
    from src.modules.real_estate.models import ApartmentMaster


def _make_master(complex_code="K001", apt_name="래미안", district_code="11680",
                 sido="서울특별시", sigungu="강남구") -> ApartmentMaster:
    return ApartmentMaster(
        complex_code=complex_code,
        apt_name=apt_name,
        district_code=district_code,
        household_count=500,
        building_count=10,
        parking_count=0,
        constructor="삼성물산",
        approved_date="20100101",
        sido=sido,
        sigungu=sigungu,
        road_address="서울 강남구 테헤란로 123",
    )


@pytest.fixture
def repo():
    """in-memory DB repo."""
    return ApartmentRepository(db_path=":memory:")


class TestApartmentRepository:
    def test_save_and_get_by_complex_code(self, repo):
        m = _make_master()
        repo.save(m)
        result = repo.get(complex_code="K001")
        assert result is not None
        assert result.apt_name == "래미안"
        assert result.district_code == "11680"

    def test_get_returns_none_for_missing(self, repo):
        assert repo.get(complex_code="NOTEXIST") is None

    def test_save_upserts_on_duplicate(self, repo):
        m = _make_master()
        m.household_count = 500
        repo.save(m)
        m2 = _make_master()
        m2.household_count = 999
        repo.save(m2)
        result = repo.get("K001")
        assert result.household_count == 999

    def test_search_by_apt_name(self, repo):
        repo.save(_make_master(complex_code="A1", apt_name="래미안강남"))
        repo.save(_make_master(complex_code="A2", apt_name="힐스테이트"))
        results = repo.search(apt_name="래미안")
        names = [r.apt_name for r in results]
        assert "래미안강남" in names
        assert "힐스테이트" not in names

    def test_search_by_sido_sigungu(self, repo):
        repo.save(_make_master(complex_code="B1", sido="서울특별시", sigungu="강남구"))
        repo.save(_make_master(complex_code="B2", sido="경기도", sigungu="분당구"))
        results = repo.search(sido="서울특별시", sigungu="강남구")
        assert all(r.sigungu == "강남구" for r in results)
        assert len(results) == 1

    def test_get_distinct_sidos(self, repo):
        repo.save(_make_master(complex_code="C1", sido="서울특별시"))
        repo.save(_make_master(complex_code="C2", sido="경기도"))
        sidos = repo.get_distinct_sidos()
        assert "서울특별시" in sidos
        assert "경기도" in sidos

    def test_get_distinct_sigungus_filtered_by_sido(self, repo):
        repo.save(_make_master(complex_code="D1", sido="서울특별시", sigungu="강남구"))
        repo.save(_make_master(complex_code="D2", sido="서울특별시", sigungu="서초구"))
        repo.save(_make_master(complex_code="D3", sido="경기도", sigungu="분당구"))
        sigungus = repo.get_distinct_sigungus(sido="서울특별시")
        assert "강남구" in sigungus
        assert "서초구" in sigungus
        assert "분당구" not in sigungus

    def test_get_distinct_constructors(self, repo):
        repo.save(_make_master(complex_code="E1", apt_name="A"))
        m2 = _make_master(complex_code="E2", apt_name="B")
        m2.constructor = "현대건설"
        repo.save(m2)
        constructors = repo.get_distinct_constructors()
        assert "삼성물산" in constructors
        assert "현대건설" in constructors

    def test_count(self, repo):
        assert repo.count() == 0
        repo.save(_make_master(complex_code="F1"))
        repo.save(_make_master(complex_code="F2"))
        assert repo.count() == 2

    def test_search_household_range(self, repo):
        m_small = _make_master(complex_code="G1", apt_name="소형")
        m_small.household_count = 100
        m_large = _make_master(complex_code="G2", apt_name="대형")
        m_large.household_count = 1000
        repo.save(m_small)
        repo.save(m_large)
        results = repo.search(min_household=500)
        assert any(r.apt_name == "대형" for r in results)
        assert not any(r.apt_name == "소형" for r in results)
