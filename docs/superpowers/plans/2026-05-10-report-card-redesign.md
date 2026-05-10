# 데일리 리포트 카드 리디자인 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 데일리 부동산 리포트를 verdict-first 구조·SVG 스파크라인·실거주/투자성 점수 분리·출퇴근 3카드 패널로 리디자인하고, TypedDict 계약으로 데이터·렌더러·출력 레이어를 격리한다.

**Architecture:** 6-레이어 구조 — DB → Aggregator → TypedDict 계약(report_types.py) → 렌더러 함수(report_formatter.py) → 조립(build_candidate_card / build_markdown / build_slack) → 출력. 렌더러는 candidate dict를 직접 접근하지 않는다. `build_candidate_card()`가 dict → TypedDict 추출의 유일한 지점.

**Tech Stack:** Python 3.12, TypedDict (typing_extensions), itertools, SQLite, Streamlit (unsafe_allow_html=True), Slack mrkdwn

---

## File Map

| 파일 | 변경 종류 |
|------|----------|
| `src/modules/real_estate/daily_report/report_types.py` | 신규 생성 |
| `src/modules/real_estate/daily_report/transaction_aggregator.py` | 수정 (SQL 추가 + `_recent_tx_points` 주입) |
| `src/modules/real_estate/daily_report/report_formatter.py` | 전면 수정 (렌더러 분리, 조립 함수 재설계) |
| `src/modules/real_estate/daily_report/daily_report_orchestrator.py` | 수정 (car/walking 추가, `_verdict`/`_key_points` 주입) |
| `src/modules/real_estate/prompts/daily_strategy.md` | 수정 (`verdict`, `key_points` 필드 추가) |
| `src/dashboard/views/real_estate.py` | 1줄 수정 (`unsafe_allow_html=True`) |
| `tests/modules/real_estate/daily_report/test_report_types.py` | 신규 생성 |
| `tests/modules/real_estate/daily_report/test_transaction_aggregator.py` | 테스트 추가 |
| `tests/modules/real_estate/daily_report/test_report_formatter.py` | 전면 교체 |

---

### Task 1: report_types.py — TypedDict 계약 정의

**Files:**
- Create: `src/modules/real_estate/daily_report/report_types.py`
- Create: `tests/modules/real_estate/daily_report/test_report_types.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# tests/modules/real_estate/daily_report/test_report_types.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

from modules.real_estate.daily_report.report_types import (
    TxPoint, TrendData, CommuteData, CandidateSummary,
)


def test_txpoint_structure():
    p: TxPoint = {"price_eok": 8.8, "deal_date": "2026-05-10"}
    assert p["price_eok"] == 8.8
    assert p["deal_date"] == "2026-05-10"


def test_trenddata_structure():
    t: TrendData = {
        "points": [{"price_eok": 8.5, "deal_date": "2026-05-07"},
                   {"price_eok": 8.8, "deal_date": "2026-05-10"}],
        "avg_eok": 8.65,
        "change_pct": -3.2,
        "area_sqm": 84.0,
    }
    assert len(t["points"]) == 2
    assert t["avg_eok"] == 8.65


def test_commutedata_structure():
    c: CommuteData = {
        "transit_minutes": 35,
        "car_minutes": None,
        "walk_minutes": None,
        "route_summary": "2호선 30분 → 도보 5분",
    }
    assert c["transit_minutes"] == 35
    assert c["car_minutes"] is None


def test_candidatesummary_structure():
    cs: CandidateSummary = {
        "apt_name": "래미안",
        "sigungu": "강남구",
        "area_sqm": 84.0,
        "household_count": 1200,
        "composite_score": 85,
        "verdict": "매수 검토",
        "key_points": ["✅ 역세권", "📈 상승 추세"],
        "trend": {
            "points": [{"price_eok": 28.0, "deal_date": "2026-05-10"}],
            "avg_eok": 28.0, "change_pct": 2.5, "area_sqm": 84.0,
        },
        "commute": {
            "transit_minutes": 20, "car_minutes": 30,
            "walk_minutes": None, "route_summary": "",
        },
        "residential_results": [],
        "investment_results": [],
    }
    assert cs["apt_name"] == "래미안"
    assert cs["composite_score"] == 85
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/daily_report/test_report_types.py -v
```

Expected: `ModuleNotFoundError: No module named 'modules.real_estate.daily_report.report_types'`

- [ ] **Step 3: report_types.py 구현**

```python
# src/modules/real_estate/daily_report/report_types.py
from typing import List, Optional
from typing_extensions import TypedDict


class TxPoint(TypedDict):
    price_eok: float    # 억 단위 (예: 8.8)
    deal_date: str      # "YYYY-MM-DD"


class TrendData(TypedDict):
    points: List[TxPoint]   # 날짜순 정렬
    avg_eok: float           # 평균가 (억)
    change_pct: float        # 전월비 변동률 (%)
    area_sqm: float          # 전용면적 (㎡)


class CommuteData(TypedDict):
    transit_minutes: Optional[int]
    car_minutes: Optional[int]
    walk_minutes: Optional[int]
    route_summary: str       # 빈 문자열이면 표시 안 함


class CandidateSummary(TypedDict):
    apt_name: str
    sigungu: str
    area_sqm: float
    household_count: int
    composite_score: int     # 0~100 정수
    verdict: str
    key_points: List[str]
    trend: TrendData
    commute: CommuteData
    residential_results: List   # List[DimensionResult]
    investment_results: List    # List[DimensionResult]
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/daily_report/test_report_types.py -v
```

Expected: 4 passed

- [ ] **Step 5: 커밋**

```bash
git add src/modules/real_estate/daily_report/report_types.py \
        tests/modules/real_estate/daily_report/test_report_types.py
git commit -m "feat(report): report_types.py — TxPoint/TrendData/CommuteData/CandidateSummary TypedDict 계약"
```

---

### Task 2: TransactionAggregator — `_recent_tx_points` 주입

**Files:**
- Modify: `src/modules/real_estate/daily_report/transaction_aggregator.py`
- Modify: `tests/modules/real_estate/daily_report/test_transaction_aggregator.py`

> **배경:** `aggregate()`가 반환하는 raw dict에 `_recent_tx_points: List[TxPoint]`를 추가해야 한다.
> `AggregatedTransaction` dataclass는 건드리지 않는다. `_recent_tx_points`는 raw dict를 통해
> candidate dict로 전달된다. 현재 `aggregate()`는 raw dict 목록에서 `AggregatedTransaction`을
> 만든 뒤 `.sort()` 후 반환하는데, raw dict가 lost된다. 해결: raw dict에 먼저 `_recent_tx_points`를
> 붙인 뒤, `AggregatedTransaction` 생성 시 무시(dataclass에 없는 키)하고, 별도로 dict로 변환할 때 합친다.
>
> **실제 흐름 확인:** `daily_report_orchestrator.py`의 `_to_dict()` 메서드가 `AggregatedTransaction`을
> dict로 변환한다. 이 메서드에 `_recent_tx_points` 키를 추가해야 raw가 candidate dict로 흘러간다.
>
> **더 단순한 접근:** raw 목록에서 `_recent_tx_points`를 미리 뽑아둔 뒤, `AggregatedTransaction`을
> sort 후 `scored[:top_k]`를 슬라이싱할 때 각 항목의 raw dict를 함께 돌려준다.
>
> **실제 구현:** `aggregate()`가 `List[AggregatedTransaction]` 대신 `List[dict]`를 반환하도록 변경하면
> 가장 단순하지만 시그니처를 바꾸면 orchestrator와 테스트가 깨진다.
>
> **채택한 접근:** `raw` 목록에서 `apt_master_id → _recent_tx_points` 매핑을 만들어 두고,
> `_to_dict()` 호출 시 orchestrator가 병합한다. 그런데 `_to_dict()`는 static method라서 매핑을
> 전달하기 어렵다.
>
> **최종 결정:** `aggregate()`의 반환 타입을 유지하되, `AggregatedTransaction`에 임시 필드
> `_recent_tx_points`를 dict 형태로 덧붙이는 대신, aggregate()가 `(List[AggregatedTransaction], Dict[int, List[TxPoint]])` 튜플을 반환하고 orchestrator에서 unpack한다. 하지만 이는 orchestrator 변경을 수반한다.
>
> **가장 깔끔한 최종 결정:** `transaction_aggregator.py`의 `aggregate()` 메서드가
> `List[dict]`를 반환하도록 변경한다. dict에는 AggregatedTransaction의 모든 필드 + `_recent_tx_points`가 포함된다. `orchestrator._to_dict()`는 삭제하고, orchestrator에서 직접 dict를 사용한다.
> 이렇게 하면 시그니처 변경이 불가피하므로 orchestrator 테스트도 함께 업데이트한다.

