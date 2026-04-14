"""
TDD: Phase 2-A — AptMasterRepository 전체 검증
Red phase: 구현 전 실패 테스트 작성
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src')))

from modules.real_estate.models import AptMasterEntry, RealEstateTransaction
from modules.real_estate.apt_master_repository import AptMasterRepository
from modules.real_estate.apartment_repository import ApartmentRepository
from modules.real_estate.transaction_repository import TransactionRepository


# ── 픽스처 ────────────────────────────────────────────────────────────────────

@pytest.fixture
def repo(tmp_path):
    return AptMasterRepository(db_path=str(tmp_path / "test.db"))


def _make_entry(apt_name, district_code, sido="서울특별시", sigungu="강남구",
                complex_code=None, tx_count=0, first_traded=None, last_traded=None):
    return AptMasterEntry(
        apt_name=apt_name,
        district_code=district_code,
        sido=sido,
        sigungu=sigungu,
        complex_code=complex_code,
        tx_count=tx_count,
        first_traded=first_traded,
        last_traded=last_traded,
    )


@pytest.fixture
def populated_repo(repo):
    samples = [
        _make_entry("래미안퍼스티지", "11650", sigungu="서초구", tx_count=30,
                    complex_code="A0001", first_traded="2020-01-15", last_traded="2024-11-10"),
        _make_entry("힐스테이트서초", "11650", sigungu="서초구", tx_count=12,
                    first_traded="2021-03-01", last_traded="2024-08-22"),
        _make_entry("자이아파트", "11680", sigungu="강남구", tx_count=5,
                    sido="서울특별시"),
        _make_entry("아이파크", "11680", sigungu="강남구", tx_count=8,
                    complex_code="B0002"),
        _make_entry("e편한세상", "11710", sido="경기도", sigungu="성남시",
                    tx_count=20, complex_code="C0003",
                    first_traded="2019-06-01", last_traded="2024-12-01"),
    ]
    for e in samples:
        repo.upsert(e)
    return repo


@pytest.fixture
def shared_db_repos(tmp_path):
    """transactions + apt_master 가 같은 DB를 공유하는 픽스처."""
    db_path = str(tmp_path / "shared.db")
    apt_repo = ApartmentRepository(db_path=db_path)
    tx_repo = TransactionRepository(db_path=db_path)
    master_repo = AptMasterRepository(db_path=db_path)
    return apt_repo, tx_repo, master_repo


# ── 기본 CRUD ──────────────────────────────────────────────────────────────────

class TestAptMasterBasicCRUD:
    def test_upsert_saves_new_entry(self, repo):
        """신규 단지 upsert 후 count가 1 증가한다."""
        repo.upsert(_make_entry("래미안퍼스티지", "11650"))
        assert repo.count() == 1

    def test_upsert_duplicate_updates_existing(self, repo):
        """동일 (apt_name, district_code) 재 upsert 시 레코드가 늘지 않는다."""
        repo.upsert(_make_entry("래미안퍼스티지", "11650", tx_count=5))
        repo.upsert(_make_entry("래미안퍼스티지", "11650", tx_count=10))
        assert repo.count() == 1

    def test_upsert_updates_tx_count(self, repo):
        """동일 단지 재 upsert 시 tx_count가 갱신된다."""
        repo.upsert(_make_entry("래미안퍼스티지", "11650", tx_count=5))
        repo.upsert(_make_entry("래미안퍼스티지", "11650", tx_count=10))
        entry = repo.get_by_name_district("래미안퍼스티지", "11650")
        assert entry.tx_count == 10

    def test_upsert_preserves_complex_code_if_not_overwritten(self, repo):
        """complex_code None으로 upsert 해도 기존 complex_code가 보존된다."""
        repo.upsert(_make_entry("래미안퍼스티지", "11650", complex_code="A0001"))
        repo.upsert(_make_entry("래미안퍼스티지", "11650", complex_code=None))
        entry = repo.get_by_name_district("래미안퍼스티지", "11650")
        assert entry.complex_code == "A0001"

    def test_get_by_id_returns_entry(self, populated_repo):
        """ID로 단지 조회 시 올바른 AptMasterEntry 반환."""
        entry = populated_repo.get_by_name_district("래미안퍼스티지", "11650")
        assert entry is not None
        fetched = populated_repo.get_by_id(entry.id)
        assert fetched is not None
        assert fetched.apt_name == "래미안퍼스티지"

    def test_get_by_id_not_found_returns_none(self, repo):
        """존재하지 않는 ID 조회 시 None 반환."""
        assert repo.get_by_id(9999) is None

    def test_get_by_name_district_returns_entry(self, populated_repo):
        """(apt_name, district_code) 정확 조회."""
        entry = populated_repo.get_by_name_district("래미안퍼스티지", "11650")
        assert entry is not None
        assert entry.apt_name == "래미안퍼스티지"
        assert entry.district_code == "11650"

    def test_get_by_name_district_not_found_returns_none(self, repo):
        """존재하지 않는 단지 조회 시 None."""
        assert repo.get_by_name_district("없는아파트", "99999") is None

    def test_count_returns_correct_number(self, populated_repo):
        """count()가 저장된 단지 수와 일치한다."""
        assert populated_repo.count() == 5

    def test_upsert_returns_apt_master_entry_type(self, repo):
        """get_by_id 반환 타입이 AptMasterEntry 이어야 한다."""
        repo.upsert(_make_entry("래미안퍼스티지", "11650"))
        entry = repo.get_by_name_district("래미안퍼스티지", "11650")
        assert isinstance(entry, AptMasterEntry)

    def test_upsert_assigns_autoincrement_id(self, repo):
        """저장된 AptMasterEntry는 None이 아닌 id를 갖는다."""
        repo.upsert(_make_entry("래미안퍼스티지", "11650"))
        entry = repo.get_by_name_district("래미안퍼스티지", "11650")
        assert entry.id is not None
        assert entry.id > 0


# ── 검색 ──────────────────────────────────────────────────────────────────────

class TestAptMasterSearch:
    def test_search_no_filter_returns_all(self, populated_repo):
        """필터 없이 호출 시 모든 레코드 반환."""
        results = populated_repo.search()
        assert len(results) == 5

    def test_search_by_apt_name_partial(self, populated_repo):
        """apt_name 부분일치 검색."""
        results = populated_repo.search(apt_name="래미안")
        assert len(results) == 1
        assert results[0].apt_name == "래미안퍼스티지"

    def test_search_by_sido(self, populated_repo):
        """시도 필터."""
        results = populated_repo.search(sido="경기도")
        assert len(results) == 1
        assert results[0].apt_name == "e편한세상"

    def test_search_by_sigungu(self, populated_repo):
        """시군구 필터."""
        results = populated_repo.search(sigungu="서초구")
        assert len(results) == 2
        names = {r.apt_name for r in results}
        assert "래미안퍼스티지" in names
        assert "힐스테이트서초" in names

    def test_search_combined_filters(self, populated_repo):
        """sido + sigungu 복합 필터."""
        results = populated_repo.search(sido="서울특별시", sigungu="강남구")
        assert len(results) == 2

    def test_search_no_match_returns_empty(self, populated_repo):
        """매칭 없으면 빈 리스트."""
        results = populated_repo.search(apt_name="존재하지않는단지")
        assert results == []

    def test_search_respects_limit(self, tmp_path):
        """limit 파라미터가 반환 건수를 제한한다."""
        repo = AptMasterRepository(db_path=str(tmp_path / "big.db"))
        for i in range(20):
            repo.upsert(_make_entry(f"아파트{i:04d}", f"{10000 + i}"))
        results = repo.search(limit=5)
        assert len(results) == 5

    def test_search_returns_apt_master_entry_type(self, populated_repo):
        """search() 결과가 AptMasterEntry 리스트여야 한다."""
        results = populated_repo.search(apt_name="래미안")
        assert all(isinstance(r, AptMasterEntry) for r in results)


# ── 필터 옵션 ─────────────────────────────────────────────────────────────────

class TestAptMasterDistinct:
    def test_get_distinct_sidos(self, populated_repo):
        """시도 목록 조회."""
        sidos = populated_repo.get_distinct_sidos()
        assert "서울특별시" in sidos
        assert "경기도" in sidos
        assert len(sidos) == len(set(sidos))  # 중복 없음

    def test_get_distinct_sigungus_all(self, populated_repo):
        """전체 시군구 목록 조회."""
        sigungus = populated_repo.get_distinct_sigungus()
        assert "서초구" in sigungus
        assert "강남구" in sigungus
        assert len(sigungus) == len(set(sigungus))

    def test_get_distinct_sigungus_filtered_by_sido(self, populated_repo):
        """시도 지정 시 해당 시도의 시군구만 반환."""
        sigungus = populated_repo.get_distinct_sigungus(sido="서울특별시")
        assert "서초구" in sigungus
        assert "강남구" in sigungus
        # 경기도 성남시는 포함되지 않음
        assert "성남시" not in sigungus


# ── transactions에서 빌드 ───────────────────────────────────────────────────────

class TestBuildFromTransactions:
    def _make_tx(self, apt_name, district_code, deal_date, price=100_000_000,
                 complex_code=None):
        return RealEstateTransaction(
            apt_name=apt_name,
            district_code=district_code,
            deal_date=deal_date,
            price=price,
            floor=5,
            exclusive_area=84.0,
            build_year=2010,
            complex_code=complex_code,
        )

    def test_build_creates_entries_for_unique_apt_district_pairs(self, shared_db_repos):
        """transactions의 (apt_name, district_code) 조합마다 apt_master 1건이 생성된다."""
        _, tx_repo, master_repo = shared_db_repos
        tx_repo.save_batch([
            self._make_tx("래미안퍼스티지", "11650", "2024-01-01"),
            self._make_tx("래미안퍼스티지", "11650", "2024-02-01"),  # 동일 단지 2건
            self._make_tx("힐스테이트", "11650", "2024-03-01"),
            self._make_tx("자이아파트", "11680", "2024-04-01"),
        ])
        count = master_repo.build_from_transactions()
        assert count == 3  # 3개 유니크 단지
        assert master_repo.count() == 3

    def test_build_counts_transactions_correctly(self, shared_db_repos):
        """apt_master.tx_count가 transactions 건수와 일치한다."""
        _, tx_repo, master_repo = shared_db_repos
        tx_repo.save_batch([
            self._make_tx("래미안퍼스티지", "11650", "2024-01-01"),
            self._make_tx("래미안퍼스티지", "11650", "2024-02-01"),
            self._make_tx("래미안퍼스티지", "11650", "2024-03-01"),
        ])
        master_repo.build_from_transactions()
        entry = master_repo.get_by_name_district("래미안퍼스티지", "11650")
        assert entry.tx_count == 3

    def test_build_sets_first_and_last_traded(self, shared_db_repos):
        """first_traded / last_traded가 올바르게 집계된다."""
        _, tx_repo, master_repo = shared_db_repos
        tx_repo.save_batch([
            self._make_tx("래미안퍼스티지", "11650", "2022-06-01"),
            self._make_tx("래미안퍼스티지", "11650", "2024-11-15"),
            self._make_tx("래미안퍼스티지", "11650", "2020-01-10"),
        ])
        master_repo.build_from_transactions()
        entry = master_repo.get_by_name_district("래미안퍼스티지", "11650")
        assert entry.first_traded == "2020-01-10"
        assert entry.last_traded == "2024-11-15"

    def test_build_fills_complex_code_from_transactions(self, shared_db_repos):
        """transactions의 complex_code가 apt_master.complex_code로 채워진다."""
        _, tx_repo, master_repo = shared_db_repos
        tx_repo.save_batch([
            self._make_tx("래미안퍼스티지", "11650", "2024-01-01", complex_code="A0001"),
            self._make_tx("래미안퍼스티지", "11650", "2024-02-01", complex_code="A0001"),
        ])
        master_repo.build_from_transactions()
        entry = master_repo.get_by_name_district("래미안퍼스티지", "11650")
        assert entry.complex_code == "A0001"

    def test_build_handles_no_complex_code(self, shared_db_repos):
        """complex_code가 없는 거래도 apt_master에 생성된다."""
        _, tx_repo, master_repo = shared_db_repos
        tx_repo.save_batch([
            self._make_tx("미매핑단지", "11650", "2024-01-01", complex_code=None),
        ])
        master_repo.build_from_transactions()
        entry = master_repo.get_by_name_district("미매핑단지", "11650")
        assert entry is not None
        assert entry.complex_code is None

    def test_build_is_idempotent(self, shared_db_repos):
        """build_from_transactions()를 두 번 호출해도 중복 없이 안전하다."""
        _, tx_repo, master_repo = shared_db_repos
        tx_repo.save_batch([
            self._make_tx("래미안퍼스티지", "11650", "2024-01-01"),
            self._make_tx("힐스테이트", "11650", "2024-02-01"),
        ])
        master_repo.build_from_transactions()
        master_repo.build_from_transactions()
        assert master_repo.count() == 2  # 중복 삽입 없음


# ── 신규 거래 동기화 ─────────────────────────────────────────────────────────────

class TestSyncFromNewTransactions:
    def _make_tx(self, apt_name, district_code, deal_date, price=100_000_000,
                 complex_code=None):
        return RealEstateTransaction(
            apt_name=apt_name,
            district_code=district_code,
            deal_date=deal_date,
            price=price,
            floor=5,
            exclusive_area=84.0,
            build_year=2010,
            complex_code=complex_code,
        )

    def test_sync_inserts_new_entries(self, shared_db_repos):
        """신규 거래 목록 sync → apt_master에 신규 단지 INSERT."""
        _, tx_repo, master_repo = shared_db_repos
        txs = [
            self._make_tx("래미안퍼스티지", "11650", "2024-01-15"),
            self._make_tx("힐스테이트", "11650", "2024-01-20"),
        ]
        tx_repo.save_batch(txs)
        count = master_repo.sync_from_new_transactions(txs)
        assert count == 2
        assert master_repo.count() == 2

    def test_sync_updates_existing_entry_stats(self, shared_db_repos):
        """기존 단지에 신규 거래 sync → tx_count / last_traded 갱신, count 0."""
        _, tx_repo, master_repo = shared_db_repos
        initial = [self._make_tx("래미안퍼스티지", "11650", "2024-01-01")]
        tx_repo.save_batch(initial)
        master_repo.sync_from_new_transactions(initial)

        new_txs = [
            self._make_tx("래미안퍼스티지", "11650", "2024-02-01"),
            self._make_tx("래미안퍼스티지", "11650", "2024-03-01"),
        ]
        tx_repo.save_batch(new_txs)
        count = master_repo.sync_from_new_transactions(new_txs)

        assert count == 0  # 신규 삽입 없음
        entry = master_repo.get_by_name_district("래미안퍼스티지", "11650")
        assert entry.tx_count == 3  # 합계 갱신
        assert entry.last_traded == "2024-03-01"

    def test_sync_empty_list_returns_zero(self, shared_db_repos):
        """빈 리스트 sync → 0 반환, apt_master 변화 없음."""
        _, tx_repo, master_repo = shared_db_repos
        count = master_repo.sync_from_new_transactions([])
        assert count == 0
        assert master_repo.count() == 0

    def test_sync_mixed_new_and_existing(self, shared_db_repos):
        """기존 1 + 신규 1 혼합 sync → 신규 1건만 반환."""
        _, tx_repo, master_repo = shared_db_repos
        initial = [self._make_tx("래미안퍼스티지", "11650", "2024-01-01")]
        tx_repo.save_batch(initial)
        master_repo.sync_from_new_transactions(initial)

        mixed = [
            self._make_tx("래미안퍼스티지", "11650", "2024-02-01"),
            self._make_tx("힐스테이트", "11680", "2024-02-15"),
        ]
        tx_repo.save_batch(mixed)
        count = master_repo.sync_from_new_transactions(mixed)

        assert count == 1  # 힐스테이트만 신규
        assert master_repo.count() == 2

    def test_sync_preserves_existing_complex_code(self, shared_db_repos):
        """complex_code 있는 단지에 NULL complex_code 거래 sync → complex_code 보존."""
        _, tx_repo, master_repo = shared_db_repos
        initial = [self._make_tx("래미안퍼스티지", "11650", "2024-01-01", complex_code="A0001")]
        tx_repo.save_batch(initial)
        master_repo.sync_from_new_transactions(initial)

        new_txs = [self._make_tx("래미안퍼스티지", "11650", "2024-02-01", complex_code=None)]
        tx_repo.save_batch(new_txs)
        master_repo.sync_from_new_transactions(new_txs)

        entry = master_repo.get_by_name_district("래미안퍼스티지", "11650")
        assert entry.complex_code == "A0001"  # 보존

    def test_sync_sets_complex_code_from_new_tx(self, shared_db_repos):
        """complex_code 없던 단지에 complex_code 있는 거래 sync → complex_code 갱신."""
        _, tx_repo, master_repo = shared_db_repos
        initial = [self._make_tx("래미안퍼스티지", "11650", "2024-01-01", complex_code=None)]
        tx_repo.save_batch(initial)
        master_repo.sync_from_new_transactions(initial)

        new_txs = [self._make_tx("래미안퍼스티지", "11650", "2024-02-01", complex_code="A0001")]
        tx_repo.save_batch(new_txs)
        master_repo.sync_from_new_transactions(new_txs)

        entry = master_repo.get_by_name_district("래미안퍼스티지", "11650")
        assert entry.complex_code == "A0001"

    def test_sync_normalizes_apt_name(self, shared_db_repos):
        """공백/괄호 있는 아파트명도 정규화 후 올바르게 동기화된다."""
        _, tx_repo, master_repo = shared_db_repos
        txs = [self._make_tx("래미안 퍼스티지", "11650", "2024-01-01")]
        tx_repo.save_batch(txs)
        count = master_repo.sync_from_new_transactions(txs)
        assert count == 1
        # save_batch가 정규화하므로 정규화된 이름으로 조회
        entry = master_repo.get_by_name_district("래미안퍼스티지", "11650")
        assert entry is not None


# ── refresh_stats ─────────────────────────────────────────────────────────────

class TestRefreshStats:
    def _make_tx(self, apt_name, district_code, deal_date, price=100_000_000):
        return RealEstateTransaction(
            apt_name=apt_name,
            district_code=district_code,
            deal_date=deal_date,
            price=price,
            floor=5,
            exclusive_area=84.0,
            build_year=2010,
        )

    def test_refresh_stats_updates_tx_count(self, shared_db_repos):
        """transactions 추가 후 refresh_stats()가 tx_count를 재계산한다."""
        _, tx_repo, master_repo = shared_db_repos
        # 초기 빌드
        tx_repo.save_batch([
            self._make_tx("래미안퍼스티지", "11650", "2024-01-01"),
        ])
        master_repo.build_from_transactions()

        # 추가 거래 삽입
        tx_repo.save_batch([
            self._make_tx("래미안퍼스티지", "11650", "2024-02-01"),
            self._make_tx("래미안퍼스티지", "11650", "2024-03-01"),
        ])
        master_repo.refresh_stats()

        entry = master_repo.get_by_name_district("래미안퍼스티지", "11650")
        assert entry.tx_count == 3
        assert entry.last_traded == "2024-03-01"
