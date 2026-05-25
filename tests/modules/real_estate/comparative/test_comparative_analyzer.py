# tests/modules/real_estate/comparative/test_comparative_analyzer.py
import sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

import sqlite3
from modules.real_estate.comparative.analyzer import ComparativeAnalyzer
from modules.real_estate.transaction_repository import TransactionRepository


def _make_tx_repo_with_data():
    tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    repo = TransactionRepository(db_path=tf.name)
    conn = sqlite3.connect(tf.name)
    # district_code="11710" (송파구), area=84, build_year=2005, 최근 거래
    conn.executemany(
        """INSERT OR IGNORE INTO transactions
           (complex_code, apt_name, district_code, deal_date, price, floor, exclusive_area, build_year, road_name)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        [
            ("CC001", "잠실엘스", "11710", "2026-04-10", 1_030_000_000, 5, 84.0, 2008, ""),
            ("CC002", "잠실리센츠", "11710", "2026-04-12", 980_000_000, 7, 84.0, 2007, ""),
            ("CC003", "레이크팰리스", "11710", "2026-04-15", 870_000_000, 3, 84.0, 2004, ""),
            ("CC_TARGET", "현대7", "11710", "2026-04-20", 930_000_000, 8, 84.0, 2003, ""),
        ]
    )
    conn.commit()
    conn.close()
    return repo, tf.name


def test_district_avg_per_sqm():
    repo, _ = _make_tx_repo_with_data()
    analyzer = ComparativeAnalyzer(tx_repo=repo)
    result = analyzer.analyze(
        complex_code="CC_TARGET", district_code="11710",
        exclusive_area=84.0, build_year=2003, avg_sale_price=930_000_000
    )
    assert result.district_avg_per_sqm > 0
    assert result.pct_vs_avg != 0.0


def test_similar_units_excludes_target():
    repo, _ = _make_tx_repo_with_data()
    analyzer = ComparativeAnalyzer(tx_repo=repo)
    result = analyzer.analyze(
        complex_code="CC_TARGET", district_code="11710",
        exclusive_area=84.0, build_year=2003, avg_sale_price=930_000_000
    )
    names = [u.name for u in result.similar_units]
    assert "현대7" not in names
    assert len(result.similar_units) <= 3


def test_no_data_returns_zero():
    tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    repo = TransactionRepository(db_path=tf.name)
    analyzer = ComparativeAnalyzer(tx_repo=repo)
    result = analyzer.analyze(
        complex_code="NONE", district_code="99999",
        exclusive_area=84.0, build_year=2000, avg_sale_price=500_000_000
    )
    assert result.district_avg_per_sqm == 0.0
    assert result.similar_units == []
