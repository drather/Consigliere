# tests/modules/real_estate/yield_analysis/test_yield_calculator.py
import sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

from modules.real_estate.yield_analysis.calculator import YieldCalculator
from modules.real_estate.jeonse.repository import JeonseRepository
from modules.real_estate.jeonse.models import JeonseTransaction


def _make_jeonse_repo_with_data(deposit: int = 58000):
    tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    repo = JeonseRepository(db_path=tf.name)
    repo.save(JeonseTransaction(
        complex_code="CC001", apt_name="래미안퍼스티지",
        district_code="11650", deal_date="2026-04-10",
        exclusive_area=84.0, deposit=deposit, monthly_rent=0,
        contract_type="jeonse", floor=5
    ))
    return repo


def test_jeonse_rate_calculation():
    jeonse_repo = _make_jeonse_repo_with_data(deposit=58000)
    calc = YieldCalculator(jeonse_repo=jeonse_repo, mortgage_rate=0.0283)
    result = calc.calculate(
        complex_code="CC001", apt_name="래미안퍼스티지",
        district_code="11650", exclusive_area=84.0,
        avg_sale_price=93000  # 만원 단위 (9.3억)
    )
    assert result is not None
    assert abs(result.jeonse_rate - 58000 / 93000) < 0.01
    assert result.gap_cost == 93000 - 58000


def test_monthly_cost_positive():
    jeonse_repo = _make_jeonse_repo_with_data()
    calc = YieldCalculator(jeonse_repo=jeonse_repo, mortgage_rate=0.0283)
    result = calc.calculate(
        complex_code="CC001", apt_name="래미안퍼스티지",
        district_code="11650", exclusive_area=84.0, avg_sale_price=93000
    )
    assert result.monthly_cost > 15  # 관리비 15만원 이상


def test_returns_none_when_no_jeonse_data():
    tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    empty_repo = JeonseRepository(db_path=tf.name)
    calc = YieldCalculator(jeonse_repo=empty_repo, mortgage_rate=0.0283)
    result = calc.calculate(
        complex_code="NONE", apt_name="없는단지",
        district_code="00000", exclusive_area=84.0, avg_sale_price=90000
    )
    assert result is None


def test_fallback_by_name_when_no_complex_code():
    jeonse_repo = _make_jeonse_repo_with_data(deposit=60000)
    # complex_code 없이 저장된 데이터
    jeonse_repo._conn.execute(
        "UPDATE jeonse_transactions SET complex_code = NULL"
    )
    jeonse_repo._conn.commit()
    calc = YieldCalculator(jeonse_repo=jeonse_repo, mortgage_rate=0.0283)
    result = calc.calculate(
        complex_code=None, apt_name="래미안퍼스티지",
        district_code="11650", exclusive_area=84.0, avg_sale_price=93000
    )
    assert result is not None
    assert result.jeonse_avg == 60000
