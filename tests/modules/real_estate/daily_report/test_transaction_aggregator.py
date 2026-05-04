import sqlite3
from datetime import date, timedelta
import pytest

from modules.real_estate.daily_report.transaction_aggregator import TransactionAggregator
from modules.real_estate.daily_report.models import AggregatedTransaction


def _setup_db(db_path: str) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS apt_master (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                apt_name TEXT NOT NULL,
                district_code TEXT NOT NULL DEFAULT '',
                sido TEXT NOT NULL DEFAULT '',
                sigungu TEXT NOT NULL DEFAULT '',
                complex_code TEXT,
                tx_count INTEGER DEFAULT 0,
                first_traded TEXT,
                last_traded TEXT,
                created_at TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                apt_master_id INTEGER,
                complex_code TEXT,
                apt_name TEXT NOT NULL,
                district_code TEXT NOT NULL,
                deal_date TEXT NOT NULL,
                price INTEGER NOT NULL,
                floor INTEGER NOT NULL DEFAULT 0,
                exclusive_area REAL NOT NULL DEFAULT 0.0,
                build_year INTEGER NOT NULL DEFAULT 0,
                road_name TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS apartments (
                complex_code TEXT PRIMARY KEY,
                household_count INTEGER DEFAULT 0,
                road_address TEXT DEFAULT ''
            );
        """)


def _insert_apt_master(conn, id: int, name: str, sigungu: str, complex_code: str = None) -> None:
    conn.execute(
        "INSERT INTO apt_master (id, apt_name, district_code, sido, sigungu, complex_code, created_at) "
        "VALUES (?, ?, '11680', '서울특별시', ?, ?, '2026-01-01')",
        (id, name, sigungu, complex_code),
    )


def _insert_tx(conn, apt_master_id: int, deal_date: str, price: int, area: float = 84.0) -> None:
    conn.execute(
        "INSERT INTO transactions (apt_master_id, apt_name, district_code, deal_date, price, floor, exclusive_area, build_year, road_name) "
        "VALUES (?, '테스트', '11680', ?, ?, 5, ?, 2002, '')",
        (apt_master_id, deal_date, price, area),
    )


class TestAggregateBasic:
    def test_returns_list_of_aggregated_transactions(self, tmp_path):
        db_path = str(tmp_path / "re.db")
        _setup_db(db_path)
        today = date.today().isoformat()
        with sqlite3.connect(db_path) as conn:
            _insert_apt_master(conn, 1, "래미안", "강남구", "CC001")
            _insert_tx(conn, 1, today, 300_000_000)
            _insert_tx(conn, 1, today, 310_000_000)

        agg = TransactionAggregator(db_path=db_path)
        result = agg.aggregate(days=3, top_k=10, persona={}, budget_available=500_000_000)

        assert len(result) == 1
        assert isinstance(result[0], AggregatedTransaction)
        assert result[0].apt_name == "래미안"
        assert result[0].recent_tx_count == 2

    def test_excludes_transactions_outside_date_range(self, tmp_path):
        db_path = str(tmp_path / "re.db")
        _setup_db(db_path)
        old_date = (date.today() - timedelta(days=10)).isoformat()
        with sqlite3.connect(db_path) as conn:
            _insert_apt_master(conn, 1, "오래된단지", "강남구")
            _insert_tx(conn, 1, old_date, 200_000_000)

        agg = TransactionAggregator(db_path=db_path)
        result = agg.aggregate(days=3, top_k=10, persona={}, budget_available=500_000_000)

        assert len(result) == 0

    def test_top_k_limits_result(self, tmp_path):
        db_path = str(tmp_path / "re.db")
        _setup_db(db_path)
        today = date.today().isoformat()
        with sqlite3.connect(db_path) as conn:
            for i in range(5):
                _insert_apt_master(conn, i + 1, f"단지{i+1}", "강남구")
                _insert_tx(conn, i + 1, today, 200_000_000 + i * 10_000_000)

        agg = TransactionAggregator(db_path=db_path)
        result = agg.aggregate(days=3, top_k=2, persona={}, budget_available=500_000_000)

        assert len(result) == 2


class TestCompositeScore:
    def test_higher_tx_count_gives_higher_score(self, tmp_path):
        db_path = str(tmp_path / "re.db")
        _setup_db(db_path)
        today = date.today().isoformat()
        with sqlite3.connect(db_path) as conn:
            _insert_apt_master(conn, 1, "활발단지", "강남구")
            _insert_apt_master(conn, 2, "조용단지", "강남구")
            for _ in range(3):
                _insert_tx(conn, 1, today, 300_000_000)
            _insert_tx(conn, 2, today, 300_000_000)

        agg = TransactionAggregator(db_path=db_path)
        result = agg.aggregate(days=3, top_k=10, persona={}, budget_available=500_000_000)

        scores = {r.apt_name: r.composite_score for r in result}
        assert scores["활발단지"] > scores["조용단지"]

    def test_interest_area_boosts_persona_affinity(self, tmp_path):
        db_path = str(tmp_path / "re.db")
        _setup_db(db_path)
        today = date.today().isoformat()
        with sqlite3.connect(db_path) as conn:
            _insert_apt_master(conn, 1, "관심지역단지", "강남구")
            _insert_apt_master(conn, 2, "비관심지역단지", "노원구")
            _insert_tx(conn, 1, today, 300_000_000)
            _insert_tx(conn, 2, today, 300_000_000)

        persona = {"user": {"interest_areas": ["강남구"]}}
        agg = TransactionAggregator(db_path=db_path)
        result = agg.aggregate(days=3, top_k=10, persona=persona, budget_available=500_000_000)

        scores = {r.apt_name: r.composite_score for r in result}
        assert scores["관심지역단지"] > scores["비관심지역단지"]

    def test_price_change_signal_uses_absolute_value(self, tmp_path):
        db_path = str(tmp_path / "re.db")
        _setup_db(db_path)
        today = date.today().isoformat()
        prior = (date.today() - timedelta(days=10)).isoformat()
        with sqlite3.connect(db_path) as conn:
            _insert_apt_master(conn, 1, "급등단지", "강남구")
            _insert_apt_master(conn, 2, "급락단지", "강남구")
            _insert_tx(conn, 1, prior, 100_000_000)
            _insert_tx(conn, 1, today, 120_000_000)
            _insert_tx(conn, 2, prior, 100_000_000)
            _insert_tx(conn, 2, today, 80_000_000)

        agg = TransactionAggregator(db_path=db_path)
        result = agg.aggregate(days=3, top_k=10, persona={}, budget_available=500_000_000)

        scores = {r.apt_name: r.composite_score for r in result}
        assert abs(scores["급등단지"] - scores["급락단지"]) < 0.05


class TestPriceChangePct:
    def test_price_change_pct_calculated_from_prior_period(self, tmp_path):
        db_path = str(tmp_path / "re.db")
        _setup_db(db_path)
        today = date.today().isoformat()
        prior = (date.today() - timedelta(days=15)).isoformat()
        with sqlite3.connect(db_path) as conn:
            _insert_apt_master(conn, 1, "테스트단지", "강남구")
            _insert_tx(conn, 1, prior, 100_000_000)
            _insert_tx(conn, 1, today, 110_000_000)

        agg = TransactionAggregator(db_path=db_path)
        result = agg.aggregate(days=3, top_k=10, persona={}, budget_available=500_000_000)

        assert len(result) == 1
        assert abs(result[0].price_change_pct - 10.0) < 1.0

    def test_no_prior_data_gives_zero_change(self, tmp_path):
        db_path = str(tmp_path / "re.db")
        _setup_db(db_path)
        today = date.today().isoformat()
        with sqlite3.connect(db_path) as conn:
            _insert_apt_master(conn, 1, "신규단지", "강남구")
            _insert_tx(conn, 1, today, 200_000_000)

        agg = TransactionAggregator(db_path=db_path)
        result = agg.aggregate(days=3, top_k=10, persona={}, budget_available=500_000_000)

        assert result[0].price_change_pct == 0.0