- [ ] **Step 1: 실패하는 테스트 작성 — `_recent_tx_points` 필드 존재 확인**

기존 `test_transaction_aggregator.py` 하단에 새 테스트 클래스를 추가한다.

```python
# tests/modules/real_estate/daily_report/test_transaction_aggregator.py 하단에 추가

class TestRecentTxPoints:
    def test_recent_tx_points_present_in_raw_dict(self, tmp_path):
        """aggregate()가 반환하는 raw dict에 _recent_tx_points가 있어야 한다."""
        db_path = str(tmp_path / "re.db")
        _setup_db(db_path)
        today = date.today().isoformat()
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        with sqlite3.connect(db_path) as conn:
            _insert_apt_master(conn, 1, "스파크단지", "강남구", "CC001")
            _insert_tx(conn, 1, yesterday, 850_000_000)
            _insert_tx(conn, 1, today, 880_000_000)

        agg = TransactionAggregator(db_path=db_path)
        results = agg.aggregate(days=3, top_k=10, persona={}, budget_available=0)

        assert len(results) == 1
        r = results[0]
        assert "_recent_tx_points" in r
        points = r["_recent_tx_points"]
        assert len(points) == 2

    def test_recent_tx_points_sorted_by_date(self, tmp_path):
        db_path = str(tmp_path / "re.db")
        _setup_db(db_path)
        today = date.today().isoformat()
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        with sqlite3.connect(db_path) as conn:
            _insert_apt_master(conn, 1, "정렬단지", "강남구", "CC001")
            _insert_tx(conn, 1, today, 900_000_000)      # 나중에 삽입
            _insert_tx(conn, 1, yesterday, 850_000_000)  # 먼저 발생

        agg = TransactionAggregator(db_path=db_path)
        results = agg.aggregate(days=3, top_k=10, persona={}, budget_available=0)

        points = results[0]["_recent_tx_points"]
        dates = [p["deal_date"] for p in points]
        assert dates == sorted(dates)  # 날짜 오름차순

    def test_recent_tx_points_price_in_eok(self, tmp_path):
        db_path = str(tmp_path / "re.db")
        _setup_db(db_path)
        today = date.today().isoformat()
        with sqlite3.connect(db_path) as conn:
            _insert_apt_master(conn, 1, "가격단지", "강남구", "CC001")
            _insert_tx(conn, 1, today, 880_000_000)

        agg = TransactionAggregator(db_path=db_path)
        results = agg.aggregate(days=3, top_k=10, persona={}, budget_available=0)

        point = results[0]["_recent_tx_points"][0]
        assert abs(point["price_eok"] - 8.8) < 0.01
        assert point["deal_date"] == today
```

> **주의:** 위 테스트에서 `results[0]`은 `dict` (현재는 `AggregatedTransaction` dataclass)다.
> `"_recent_tx_points" in r`이 실패할 것이다 — dataclass에는 해당 필드가 없으므로.

- [ ] **Step 2: 테스트 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/daily_report/test_transaction_aggregator.py::TestRecentTxPoints -v
```

Expected: `TypeError` 또는 `AssertionError` — `AggregatedTransaction` 객체에 `_recent_tx_points` 없음

- [ ] **Step 3: `transaction_aggregator.py` 수정**

`aggregate()`가 `List[dict]`를 반환하도록 변경한다. 기존 `AggregatedTransaction` dataclass는 유지하지만 `aggregate()` 반환 타입이 바뀐다. 기존 테스트들(`TestAggregateBasic`, `TestCompositeScore`, `TestPriceChangePct`)은 `result[0].apt_name` 등 attribute access를 사용하므로 함께 업데이트한다.

**`transaction_aggregator.py` 전체 교체 (변경 부분만 표시):**

```python
# src/modules/real_estate/daily_report/transaction_aggregator.py
import sqlite3
from datetime import date, timedelta
from typing import Dict, List, Optional

from core.logger import get_logger
from .models import AggregatedTransaction

logger = get_logger(__name__)

_AGGREGATE_SQL = """
WITH recent AS (
    SELECT
        t.apt_master_id,
        COUNT(*) AS recent_tx_count,
        AVG(t.price) AS avg_recent_price
    FROM transactions t
    WHERE t.deal_date >= :date_from
      AND t.apt_master_id IS NOT NULL
    GROUP BY t.apt_master_id
),
prior AS (
    SELECT
        apt_master_id,
        AVG(price) AS prior_avg_price
    FROM transactions
    WHERE deal_date >= :date_prior AND deal_date < :date_from
      AND apt_master_id IS NOT NULL
    GROUP BY apt_master_id
),
top_area AS (
    SELECT apt_master_id, exclusive_area
    FROM (
        SELECT apt_master_id, exclusive_area,
               ROW_NUMBER() OVER (PARTITION BY apt_master_id ORDER BY COUNT(*) DESC) AS rn
        FROM transactions
        WHERE deal_date >= :date_from AND apt_master_id IS NOT NULL
        GROUP BY apt_master_id, exclusive_area
    ) WHERE rn = 1
)
SELECT
    am.id                          AS apt_master_id,
    am.apt_name,
    am.district_code,
    am.sigungu,
    am.complex_code,
    r.recent_tx_count,
    r.avg_recent_price,
    COALESCE(
        CASE WHEN p.prior_avg_price > 0
             THEN (r.avg_recent_price - p.prior_avg_price) / p.prior_avg_price * 100.0
             ELSE 0.0 END,
        0.0
    )                              AS price_change_pct,
    COALESCE(ta.exclusive_area, 84.0) AS exclusive_area,
    COALESCE(a.household_count, 0) AS household_count,
    a.road_address,
    am.pnu
FROM recent r
JOIN apt_master am ON r.apt_master_id = am.id
LEFT JOIN prior p ON r.apt_master_id = p.apt_master_id
LEFT JOIN top_area ta ON r.apt_master_id = ta.apt_master_id
LEFT JOIN apartments a ON am.complex_code = a.complex_code
ORDER BY r.recent_tx_count DESC
LIMIT :limit
"""

_RECENT_TX_SQL = """
SELECT price, deal_date
FROM transactions
WHERE apt_master_id = :apt_master_id
  AND deal_date >= :date_from
ORDER BY deal_date ASC
LIMIT 10
"""


