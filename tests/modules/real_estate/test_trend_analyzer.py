import os
import sys
import sqlite3
import pytest
from datetime import date, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src')))

from modules.real_estate.trend_analyzer import TrendAnalyzer, TrendData


def _insert_tx(conn, apt_master_id, price, deal_date, exclusive_area=84.0):
    conn.execute(
        "INSERT INTO transactions (apt_master_id, apt_name, district_code, deal_date, price, floor, exclusive_area, build_year, road_name) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (apt_master_id, "테스트아파트", "11680", deal_date, price, 5, exclusive_area, 2000, ""),
    )


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "re.db")
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            apt_master_id INTEGER,
            apt_name TEXT NOT NULL,
            district_code TEXT NOT NULL,
            deal_date TEXT NOT NULL,
            price INTEGER NOT NULL,
            floor INTEGER NOT NULL DEFAULT 0,
            exclusive_area REAL NOT NULL DEFAULT 0.0,
            build_year INTEGER NOT NULL DEFAULT 0,
            road_name TEXT NOT NULL DEFAULT ''
        )
    """)
    today = date.today()
    for i in range(6):
        month_ago = today - timedelta(days=30 * i)
        d = month_ago.strftime("%Y-%m-%d")
        price = 1_200_000_000 + i * 10_000_000
        _insert_tx(conn, 1, price, d)
    conn.commit()
    conn.close()
    return path


@pytest.fixture
def analyzer(db_path):
    return TrendAnalyzer(db_path=db_path)


class TestTrendAnalyzer:
    def test_get_trend_returns_trend_data(self, analyzer):
        result = analyzer.get_trend(apt_master_id=1, area_sqm=84.0)
        assert isinstance(result, TrendData)
        assert result.sample_count == 6
        assert result.avg_price > 0

    def test_avg_price_calculation(self, analyzer):
        result = analyzer.get_trend(apt_master_id=1, area_sqm=84.0)
        expected = (1_200_000_000 + 1_210_000_000 + 1_220_000_000 +
                    1_230_000_000 + 1_240_000_000 + 1_250_000_000) // 6
        assert abs(result.avg_price - expected) < 1_000_000

    def test_price_change_pct_with_rising_prices(self, analyzer):
        result = analyzer.get_trend(apt_master_id=1, area_sqm=84.0)
        assert isinstance(result.price_change_pct, float)

    def test_returns_none_for_no_data(self, analyzer):
        result = analyzer.get_trend(apt_master_id=999, area_sqm=84.0)
        assert result is None

    def test_monthly_volume(self, analyzer):
        result = analyzer.get_trend(apt_master_id=1, area_sqm=84.0)
        assert result.monthly_volume > 0

    def test_area_filter_excludes_other_areas(self, db_path):
        conn = sqlite3.connect(db_path)
        today = date.today().strftime("%Y-%m-%d")
        _insert_tx(conn, 1, 800_000_000, today, exclusive_area=59.0)
        conn.commit()
        conn.close()
        analyzer = TrendAnalyzer(db_path=db_path)
        result_84 = analyzer.get_trend(apt_master_id=1, area_sqm=84.0)
        result_59 = analyzer.get_trend(apt_master_id=1, area_sqm=59.0)
        assert result_84.avg_price != result_59.avg_price
