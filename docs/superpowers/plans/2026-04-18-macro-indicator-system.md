# Macro Indicator System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** BOK ECOS 거시경제 지표를 SQLite DB에 영구 저장·수집·조회하는 공유 macro 모듈을 구축하고, 기존 real_estate 매크로 코드를 이 모듈로 통합한다.

**Architecture:** `src/modules/macro/`에 도메인 중립 공유 모듈(models, repository, bok_client, service)을 신설한다. 지표 메타데이터는 `macro_indicator_definitions` 테이블, 시계열은 `macro_records` 테이블에 저장한다. 기존 `real_estate/macro/bok_service.py`·`models.py`는 삭제하고 `real_estate/macro/service.py`는 공유 서비스에 위임하는 어댑터로 교체한다.

**Tech Stack:** Python 3.12, SQLite3 (dataclasses 기반 레포지토리 패턴), FastAPI, Streamlit, pytest, unittest.mock

---

## File Map

| 상태 | 파일 | 역할 |
|------|------|------|
| 신규 | `src/modules/macro/__init__.py` | 패키지 선언 |
| 신규 | `src/modules/macro/models.py` | MacroIndicatorDef, MacroRecord 데이터클래스 |
| 신규 | `src/modules/macro/repository.py` | SQLite CRUD (macro.db) |
| 신규 | `src/modules/macro/bok_client.py` | BOK ECOS API 클라이언트 (기존 이전) |
| 신규 | `src/modules/macro/service.py` | MacroCollectionService (수집 오케스트레이션) |
| 신규 | `src/api/routers/macro.py` | /jobs/macro/collect, /dashboard/macro/* |
| 신규 | `scripts/seed_macro_indicators.py` | 초기 지표 정의 시딩 |
| 신규 | `scripts/verify_bok_item_codes.py` | BOK ECOS item_code 사전 검증 |
| 신규 | `tests/modules/macro/__init__.py` | 테스트 패키지 |
| 신규 | `tests/modules/macro/test_macro_repository.py` | Repository TDD |
| 신규 | `tests/modules/macro/test_macro_service.py` | Service TDD |
| 수정 | `src/modules/real_estate/config.yaml` | macro_db_path 추가 |
| 수정 | `src/modules/real_estate/macro/service.py` | MacroCollectionService 위임 어댑터로 교체 |
| 수정 | `src/modules/real_estate/service.py` | fetch_macro_data() → collect_due_indicators() 호출 |
| 수정 | `src/api/dependencies.py` | MacroRepository, MacroCollectionService DI 등록 |
| 수정 | `src/api/routers/real_estate.py` | macro 엔드포인트 신규 서비스로 위임 |
| 수정 | `src/main.py` | macro_router 등록 |
| 수정 | `src/dashboard/api_client.py` | macro API 메서드 추가 |
| 수정 | `src/dashboard/views/real_estate.py` | 거시경제 탭 카테고리 서브탭으로 확장 |
| 삭제 | `src/modules/real_estate/macro/bok_service.py` | macro/bok_client.py로 대체 |
| 삭제 | `src/modules/real_estate/macro/models.py` | macro/models.py로 대체 |
| 삭제 | `tests/test_bok_macro.py` | tests/modules/macro/로 대체 |

---

## Task 1: 데이터 모델 정의

**Files:**
- Create: `src/modules/macro/__init__.py`
- Create: `src/modules/macro/models.py`

- [ ] **Step 1: 패키지 파일 생성**

```bash
mkdir -p src/modules/macro
touch src/modules/macro/__init__.py
```

- [ ] **Step 2: models.py 작성**

`src/modules/macro/models.py`:
```python
from dataclasses import dataclass
from typing import Optional


@dataclass
class MacroIndicatorDef:
    id: Optional[int]
    code: str           # BOK stat_code (예: "722Y001")
    item_code: str      # BOK item_code (예: "0101000")
    name: str           # "한국은행 기준금리"
    unit: str           # "%", "십억원", "지수"
    frequency: str      # "M"월별, "Q"분기, "A"연간, "D"일별
    collect_every_days: int
    domain: str         # "real_estate", "finance", "common"
    category: str       # "금리", "주택시장", "물가", "유동성", "경기"
    is_active: bool
    last_collected_at: Optional[str]  # ISO datetime
    created_at: str                   # ISO datetime


@dataclass
class MacroRecord:
    id: Optional[int]
    indicator_id: int
    period: str         # "202503" (BOK 발표 기준 기간)
    value: float
    collected_at: str   # ISO datetime (실제 수집 일시)
```

- [ ] **Step 3: import 확인**

```bash
arch -arm64 .venv/bin/python3.12 -c "from modules.macro.models import MacroIndicatorDef, MacroRecord; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/modules/macro/__init__.py src/modules/macro/models.py
git commit -m "feat(macro): MacroIndicatorDef, MacroRecord 데이터 모델 추가"
```

---

## Task 2: MacroRepository (TDD)

**Files:**
- Create: `src/modules/macro/repository.py`
- Create: `tests/modules/macro/__init__.py`
- Create: `tests/modules/macro/test_macro_repository.py`

- [ ] **Step 1: 테스트 패키지 파일 생성**

```bash
mkdir -p tests/modules/macro
touch tests/modules/macro/__init__.py
```

- [ ] **Step 2: 실패 테스트 작성**

`tests/modules/macro/test_macro_repository.py`:
```python
import os
import pytest
import tempfile
from datetime import datetime, timezone
from modules.macro.models import MacroIndicatorDef, MacroRecord
from modules.macro.repository import MacroRepository


@pytest.fixture
def repo(tmp_path):
    db_path = str(tmp_path / "test_macro.db")
    return MacroRepository(db_path=db_path)


def _make_def(**kwargs) -> MacroIndicatorDef:
    defaults = dict(
        id=None,
        code="722Y001",
        item_code="0101000",
        name="한국은행 기준금리",
        unit="%",
        frequency="M",
        collect_every_days=30,
        domain="common",
        category="금리",
        is_active=True,
        last_collected_at=None,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    defaults.update(kwargs)
    return MacroIndicatorDef(**defaults)


def _make_record(indicator_id: int, period: str, value: float, collected_at: str) -> MacroRecord:
    return MacroRecord(id=None, indicator_id=indicator_id, period=period,
                       value=value, collected_at=collected_at)


class TestMacroRepository:
    def test_init_creates_tables(self, repo):
        # DB 생성 후 테이블 존재 확인
        import sqlite3
        conn = sqlite3.connect(repo.db_path)
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        conn.close()
        assert "macro_indicator_definitions" in tables
        assert "macro_records" in tables

    def test_insert_indicator_returns_id(self, repo):
        ind = _make_def()
        new_id = repo.insert_indicator(ind)
        assert isinstance(new_id, int)
        assert new_id > 0

    def test_get_active_indicators_all(self, repo):
        repo.insert_indicator(_make_def(code="722Y001", domain="common"))
        repo.insert_indicator(_make_def(code="121Y002", domain="real_estate",
                                        name="주담대금리", item_code="BEABAA2"))
        indicators = repo.get_active_indicators()
        assert len(indicators) == 2

    def test_get_active_indicators_by_domain(self, repo):
        repo.insert_indicator(_make_def(code="722Y001", domain="common"))
        repo.insert_indicator(_make_def(code="121Y002", domain="real_estate",
                                        name="주담대금리", item_code="BEABAA2"))
        result = repo.get_active_indicators(domain="real_estate")
        assert len(result) == 1
        assert result[0].domain == "real_estate"

    def test_get_active_indicators_excludes_inactive(self, repo):
        ind = _make_def(is_active=False)
        repo.insert_indicator(ind)
        result = repo.get_active_indicators()
        assert len(result) == 0

    def test_update_last_collected(self, repo):
        new_id = repo.insert_indicator(_make_def())
        ts = "2026-04-18T10:00:00+00:00"
        repo.update_last_collected(new_id, ts)
        indicators = repo.get_active_indicators()
        assert indicators[0].last_collected_at == ts

    def test_insert_records_basic(self, repo):
        ind_id = repo.insert_indicator(_make_def())
        records = [
            _make_record(ind_id, "202503", 3.50, "2026-04-18T10:00:00+00:00"),
            _make_record(ind_id, "202502", 3.50, "2026-04-18T10:00:00+00:00"),
        ]
        repo.insert_records(records)
        history = repo.get_history(ind_id, months=12)
        assert len(history) == 2

    def test_insert_records_ignores_duplicate(self, repo):
        ind_id = repo.insert_indicator(_make_def())
        record = _make_record(ind_id, "202503", 3.50, "2026-04-18T10:00:00+00:00")
        repo.insert_records([record])
        repo.insert_records([record])  # 동일 수집 - 무시
        history = repo.get_history(ind_id, months=12)
        assert len(history) == 1

    def test_insert_records_allows_revision(self, repo):
        ind_id = repo.insert_indicator(_make_def())
        repo.insert_records([_make_record(ind_id, "202503", 3.50, "2026-01-15T00:00:00+00:00")])
        repo.insert_records([_make_record(ind_id, "202503", 3.25, "2026-02-15T00:00:00+00:00")])
        # 두 수집일이 다르므로 둘 다 저장
        import sqlite3
        conn = sqlite3.connect(repo.db_path)
        rows = conn.execute(
            "SELECT COUNT(*) FROM macro_records WHERE indicator_id=? AND period='202503'",
            (ind_id,)
        ).fetchone()[0]
        conn.close()
        assert rows == 2

    def test_get_history_returns_latest_per_period(self, repo):
        ind_id = repo.insert_indicator(_make_def())
        # 동일 period, 두 번 수집
        repo.insert_records([_make_record(ind_id, "202503", 3.50, "2026-01-15T00:00:00+00:00")])
        repo.insert_records([_make_record(ind_id, "202503", 3.25, "2026-02-15T00:00:00+00:00")])
        history = repo.get_history(ind_id, months=12)
        assert len(history) == 1
        assert history[0].value == 3.25  # 최신 수집값

    def test_get_latest_returns_most_recent_period(self, repo):
        ind_id = repo.insert_indicator(_make_def())
        repo.insert_records([
            _make_record(ind_id, "202501", 3.50, "2026-02-01T00:00:00+00:00"),
            _make_record(ind_id, "202502", 3.25, "2026-03-01T00:00:00+00:00"),
            _make_record(ind_id, "202503", 3.00, "2026-04-01T00:00:00+00:00"),
        ])
        latest = repo.get_latest()
        assert len(latest) == 1
        assert latest[0]["period"] == "202503"
        assert latest[0]["value"] == 3.00

    def test_get_indicator_by_id(self, repo):
        new_id = repo.insert_indicator(_make_def())
        ind = repo.get_indicator_by_id(new_id)
        assert ind is not None
        assert ind.code == "722Y001"
```

- [ ] **Step 3: 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/macro/test_macro_repository.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'modules.macro.repository'`

- [ ] **Step 4: repository.py 구현**

`src/modules/macro/repository.py`:
```python
import sqlite3
from datetime import datetime, timezone
from typing import List, Optional
from .models import MacroIndicatorDef, MacroRecord

_DDL = """
CREATE TABLE IF NOT EXISTS macro_indicator_definitions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    code                TEXT NOT NULL,
    item_code           TEXT NOT NULL,
    name                TEXT NOT NULL,
    unit                TEXT NOT NULL,
    frequency           TEXT NOT NULL,
    collect_every_days  INTEGER NOT NULL,
    domain              TEXT NOT NULL,
    category            TEXT NOT NULL,
    is_active           INTEGER DEFAULT 1,
    last_collected_at   TEXT,
    created_at          TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS macro_records (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    indicator_id    INTEGER NOT NULL REFERENCES macro_indicator_definitions(id),
    period          TEXT NOT NULL,
    value           REAL NOT NULL,
    collected_at    TEXT NOT NULL,
    UNIQUE(indicator_id, period, collected_at)
);

CREATE INDEX IF NOT EXISTS idx_mr_ind_period ON macro_records(indicator_id, period);
CREATE INDEX IF NOT EXISTS idx_mr_collected  ON macro_records(collected_at);
CREATE INDEX IF NOT EXISTS idx_mid_domain    ON macro_indicator_definitions(domain);
CREATE INDEX IF NOT EXISTS idx_mid_active    ON macro_indicator_definitions(is_active);
"""


class MacroRepository:
    def __init__(self, db_path: str = "data/macro.db"):
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript(_DDL)

    # ── Indicator Definitions ────────────────────────────────────

    def insert_indicator(self, ind: MacroIndicatorDef) -> int:
        sql = """
        INSERT INTO macro_indicator_definitions
            (code, item_code, name, unit, frequency, collect_every_days,
             domain, category, is_active, last_collected_at, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        with self._connect() as conn:
            cur = conn.execute(sql, (
                ind.code, ind.item_code, ind.name, ind.unit, ind.frequency,
                ind.collect_every_days, ind.domain, ind.category,
                1 if ind.is_active else 0,
                ind.last_collected_at, ind.created_at,
            ))
            return cur.lastrowid

    def get_active_indicators(self, domain: Optional[str] = None) -> List[MacroIndicatorDef]:
        sql = "SELECT * FROM macro_indicator_definitions WHERE is_active = 1"
        params: list = []
        if domain:
            sql += " AND (domain = ? OR domain = 'common')"
            params.append(domain)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_row_to_def(r) for r in rows]

    def get_indicator_by_id(self, indicator_id: int) -> Optional[MacroIndicatorDef]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM macro_indicator_definitions WHERE id = ?", (indicator_id,)
            ).fetchone()
        return _row_to_def(row) if row else None

    def update_last_collected(self, indicator_id: int, collected_at: str):
        with self._connect() as conn:
            conn.execute(
                "UPDATE macro_indicator_definitions SET last_collected_at = ? WHERE id = ?",
                (collected_at, indicator_id),
            )

    # ── Records ─────────────────────────────────────────────────

    def insert_records(self, records: List[MacroRecord]):
        sql = """
        INSERT OR IGNORE INTO macro_records (indicator_id, period, value, collected_at)
        VALUES (?, ?, ?, ?)
        """
        with self._connect() as conn:
            conn.executemany(
                sql,
                [(r.indicator_id, r.period, r.value, r.collected_at) for r in records],
            )

    def get_history(self, indicator_id: int, months: int = 24) -> List[MacroRecord]:
        """period별 최신 수집값 기준 시계열, 최근 N개월."""
        sql = """
        SELECT id, indicator_id, period, value, collected_at
        FROM macro_records
        WHERE indicator_id = ?
          AND collected_at = (
              SELECT MAX(r2.collected_at)
              FROM macro_records r2
              WHERE r2.indicator_id = macro_records.indicator_id
                AND r2.period = macro_records.period
          )
        ORDER BY period DESC
        LIMIT ?
        """
        with self._connect() as conn:
            rows = conn.execute(sql, (indicator_id, months)).fetchall()
        return [_row_to_record(r) for r in rows]

    def get_latest(self, domain: Optional[str] = None) -> List[dict]:
        """각 지표별 최신 period, 최신 수집값 반환."""
        domain_filter = "AND (d.domain = ? OR d.domain = 'common')" if domain else ""
        params = [domain] if domain else []
        sql = f"""
        SELECT d.id, d.name, d.unit, d.domain, d.category,
               r.period, r.value, r.collected_at
        FROM macro_indicator_definitions d
        JOIN macro_records r ON r.indicator_id = d.id
        WHERE d.is_active = 1
          {domain_filter}
          AND r.collected_at = (
              SELECT MAX(r2.collected_at)
              FROM macro_records r2
              WHERE r2.indicator_id = r.indicator_id AND r2.period = r.period
          )
          AND r.period = (
              SELECT MAX(r3.period)
              FROM macro_records r3
              WHERE r3.indicator_id = d.id
          )
        ORDER BY d.category, d.name
        """
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


# ── Row Converters ───────────────────────────────────────────────

def _row_to_def(row: sqlite3.Row) -> MacroIndicatorDef:
    return MacroIndicatorDef(
        id=row["id"],
        code=row["code"],
        item_code=row["item_code"],
        name=row["name"],
        unit=row["unit"],
        frequency=row["frequency"],
        collect_every_days=row["collect_every_days"],
        domain=row["domain"],
        category=row["category"],
        is_active=bool(row["is_active"]),
        last_collected_at=row["last_collected_at"],
        created_at=row["created_at"],
    )


def _row_to_record(row: sqlite3.Row) -> MacroRecord:
    return MacroRecord(
        id=row["id"],
        indicator_id=row["indicator_id"],
        period=row["period"],
        value=row["value"],
        collected_at=row["collected_at"],
    )
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/macro/test_macro_repository.py -v
```

Expected: `12 passed`

- [ ] **Step 6: Commit**

```bash
git add src/modules/macro/repository.py tests/modules/macro/__init__.py tests/modules/macro/test_macro_repository.py
git commit -m "feat(macro): MacroRepository SQLite CRUD 구현 (TDD 12 tests)"
```

---

## Task 3: BOKClient 이전 및 개선

**Files:**
- Create: `src/modules/macro/bok_client.py`

- [ ] **Step 1: bok_client.py 작성**

`src/modules/macro/bok_client.py`:
```python
import os
import requests
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

try:
    from core.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class BOKClient:
    """Bank of Korea ECOS Open API 클라이언트."""

    BASE_URL = "https://ecos.bok.or.kr/api/StatisticSearch"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("BOK_API_KEY", "sample")

    def get_statistic_series(
        self,
        stat_code: str,
        item_code: str,
        months: int = 24,
        frequency: str = "M",
        item_code2: str = "?",
        item_code3: str = "?",
    ) -> List[Dict[str, Any]]:
        """
        BOK ECOS 시계열 조회.

        Args:
            stat_code: 통계표 코드 (예: "722Y001")
            item_code: 항목 코드 (예: "0101000"). "?"이면 전체 항목 반환.
            months: 조회 개월 수 (rows 수 결정)
            frequency: "M"월별, "Q"분기, "A"연간, "D"일별
            item_code2, item_code3: 추가 항목 필터 (기본 전체)
        Returns:
            [{"TIME": "202503", "DATA_VALUE": "3.50", ...}, ...]
        """
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=30 * months)

        if frequency == "D":
            start_date = start_dt.strftime("%Y%m%d")
            end_date = end_dt.strftime("%Y%m%d")
        elif frequency in ("M", "Q", "A"):
            start_date = start_dt.strftime("%Y%m")
            end_date = end_dt.strftime("%Y%m")
        else:
            start_date = start_dt.strftime("%Y%m")
            end_date = end_dt.strftime("%Y%m")

        url = (
            f"{self.BASE_URL}/{self.api_key}/json/kr/1/{months}/"
            f"{stat_code}/{frequency}/{start_date}/{end_date}/"
            f"{item_code}/{item_code2}/{item_code3}"
        )

        try:
            logger.info(f"🌐 [BOKClient] Fetching {stat_code} ({frequency}, {months}건)")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("StatisticSearch", {}).get("row", [])
        except Exception as e:
            logger.error(f"❌ [BOKClient] {stat_code} 조회 실패: {e}")
            return []

    def list_items(self, stat_code: str) -> List[Dict[str, Any]]:
        """
        stat_code의 사용 가능한 item_code 목록 조회 (item_code="?" 사용).
        신규 지표 추가 시 item_code 확인용.
        """
        return self.get_statistic_series(stat_code, item_code="?", months=1)
```

- [ ] **Step 2: import 확인**

```bash
arch -arm64 .venv/bin/python3.12 -c "from modules.macro.bok_client import BOKClient; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/modules/macro/bok_client.py
git commit -m "feat(macro): BOKClient 공유 모듈로 이전 및 frequency/item_code 파라미터 추가"
```

---

## Task 4: MacroCollectionService (TDD)

**Files:**
- Create: `src/modules/macro/service.py`
- Create: `tests/modules/macro/test_macro_service.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests/modules/macro/test_macro_service.py`:
```python
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
from modules.macro.models import MacroIndicatorDef, MacroRecord
from modules.macro.service import MacroCollectionService


def _make_def(ind_id=1, collect_every_days=30, last_collected_at=None, **kwargs) -> MacroIndicatorDef:
    defaults = dict(
        id=ind_id,
        code="722Y001",
        item_code="0101000",
        name="한국은행 기준금리",
        unit="%",
        frequency="M",
        collect_every_days=collect_every_days,
        domain="common",
        category="금리",
        is_active=True,
        last_collected_at=last_collected_at,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    defaults.update(kwargs)
    return MacroIndicatorDef(**defaults)


class TestMacroCollectionService:
    @pytest.fixture
    def service(self, tmp_path):
        svc = MacroCollectionService(db_path=str(tmp_path / "test.db"))
        return svc

    def test_collect_due_skips_recent(self, service):
        recent = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        ind = _make_def(collect_every_days=30, last_collected_at=recent)
        service.repo.get_active_indicators = MagicMock(return_value=[ind])
        result = service.collect_due_indicators()
        assert "한국은행 기준금리" in result["skipped"]
        assert result["collected"] == []

    def test_collect_due_collects_overdue(self, service):
        old = (datetime.now(timezone.utc) - timedelta(days=45)).isoformat()
        ind = _make_def(collect_every_days=30, last_collected_at=old)
        service.repo.get_active_indicators = MagicMock(return_value=[ind])
        service.client.get_statistic_series = MagicMock(return_value=[
            {"TIME": "202503", "DATA_VALUE": "3.50"},
            {"TIME": "202502", "DATA_VALUE": "3.50"},
        ])
        service.repo.insert_records = MagicMock()
        service.repo.update_last_collected = MagicMock()
        result = service.collect_due_indicators()
        assert "한국은행 기준금리" in result["collected"]
        service.repo.insert_records.assert_called_once()
        service.repo.update_last_collected.assert_called_once_with(1, pytest.approx)

    def test_collect_due_collects_never_collected(self, service):
        ind = _make_def(last_collected_at=None)
        service.repo.get_active_indicators = MagicMock(return_value=[ind])
        service.client.get_statistic_series = MagicMock(return_value=[
            {"TIME": "202503", "DATA_VALUE": "3.50"},
        ])
        service.repo.insert_records = MagicMock()
        service.repo.update_last_collected = MagicMock()
        result = service.collect_due_indicators()
        assert "한국은행 기준금리" in result["collected"]

    def test_collect_due_handles_bok_error(self, service):
        ind = _make_def(last_collected_at=None)
        service.repo.get_active_indicators = MagicMock(return_value=[ind])
        service.client.get_statistic_series = MagicMock(return_value=[])  # BOK 응답 없음
        service.repo.insert_records = MagicMock()
        service.repo.update_last_collected = MagicMock()
        result = service.collect_due_indicators()
        # 데이터 없어도 에러 없이 완료, last_collected_at 업데이트
        assert result["errors"] == []
        service.repo.update_last_collected.assert_called_once()

    def test_collect_all_ignores_due_check(self, service):
        recent = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        ind = _make_def(collect_every_days=30, last_collected_at=recent)
        service.repo.get_active_indicators = MagicMock(return_value=[ind])
        service.client.get_statistic_series = MagicMock(return_value=[])
        service.repo.insert_records = MagicMock()
        service.repo.update_last_collected = MagicMock()
        result = service.collect_all()
        assert "한국은행 기준금리" in result["collected"]

    def test_collect_domain_filter_passed_to_repo(self, service):
        service.repo.get_active_indicators = MagicMock(return_value=[])
        service.collect_due_indicators(domain="real_estate")
        service.repo.get_active_indicators.assert_called_once_with(domain="real_estate")

    def test_get_latest_delegates_to_repo(self, service):
        service.repo.get_latest = MagicMock(return_value=[{"name": "기준금리", "value": 3.5}])
        result = service.get_latest(domain="common")
        service.repo.get_latest.assert_called_once_with(domain="common")
        assert result[0]["name"] == "기준금리"

    def test_get_history_delegates_to_repo(self, service):
        service.repo.get_history = MagicMock(return_value=[])
        service.get_history(indicator_id=1, months=12)
        service.repo.get_history.assert_called_once_with(1, 12)
```

- [ ] **Step 2: 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/macro/test_macro_service.py -v 2>&1 | head -10
```

Expected: `ModuleNotFoundError: No module named 'modules.macro.service'`

- [ ] **Step 3: service.py 구현**

`src/modules/macro/service.py`:
```python
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

from .models import MacroIndicatorDef, MacroRecord
from .repository import MacroRepository
from .bok_client import BOKClient

try:
    from core.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class MacroCollectionService:
    def __init__(self, db_path: str = "data/macro.db", api_key: Optional[str] = None):
        self.repo = MacroRepository(db_path=db_path)
        self.client = BOKClient(api_key=api_key)

    # ── 수집 ────────────────────────────────────────────────────

    def collect_due_indicators(self, domain: Optional[str] = None) -> Dict[str, Any]:
        """collect_every_days 기준으로 수집 기한이 된 지표만 수집."""
        indicators = self.repo.get_active_indicators(domain=domain)
        collected, skipped, errors = [], [], []

        for ind in indicators:
            if not self._is_due(ind):
                skipped.append(ind.name)
                continue
            try:
                self._collect_one(ind)
                collected.append(ind.name)
            except Exception as e:
                logger.error(f"❌ [MacroCollectionService] {ind.name}: {e}")
                errors.append({"name": ind.name, "error": str(e)})

        return {"collected": collected, "skipped": skipped, "errors": errors}

    def collect_all(self, domain: Optional[str] = None) -> Dict[str, Any]:
        """기한 무관하게 전체 강제 수집. 초기 시딩 및 수동 트리거용."""
        indicators = self.repo.get_active_indicators(domain=domain)
        collected, errors = [], []

        for ind in indicators:
            try:
                self._collect_one(ind)
                collected.append(ind.name)
            except Exception as e:
                logger.error(f"❌ [MacroCollectionService] {ind.name}: {e}")
                errors.append({"name": ind.name, "error": str(e)})

        return {"collected": collected, "errors": errors}

    def _is_due(self, ind: MacroIndicatorDef) -> bool:
        if not ind.last_collected_at:
            return True
        last = datetime.fromisoformat(ind.last_collected_at)
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) >= last + timedelta(days=ind.collect_every_days)

    def _collect_one(self, ind: MacroIndicatorDef):
        now = datetime.now(timezone.utc).isoformat()
        rows = self.client.get_statistic_series(
            stat_code=ind.code,
            item_code=ind.item_code,
            months=24,
            frequency=ind.frequency,
        )
        records = []
        for r in rows:
            try:
                records.append(MacroRecord(
                    id=None,
                    indicator_id=ind.id,
                    period=r["TIME"],
                    value=float(r["DATA_VALUE"]),
                    collected_at=now,
                ))
            except (KeyError, ValueError):
                continue
        if records:
            self.repo.insert_records(records)
        self.repo.update_last_collected(ind.id, now)

    # ── 조회 ────────────────────────────────────────────────────

    def get_latest(self, domain: Optional[str] = None) -> List[dict]:
        return self.repo.get_latest(domain=domain)

    def get_history(self, indicator_id: int, months: int = 24) -> List[MacroRecord]:
        return self.repo.get_history(indicator_id, months)
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/macro/ -v
```

Expected: `20 passed` (repository 12 + service 8)

- [ ] **Step 5: Commit**

```bash
git add src/modules/macro/service.py tests/modules/macro/test_macro_service.py
git commit -m "feat(macro): MacroCollectionService 수집 오케스트레이션 구현 (TDD 8 tests)"
```

---

## Task 5: BOK item_code 검증 및 시딩 스크립트

**Files:**
- Create: `scripts/verify_bok_item_codes.py`
- Create: `scripts/seed_macro_indicators.py`

- [ ] **Step 1: item_code 검증 스크립트 작성**

`scripts/verify_bok_item_codes.py`:
```python
"""
BOK ECOS item_code 사전 검증 스크립트.
실행: arch -arm64 .venv/bin/python3.12 scripts/verify_bok_item_codes.py
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from modules.macro.bok_client import BOKClient

STAT_CODES_TO_VERIFY = [
    ("121Y013", "COFIX 신규취급액"),
    ("600Y001", "가계신용"),
    ("901Y062", "주택매매가격지수"),
    ("901Y063", "전세가격지수"),
    ("902Y009", "소비자물가지수(CPI)"),
    ("200Y001", "GDP 성장률"),
]

def main():
    client = BOKClient()
    for code, name in STAT_CODES_TO_VERIFY:
        print(f"\n{'='*60}")
        print(f"[{code}] {name}")
        rows = client.get_statistic_series(code, item_code="?", months=1)
        if not rows:
            print("  ⚠️  데이터 없음 (sample key 한도 또는 코드 오류)")
            continue
        for r in rows[:5]:
            print(f"  item_code: {r.get('ITEM_CODE1', r.get('STAT_CODE', '?'))} "
                  f"| TIME: {r.get('TIME')} | VALUE: {r.get('DATA_VALUE')} "
                  f"| 항목명: {r.get('ITEM_NAME1', '')}")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 검증 스크립트 실행**

```bash
arch -arm64 .venv/bin/python3.12 scripts/verify_bok_item_codes.py
```

출력을 보고 각 stat_code의 올바른 `item_code`를 확인한다. 출력 예:
```
[121Y013] COFIX 신규취급액
  item_code: BECBBA | TIME: 202503 | VALUE: 3.56 | 항목명: 신규취급액 기준 코픽스
```

- [ ] **Step 3: 검증된 item_code로 시딩 스크립트 작성**

검증 결과를 반영하여 `scripts/seed_macro_indicators.py` 작성. 아래에서 `item_code` 값은 Step 2 출력 결과로 교체한다:

`scripts/seed_macro_indicators.py`:
```python
"""
BOK ECOS 지표 초기 시딩 스크립트.
실행: arch -arm64 .venv/bin/python3.12 scripts/seed_macro_indicators.py
중복 실행 시 이미 존재하는 지표는 건너뜀.
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from datetime import datetime, timezone
from modules.macro.models import MacroIndicatorDef
from modules.macro.repository import MacroRepository

NOW = datetime.now(timezone.utc).isoformat()

# item_code는 scripts/verify_bok_item_codes.py 실행 결과로 확정
INDICATORS = [
    MacroIndicatorDef(id=None, code="722Y001",  item_code="0101000",
                      name="한국은행 기준금리",         unit="%",    frequency="M",
                      collect_every_days=30, domain="common",        category="금리",
                      is_active=True, last_collected_at=None, created_at=NOW),
    MacroIndicatorDef(id=None, code="121Y002",  item_code="BEABAA2",
                      name="예금은행 주택담보대출 금리", unit="%",    frequency="M",
                      collect_every_days=30, domain="real_estate",   category="금리",
                      is_active=True, last_collected_at=None, created_at=NOW),
    MacroIndicatorDef(id=None, code="121Y013",  item_code="VERIFIED_ITEM_CODE",
                      name="COFIX 신규취급액 기준금리", unit="%",    frequency="M",
                      collect_every_days=30, domain="real_estate",   category="금리",
                      is_active=True, last_collected_at=None, created_at=NOW),
    MacroIndicatorDef(id=None, code="101Y001",  item_code="BBGS00",
                      name="M2 통화량(기말, 계절조정)", unit="십억원", frequency="M",
                      collect_every_days=30, domain="common",        category="유동성",
                      is_active=True, last_collected_at=None, created_at=NOW),
    MacroIndicatorDef(id=None, code="600Y001",  item_code="VERIFIED_ITEM_CODE",
                      name="가계신용 총량",              unit="십억원", frequency="Q",
                      collect_every_days=90, domain="common",        category="유동성",
                      is_active=True, last_collected_at=None, created_at=NOW),
    MacroIndicatorDef(id=None, code="901Y062",  item_code="VERIFIED_ITEM_CODE",
                      name="주택매매가격지수(전국)",     unit="지수",  frequency="M",
                      collect_every_days=30, domain="real_estate",   category="주택시장",
                      is_active=True, last_collected_at=None, created_at=NOW),
    MacroIndicatorDef(id=None, code="901Y063",  item_code="VERIFIED_ITEM_CODE",
                      name="전세가격지수(전국)",          unit="지수",  frequency="M",
                      collect_every_days=30, domain="real_estate",   category="주택시장",
                      is_active=True, last_collected_at=None, created_at=NOW),
    MacroIndicatorDef(id=None, code="902Y009",  item_code="VERIFIED_ITEM_CODE",
                      name="소비자물가지수(CPI)",         unit="지수",  frequency="M",
                      collect_every_days=30, domain="common",        category="물가",
                      is_active=True, last_collected_at=None, created_at=NOW),
    MacroIndicatorDef(id=None, code="200Y001",  item_code="VERIFIED_ITEM_CODE",
                      name="실질GDP 성장률",              unit="%",    frequency="Q",
                      collect_every_days=90, domain="common",        category="경기",
                      is_active=True, last_collected_at=None, created_at=NOW),
]


def main():
    db_path = os.getenv("MACRO_DB_PATH", "data/macro.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    repo = MacroRepository(db_path=db_path)

    for ind in INDICATORS:
        try:
            new_id = repo.insert_indicator(ind)
            print(f"✅ [{new_id}] {ind.name} ({ind.code})")
        except Exception as e:
            print(f"⚠️  Skip: {ind.name} — {e}")

    total = len(repo.get_active_indicators())
    print(f"\n📊 총 활성 지표: {total}개")


if __name__ == "__main__":
    main()
```

> **중요:** `VERIFIED_ITEM_CODE` 자리를 Step 2 검증 결과로 교체한 후 다음 단계 실행.

- [ ] **Step 4: 시딩 실행**

```bash
arch -arm64 .venv/bin/python3.12 scripts/seed_macro_indicators.py
```

Expected:
```
✅ [1] 한국은행 기준금리 (722Y001)
✅ [2] 예금은행 주택담보대출 금리 (121Y002)
...
📊 총 활성 지표: 9개
```

- [ ] **Step 5: Commit**

```bash
git add scripts/verify_bok_item_codes.py scripts/seed_macro_indicators.py
git commit -m "feat(macro): BOK item_code 검증 스크립트 및 지표 시딩 스크립트 추가"
```

---

## Task 6: API Router 추가

**Files:**
- Create: `src/api/routers/macro.py`
- Modify: `src/api/dependencies.py`
- Modify: `src/main.py`

- [ ] **Step 1: DI 등록 — dependencies.py**

`src/api/dependencies.py` 하단에 추가:
```python
from modules.macro.service import MacroCollectionService
from modules.real_estate.config import RealEstateConfig as _REConfig

_macro_db_path = _REConfig().get("macro_db_path", "data/macro.db")
_macro_service = MacroCollectionService(db_path=_macro_db_path)


def get_macro_service() -> MacroCollectionService:
    return _macro_service
```

- [ ] **Step 2: macro.py 라우터 작성**

`src/api/routers/macro.py`:
```python
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from modules.macro.service import MacroCollectionService
from api.dependencies import get_macro_service
from core.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["Macro"])


@router.post("/jobs/macro/collect")
def job_collect_macro(
    domain: Optional[str] = None,
    force_all: bool = False,
    service: MacroCollectionService = Depends(get_macro_service),
):
    """
    거시경제 지표 수집 Job.
    - domain: "real_estate" / "finance" / "common" / None(전체)
    - force_all: True면 수집 기한 무관하게 강제 수집
    """
    try:
        if force_all:
            result = service.collect_all(domain=domain)
        else:
            result = service.collect_due_indicators(domain=domain)
        return {"status": "success", **result}
    except Exception as e:
        logger.error(f"Macro Collect Job Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/macro/latest")
def get_macro_latest(
    domain: Optional[str] = None,
    service: MacroCollectionService = Depends(get_macro_service),
):
    """지표별 최신값. domain 필터 가능."""
    try:
        return service.get_latest(domain=domain)
    except Exception as e:
        logger.error(f"Macro Latest API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/macro/history/{indicator_id}")
def get_macro_history_by_id(
    indicator_id: int,
    months: int = 24,
    service: MacroCollectionService = Depends(get_macro_service),
):
    """단일 지표 시계열 (최근 N개월)."""
    try:
        ind = service.repo.get_indicator_by_id(indicator_id)
        if not ind:
            raise HTTPException(status_code=404, detail=f"indicator_id={indicator_id} not found")
        records = service.get_history(indicator_id, months=months)
        return {
            "indicator": {
                "id": ind.id, "name": ind.name, "unit": ind.unit,
                "domain": ind.domain, "category": ind.category,
            },
            "records": [
                {"period": r.period, "value": r.value, "collected_at": r.collected_at}
                for r in records
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Macro History API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 3: main.py에 라우터 등록**

`src/main.py`에서 기존 import 블록에 추가:
```python
from api.routers.macro import router as macro_router
```

`app.include_router` 블록에 추가:
```python
app.include_router(macro_router)
```

- [ ] **Step 4: 서버 구동 및 엔드포인트 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
sleep 3
curl -s http://localhost:8000/dashboard/macro/latest | python3 -m json.tool | head -20
```

Expected: JSON 배열 (시딩 후 collect_all 실행했다면 데이터 있음, 아니면 `[]`)

- [ ] **Step 5: Commit**

```bash
git add src/api/routers/macro.py src/api/dependencies.py src/main.py
git commit -m "feat(macro): /jobs/macro/collect, /dashboard/macro/latest, /history/{id} API 추가"
```

---

## Task 7: Real Estate 어댑터 교체 + 기존 엔드포인트 위임

**Files:**
- Modify: `src/modules/real_estate/macro/service.py`
- Modify: `src/modules/real_estate/service.py`
- Modify: `src/api/routers/real_estate.py`
- Modify: `src/modules/real_estate/config.yaml`
- Delete: `src/modules/real_estate/macro/bok_service.py`
- Delete: `src/modules/real_estate/macro/models.py`
- Delete: `tests/test_bok_macro.py`

- [ ] **Step 1: config.yaml에 macro_db_path 추가**

`src/modules/real_estate/config.yaml` 상단 bok_codes 아래에 추가:
```yaml
macro_db_path: "data/macro.db"
```

- [ ] **Step 2: real_estate/macro/service.py 어댑터로 교체**

`src/modules/real_estate/macro/service.py` 전체를 아래로 교체:
```python
"""
Real Estate 도메인 전용 거시경제 조회 어댑터.
실제 수집/저장은 modules.macro.service.MacroCollectionService에 위임한다.
"""
from typing import Dict, Any, List, Optional

try:
    from modules.macro.service import MacroCollectionService
    from modules.real_estate.config import RealEstateConfig
except ImportError:
    from src.modules.macro.service import MacroCollectionService
    from src.modules.real_estate.config import RealEstateConfig

try:
    from core.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class MacroService:
    """
    RealEstateAgent가 직접 참조하는 어댑터.
    MacroCollectionService에 위임하고, 기존 응답 포맷(MacroData 호환)을 유지한다.
    """

    def __init__(self, api_key: Optional[str] = None):
        config = RealEstateConfig()
        db_path = config.get("macro_db_path", "data/macro.db")
        self._svc = MacroCollectionService(db_path=db_path, api_key=api_key)

    def fetch_latest_macro_data(self) -> Dict[str, Any]:
        """
        DB에서 real_estate + common 도메인 최신값 조회.
        기존 MacroData.model_dump() 호환 dict 반환.
        """
        latest = self._svc.get_latest(domain="real_estate")
        result: Dict[str, Any] = {"updated_at": None}

        for item in latest:
            name = item.get("name", "")
            collected_at = item.get("collected_at")
            if not result["updated_at"] or collected_at > result["updated_at"]:
                result["updated_at"] = collected_at

            entry = {
                "name": name,
                "code": str(item.get("id")),
                "value": item.get("value"),
                "unit": item.get("unit"),
                "date": item.get("period"),
            }

            if "기준금리" in name:
                result["base_rate"] = entry
            elif "주택담보대출" in name or "주담대" in name:
                result["loan_rate"] = entry
            elif "M2" in name:
                result["m2_growth"] = entry

        return result

    def fetch_macro_history(self, months: int = 24) -> Dict[str, List[Dict[str, Any]]]:
        """
        기준금리·주담대 시계열 반환.
        기존 dashboard macro-history 응답 포맷 유지:
        {"base_rate": [{"date": "2025-03", "value": 3.5, "name": "..."}], "loan_rate": [...]}
        """
        latest_list = self._svc.get_latest(domain="real_estate")
        base_id = next((i["id"] for i in latest_list if "기준금리" in i["name"]), None)
        loan_id = next((i["id"] for i in latest_list if "주택담보대출" in i["name"]), None)

        def _to_series(indicator_id, label):
            if not indicator_id:
                return []
            records = self._svc.get_history(indicator_id, months=months)
            return [
                {"date": f"{r.period[:4]}-{r.period[4:]}", "value": r.value, "name": label}
                for r in sorted(records, key=lambda x: x.period)
            ]

        return {
            "base_rate": _to_series(base_id, "한국은행 기준금리(%)"),
            "loan_rate":  _to_series(loan_id, "주담대금리(%)"),
        }

    def collect_real_estate_indicators(self) -> Dict[str, Any]:
        """real_estate + common 지표 수집 (기한 도래분만)."""
        return self._svc.collect_due_indicators(domain="real_estate")
```

- [ ] **Step 3: RealEstateAgent.fetch_macro_data() 업데이트**

`src/modules/real_estate/service.py`의 `fetch_macro_data` 메서드를 아래로 교체:
```python
def fetch_macro_data(self) -> Dict[str, Any]:
    """Job 3: 거시경제 지표 수집 → macro.db 저장 + JSON 백업."""
    logger.info("[Job3] Fetching macro data via MacroCollectionService...")
    result = self.macro_service.collect_real_estate_indicators()

    # 기존 파이프라인 호환: JSON 백업 파일 유지
    macro_dict = self.macro_service.fetch_latest_macro_data()
    macro_dir = os.path.join(os.getenv("LOCAL_STORAGE_PATH", "./data"), "real_estate", "macro")
    os.makedirs(macro_dir, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    macro_path = os.path.join(macro_dir, f"{today}_macro.json")
    import json
    with open(macro_path, "w", encoding="utf-8") as f:
        json.dump(macro_dict, f, ensure_ascii=False, indent=2)

    logger.info(f"[Job3] Saved macro backup: {macro_path}")
    return {"macro": macro_dict, "collect_result": result}
```

- [ ] **Step 4: real_estate 라우터 macro-history 위임 업데이트**

`src/api/routers/real_estate.py`에서 `get_macro_history` 함수를 찾아 아래로 교체:
```python
@router.get("/dashboard/real-estate/macro-history")
def get_macro_history(agent: RealEstateAgent = Depends(get_real_estate_agent)):
    """거시경제 지표 시계열 데이터. macro.db에서 조회 (기존 응답 포맷 유지)."""
    try:
        return agent.macro_service.fetch_macro_history()
    except Exception as e:
        logger.error(f"Macro History API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 5: 구 파일 삭제**

```bash
rm src/modules/real_estate/macro/bok_service.py
rm src/modules/real_estate/macro/models.py
rm tests/test_bok_macro.py
```

- [ ] **Step 6: 기존 테스트 전체 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/ -v --ignore=tests/e2e 2>&1 | tail -20
```

Expected: 모든 기존 테스트 PASS (회귀 없음), `test_bok_macro.py` 삭제로 제외됨.

- [ ] **Step 7: Commit**

```bash
git add src/modules/real_estate/config.yaml \
        src/modules/real_estate/macro/service.py \
        src/modules/real_estate/service.py \
        src/api/routers/real_estate.py
git rm src/modules/real_estate/macro/bok_service.py \
       src/modules/real_estate/macro/models.py \
       tests/test_bok_macro.py
git commit -m "refactor(macro): real_estate 매크로 어댑터 교체 및 구 파일 삭제"
```

---

## Task 8: 초기 데이터 수집 실행

- [ ] **Step 1: 서버 실행 확인 (Task 6에서 구동 중이면 생략)**

```bash
arch -arm64 .venv/bin/python3.12 -m uvicorn main:app --host 0.0.0.0 --port 8000 &
sleep 3
```

- [ ] **Step 2: collect_all 실행 (최근 24개월 초기 수집)**

```bash
curl -s -X POST "http://localhost:8000/jobs/macro/collect?force_all=true" | python3 -m json.tool
```

Expected:
```json
{
  "status": "success",
  "collected": ["한국은행 기준금리", "예금은행 주택담보대출 금리", ...],
  "errors": []
}
```

- [ ] **Step 3: 최신값 조회 확인**

```bash
curl -s "http://localhost:8000/dashboard/macro/latest?domain=real_estate" | python3 -m json.tool
```

Expected: 9개 지표 최신값 JSON 배열

- [ ] **Step 4: 기존 macro-history 엔드포인트 호환 확인**

```bash
curl -s "http://localhost:8000/dashboard/real-estate/macro-history" | python3 -m json.tool
```

Expected: `{"base_rate": [...], "loan_rate": [...]}` 기존 포맷 유지

---

## Task 9: 대시보드 거시경제 탭 확장

**Files:**
- Modify: `src/dashboard/api_client.py`
- Modify: `src/dashboard/views/real_estate.py`

- [ ] **Step 1: DashboardClient에 신규 API 메서드 추가**

`src/dashboard/api_client.py`의 `DashboardClient` 클래스 안에 추가:
```python
@staticmethod
def get_macro_latest(domain: str = "real_estate") -> list:
    """지표별 최신값 (카테고리별 그룹화 용도)."""
    try:
        response = requests.get(
            f"{API_BASE_URL}/dashboard/macro/latest",
            params={"domain": domain},
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching macro latest: {e}")
        return []

@staticmethod
def get_macro_indicator_history(indicator_id: int, months: int = 24) -> dict:
    """단일 지표 시계열."""
    try:
        response = requests.get(
            f"{API_BASE_URL}/dashboard/macro/history/{indicator_id}",
            params={"months": months},
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching macro history {indicator_id}: {e}")
        return {}

@staticmethod
def trigger_collect_macro(domain: str = "real_estate") -> dict:
    """거시경제 수집 Job 트리거."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/jobs/macro/collect",
            params={"domain": domain},
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}
```

- [ ] **Step 2: 거시경제 탭 카테고리 서브탭으로 교체**

`src/dashboard/views/real_estate.py`의 `news_tab0` 블록 (`with news_tab0:` 부터 `st.button("🔄 새로고침"...` 까지)을 아래로 교체:

```python
with news_tab0:
    st.subheader("거시경제 지표")

    if "macro_latest" not in st.session_state:
        with st.spinner("한국은행 지표 로딩 중..."):
            st.session_state.macro_latest = DashboardClient.get_macro_latest(domain="real_estate")

    items = st.session_state.macro_latest

    if not items:
        st.info("거시경제 데이터를 불러올 수 없습니다.")
        st.caption("수집 Job을 먼저 실행하거나 '📋 Report Archive' 탭에서 거시경제 수집을 실행하세요.")
    else:
        # 카테고리별 그룹화
        from collections import defaultdict
        by_category: dict = defaultdict(list)
        for item in items:
            by_category[item.get("category", "기타")].append(item)

        cat_tabs = st.tabs([f"📊 {cat}" for cat in by_category])
        for cat_tab, (cat_name, cat_items) in zip(cat_tabs, by_category.items()):
            with cat_tab:
                cols = st.columns(min(len(cat_items), 3))
                for col, item in zip(cols, cat_items):
                    with col:
                        st.metric(
                            label=item["name"],
                            value=f"{item['value']}{item['unit']}",
                            help=f"기준기간: {item['period']} | 수집: {item['collected_at'][:10]}",
                        )

                st.markdown("---")

                # 첫 번째 지표 시계열 차트
                first = cat_items[0]
                chart_data = DashboardClient.get_macro_indicator_history(
                    indicator_id=first["id"], months=24
                )
                records = chart_data.get("records", [])
                if records:
                    import pandas as pd
                    df = pd.DataFrame(records).set_index("period")
                    st.markdown(f"**{first['name']} 추이 (최근 24개월)**")
                    st.line_chart(df["value"], height=250)
                    st.caption(f"출처: 한국은행 ECOS | 단위: {first['unit']}")

    if st.button("🔄 새로고침", key="macro_refresh"):
        st.session_state.pop("macro_latest", None)
        st.rerun()
```

- [ ] **Step 3: 대시보드 실행 및 화면 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m streamlit run src/dashboard/main.py --server.port 8502
```

브라우저에서 부동산 탭 → 뉴스/지표 탭 → "📈 거시경제" 서브탭을 열어 카테고리 탭(금리, 주택시장, 물가/경기, 유동성)이 표시되는지 확인.

- [ ] **Step 4: Commit**

```bash
git add src/dashboard/api_client.py src/dashboard/views/real_estate.py
git commit -m "feat(dashboard): 거시경제 지표 탭 카테고리 서브탭으로 확장"
```

---

## Task 10: 최종 검증 및 정리

- [ ] **Step 1: 전체 단위 테스트**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/ -v --ignore=tests/e2e 2>&1 | tail -30
```

Expected: 모든 테스트 PASS, `tests/modules/macro/` 20개 포함.

- [ ] **Step 2: macro 모듈 통합 흐름 확인**

```bash
# 1) 시딩 확인
arch -arm64 .venv/bin/python3.12 -c "
from modules.macro.repository import MacroRepository
repo = MacroRepository('data/macro.db')
inds = repo.get_active_indicators()
print(f'Active indicators: {len(inds)}')
for i in inds: print(f'  [{i.id}] {i.name} ({i.domain})')
"

# 2) 최신값 확인
curl -s "http://localhost:8000/dashboard/macro/latest" | python3 -m json.tool | head -30

# 3) 히스토리 확인 (indicator_id=1 기준금리)
curl -s "http://localhost:8000/dashboard/macro/history/1?months=6" | python3 -m json.tool
```

- [ ] **Step 3: 기존 파이프라인 호환 확인**

```bash
# 구 엔드포인트가 여전히 동작하는지
curl -s "http://localhost:8000/dashboard/real-estate/macro-history" | python3 -m json.tool | head -10
```

Expected: `{"base_rate": [...], "loan_rate": [...]}` 기존 포맷

- [ ] **Step 4: 최종 Commit**

```bash
git add .
git commit -m "feat(macro): 거시경제 지표 수집 시스템 구축 완료"
```