class TransactionAggregator:
    """최근 N일 실거래를 집계해 composite_score 상위 K개 단지를 반환한다."""

    def __init__(self, db_path: str = "data/real_estate.db"):
        self._db_path = db_path

    def aggregate(
        self,
        days: int = 3,
        top_k: int = 10,
        persona: Optional[Dict] = None,
        budget_available: int = 0,
    ) -> List[Dict]:
        """반환: List[dict] — AggregatedTransaction 필드 + _recent_tx_points."""
        today = date.today()
        date_from = (today - timedelta(days=days)).isoformat()
        date_prior = (today - timedelta(days=days + 30)).isoformat()

        try:
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                _AGGREGATE_SQL,
                {"date_from": date_from, "date_prior": date_prior, "limit": top_k * 3},
            ).fetchall()
        except sqlite3.Error as e:
            logger.error("[Aggregator] DB 조회 실패: %s", e)
            return []

        if not rows:
            conn.close()
            return []

        raw = [dict(r) for r in rows]

        for item in raw:
            tx_rows = conn.execute(
                _RECENT_TX_SQL,
                {"apt_master_id": item["apt_master_id"], "date_from": date_from},
            ).fetchall()
            item["_recent_tx_points"] = [
                {
                    "price_eok": round(r["price"] / 100_000_000, 2),
                    "deal_date": r["deal_date"],
                }
                for r in tx_rows
            ]
        conn.close()

        max_tx = max(r["recent_tx_count"] for r in raw) or 1
        persona = persona or {}

        for item in raw:
            item["composite_score"] = self._composite_score(
                recent_tx_count=item["recent_tx_count"],
                max_tx_count=max_tx,
                price_change_pct=item["price_change_pct"],
                sigungu=item["sigungu"],
                avg_recent_price=item["avg_recent_price"],
                household_count=item["household_count"],
                persona=persona,
                budget_available=budget_available,
            )

        raw.sort(key=lambda x: x["composite_score"], reverse=True)
        logger.info(
            "[Aggregator] 최근 %d일 거래 집계 완료 — 단지 %d개 → 상위 %d개 선택",
            days, len(raw), top_k,
        )
        return raw[:top_k]

    @staticmethod
    def _composite_score(
        recent_tx_count: int,
        max_tx_count: int,
        price_change_pct: float,
        sigungu: str,
        avg_recent_price: float,
        household_count: int,
        persona: Dict,
        budget_available: int,
        weights: Optional[Dict] = None,
    ) -> float:
        w = weights or {"tx": 0.4, "price": 0.3, "persona": 0.3}
        tx_score = recent_tx_count / max_tx_count if max_tx_count > 0 else 0.0
        price_signal = min(abs(price_change_pct) / 10.0, 1.0)
        interest_areas = persona.get("user", {}).get("interest_areas", [])
        min_hh = persona.get("apartment_preferences", {}).get("min_household_count", 0)
        budget_fit = 1.0
        if budget_available > 0:
            if avg_recent_price <= budget_available:
                budget_fit = 1.0
            else:
                budget_fit = max(0.0, 1.0 - (avg_recent_price - budget_available) / budget_available)
        area_fit = 1.0 if sigungu in interest_areas else 0.5
        household_fit = 1.0 if (min_hh == 0 or household_count >= min_hh) else 0.0
        persona_affinity = (budget_fit + area_fit + household_fit) / 3
        return (
            tx_score * w["tx"]
            + price_signal * w["price"]
            + persona_affinity * w["persona"]
        )
```

- [ ] **Step 4: 기존 테스트 업데이트 — attribute access → dict access**

`test_transaction_aggregator.py`의 기존 테스트들은 `result[0].apt_name` 등 attribute access를 사용한다. `aggregate()`가 `List[dict]`를 반환하므로 `result[0]["apt_name"]` 형태로 수정한다.

`TestAggregateBasic.test_returns_list_of_aggregated_transactions`에서:
```python
# 변경 전
assert isinstance(result[0], AggregatedTransaction)
assert result[0].apt_name == "래미안"
assert result[0].recent_tx_count == 2
# 변경 후
assert isinstance(result[0], dict)
assert result[0]["apt_name"] == "래미안"
assert result[0]["recent_tx_count"] == 2
```

`TestCompositeScore`의 두 테스트에서:
```python
# 변경 전
scores = {r.apt_name: r.composite_score for r in result}
# 변경 후
scores = {r["apt_name"]: r["composite_score"] for r in result}
```

`TestPriceChangePct`의 두 테스트에서:
```python
# 변경 전
assert abs(result[0].price_change_pct - 10.0) < 1.0
assert result[0].price_change_pct == 0.0
# 변경 후
assert abs(result[0]["price_change_pct"] - 10.0) < 1.0
assert result[0]["price_change_pct"] == 0.0
```

- [ ] **Step 5: 전체 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/daily_report/test_transaction_aggregator.py -v
```

Expected: 모든 기존 테스트 + `TestRecentTxPoints` 3개 통과

- [ ] **Step 6: orchestrator._to_dict() 제거 및 호출부 업데이트**

`daily_report_orchestrator.py`에서 `_to_dict()` static method는 더 이상 필요 없다.
`aggregate()` 결과가 이미 dict이므로 `_to_dict(a)` 호출을 `a`로 교체한다.

`daily_report_orchestrator.py`에서:
```python
# 현재 (orchestrator.py line ~114 부근)
aggregated = self._aggregator.aggregate(
    days=days, top_k=top_k * 3, persona=persona, budget_available=budget_available
)
candidates = [self._to_dict(a) for a in aggregated]
```
→
```python
candidates = self._aggregator.aggregate(
    days=days, top_k=top_k * 3, persona=persona, budget_available=budget_available
)
```

그리고 `_to_dict()` static method 전체 삭제 (218~234줄).

또한 `total_transactions` 계산도 수정:
```python
# 변경 전
total_transactions=sum(a.recent_tx_count for a in aggregated),
# 변경 후 (candidates에서 직접)
total_transactions=sum(c.get("recent_tx_count", 0) for c in candidates),
```

- [ ] **Step 7: 커밋**

```bash
git add src/modules/real_estate/daily_report/transaction_aggregator.py \
        src/modules/real_estate/daily_report/daily_report_orchestrator.py \
        tests/modules/real_estate/daily_report/test_transaction_aggregator.py
git commit -m "feat(aggregator): _recent_tx_points 주입 — 건별 거래 날짜·가격 리스트 추가"
```

---

### Task 3: `render_trend()` — SVG 스파크라인

**Files:**
- Modify: `src/modules/real_estate/daily_report/report_formatter.py` (함수 추가)
- Modify: `tests/modules/real_estate/daily_report/test_report_formatter.py` (테스트 추가)

> **배경:** `report_formatter.py`는 현재 `format_macro_summary`, `format_stat_block`,
> `format_dimension_scores`, `build_markdown`으로 구성된다. 이 태스크에서는 새 함수
> `render_trend(trend: TrendData) -> str`만 추가한다. 기존 함수는 아직 건드리지 않는다.

- [ ] **Step 1: 실패하는 테스트 작성**

`test_report_formatter.py` 상단 import에 아래 추가:
```python
from modules.real_estate.daily_report.report_types import TrendData
```

