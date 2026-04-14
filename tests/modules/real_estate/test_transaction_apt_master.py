"""
TDD: Phase 2-A — TransactionRepository apt_master_id FK 지원 검증
Red phase: get_by_apt_master_id() / fill_apt_master_ids() 구현 전 실패 테스트
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src')))

from modules.real_estate.models import RealEstateTransaction, AptMasterEntry
from modules.real_estate.transaction_repository import TransactionRepository
from modules.real_estate.apt_master_repository import AptMasterRepository


# ── 픽스처 ────────────────────────────────────────────────────────────────────

@pytest.fixture
def shared_repos(tmp_path):
    db_path = str(tmp_path / "shared.db")
    tx_repo = TransactionRepository(db_path=db_path)
    master_repo = AptMasterRepository(db_path=db_path)
    return tx_repo, master_repo


def _make_tx(apt_name, district_code, deal_date, price=100_000_000,
             complex_code=None, floor=5, apt_master_id=None):
    return RealEstateTransaction(
        apt_name=apt_name,
        district_code=district_code,
        deal_date=deal_date,
        price=price,
        floor=floor,
        exclusive_area=84.0,
        build_year=2010,
        complex_code=complex_code,
        apt_master_id=apt_master_id,
    )


def _make_entry(apt_name, district_code, tx_count=0):
    return AptMasterEntry(
        apt_name=apt_name,
        district_code=district_code,
        sido="서울특별시",
        sigungu="강남구",
        tx_count=tx_count,
    )


# ── get_by_apt_master_id ─────────────────────────────────────────────────────

class TestGetByAptMasterId:
    def test_get_by_apt_master_id_returns_correct_transactions(self, shared_repos):
        """apt_master_id로 조회 시 해당 단지의 거래만 반환된다."""
        tx_repo, master_repo = shared_repos

        # 단지 등록 및 거래 저장
        master_repo.upsert(_make_entry("래미안퍼스티지", "11650"))
        master_repo.upsert(_make_entry("힐스테이트", "11650"))
        entry_a = master_repo.get_by_name_district("래미안퍼스티지", "11650")
        entry_b = master_repo.get_by_name_district("힐스테이트", "11650")

        tx_repo.save_batch([
            _make_tx("래미안퍼스티지", "11650", "2024-01-01", apt_master_id=entry_a.id),
            _make_tx("래미안퍼스티지", "11650", "2024-02-01", apt_master_id=entry_a.id),
            _make_tx("힐스테이트", "11650", "2024-01-15", apt_master_id=entry_b.id),
        ])

        txs = tx_repo.get_by_apt_master_id(entry_a.id)
        assert len(txs) == 2
        assert all(t.apt_name == "래미안퍼스티지" for t in txs)

    def test_get_by_apt_master_id_with_limit(self, shared_repos):
        """limit 파라미터가 반환 건수를 제한한다."""
        tx_repo, master_repo = shared_repos
        master_repo.upsert(_make_entry("래미안퍼스티지", "11650"))
        entry = master_repo.get_by_name_district("래미안퍼스티지", "11650")

        txs_data = [
            _make_tx("래미안퍼스티지", "11650", f"2024-{i:02d}-01",
                     apt_master_id=entry.id, floor=i)
            for i in range(1, 11)
        ]
        tx_repo.save_batch(txs_data)

        txs = tx_repo.get_by_apt_master_id(entry.id, limit=3)
        assert len(txs) == 3

    def test_get_by_apt_master_id_with_date_range(self, shared_repos):
        """date_from / date_to 필터가 적용된다."""
        tx_repo, master_repo = shared_repos
        master_repo.upsert(_make_entry("래미안퍼스티지", "11650"))
        entry = master_repo.get_by_name_district("래미안퍼스티지", "11650")

        tx_repo.save_batch([
            _make_tx("래미안퍼스티지", "11650", "2023-06-01", apt_master_id=entry.id, floor=1),
            _make_tx("래미안퍼스티지", "11650", "2024-03-15", apt_master_id=entry.id, floor=2),
            _make_tx("래미안퍼스티지", "11650", "2024-11-01", apt_master_id=entry.id, floor=3),
        ])

        txs = tx_repo.get_by_apt_master_id(
            entry.id, date_from="2024-01-01", date_to="2024-12-31"
        )
        assert len(txs) == 2
        assert all("2024" in t.deal_date for t in txs)

    def test_get_by_apt_master_id_not_found_returns_empty(self, shared_repos):
        """존재하지 않는 apt_master_id 조회 시 빈 리스트 반환."""
        tx_repo, _ = shared_repos
        txs = tx_repo.get_by_apt_master_id(9999)
        assert txs == []

    def test_get_by_apt_master_id_returns_descending_order(self, shared_repos):
        """결과가 deal_date 내림차순으로 정렬된다."""
        tx_repo, master_repo = shared_repos
        master_repo.upsert(_make_entry("래미안퍼스티지", "11650"))
        entry = master_repo.get_by_name_district("래미안퍼스티지", "11650")

        tx_repo.save_batch([
            _make_tx("래미안퍼스티지", "11650", "2024-01-01", apt_master_id=entry.id, floor=1),
            _make_tx("래미안퍼스티지", "11650", "2024-06-15", apt_master_id=entry.id, floor=2),
            _make_tx("래미안퍼스티지", "11650", "2023-12-01", apt_master_id=entry.id, floor=3),
        ])

        txs = tx_repo.get_by_apt_master_id(entry.id)
        dates = [t.deal_date for t in txs]
        assert dates == sorted(dates, reverse=True)


# ── fill_apt_master_ids ───────────────────────────────────────────────────────

class TestFillAptMasterIds:
    def test_fill_apt_master_ids_populates_all(self, shared_repos):
        """fill_apt_master_ids()가 모든 거래의 apt_master_id를 채운다."""
        tx_repo, master_repo = shared_repos

        # apt_master에 단지 등록
        master_repo.upsert(_make_entry("래미안퍼스티지", "11650"))
        master_repo.upsert(_make_entry("힐스테이트", "11650"))

        # apt_master_id 없이 거래 저장 (구버전 호환)
        tx_repo.save_batch([
            _make_tx("래미안퍼스티지", "11650", "2024-01-01"),
            _make_tx("래미안퍼스티지", "11650", "2024-02-01"),
            _make_tx("힐스테이트", "11650", "2024-01-15"),
        ])

        filled = tx_repo.fill_apt_master_ids(master_repo)
        assert filled == 3

    def test_fill_apt_master_ids_returns_zero_if_already_filled(self, shared_repos):
        """이미 apt_master_id가 채워진 경우 0을 반환한다."""
        tx_repo, master_repo = shared_repos
        master_repo.upsert(_make_entry("래미안퍼스티지", "11650"))
        entry = master_repo.get_by_name_district("래미안퍼스티지", "11650")

        tx_repo.save_batch([
            _make_tx("래미안퍼스티지", "11650", "2024-01-01", apt_master_id=entry.id),
        ])

        filled = tx_repo.fill_apt_master_ids(master_repo)
        assert filled == 0
