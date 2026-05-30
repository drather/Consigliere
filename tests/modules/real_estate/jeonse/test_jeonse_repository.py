# tests/modules/real_estate/jeonse/test_jeonse_repository.py
import sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

from modules.real_estate.jeonse.repository import JeonseRepository
from modules.real_estate.jeonse.models import JeonseTransaction


def _make_repo():
    tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    return JeonseRepository(db_path=tf.name)


def _tx(**kwargs):
    defaults = dict(
        complex_code="CC001", apt_name="래미안퍼스티지", district_code="11650",
        deal_date="2026-04-15", exclusive_area=84.0, deposit=58000,
        monthly_rent=0, contract_type="jeonse", floor=10
    )
    defaults.update(kwargs)
    return JeonseTransaction(**defaults)


def test_save_and_get_by_complex_code():
    repo = _make_repo()
    repo.save(_tx())
    results = repo.get_recent(complex_code="CC001", area=84.0, months=6)
    assert len(results) == 1
    assert results[0].deposit == 58000


def test_get_fallback_by_name_when_no_complex_code():
    repo = _make_repo()
    repo.save(_tx(complex_code=None))
    results = repo.get_recent(
        complex_code=None, apt_name="래미안퍼스티지",
        district_code="11650", area=84.0, months=6
    )
    assert len(results) == 1


def test_area_filter_excludes_different_size():
    repo = _make_repo()
    repo.save(_tx(exclusive_area=59.0))
    results = repo.get_recent(complex_code="CC001", area=84.0, months=6)
    assert len(results) == 0  # ±5㎡ 밖이면 제외


def test_dedup_ignores_duplicate():
    repo = _make_repo()
    tx = _tx()
    repo.save(tx)
    repo.save(tx)  # 동일 레코드 두 번 저장
    results = repo.get_recent(complex_code="CC001", area=84.0, months=6)
    assert len(results) == 1


def test_monthly_rent_excluded_from_jeonse_query():
    repo = _make_repo()
    repo.save(_tx(contract_type="monthly", monthly_rent=50, deposit=10000))
    results = repo.get_recent(complex_code="CC001", area=84.0, months=6, jeonse_only=True)
    assert len(results) == 0


import pytest


@pytest.fixture
def jeonse_repo(tmp_path):
    return JeonseRepository(db_path=str(tmp_path / "test.db"))


def test_get_by_complex_returns_all_for_complex_code(jeonse_repo):
    tx1 = JeonseTransaction(
        complex_code="CC001", apt_name="래미안", district_code="41135",
        deal_date="2026-01-15", exclusive_area=84.0, deposit=500_000_000,
        monthly_rent=0, contract_type="jeonse", floor=5
    )
    tx2 = JeonseTransaction(
        complex_code="CC001", apt_name="래미안", district_code="41135",
        deal_date="2026-02-10", exclusive_area=59.0, deposit=350_000_000,
        monthly_rent=0, contract_type="jeonse", floor=3
    )
    tx_other = JeonseTransaction(
        complex_code="CC999", apt_name="힐스테이트", district_code="41135",
        deal_date="2026-02-01", exclusive_area=84.0, deposit=600_000_000,
        monthly_rent=0, contract_type="jeonse", floor=7
    )
    jeonse_repo.save(tx1)
    jeonse_repo.save(tx2)
    jeonse_repo.save(tx_other)

    results = jeonse_repo.get_by_complex("CC001")
    assert len(results) == 2
    assert all(r.complex_code == "CC001" for r in results)


def test_get_by_complex_returns_empty_when_no_data(jeonse_repo):
    assert jeonse_repo.get_by_complex("NONEXISTENT") == []