파일 하단에 새 클래스 추가:
```python
class TestRenderTrend:
    def _make_trend(self, prices_eok, dates=None) -> TrendData:
        n = len(prices_eok)
        if dates is None:
            dates = [f"2026-05-{i+1:02d}" for i in range(n)]
        return TrendData(
            points=[{"price_eok": p, "deal_date": d} for p, d in zip(prices_eok, dates)],
            avg_eok=sum(prices_eok) / n,
            change_pct=-5.0,
            area_sqm=84.0,
        )

    def test_render_trend_returns_svg(self):
        from modules.real_estate.daily_report.report_formatter import render_trend
        trend = self._make_trend([8.5, 8.8, 8.3])
        result = render_trend(trend)
        assert "<svg" in result

    def test_render_trend_falling_uses_red(self):
        from modules.real_estate.daily_report.report_formatter import render_trend
        trend = self._make_trend([9.5, 9.0, 8.8])  # 하락
        result = render_trend(trend)
        assert "#f38ba8" in result

    def test_render_trend_rising_uses_green(self):
        from modules.real_estate.daily_report.report_formatter import render_trend
        trend = self._make_trend([8.0, 8.5, 9.0])  # 상승
        result = render_trend(trend)
        assert "#a6e3a1" in result

    def test_render_trend_last_point_has_star(self):
        from modules.real_estate.daily_report.report_formatter import render_trend
        trend = self._make_trend([8.5, 8.8])
        result = render_trend(trend)
        assert "★" in result

    def test_render_trend_empty_points_fallback(self):
        from modules.real_estate.daily_report.report_formatter import render_trend
        trend = TrendData(points=[], avg_eok=0.0, change_pct=0.0, area_sqm=84.0)
        result = render_trend(trend)
        assert "<svg" not in result
        assert "데이터 없음" in result

    def test_render_trend_single_point(self):
        from modules.real_estate.daily_report.report_formatter import render_trend
        trend = self._make_trend([8.8])
        result = render_trend(trend)
        assert "<svg" in result
        assert "★" in result
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/daily_report/test_report_formatter.py::TestRenderTrend -v
```

Expected: `ImportError: cannot import name 'render_trend'`

- [ ] **Step 3: `render_trend()` 구현**

`report_formatter.py` 상단에 추가:
```python
import itertools
from typing import List
from .report_types import TrendData, CommuteData
```

`report_formatter.py`에 함수 추가:
```python
_TREND_COUNTER = itertools.count()


def render_trend(trend: TrendData) -> str:
    points = trend["points"]
    if not points:
        return "**📈 거래 추세** — 데이터 없음"

    uid = next(_TREND_COUNTER)
    avg_eok = trend["avg_eok"]
    change_pct = trend["change_pct"]
    area_sqm = trend["area_sqm"]
    prices = [p["price_eok"] for p in points]
    dates = [p["deal_date"] for p in points]
    n = len(points)

    is_rising = n < 2 or prices[-1] >= prices[0]
    color = "#a6e3a1" if is_rising else "#f38ba8"
    arrow = "▲" if change_pct > 0 else ("▼" if change_pct < 0 else "―")
    change_color = "#a6e3a1" if change_pct >= 0 else "#f38ba8"

    # SVG 좌표 계산
    x_start, x_end = 60, 500
    y_top, y_bottom = 15, 70
    xs = (
        [x_start]
        if n == 1
        else [int(x_start + i * (x_end - x_start) / (n - 1)) for i in range(n)]
    )

    p_min, p_max = min(prices), max(prices)

    def price_to_y(p: float) -> int:
        if p_max == p_min:
            return (y_top + y_bottom) // 2
        return int(y_bottom - (p - p_min) / (p_max - p_min) * (y_bottom - y_top))

    ys = [price_to_y(p) for p in prices]
    high_idx = prices.index(max(prices))

    polyline_pts = " ".join(f"{x},{y}" for x, y in zip(xs, ys))
    polygon_pts = f"{polyline_pts} {xs[-1]},{y_bottom + 5} {xs[0]},{y_bottom + 5}"

    circles = ""
    labels = ""
    for i, (x, y, p) in enumerate(zip(xs, ys, prices)):
        is_last = i == n - 1
        is_high = i == high_idx and n > 1

        if is_last:
            fill, stroke, r = "#89b4fa", "#89b4fa", 6
            label_color, label_text = "#89b4fa", f"{p:.1f}억 ★"
        elif is_high:
            fill, stroke, r = color, color, 5
            label_color, label_text = color, f"{p:.1f}억 ↑"
        else:
            fill, stroke, r = "#1e1e2e", color, 4
            label_color, label_text = "#a6adc8", f"{p:.1f}억"

        circles += (
            f'<circle cx="{x}" cy="{y}" r="{r}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="2"/>\n'
        )
        labels += (
            f'<text x="{x}" y="{y - 8}" text-anchor="middle" '
            f'fill="{label_color}" font-size="10" font-family="system-ui" '
            f'font-weight="600">{label_text}</text>\n'
        )

    # Y축 레이블
    mid_price = (p_max + p_min) / 2
    y_mid = (y_top + y_bottom) // 2
    y_labels = (
        f'<text x="555" y="18" text-anchor="end" fill="#6c7086" font-size="9" font-family="system-ui">{p_max:.1f}억</text>\n'
        f'<text x="555" y="{y_mid + 3}" text-anchor="end" fill="#6c7086" font-size="9" font-family="system-ui">{mid_price:.1f}억</text>\n'
        f'<text x="555" y="{y_bottom}" text-anchor="end" fill="#6c7086" font-size="9" font-family="system-ui">{p_min:.1f}억</text>\n'
    ) if p_max != p_min else ""

    # 날짜 레이블 (MM-DD 형식)
    date_items = "".join(
        f'<span style="flex:1;text-align:center">{d[5:]}</span>' for d in dates
    )
    date_labels = (
        f'<div style="display:flex;font-size:10px;color:#6c7086;'
        f'margin-top:4px;padding:0 50px">{date_items}</div>'
    )

    # 헤더 텍스트
    date_range_str = f"{dates[0][5:]} ~ {dates[-1][5:]}" if n > 1 else dates[0][5:]

    return (
        f'<div style="background:#181825;border-radius:10px;padding:12px 14px;margin-bottom:12px">\n'
        f'  <div style="display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:8px">\n'
        f'    <div>\n'
        f'      <div style="font-size:10px;text-transform:uppercase;letter-spacing:.07em;color:#6c7086">📈 최근 실거래 추세 ({n}건)</div>\n'
        f'      <div style="font-size:11px;color:#585b70;margin-top:2px">{date_range_str} · {area_sqm:.0f}㎡</div>\n'
        f'    </div>\n'
        f'    <div style="text-align:right">\n'
        f'      <div style="font-size:18px;font-weight:800;color:#cdd6f4">{avg_eok:.1f}억</div>\n'
        f'      <div style="font-size:12px;font-weight:700;color:{change_color}">{arrow} {abs(change_pct):.1f}% 전월比</div>\n'
        f'    </div>\n'
        f'  </div>\n'
        f'  <svg viewBox="0 0 560 90" xmlns="http://www.w3.org/2000/svg" style="display:block;width:100%">\n'
        f'    <defs>\n'
        f'      <linearGradient id="grad{uid}" x1="0" y1="0" x2="0" y2="1">\n'
        f'        <stop offset="0%" stop-color="{color}" stop-opacity="0.25"/>\n'
        f'        <stop offset="100%" stop-color="{color}" stop-opacity="0"/>\n'
        f'      </linearGradient>\n'
        f'    </defs>\n'
        f'    <line x1="0" y1="22" x2="560" y2="22" stroke="#313244" stroke-width="1" stroke-dasharray="4,4"/>\n'
        f'    <line x1="0" y1="45" x2="560" y2="45" stroke="#313244" stroke-width="1" stroke-dasharray="4,4"/>\n'
        f'    <line x1="0" y1="68" x2="560" y2="68" stroke="#313244" stroke-width="1" stroke-dasharray="4,4"/>\n'
        f'    {y_labels}'
        f'    <polygon points="{polygon_pts}" fill="url(#grad{uid})"/>\n'
        f'    <polyline points="{polyline_pts}" fill="none" stroke="{color}" '
        f'stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>\n'
        f'    {circles}'
        f'    {labels}'
        f'  </svg>\n'
        f'  {date_labels}\n'
        f'</div>'
    )
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/daily_report/test_report_formatter.py::TestRenderTrend -v
```

