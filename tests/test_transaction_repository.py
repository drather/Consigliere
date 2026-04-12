"""
TransactionRepository (real_estate.db / transactions 테이블) 단위 테스트.
in-memory SQLite 사용.
"""
import pytest
from datetime import date, timedelta

try:
    from modules.real_estate.apartment_repository import ApartmentRepository
    from modules.real_estate.transaction_repository import TransactionRepository
    from modules.real_estate.models import ApartmentMaster, RealEstateTransaction
except ImportError:
    from src.modules.real_estate.apartment_repository import ApartmentRepository
    from src.modules.real_estate.transaction_repository import TransactionRepository
    from src.modules.real_estate.models import ApartmentMaster, RealEstateTransaction


def _apt(complex_code="K001", apt_name="래미안", district_code="11680") -> ApartmentMaster:
    return ApartmentMaster(
        complex_code=complex_code, apt_name=apt_name, district_code=district_code,
        household_count=300, building_count=5, parking_count=0,
        constructor="삼성물산", approved_date="20100101",
        sido="서울특별시", sigungu="강남구",
    )


def _tx(apt_name="래미안", district_code="11680",
        deal_date="2026-03-15", price=1_500_000_000,
        complex_code=None) -> RealEstateTransaction:
    return RealEstateTransaction(
        apt_name=apt_name,
        district_code=district_code,
        deal_date=deal_date,
        price=price,
        floor=10,
        exclusive_area=84.97,
        build_year=2010,
        road_name="테헤란로",
        complex_code=complex_code,
    )


@pytest.fixture
def repos():
    apt_repo = ApartmentRepository(db_path=":memory:")
    tx_repo = TransactionRepository(db_path=":memory:")
    return apt_repo, tx_repo


class TestTransactionRepository:
    def test_save_and_get_by_complex_code(self, repos):
        apt_repo, tx_repo = repos
        apt_repo.save(_apt("K001", "래미안"))
        tx = _tx(apt_name="래미안", district_code="11680", complex_code="K001")
        tx_repo.save(tx)
        results = tx_repo.get_by_complex("K001")
        assert len(results) == 1
        assert results[0].apt_name == "래미안"

    def test_get_by_district(self, repos):
        _, tx_repo = repos
        tx_repo.save(_tx(district_code="11680", deal_date="2026-03-01"))
        tx_repo.save(_tx(district_code="11680", deal_date="2026-03-10"))
        tx_repo.save(_tx(district_code="11350", deal_date="2026-03-05"))
        results = tx_repo.get_by_district("11680")
        assert len(results) == 2
        assert all(r.district_code == "11680" for r in results)

    def test_get_by_district_ordered_by_date_desc(self, repos):
        _, tx_repo = repos
        tx_repo.save(_tx(deal_date="2026-01-01"))
        tx_repo.save(_tx(deal_date="2026-03-01"))
        tx_repo.save(_tx(deal_date="2026-02-01"))
        results = tx_repo.get_by_district("11680")
        dates = [r.deal_date for r in results]
        assert dates == sorted(dates, reverse=True)

    def test_get_by_district_limit(self, repos):
        _, tx_repo = repos
        for i in range(10):
            tx_repo.save(_tx(deal_date=f"2026-03-{i+1:02d}"))
        results = tx_repo.get_by_district("11680", limit=3)
        assert len(results) == 3

    def test_delete_before_cutoff(self, repos):
        _, tx_repo = repos
        tx_repo.save(_tx(deal_date="2024-01-01"))  # old
        tx_repo.save(_tx(deal_date="2026-03-01"))  # recent
        cutoff = date(2025, 1, 1)
        deleted = tx_repo.delete_before(cutoff)
        assert deleted == 1
        remaining = tx_repo.get_by_district("11680")
        assert all(r.deal_date >= "2025-01-01" for r in remaining)

    def test_save_batch_dedup(self, repos):
        _, tx_repo = repos
        txs = [
            _tx(deal_date="2026-03-01", price=1_000_000_000),
            _tx(deal_date="2026-03-01", price=1_000_000_000),  # 중복
        ]
        saved = tx_repo.save_batch(txs)
        assert saved == 1  # 중복 제거

    def test_save_batch_returns_count(self, repos):
        _, tx_repo = repos
        txs = [
            _tx(deal_date="2026-03-01"),
            _tx(deal_date="2026-03-02"),
            _tx(deal_date="2026-03-03"),
        ]
        saved = tx_repo.save_batch(txs)
        assert saved == 3

    def test_resolve_complex_codes_fuzzy_match(self, repos):
        apt_repo, tx_repo = repos
        # master: "중계무지개아파트", transaction: "중계무지개" (이름 불일치)
        apt_repo.save(_apt("K999", "중계무지개아파트", "11350"))
        tx = _tx(apt_name="중계무지개", district_code="11350", complex_code=None)
        tx_repo.save(tx)
        resolved = tx_repo.resolve_complex_codes(apt_repo)
        assert resolved >= 1
        results = tx_repo.get_by_complex("K999")
        assert len(results) == 1

    def test_resolve_complex_codes_no_match_stays_null(self, repos):
        apt_repo, tx_repo = repos
        tx = _tx(apt_name="존재하지않는단지", district_code="11680", complex_code=None)
        tx_repo.save(tx)
        tx_repo.resolve_complex_codes(apt_repo)
        # complex_code가 없는 거래는 그대로 보존
        all_txs = tx_repo.get_by_district("11680")
        assert len(all_txs) == 1

    def test_get_by_complex_ordered_desc(self, repos):
        _, tx_repo = repos
        tx_repo.save(_tx(deal_date="2026-01-01", complex_code="K001"))
        tx_repo.save(_tx(deal_date="2026-03-01", complex_code="K001"))
        results = tx_repo.get_by_complex("K001")
        assert results[0].deal_date >= results[-1].deal_date
