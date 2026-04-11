"""
TDD tests for DashboardClient.get_transactions_by_district_codes
"""
import pandas as pd
import pytest
from unittest.mock import patch

try:
    from dashboard.api_client import DashboardClient
except ImportError:
    from src.dashboard.api_client import DashboardClient


def _make_tx_df(apt_name: str, district_code: str) -> pd.DataFrame:
    return pd.DataFrame([
        {"apt_name": apt_name, "district_code": district_code,
         "deal_date": "2026-03-01", "price": 1_000_000_000,
         "exclusive_area": 84.0, "floor": 5},
    ])


# ── 단일 district_code 조회 ───────────────────────────────────────────────────

def test_single_district_code_returns_df(monkeypatch):
    monkeypatch.setattr(
        DashboardClient,
        "get_real_estate_transactions",
        staticmethod(lambda district_code=None, limit=500: _make_tx_df("래미안", "11680")),
    )
    result = DashboardClient.get_transactions_by_district_codes(["11680"])
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 1


# ── 복수 district_code → 합산 반환 ────────────────────────────────────────────

def test_multiple_district_codes_concatenated(monkeypatch):
    def fake_get(district_code=None, limit=500):
        if district_code == "11680":
            return _make_tx_df("래미안", "11680")
        if district_code == "11650":
            return _make_tx_df("아크로", "11650")
        return pd.DataFrame()

    monkeypatch.setattr(DashboardClient, "get_real_estate_transactions", staticmethod(fake_get))
    result = DashboardClient.get_transactions_by_district_codes(["11680", "11650"])
    assert len(result) == 2
    assert set(result["district_code"]) == {"11680", "11650"}


# ── apt_names 필터 ────────────────────────────────────────────────────────────

def test_apt_names_filter_excludes_unmatched(monkeypatch):
    def fake_get(district_code=None, limit=500):
        return pd.DataFrame([
            {"apt_name": "래미안", "district_code": "11680",
             "deal_date": "2026-01-01", "price": 1_000_000_000,
             "exclusive_area": 84.0, "floor": 3},
            {"apt_name": "힐스테이트", "district_code": "11680",
             "deal_date": "2026-02-01", "price": 900_000_000,
             "exclusive_area": 59.0, "floor": 7},
        ])

    monkeypatch.setattr(DashboardClient, "get_real_estate_transactions", staticmethod(fake_get))
    result = DashboardClient.get_transactions_by_district_codes(
        ["11680"], apt_names={"래미안"}
    )
    assert len(result) == 1
    assert result.iloc[0]["apt_name"] == "래미안"


def test_apt_names_none_returns_all(monkeypatch):
    def fake_get(district_code=None, limit=500):
        return pd.DataFrame([
            {"apt_name": "래미안", "district_code": "11680",
             "deal_date": "2026-01-01", "price": 1_000_000_000,
             "exclusive_area": 84.0, "floor": 3},
            {"apt_name": "힐스테이트", "district_code": "11680",
             "deal_date": "2026-02-01", "price": 900_000_000,
             "exclusive_area": 59.0, "floor": 7},
        ])

    monkeypatch.setattr(DashboardClient, "get_real_estate_transactions", staticmethod(fake_get))
    result = DashboardClient.get_transactions_by_district_codes(["11680"], apt_names=None)
    assert len(result) == 2


# ── 빈 결과 처리 ──────────────────────────────────────────────────────────────

def test_empty_district_codes_returns_empty_df(monkeypatch):
    result = DashboardClient.get_transactions_by_district_codes([])
    assert isinstance(result, pd.DataFrame)
    assert result.empty


def test_all_districts_return_empty_returns_empty_df(monkeypatch):
    monkeypatch.setattr(
        DashboardClient,
        "get_real_estate_transactions",
        staticmethod(lambda district_code=None, limit=500: pd.DataFrame()),
    )
    result = DashboardClient.get_transactions_by_district_codes(["11680", "11650"])
    assert isinstance(result, pd.DataFrame)
    assert result.empty


def test_apt_names_filter_on_empty_df(monkeypatch):
    monkeypatch.setattr(
        DashboardClient,
        "get_real_estate_transactions",
        staticmethod(lambda district_code=None, limit=500: pd.DataFrame()),
    )
    result = DashboardClient.get_transactions_by_district_codes(
        ["11680"], apt_names={"래미안"}
    )
    assert result.empty