Expected: 6 passed

- [ ] **Step 5: 커밋**

```bash
git add src/modules/real_estate/daily_report/report_formatter.py \
        tests/modules/real_estate/daily_report/test_report_formatter.py
git commit -m "feat(formatter): render_trend() — SVG 스파크라인 (상승=초록, 하락=빨강, 최신=★)"
```

---

### Task 4: `render_commute()` / `render_scores()` / `render_verdict()` / `render_keypoints()`

**Files:**
- Modify: `src/modules/real_estate/daily_report/report_formatter.py` (함수 추가)
- Modify: `tests/modules/real_estate/daily_report/test_report_formatter.py` (테스트 추가)

- [ ] **Step 1: 실패하는 테스트 작성**

`test_report_formatter.py`에 클래스 추가:

```python
class TestRenderCommute:
    def _make_commute(self, transit=None, car=None, walk=None, route="") -> "CommuteData":
        from modules.real_estate.daily_report.report_types import CommuteData
        return CommuteData(
            transit_minutes=transit, car_minutes=car,
            walk_minutes=walk, route_summary=route,
        )

    def test_all_modes_present(self):
        from modules.real_estate.daily_report.report_formatter import render_commute
        result = render_commute(self._make_commute(transit=35, car=20, walk=90))
        assert "35분" in result
        assert "20분" in result
        assert "90분" in result

    def test_none_mode_shows_unavailable(self):
        from modules.real_estate.daily_report.report_formatter import render_commute
        result = render_commute(self._make_commute(transit=35, car=None, walk=None))
        assert "35분" in result
        assert result.count("조회 불가") == 2

    def test_all_none_shows_three_unavailable(self):
        from modules.real_estate.daily_report.report_formatter import render_commute
        result = render_commute(self._make_commute())
        assert result.count("조회 불가") == 3

    def test_route_summary_shown_when_present(self):
        from modules.real_estate.daily_report.report_formatter import render_commute
        result = render_commute(self._make_commute(transit=35, route="2호선 30분"))
        assert "2호선 30분" in result


class TestRenderScores:
    def test_renders_residential_and_investment(self):
        from modules.real_estate.daily_report.report_formatter import render_scores
        from modules.real_estate.location.dimension_result import DimensionResult
        res = [DimensionResult(id="transportation", label="🚇 교통", score=80, evidence=["22분"])]
        inv = [DimensionResult(id="commercial", label="🛍️ 상업", score=60, evidence=["음식점 15개"])]
        result = render_scores(res, inv)
        assert "🚇 교통" in result
        assert "80점" in result
        assert "🛍️ 상업" in result
        assert "음식점 15개" in result

    def test_empty_lists_returns_empty(self):
        from modules.real_estate.daily_report.report_formatter import render_scores
        assert render_scores([], []) == ""

    def test_unknown_dimension_id_still_renders(self):
        from modules.real_estate.daily_report.report_formatter import render_scores
        from modules.real_estate.location.dimension_result import DimensionResult
        res = [DimensionResult(id="mystery", label="🔮 미지의차원", score=99, evidence=["비밀"])]
        result = render_scores(res, [])
        assert "🔮 미지의차원" in result
        assert "99점" in result


class TestRenderVerdictKeypoints:
    def test_render_verdict_with_text(self):
        from modules.real_estate.daily_report.report_formatter import render_verdict
        result = render_verdict("관망 — 하락 추세 중")
        assert "관망" in result
        assert "🔍" in result

    def test_render_verdict_empty_returns_empty(self):
        from modules.real_estate.daily_report.report_formatter import render_verdict
        assert render_verdict("") == ""

    def test_render_keypoints_with_items(self):
        from modules.real_estate.daily_report.report_formatter import render_keypoints
        result = render_keypoints(["✅ 역세권", "📉 하락 추세"])
        assert "✅ 역세권" in result
        assert "📉 하락 추세" in result

    def test_render_keypoints_empty_returns_empty(self):
        from modules.real_estate.daily_report.report_formatter import render_keypoints
        assert render_keypoints([]) == ""
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/daily_report/test_report_formatter.py::TestRenderCommute tests/modules/real_estate/daily_report/test_report_formatter.py::TestRenderScores tests/modules/real_estate/daily_report/test_report_formatter.py::TestRenderVerdictKeypoints -v
```

Expected: `ImportError: cannot import name 'render_commute'` 등

- [ ] **Step 3: 4개 함수 구현**

`report_formatter.py`에 추가:

```python
def render_commute(commute: CommuteData) -> str:
    def fmt(minutes: Optional[int]) -> str:
        return f"{minutes}분" if minutes is not None else "조회 불가"

    transit_str = fmt(commute["transit_minutes"])
    car_str = fmt(commute["car_minutes"])
    walk_str = fmt(commute["walk_minutes"])
    route = commute.get("route_summary", "")

    lines = [
        "**🚌 출퇴근**",
        f"| 대중교통 | 자차 | 도보 |",
        f"|:---:|:---:|:---:|",
        f"| {transit_str} | {car_str} | {walk_str} |",
    ]
    if route:
        lines.append(f"*{route}*")
    return "\n".join(lines)


def render_scores(residential: List, investment: List) -> str:
    if not residential and not investment:
        return ""
    lines = ["**실거주 점수 분석**"]
    for dr in residential:
        lines.append(f"- {dr.label}: **{dr.score}점**")
        for sub in dr.evidence:
            lines.append(f"  - {sub}")
    lines += ["", "**투자성 점수 분석**"]
    for dr in investment:
        lines.append(f"- {dr.label}: **{dr.score}점**")
        for sub in dr.evidence:
            lines.append(f"  - {sub}")
    return "\n".join(lines)


def render_verdict(verdict: str) -> str:
    if not verdict:
        return ""
    return f"> 🔍 **오늘의 판단:** {verdict}"


def render_keypoints(key_points: List[str]) -> str:
    if not key_points:
        return ""
    lines = ["**주목할 점**"]
    lines.extend(f"- {kp}" for kp in key_points)
    return "\n".join(lines)
```

`report_formatter.py` 상단 import에 `Optional` 추가:
```python
from typing import Dict, List, Optional
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/daily_report/test_report_formatter.py -v
```

Expected: 모든 테스트 통과 (기존 + 신규)

- [ ] **Step 5: 커밋**

```bash
git add src/modules/real_estate/daily_report/report_formatter.py \
        tests/modules/real_estate/daily_report/test_report_formatter.py
git commit -m "feat(formatter): render_commute/scores/verdict/keypoints — TypedDict 기반 텍스트 렌더러"
```

---

### Task 5: `build_candidate_card()` + `_extract_*` + `build_markdown()` 업데이트

**Files:**
- Modify: `src/modules/real_estate/daily_report/report_formatter.py`
- Modify: `src/dashboard/views/real_estate.py` (1줄)
- Modify: `tests/modules/real_estate/daily_report/test_report_formatter.py`

> **이 태스크에서 삭제:** `format_stat_block()`, `format_dimension_scores()`, `<!-- stats -->` 태그.
> `build_markdown()`은 시그니처를 유지하되 `build_candidate_card()` 호출로 내부 루프 단순화.

- [ ] **Step 1: 실패하는 테스트 작성**

`test_report_formatter.py`에서 아래를 제거:
- `test_format_stat_block_basic`
- `test_format_stat_block_negative_change`
- `test_format_dimension_scores_renders_all_dims`
- `test_format_dimension_scores_empty_when_no_score`
- `test_format_dimension_scores_evidence_indented`
- `test_format_dimension_scores_no_hardcoded_dimension_ids`
- `test_build_markdown_contains_sections`

아래 새 테스트로 교체:

```python
class TestBuildCandidateCard:
    def _make_candidate(self) -> dict:
        from modules.real_estate.location.dimension_result import DimensionResult
        from modules.real_estate.location.location_scorer import LocationScore
        return {
            "apt_name": "래미안",
            "sigungu": "강남구",
            "exclusive_area": 84.0,
            "household_count": 1200,
            "composite_score": 0.85,
            "avg_recent_price": 280_000_000,
            "price_change_pct": 2.5,
            "_recent_tx_points": [
                {"price_eok": 2.7, "deal_date": "2026-05-07"},
                {"price_eok": 2.8, "deal_date": "2026-05-10"},
            ],
            "commute_transit_minutes": 35,
            "commute_car_minutes": 20,
            "commute_walk_minutes": None,
            "_commute_route_summary": "2호선 30분",
            "_location_score": LocationScore(
                complex_code="CC001",
                residential_total=75,
                residential_results=[
                    DimensionResult(id="transportation", label="🚇 교통", score=80,
                                    evidence=["대중교통 22분"]),
                ],
                investment_total=65,
                investment_results=[
                    DimensionResult(id="commercial", label="🛍️ 상업", score=60,
                                    evidence=["음식점 15개"]),
                ],
                scored_at="2026-05-10T00:00:00+00:00",
            ),
            "_verdict": "매수 검토 — 역세권 우수",
            "_key_points": ["✅ 역세권", "📈 상승 추세"],
        }

    def test_build_candidate_card_contains_name(self):
        from modules.real_estate.daily_report.report_formatter import build_candidate_card
        result = build_candidate_card(self._make_candidate())
        assert "래미안" in result

    def test_build_candidate_card_contains_svg(self):
        from modules.real_estate.daily_report.report_formatter import build_candidate_card
        result = build_candidate_card(self._make_candidate())
        assert "<svg" in result

    def test_build_candidate_card_contains_commute(self):
        from modules.real_estate.daily_report.report_formatter import build_candidate_card
        result = build_candidate_card(self._make_candidate())
        assert "35분" in result  # transit
        assert "20분" in result  # car
        assert "조회 불가" in result  # walk is None

    def test_build_candidate_card_contains_verdict(self):
        from modules.real_estate.daily_report.report_formatter import build_candidate_card
        result = build_candidate_card(self._make_candidate())
        assert "매수 검토" in result

    def test_build_candidate_card_contains_keypoints(self):
        from modules.real_estate.daily_report.report_formatter import build_candidate_card
        result = build_candidate_card(self._make_candidate())
        assert "✅ 역세권" in result

    def test_build_candidate_card_no_stats_tag(self):
        from modules.real_estate.daily_report.report_formatter import build_candidate_card
        result = build_candidate_card(self._make_candidate())
        assert "<!-- stats -->" not in result


class TestBuildMarkdown:
    def test_build_markdown_structure(self):
        from modules.real_estate.daily_report.report_formatter import build_markdown
        from modules.real_estate.location.dimension_result import DimensionResult
        from modules.real_estate.location.location_scorer import LocationScore
        candidates = [{
            "apt_name": "래미안", "sigungu": "강남구",
            "exclusive_area": 84.0, "household_count": 1200,
            "composite_score": 0.85, "avg_recent_price": 280_000_000,
            "price_change_pct": 2.5, "_recent_tx_points": [],
            "commute_transit_minutes": None, "commute_car_minutes": None,
            "commute_walk_minutes": None, "_commute_route_summary": "",
            "_location_score": None, "_verdict": "관망", "_key_points": [],
        }]
        md = build_markdown(
            date_str="2026-05-10",
            date_range="2026-05-07 ~ 2026-05-10",
            macro_summary="기준금리: 3.5%",
            market_summary="강남권 거래 활발",
            candidates=candidates,
            insights_map={},
        )
        assert "데일리 부동산 브리핑" in md
        assert "래미안" in md
        assert "<!-- stats -->" not in md
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/daily_report/test_report_formatter.py::TestBuildCandidateCard tests/modules/real_estate/daily_report/test_report_formatter.py::TestBuildMarkdown -v
```

Expected: `ImportError: cannot import name 'build_candidate_card'`

- [ ] **Step 3: `report_formatter.py` 재작성**

`format_stat_block()`, `format_dimension_scores()` 삭제.
`build_markdown()` 수정.
`_extract_trend()`, `_extract_commute()`, `_render_header()`, `build_candidate_card()` 추가.

```python
def _extract_trend(c: dict) -> TrendData:
    return TrendData(
        points=c.get("_recent_tx_points", []),
        avg_eok=round(c.get("avg_recent_price", 0) / 100_000_000, 2),
        change_pct=c.get("price_change_pct", 0.0),
        area_sqm=c.get("exclusive_area", 84.0),
    )


def _extract_commute(c: dict) -> CommuteData:
    return CommuteData(
        transit_minutes=c.get("commute_transit_minutes"),
        car_minutes=c.get("commute_car_minutes"),
        walk_minutes=c.get("commute_walk_minutes"),
        route_summary=c.get("_commute_route_summary", ""),
    )


def _render_header(c: dict, index: int) -> str:
    name = c.get("apt_name", "?")
    score_pct = int(c.get("composite_score", 0) * 100)
    sigungu = c.get("sigungu", "")
    area = c.get("exclusive_area", 84)
    households = c.get("household_count", 0)
    return (
        f"### {index}. {name} — 종합 {score_pct}점\n\n"
        f"📍 {sigungu} · {area:.0f}㎡ · {households}세대"
    )


def build_candidate_card(c: dict, index: int = 0) -> str:
    trend = _extract_trend(c)
    commute = _extract_commute(c)
    ls = c.get("_location_score")

    parts = [
        _render_header(c, index),
        render_trend(trend),
        render_commute(commute),
        render_scores(ls.residential_results, ls.investment_results) if ls else "",
        render_verdict(c.get("_verdict", "")),
        render_keypoints(c.get("_key_points", [])),
    ]
    return "\n\n".join(p for p in parts if p)


def build_markdown(
    date_str: str,
    date_range: str,
    macro_summary: str,
    market_summary: str,
    candidates: List[Dict],
    insights_map: Dict[str, Dict],
) -> str:
    lines = [
        f"# 데일리 부동산 브리핑 — {date_str}",
        "",
        f"**분석 기간:** {date_range} | **주목 단지:** {len(candidates)}개",
        "",
        "---",
        "",
        "## 거시경제 현황",
        *format_macro_summary(macro_summary),
        "",
        "---",
        "",
        "## 오늘의 시장 신호",
        market_summary or "분석 데이터 부족",
        "",
        "---",
        "",
        "## 주목 단지 분석",
        "",
    ]

    for i, c in enumerate(candidates, 1):
        # LLM insights를 candidate dict에 병합 (orchestrator가 주입했으면 이미 있음)
        lines.append(build_candidate_card(c, index=i))
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)
```

- [ ] **Step 4: 대시보드 `unsafe_allow_html=True` 패치**

`src/dashboard/views/real_estate.py:1080`:
```python
# 변경 전
            st.markdown(markdown)
# 변경 후
            st.markdown(markdown, unsafe_allow_html=True)
```

- [ ] **Step 5: 전체 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/daily_report/test_report_formatter.py -v
```

Expected: 모든 테스트 통과

- [ ] **Step 6: 커밋**

```bash
git add src/modules/real_estate/daily_report/report_formatter.py \
        src/dashboard/views/real_estate.py \
        tests/modules/real_estate/daily_report/test_report_formatter.py
git commit -m "feat(formatter): build_candidate_card() — dict→TypedDict 추출 경계, build_markdown 단순화"
```

---

### Task 6: `build_slack()` — Slack mrkdwn 조립

**Files:**
- Modify: `src/modules/real_estate/daily_report/report_formatter.py`
- Modify: `tests/modules/real_estate/daily_report/test_report_formatter.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
class TestBuildSlack:
    def _make_candidate(self, transit=35, car=20):
        return {
            "apt_name": "래미안", "sigungu": "강남구",
            "composite_score": 0.85,
            "_recent_tx_points": [
                {"price_eok": 8.5, "deal_date": "2026-05-07"},
                {"price_eok": 8.8, "deal_date": "2026-05-10"},
            ],
            "avg_recent_price": 880_000_000,
            "price_change_pct": 3.5,
            "exclusive_area": 84.0,
            "commute_transit_minutes": transit,
            "commute_car_minutes": car,
            "commute_walk_minutes": None,
            "_commute_route_summary": "",
            "_verdict": "매수 검토",
            "_key_points": ["✅ 역세권"],
            "_location_score": None,
        }

    def test_build_slack_contains_apt_name(self):
        from modules.real_estate.daily_report.report_formatter import build_slack
        result = build_slack([self._make_candidate()])
        assert "래미안" in result

    def test_build_slack_no_svg(self):
        from modules.real_estate.daily_report.report_formatter import build_slack
        result = build_slack([self._make_candidate()])
        assert "<svg" not in result

    def test_build_slack_has_text_sparkline(self):
        from modules.real_estate.daily_report.report_formatter import build_slack
        result = build_slack([self._make_candidate()])
        # 유니코드 블록 문자 중 하나 이상 포함
        spark_chars = set("▁▂▃▄▅▆▇█")
        assert any(ch in result for ch in spark_chars)

    def test_build_slack_transit_shown(self):
        from modules.real_estate.daily_report.report_formatter import build_slack
        result = build_slack([self._make_candidate(transit=35)])
        assert "35분" in result

    def test_build_slack_none_transit_shows_unavailable(self):
        from modules.real_estate.daily_report.report_formatter import build_slack
        result = build_slack([self._make_candidate(transit=None)])
        assert "조회불가" in result or "조회 불가" in result

    def test_build_slack_multiple_candidates_separated(self):
        from modules.real_estate.daily_report.report_formatter import build_slack
        c1 = self._make_candidate()
        c2 = {**self._make_candidate(), "apt_name": "힐스테이트"}
        result = build_slack([c1, c2])
        assert "래미안" in result
        assert "힐스테이트" in result
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/daily_report/test_report_formatter.py::TestBuildSlack -v
```

Expected: `ImportError: cannot import name 'build_slack'`

- [ ] **Step 3: `build_slack()` 구현**

`report_formatter.py`에 추가:

```python
_SPARK_CHARS = "▁▂▃▄▅▆▇█"


def _text_sparkline(points: List) -> str:
    if not points:
        return ""
    prices = [p["price_eok"] for p in points]
    p_min, p_max = min(prices), max(prices)
    if p_max == p_min:
        return "▄" * len(prices)
    return "".join(
        _SPARK_CHARS[int((p - p_min) / (p_max - p_min) * 7)]
        for p in prices
    )


def _slack_candidate_block(c: dict) -> str:
    trend = _extract_trend(c)
    commute = _extract_commute(c)

    name = c.get("apt_name", "?")
    score_pct = int(c.get("composite_score", 0) * 100)
    verdict = c.get("_verdict", "")
    key_points = c.get("_key_points", [])

    spark = _text_sparkline(trend["points"])
    avg = trend["avg_eok"]
    chg = trend["change_pct"]
    arrow = "▲" if chg > 0 else ("▼" if chg < 0 else "―")

    transit = commute["transit_minutes"]
    car = commute["car_minutes"]
    transit_str = f"🚌 {transit}분" if transit is not None else "🚌 조회불가"
    car_str = f" | 🚗 {car}분" if car is not None else ""

    lines = [
        f"*{name}* — 종합 {score_pct}점",
        f"💰 {avg:.1f}억 {arrow} {abs(chg):.1f}% {spark}",
        f"{transit_str}{car_str}",
    ]
    if verdict:
        lines.append(f"🔍 {verdict}")
    lines.extend(f"• {kp}" for kp in key_points[:3])
    return "\n".join(lines)


def build_slack(candidates: List[Dict]) -> str:
    blocks = [_slack_candidate_block(c) for c in candidates]
    return "\n\n---\n\n".join(blocks)
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/daily_report/test_report_formatter.py -v
```

Expected: 모든 테스트 통과

- [ ] **Step 5: 커밋**

```bash
git add src/modules/real_estate/daily_report/report_formatter.py \
        tests/modules/real_estate/daily_report/test_report_formatter.py
git commit -m "feat(formatter): build_slack() — Slack mrkdwn 조립, 텍스트 스파크라인"
```

---

### Task 7: Orchestrator — car/walking 3모드 + `_verdict`/`_key_points` 주입

**Files:**
- Modify: `src/modules/real_estate/daily_report/daily_report_orchestrator.py`
- Modify: `src/modules/real_estate/prompts/daily_strategy.md`
- Modify: `tests/modules/real_estate/daily_report/test_daily_report_orchestrator.py`

> **배경:** 현재 `_enrich_with_commute_quota()`는 `mode="transit"`만 호출한다.
> car/walking도 추가해야 한다. 또한 LLM 결과에서 `verdict`와 `key_points`를
> candidate dict에 `_verdict`, `_key_points` 키로 주입해야 한다.
> `mode="walking"` → dict 키는 `commute_walk_minutes` (service.py 기존 관행 일치).

- [ ] **Step 1: 기존 orchestrator 테스트 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/daily_report/test_daily_report_orchestrator.py -v
```

현재 테스트가 통과하는지 확인 (실패 시 먼저 수정).

- [ ] **Step 2: 실패하는 테스트 작성**

`test_daily_report_orchestrator.py`에서 `_enrich_with_commute_quota` 관련 섹션을 찾아 아래 테스트 추가:

```python
class TestEnrichCommuteAllModes:
    def _make_svc_with_cache(self, transit_min, car_min, walk_min):
        """transit/car/walking 캐시 결과를 반환하는 mock CommuteService."""
        from unittest.mock import MagicMock
        from modules.real_estate.commute.models import CommuteResult

        def make_result(mode, minutes):
            return CommuteResult(
                origin_key="test__단지A", destination="삼성역",
                mode=mode, duration_minutes=minutes, distance_meters=10000,
                cached=True, route_summary=f"{mode} 경로",
            )

        svc = MagicMock()
        cache_map = {
            "transit": make_result("transit", transit_min) if transit_min else None,
            "car": make_result("car", car_min) if car_min else None,
            "walking": make_result("walking", walk_min) if walk_min else None,
        }
        svc.get_cached.side_effect = lambda origin_key, dest, mode: cache_map.get(mode)
        return svc

    def test_transit_car_walk_all_enriched_from_cache(self, tmp_path):
        """캐시에 3모드 모두 있으면 candidate dict에 3개 키가 채워진다."""
        from modules.real_estate.daily_report.daily_report_orchestrator import DailyReportOrchestrator

        svc = self._make_svc_with_cache(35, 20, 90)
        orch = DailyReportOrchestrator.__new__(DailyReportOrchestrator)
        orch._commute_svc = svc
        orch._max_new_commute_api_calls = 0

        candidates = [{
            "apt_name": "단지A", "district_code": "test",
            "road_address": "서울 강남구",
        }]
        result = orch._enrich_with_commute_quota(
            candidates, dest="삼성역", dest_lat=37.5, dest_lng=127.0, max_new_calls=0
        )

        assert result[0].get("commute_transit_minutes") == 35
        assert result[0].get("commute_car_minutes") == 20
        assert result[0].get("commute_walk_minutes") == 90

    def test_missing_road_address_skips_candidate(self, tmp_path):
        from modules.real_estate.daily_report.daily_report_orchestrator import DailyReportOrchestrator

        svc = self._make_svc_with_cache(35, 20, 90)
        orch = DailyReportOrchestrator.__new__(DailyReportOrchestrator)
        orch._commute_svc = svc
        orch._max_new_commute_api_calls = 0

        candidates = [{"apt_name": "단지B", "district_code": "test", "road_address": ""}]
        result = orch._enrich_with_commute_quota(
            candidates, dest="삼성역", dest_lat=37.5, dest_lng=127.0, max_new_calls=0
        )

        assert result[0].get("commute_transit_minutes") is None
        assert result[0].get("commute_car_minutes") is None
```

- [ ] **Step 3: 테스트 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/daily_report/test_daily_report_orchestrator.py::TestEnrichCommuteAllModes -v
```

Expected: FAIL — `commute_car_minutes`와 `commute_walk_minutes`가 None

- [ ] **Step 4: `_enrich_with_commute_quota()` 수정**

`daily_report_orchestrator.py`의 `_enrich_with_commute_quota()` 전체 교체:

```python
_MODE_TO_KEY = {"transit": "transit", "car": "car", "walking": "walk"}

def _enrich_with_commute_quota(
    self,
    candidates: List[Dict],
    dest: Optional[str],
    dest_lat: Optional[float],
    dest_lng: Optional[float],
    max_new_calls: int,
) -> List[Dict]:
    """transit/car/walking 3모드 출퇴근 시간을 candidate dict에 주입. 신규 API 호출은 단지 단위 quota."""
    if not self._commute_svc or dest is None:
        return candidates

    new_calls_used = 0
    enriched = []
    for c in candidates:
        result = dict(c)
        road_address = c.get("road_address") or ""
        if not road_address:
            enriched.append(result)
            continue

        apt_name = c.get("apt_name", "")
        district_code = c.get("district_code", "")
        origin_key = f"{district_code}__{apt_name}"

        # 캐시에서 3모드 모두 시도
        need_api_call = False
        for mode in ("transit", "car", "walking"):
            key = f"commute_{_MODE_TO_KEY[mode]}_minutes"
            cached = self._commute_svc.get_cached(origin_key, dest, mode)
            if cached is not None:
                result[key] = cached.duration_minutes
                if mode == "transit":
                    result["_commute_route_summary"] = cached.route_summary
                logger.debug("[DailyOrchestrator] 캐시 히트 (%s): %s", mode, apt_name)
            else:
                need_api_call = True

        # 캐시 미스 + quota 여유 시 API 호출 (단지 단위 1 소진)
        if need_api_call and new_calls_used < max_new_calls:
            for mode in ("transit", "car", "walking"):
                key = f"commute_{_MODE_TO_KEY[mode]}_minutes"
                if result.get(key) is not None:
                    continue  # 이미 캐시에서 채워짐
                try:
                    cr = self._commute_svc.get(
                        origin_key=origin_key,
                        road_address=road_address,
                        apt_name=apt_name,
                        district_code=district_code,
                        mode=mode,
                        dest_override=dest,
                        dest_lat_override=dest_lat,
                        dest_lng_override=dest_lng,
                    )
                    if cr:
                        result[key] = cr.duration_minutes
                        if mode == "transit":
                            result["_commute_route_summary"] = cr.route_summary
                except Exception as e:
                    logger.warning("[DailyOrchestrator] %s 실패 %s: %s", mode, apt_name, e)
            new_calls_used += 1
            logger.info(
                "[DailyOrchestrator] 출퇴근 API 호출 %d/%d: %s",
                new_calls_used, max_new_calls, apt_name,
            )
        elif need_api_call:
            logger.info(
                "[DailyOrchestrator] 출퇴근 quota 소진 (%d/%d), 스킵: %s",
                new_calls_used, max_new_calls, apt_name,
            )

        enriched.append(result)
    return enriched
```

- [ ] **Step 5: `_verdict`/`_key_points` 주입 추가**

`generate()` 메서드에서 insights_map 처리 직후 (현재 line ~187):

```python
# 기존
insights_map = {i.get("apt_name", ""): i for i in candidate_insights}

# 추가: _verdict, _key_points 주입
for c in candidates:
    name = c.get("apt_name", "")
    ins = insights_map.get(name, {})
    c["_verdict"] = ins.get("verdict", "")
    c["_key_points"] = ins.get("key_points", [])
```

- [ ] **Step 6: `daily_strategy.md` 프롬프트 업데이트**

`src/modules/real_estate/prompts/daily_strategy.md`의 JSON 응답 형식에 `verdict`와 `key_points` 추가:

```json
      "verdict": "관망 — 하락 추세 중, 역세권 없어 삼성역 출퇴근 부적합 (한 줄, 50자 이내)",
      "key_points": [
        "📉 구체적 수치 포함한 핵심 리스크 또는 기회",
        "✅ 강점 또는 주목할 긍정 요소",
        "❌ 주의해야 할 결정적 약점"
      ],
```

`strategy_bullets` 앞에 삽입. 그리고 주의사항에 추가:
```
- verdict는 반드시 50자 이내 한 문장으로 작성하세요.
- key_points는 2~3개, 이모지로 시작하고 구체적 수치를 포함하세요.
```

- [ ] **Step 7: 전체 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/daily_report/ -v
```

Expected: 모든 테스트 통과

- [ ] **Step 8: 커밋**

```bash
git add src/modules/real_estate/daily_report/daily_report_orchestrator.py \
        src/modules/real_estate/prompts/daily_strategy.md \
        tests/modules/real_estate/daily_report/test_daily_report_orchestrator.py
git commit -m "feat(orchestrator): car/walking 출퇴근 3모드 + _verdict/_key_points LLM 주입"
```
