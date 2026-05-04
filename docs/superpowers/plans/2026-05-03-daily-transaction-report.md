# 데일리 실거래 기반 부동산 전략 리포트 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 최근 3일 실거래가를 기반으로 주목 단지 5~10개를 선별·풀분석하여 매일 아침 Slack으로 전송하고 Streamlit에 보관하는 데일리 부동산 전략 리포트를 구축한다.

**Architecture:** `TransactionAggregator`가 최근 N일 거래를 SQL로 집계·스코어링해 상위 K개를 반환하면, `DailyReportOrchestrator`가 기존 enrich 함수(geocode→POI→building→commute→trend)를 순서대로 적용한 뒤 LLM이 시장 총평과 단지별 전략 코멘트를 생성한다. 결과는 `data/daily_reports/daily_YYYY-MM-DD.md`로 저장되고 `SlackSender`로 전문 전송된다.

**Tech Stack:** Python 3.12, SQLite (real_estate.db), pytest, FastAPI, Streamlit, SlackSender (src/core/notify/slack.py)

---

## 파일 변경 범위

| 파일 | 역할 |
|------|------|
| `src/modules/real_estate/daily_report/__init__.py` | 패키지 초기화 |
| `src/modules/real_estate/daily_report/models.py` | AggregatedTransaction, DailyReport 데이터클래스 |
| `src/modules/real_estate/daily_report/transaction_aggregator.py` | 최근 N일 거래 SQL 집계 + composite score |
| `src/modules/real_estate/daily_report/daily_report_repository.py` | data/daily_reports/ MD 파일 저장/조회 |
| `src/modules/real_estate/daily_report/daily_report_orchestrator.py` | 파이프라인 오케스트레이터 |
| `src/modules/real_estate/prompts/daily_strategy.md` | LLM 프롬프트 |
| `src/modules/real_estate/config.yaml` | daily_report 섹션 추가 |
| `src/api/routers/real_estate.py` | POST /jobs/daily-report/generate 추가 |
| `src/dashboard/views/real_estate.py` | 📰 데일리 리포트 탭 추가 |
| `tests/modules/real_estate/daily_report/test_transaction_aggregator.py` | 신규 |
| `tests/modules/real_estate/daily_report/test_daily_report_orchestrator.py` | 신규 |
| `tests/modules/real_estate/daily_report/__init__.py` | 신규 |

---

## Task 1: Models

**Files:**
- Create: `src/modules/real_estate/daily_report/__init__.py`
- Create: `src/modules/real_estate/daily_report/models.py`

- [ ] **Step 1: 패키지 생성**

```bash
mkdir -p src/modules/real_estate/daily_report
touch src/modules/real_estate/daily_report/__init__.py
```

- [ ] **Step 2: models.py 작성**

`src/modules/real_estate/daily_report/models.py` 를 아래 내용으로 생성:

```python
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class AggregatedTransaction:
    apt_master_id: int
    apt_name: str
    district_code: str
    sigungu: str
    complex_code: Optional[str]
    recent_tx_count: int
    avg_recent_price: float        # 만원 단위
    price_change_pct: float        # 직전 30일 대비 변동률 (%)
    exclusive_area: float          # 가장 많이 거래된 면적 (㎡)
    household_count: int
    composite_score: float         # 0.0 ~ 1.0


@dataclass
class DailyReport:
    date: str                      # YYYY-MM-DD
    analysis_period: str           # "2026-05-01 ~ 2026-05-03"
    total_transactions: int
    top_k: int
    macro_summary: str
    market_summary: str            # LLM 생성 시장 총평
    candidates: List[dict]         # enrich 완료 단지 목록 (직렬화 가능)
    markdown: str                  # 최종 렌더링 MD
    generated_at: str
```

- [ ] **Step 3: 커밋**

```bash
git add src/modules/real_estate/daily_report/__init__.py \
        src/modules/real_estate/daily_report/models.py
git commit -m "feat(daily-report): models 추가 — AggregatedTransaction, DailyReport"
```

---

## Task 2: TransactionAggregator (TDD)

**Files:**
- Create: `src/modules/real_estate/daily_report/transaction_aggregator.py`
- Create: `tests/modules/real_estate/daily_report/__init__.py`
- Create: `tests/modules/real_estate/daily_report/test_transaction_aggregator.py`

- [ ] **Step 1: 테스트 디렉토리 생성**

```bash
mkdir -p tests/modules/real_estate/daily_report
touch tests/modules/real_estate/daily_report/__init__.py
```

- [ ] **Step 2: 실패 테스트 작성**

`tests/modules/real_estate/daily_report/test_transaction_aggregator.py`:

```python
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
        """최근 3일 거래가 있는 단지가 AggregatedTransaction 목록으로 반환된다."""
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
        """분석 기간 이전 거래는 포함되지 않는다."""
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
        """top_k=2이면 상위 2개 단지만 반환된다."""
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
        """거래량이 많은 단지가 더 높은 composite_score를 받는다."""
        db_path = str(tmp_path / "re.db")
        _setup_db(db_path)
        today = date.today().isoformat()
        with sqlite3.connect(db_path) as conn:
            _insert_apt_master(conn, 1, "활발단지", "강남구")
            _insert_apt_master(conn, 2, "조용단지", "강남구")
            # 활발단지: 3건
            for _ in range(3):
                _insert_tx(conn, 1, today, 300_000_000)
            # 조용단지: 1건
            _insert_tx(conn, 2, today, 300_000_000)

        agg = TransactionAggregator(db_path=db_path)
        result = agg.aggregate(days=3, top_k=10, persona={}, budget_available=500_000_000)

        scores = {r.apt_name: r.composite_score for r in result}
        assert scores["활발단지"] > scores["조용단지"]

    def test_interest_area_boosts_persona_affinity(self, tmp_path):
        """persona.interest_areas에 포함된 sigungu 단지가 더 높은 점수를 받는다."""
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
        """가격 급락 단지도 급등 단지와 동일하게 price_signal에서 높은 점수를 받는다."""
        db_path = str(tmp_path / "re.db")
        _setup_db(db_path)
        today = date.today().isoformat()
        prior = (date.today() - timedelta(days=10)).isoformat()
        with sqlite3.connect(db_path) as conn:
            _insert_apt_master(conn, 1, "급등단지", "강남구")
            _insert_apt_master(conn, 2, "급락단지", "강남구")
            # 급등단지: 직전 1억 → 최근 1.2억 (+20%)
            _insert_tx(conn, 1, prior, 100_000_000)
            _insert_tx(conn, 1, today, 120_000_000)
            # 급락단지: 직전 1억 → 최근 0.8억 (-20%)
            _insert_tx(conn, 2, prior, 100_000_000)
            _insert_tx(conn, 2, today, 80_000_000)

        agg = TransactionAggregator(db_path=db_path)
        result = agg.aggregate(days=3, top_k=10, persona={}, budget_available=500_000_000)

        scores = {r.apt_name: r.composite_score for r in result}
        assert abs(scores["급등단지"] - scores["급락단지"]) < 0.05  # 거의 동일한 점수


class TestPriceChangePct:
    def test_price_change_pct_calculated_from_prior_period(self, tmp_path):
        """price_change_pct = (최근 평균 - 직전 30일 평균) / 직전 30일 평균 * 100."""
        db_path = str(tmp_path / "re.db")
        _setup_db(db_path)
        today = date.today().isoformat()
        prior = (date.today() - timedelta(days=15)).isoformat()
        with sqlite3.connect(db_path) as conn:
            _insert_apt_master(conn, 1, "테스트단지", "강남구")
            _insert_tx(conn, 1, prior, 100_000_000)   # 직전 1억
            _insert_tx(conn, 1, today, 110_000_000)   # 최근 1.1억 → +10%

        agg = TransactionAggregator(db_path=db_path)
        result = agg.aggregate(days=3, top_k=10, persona={}, budget_available=500_000_000)

        assert len(result) == 1
        assert abs(result[0].price_change_pct - 10.0) < 1.0

    def test_no_prior_data_gives_zero_change(self, tmp_path):
        """직전 데이터 없으면 price_change_pct = 0.0."""
        db_path = str(tmp_path / "re.db")
        _setup_db(db_path)
        today = date.today().isoformat()
        with sqlite3.connect(db_path) as conn:
            _insert_apt_master(conn, 1, "신규단지", "강남구")
            _insert_tx(conn, 1, today, 200_000_000)

        agg = TransactionAggregator(db_path=db_path)
        result = agg.aggregate(days=3, top_k=10, persona={}, budget_available=500_000_000)

        assert result[0].price_change_pct == 0.0
```

- [ ] **Step 3: 테스트 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/daily_report/test_transaction_aggregator.py -v 2>&1 | tail -15
```

Expected: `ModuleNotFoundError` — `transaction_aggregator` not found.

- [ ] **Step 4: TransactionAggregator 구현**

`src/modules/real_estate/daily_report/transaction_aggregator.py`:

```python
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
    COALESCE(a.household_count, 0) AS household_count
FROM recent r
JOIN apt_master am ON r.apt_master_id = am.id
LEFT JOIN prior p ON r.apt_master_id = p.apt_master_id
LEFT JOIN top_area ta ON r.apt_master_id = ta.apt_master_id
LEFT JOIN apartments a ON am.complex_code = a.complex_code
ORDER BY r.recent_tx_count DESC
LIMIT :limit
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
    ) -> List[AggregatedTransaction]:
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
            conn.close()
        except sqlite3.Error as e:
            logger.error("[Aggregator] DB 조회 실패: %s", e)
            return []

        if not rows:
            return []

        raw = [dict(r) for r in rows]
        max_tx = max(r["recent_tx_count"] for r in raw) or 1
        persona = persona or {}

        scored = [
            AggregatedTransaction(
                apt_master_id=r["apt_master_id"],
                apt_name=r["apt_name"],
                district_code=r["district_code"],
                sigungu=r["sigungu"],
                complex_code=r["complex_code"],
                recent_tx_count=r["recent_tx_count"],
                avg_recent_price=r["avg_recent_price"],
                price_change_pct=r["price_change_pct"],
                exclusive_area=r["exclusive_area"],
                household_count=r["household_count"],
                composite_score=self._composite_score(
                    recent_tx_count=r["recent_tx_count"],
                    max_tx_count=max_tx,
                    price_change_pct=r["price_change_pct"],
                    sigungu=r["sigungu"],
                    avg_recent_price=r["avg_recent_price"],
                    household_count=r["household_count"],
                    persona=persona,
                    budget_available=budget_available,
                ),
            )
            for r in raw
        ]

        scored.sort(key=lambda x: x.composite_score, reverse=True)
        logger.info("[Aggregator] 최근 %d일 거래 집계 완료 — 단지 %d개 → 상위 %d개 선택", days, len(scored), top_k)
        return scored[:top_k]

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

        # persona_affinity
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

- [ ] **Step 5: 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/daily_report/test_transaction_aggregator.py -v 2>&1 | tail -20
```

Expected: 모든 테스트 PASS.

- [ ] **Step 6: 커밋**

```bash
git add src/modules/real_estate/daily_report/transaction_aggregator.py \
        tests/modules/real_estate/daily_report/__init__.py \
        tests/modules/real_estate/daily_report/test_transaction_aggregator.py
git commit -m "feat(daily-report): TransactionAggregator — 최근 N일 거래 집계 + composite score"
```

---

## Task 3: DailyReportRepository

**Files:**
- Create: `src/modules/real_estate/daily_report/daily_report_repository.py`

- [ ] **Step 1: daily_report_repository.py 작성**

`src/modules/real_estate/daily_report/daily_report_repository.py`:

```python
import os
from typing import List, Optional

from core.logger import get_logger
from .models import DailyReport

logger = get_logger(__name__)


class DailyReportRepository:
    """data/daily_reports/ 디렉토리에 MD 파일 형식으로 daily report를 저장·조회한다."""

    def __init__(self, storage_path: str = "data/daily_reports"):
        self._path = storage_path
        os.makedirs(storage_path, exist_ok=True)

    def save(self, report: DailyReport) -> str:
        """리포트를 MD 파일로 저장하고 파일 경로를 반환한다."""
        filename = f"daily_{report.date}.md"
        filepath = os.path.join(self._path, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report.markdown)
        logger.info("[DailyReportRepository] 저장: %s", filepath)
        return filepath

    def load_markdown(self, date_str: str) -> Optional[str]:
        """날짜(YYYY-MM-DD) 기준 MD 파일 내용을 반환. 없으면 None."""
        filepath = os.path.join(self._path, f"daily_{date_str}.md")
        if not os.path.exists(filepath):
            return None
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()

    def list_dates(self) -> List[str]:
        """저장된 모든 리포트 날짜 목록을 최신순으로 반환."""
        dates = []
        for fname in os.listdir(self._path):
            if fname.startswith("daily_") and fname.endswith(".md"):
                date_str = fname[len("daily_"):-len(".md")]
                dates.append(date_str)
        return sorted(dates, reverse=True)

    def exists(self, date_str: str) -> bool:
        filepath = os.path.join(self._path, f"daily_{date_str}.md")
        return os.path.exists(filepath)
```

- [ ] **Step 2: 커밋**

```bash
git add src/modules/real_estate/daily_report/daily_report_repository.py
git commit -m "feat(daily-report): DailyReportRepository — MD 파일 저장·조회"
```

---

## Task 4: config.yaml 업데이트

**Files:**
- Modify: `src/modules/real_estate/config.yaml`

- [ ] **Step 1: daily_report 섹션 추가**

`src/modules/real_estate/config.yaml` 파일 끝에 아래 내용 추가:

```yaml
daily_report:
  days: 3                        # 분석 기간 (일)
  top_k: 5                       # 기본 상위 단지 수
  max_top_k: 10                  # 최대 상위 단지 수
  storage_path: "data/daily_reports"
  prior_period_days: 30          # 직전 비교 기간 (일)
  max_new_commute_api_calls: 5   # 일일 TMAP API 신규 호출 상한 (캐시 히트는 제외)
  scoring:
    tx_weight: 0.4
    price_weight: 0.3
    persona_weight: 0.3
```

- [ ] **Step 2: 커밋**

```bash
git add src/modules/real_estate/config.yaml
git commit -m "config(daily-report): daily_report 섹션 추가 — scoring 가중치 zero-hardcoding"
```

---

## Task 5: LLM 프롬프트 작성

**Files:**
- Create: `src/modules/real_estate/prompts/daily_strategy.md`

- [ ] **Step 1: 프롬프트 파일 작성**

`src/modules/real_estate/prompts/daily_strategy.md`:

```markdown
---
task_type: REAL_ESTATE_ANALYSIS
output_format: json
---

당신은 매일 아침 실거래 데이터를 기반으로 브리핑을 준비하는 부동산 전략 컨설턴트입니다.
아래 데이터를 분석하여 오늘의 시장 신호와 단지별 전략을 제안하세요.

[분석 기간]
{{date_range}}

[페르소나]
- 예산: {{budget_str}}
- 직장: {{workplace_station}}
- 선호 면적: {{preferred_area}}㎡
- 투자 스타일: {{investment_style}}

[거시경제 요약]
{{macro_summary}}

[주목 단지 {{candidate_count}}개]
{{candidates_text}}

---

아래 JSON 형식으로만 응답하세요. 다른 텍스트는 포함하지 마세요.

```json
{
  "market_summary": "오늘 시장에서 주목할 패턴을 3~5문장으로 서술. 어떤 지역이 활발했고, 가격 방향은 어떠했으며, 페르소나 관점에서 오늘의 시장이 의미하는 바는 무엇인가.",
  "candidate_insights": [
    {
      "apt_name": "단지명 (candidates_text에 있는 이름 그대로)",
      "trading_comment": "이 단지의 최근 거래 동향을 1~2문장으로 서술. 거래량, 가격 변동, 면적대 등.",
      "characteristics_comment": "단지 특징을 1~2문장으로 서술. 세대수, 준공연도, 용적률, 역세권, 학군 등.",
      "strategy_comment": "페르소나 관점에서 이 단지에 대한 전략적 제안을 1~2문장으로 서술. 매수 시점, 주의사항, 경쟁 대안 등."
    }
  ]
}
```

주의사항:
- apt_name은 반드시 candidates_text에 나온 단지명 그대로 사용하세요. 변형하지 마세요.
- candidate_insights 배열의 순서는 candidates_text의 순서와 동일하게 유지하세요.
- 숫자는 직접 계산하지 말고 주어진 데이터를 그대로 인용하세요.
- 데이터가 없는 항목(출퇴근 시간 없음 등)은 "미수집"으로 표기하세요.
```

- [ ] **Step 2: 커밋**

```bash
git add src/modules/real_estate/prompts/daily_strategy.md
git commit -m "feat(daily-report): daily_strategy LLM 프롬프트 작성"
```

---

## Task 6: DailyReportOrchestrator (TDD)

**Files:**
- Create: `src/modules/real_estate/daily_report/daily_report_orchestrator.py`
- Create: `tests/modules/real_estate/daily_report/test_daily_report_orchestrator.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests/modules/real_estate/daily_report/test_daily_report_orchestrator.py`:

```python
from datetime import date
from unittest.mock import MagicMock, patch
import pytest

from modules.real_estate.daily_report.daily_report_orchestrator import DailyReportOrchestrator
from modules.real_estate.daily_report.models import AggregatedTransaction, DailyReport


def _make_aggregated(name: str = "래미안", score: float = 0.8) -> AggregatedTransaction:
    return AggregatedTransaction(
        apt_master_id=1,
        apt_name=name,
        district_code="11680",
        sigungu="강남구",
        complex_code="CC001",
        recent_tx_count=3,
        avg_recent_price=280_000_000,
        price_change_pct=2.5,
        exclusive_area=84.0,
        household_count=1200,
        composite_score=score,
    )


def _make_orchestrator(tmp_path) -> DailyReportOrchestrator:
    mock_llm = MagicMock()
    mock_llm.generate_json.return_value = {
        "market_summary": "오늘 강남권 거래가 활발했습니다.",
        "candidate_insights": [
            {
                "apt_name": "래미안",
                "trading_comment": "3건 거래, 전월비 +2.5%",
                "characteristics_comment": "1200세대, 2002년 준공",
                "strategy_comment": "삼성역 22분, 예산 범위 내"
            }
        ],
    }
    mock_prompt_loader = MagicMock()
    mock_prompt_loader.load.return_value = ({"task_type": "REAL_ESTATE_ANALYSIS"}, "prompt text")
    mock_aggregator = MagicMock()
    mock_aggregator.aggregate.return_value = [_make_aggregated()]
    mock_repo = MagicMock()
    mock_repo.save.return_value = str(tmp_path / "daily_2026-05-03.md")

    return DailyReportOrchestrator(
        llm=mock_llm,
        prompt_loader=mock_prompt_loader,
        aggregator=mock_aggregator,
        report_repo=mock_repo,
        db_path=str(tmp_path / "re.db"),
    )


class TestGenerate:
    def test_returns_daily_report(self, tmp_path):
        """generate()는 DailyReport 인스턴스를 반환한다."""
        orch = _make_orchestrator(tmp_path)
        result = orch.generate(
            target_date=date(2026, 5, 3),
            days=3,
            top_k=5,
            persona={},
            macro_summary="기준금리: 3.5%",
        )
        assert isinstance(result, DailyReport)
        assert result.date == "2026-05-03"
        assert result.market_summary == "오늘 강남권 거래가 활발했습니다."

    def test_aggregator_called_with_correct_params(self, tmp_path):
        """aggregator.aggregate()가 days, top_k 파라미터로 호출된다."""
        orch = _make_orchestrator(tmp_path)
        orch.generate(
            target_date=date(2026, 5, 3),
            days=3,
            top_k=5,
            persona={},
            macro_summary="",
        )
        orch._aggregator.aggregate.assert_called_once()
        call_kwargs = orch._aggregator.aggregate.call_args
        assert call_kwargs.kwargs.get("days") == 3 or call_kwargs.args[0] == 3

    def test_llm_called_with_prompt(self, tmp_path):
        """LLM이 daily_strategy 프롬프트와 함께 호출된다."""
        orch = _make_orchestrator(tmp_path)
        orch.generate(
            target_date=date(2026, 5, 3),
            days=3,
            top_k=5,
            persona={},
            macro_summary="기준금리: 3.5%",
        )
        orch._llm.generate_json.assert_called_once()

    def test_report_repo_save_called(self, tmp_path):
        """report_repo.save()가 DailyReport로 호출된다."""
        orch = _make_orchestrator(tmp_path)
        orch.generate(
            target_date=date(2026, 5, 3),
            days=3,
            top_k=5,
            persona={},
            macro_summary="",
        )
        orch._repo.save.assert_called_once()
        saved = orch._repo.save.call_args.args[0]
        assert isinstance(saved, DailyReport)

    def test_empty_aggregation_returns_report_with_empty_candidates(self, tmp_path):
        """집계 결과가 없어도 빈 candidates로 DailyReport를 반환한다."""
        orch = _make_orchestrator(tmp_path)
        orch._aggregator.aggregate.return_value = []
        result = orch.generate(
            target_date=date(2026, 5, 3),
            days=3,
            top_k=5,
            persona={},
            macro_summary="",
        )
        assert isinstance(result, DailyReport)
        assert result.candidates == []


class TestCommuteQuota:
    def test_cached_commute_does_not_consume_quota(self, tmp_path):
        """캐시에 있는 출퇴근 데이터는 API 호출 없이 반환된다."""
        from modules.real_estate.commute.models import CommuteResult

        mock_repo = MagicMock()
        mock_repo.get.return_value = CommuteResult(
            origin_key="11680__래미안", destination="삼성역", mode="transit",
            duration_minutes=18, distance_meters=900,
        )
        mock_svc = MagicMock()
        mock_svc._repo = mock_repo

        orch = _make_orchestrator(tmp_path)
        orch._commute_svc = mock_svc

        candidates = [{"apt_name": "래미안", "district_code": "11680", "road_address": "서울 강남구 역삼 1"}]
        result = orch._enrich_with_commute_quota(candidates, "삼성역", 37.5088, 127.0633, max_new_calls=0)

        assert result[0]["commute_transit_minutes"] == 18
        mock_svc.get.assert_not_called()  # API 호출 없음

    def test_quota_zero_skips_uncached_candidates(self, tmp_path):
        """max_new_calls=0이면 캐시 미스 단지는 commute_transit_minutes가 None이다."""
        mock_repo = MagicMock()
        mock_repo.get.return_value = None  # 캐시 없음
        mock_svc = MagicMock()
        mock_svc._repo = mock_repo

        orch = _make_orchestrator(tmp_path)
        orch._commute_svc = mock_svc

        candidates = [{"apt_name": "신규단지", "district_code": "11680", "road_address": "서울 강남구 1"}]
        result = orch._enrich_with_commute_quota(candidates, "삼성역", 37.5088, 127.0633, max_new_calls=0)

        assert result[0].get("commute_transit_minutes") is None
        mock_svc.get.assert_not_called()

    def test_quota_limits_new_api_calls(self, tmp_path):
        """max_new_calls=2이면 캐시 미스 단지 중 2개만 API 호출한다."""
        from modules.real_estate.commute.models import CommuteResult

        mock_repo = MagicMock()
        mock_repo.get.return_value = None  # 모두 캐시 미스
        mock_svc = MagicMock()
        mock_svc._repo = mock_repo
        mock_svc.get.return_value = CommuteResult(
            origin_key="x", destination="삼성역", mode="transit",
            duration_minutes=25, distance_meters=1200,
        )

        orch = _make_orchestrator(tmp_path)
        orch._commute_svc = mock_svc

        candidates = [
            {"apt_name": f"단지{i}", "district_code": "11680", "road_address": f"서울 강남구 {i}"}
            for i in range(5)
        ]
        orch._enrich_with_commute_quota(candidates, "삼성역", 37.5088, 127.0633, max_new_calls=2)

        assert mock_svc.get.call_count == 2


class TestBuildMarkdown:
    def test_markdown_contains_date_and_apt_name(self, tmp_path):
        """생성된 markdown에 날짜와 단지명이 포함된다."""
        orch = _make_orchestrator(tmp_path)
        result = orch.generate(
            target_date=date(2026, 5, 3),
            days=3,
            top_k=5,
            persona={},
            macro_summary="기준금리: 3.5%",
        )
        assert "2026-05-03" in result.markdown
        assert "래미안" in result.markdown

    def test_markdown_contains_market_summary(self, tmp_path):
        """markdown에 LLM이 생성한 시장 총평이 포함된다."""
        orch = _make_orchestrator(tmp_path)
        result = orch.generate(
            target_date=date(2026, 5, 3),
            days=3,
            top_k=5,
            persona={},
            macro_summary="",
        )
        assert "오늘 강남권 거래가 활발했습니다." in result.markdown
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/daily_report/test_daily_report_orchestrator.py -v 2>&1 | tail -10
```

Expected: `ModuleNotFoundError` — `daily_report_orchestrator` not found.

- [ ] **Step 3: DailyReportOrchestrator 구현**

`src/modules/real_estate/daily_report/daily_report_orchestrator.py`:

```python
import json
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from core.llm import BaseLLMClient
from core.prompt_loader import PromptLoader
from core.logger import get_logger
from modules.real_estate.report_orchestrator import (
    _enrich_with_geocode,
    _enrich_with_poi,
    _enrich_with_building,
    _enrich_with_trend,
    _resolve_workplace_coords,
)
from modules.real_estate.trend_analyzer import TrendAnalyzer
from modules.real_estate.poi_collector import PoiCollector
from .models import AggregatedTransaction, DailyReport
from .transaction_aggregator import TransactionAggregator
from .daily_report_repository import DailyReportRepository

logger = get_logger(__name__)


def _format_candidate_for_llm(c: Dict) -> str:
    """단지 dict를 LLM 입력용 텍스트로 포맷."""
    lines = [f"### {c.get('apt_name', '?')} ({c.get('sigungu', '')}"]
    lines.append(f"- 최근 거래: {c.get('recent_tx_count', 0)}건, "
                 f"평균 {c.get('avg_recent_price', 0) / 10000:.0f}만원, "
                 f"전월比 {c.get('price_change_pct', 0):+.1f}%")
    lines.append(f"- 면적: {c.get('exclusive_area', 84):.0f}㎡, "
                 f"세대수: {c.get('household_count', 0)}세대")
    if c.get("build_year"):
        lines.append(f"- 준공: {c['build_year']}년, "
                     f"용적률: {c.get('floor_area_ratio', '?')}%, "
                     f"건폐율: {c.get('building_coverage_ratio', '?')}%")
    commute = c.get("commute_transit_minutes")
    lines.append(f"- 출퇴근(대중교통): {'미수집' if commute is None else f'{commute}분'}")
    poi = c.get("_poi")
    if poi:
        stations = poi.subway_stations[:2] if hasattr(poi, "subway_stations") else []
        station_str = ", ".join(f"{s.get('name','?')}({s.get('line','?')})" for s in stations) or "없음"
        lines.append(f"- 역세권: {station_str}")
        lines.append(f"- 학교 {poi.schools_count}개, 학원 {poi.academies_count}개, 마트 {poi.marts_count}개")
    trend = c.get("_trend")
    if trend:
        lines.append(f"- 시세추세({c.get('_trend_area_sqm', 84):.0f}㎡): "
                     f"평균 {trend.avg_price / 10000:.0f}만원, "
                     f"변동 {trend.price_change_pct:+.1f}%, "
                     f"월거래량 {trend.monthly_volume:.1f}건")
    return "\n".join(lines)


class DailyReportOrchestrator:
    def __init__(
        self,
        llm: BaseLLMClient,
        prompt_loader: PromptLoader,
        aggregator: TransactionAggregator,
        report_repo: DailyReportRepository,
        db_path: str = "data/real_estate.db",
        poi_collector: Optional[PoiCollector] = None,
        trend_analyzer: Optional[TrendAnalyzer] = None,
        commute_svc=None,
        geocoder=None,
        max_new_commute_api_calls: int = 5,
    ):
        self._llm = llm
        self._prompt_loader = prompt_loader
        self._aggregator = aggregator
        self._repo = report_repo
        self._db_path = db_path
        self._poi_collector = poi_collector
        self._trend_analyzer = trend_analyzer
        self._commute_svc = commute_svc
        self._geocoder = geocoder
        self._max_new_commute_api_calls = max_new_commute_api_calls

    def generate(
        self,
        target_date: date,
        days: int = 3,
        top_k: int = 5,
        persona: Optional[Dict] = None,
        macro_summary: str = "",
        budget_available: int = 0,
    ) -> DailyReport:
        persona = persona or {}
        date_str = target_date.isoformat()

        # Step 1. 거래 집계
        aggregated = self._aggregator.aggregate(
            days=days, top_k=top_k, persona=persona, budget_available=budget_available
        )

        if not aggregated:
            logger.warning("[DailyOrchestrator] 최근 %d일 거래 없음", days)
            return self._empty_report(date_str, days, macro_summary)

        logger.info("[DailyOrchestrator] 집계 완료 — %d개 단지", len(aggregated))

        # Step 2. AggregatedTransaction → enrich 입력 dict
        candidates = [self._to_dict(a) for a in aggregated]

        # Step 3. Enrich pipeline
        candidates = _enrich_with_geocode(candidates, self._geocoder)
        if self._poi_collector:
            candidates = _enrich_with_poi(candidates, self._poi_collector)
        candidates = _enrich_with_building(candidates, self._db_path)
        if self._commute_svc and self._geocoder:
            dest, dest_lat, dest_lng = _resolve_workplace_coords(persona, self._geocoder)
            max_new_calls = self._max_new_commute_api_calls
            candidates = self._enrich_with_commute_quota(candidates, dest, dest_lat, dest_lng, max_new_calls)
        if self._trend_analyzer:
            preferred_areas = persona.get("apartment_preferences", {}).get("preferred_area_sqm", [84.0])
            candidates = _enrich_with_trend(candidates, self._trend_analyzer, preferred_areas=preferred_areas)

        # Step 4. LLM 분석
        candidates_text = "\n\n".join(_format_candidate_for_llm(c) for c in candidates)
        user = persona.get("user", {})
        budget_str = f"{budget_available / 10000:.0f}만원" if budget_available > 0 else "미설정"
        preferred_area = persona.get("apartment_preferences", {}).get("preferred_area_sqm", [84])[0]
        date_from = (target_date - timedelta(days=days)).isoformat()
        date_range = f"{date_from} ~ {date_str}"

        metadata, prompt = self._prompt_loader.load(
            "daily_strategy",
            variables={
                "date_range": date_range,
                "budget_str": budget_str,
                "workplace_station": persona.get("commute", {}).get("workplace_station", "미설정"),
                "preferred_area": preferred_area,
                "investment_style": persona.get("investment_style", "미설정"),
                "macro_summary": macro_summary or "거시경제 데이터 없음",
                "candidate_count": len(candidates),
                "candidates_text": candidates_text,
            },
        )
        try:
            llm_result = self._llm.generate_json(prompt, metadata=metadata)
            market_summary = llm_result.get("market_summary", "")
            candidate_insights = llm_result.get("candidate_insights", [])
        except Exception as e:
            logger.warning("[DailyOrchestrator] LLM 실패: %s", e)
            market_summary = ""
            candidate_insights = []

        # Step 5. Markdown 조립
        insights_map = {i.get("apt_name", ""): i for i in candidate_insights}
        markdown = self._build_markdown(
            date_str=date_str,
            date_range=date_range,
            days=days,
            macro_summary=macro_summary,
            market_summary=market_summary,
            candidates=candidates,
            insights_map=insights_map,
        )

        # Step 6. 저장 가능한 dict로 변환 (직렬화)
        serializable_candidates = [
            {k: v for k, v in c.items() if not k.startswith("_")}
            for c in candidates
        ]

        from datetime import datetime
        report = DailyReport(
            date=date_str,
            analysis_period=date_range,
            total_transactions=sum(a.recent_tx_count for a in aggregated),
            top_k=len(candidates),
            macro_summary=macro_summary,
            market_summary=market_summary,
            candidates=serializable_candidates,
            markdown=markdown,
            generated_at=datetime.now().isoformat(),
        )

        # Step 7. 저장
        self._repo.save(report)
        return report

    # ── Private ───────────────────────────────────────────────────────────

    @staticmethod
    def _to_dict(a: AggregatedTransaction) -> Dict:
        return {
            "id": a.apt_master_id,
            "apt_master_id": a.apt_master_id,
            "apt_name": a.apt_name,
            "district_code": a.district_code,
            "sigungu": a.sigungu,
            "complex_code": a.complex_code,
            "recent_tx_count": a.recent_tx_count,
            "avg_recent_price": a.avg_recent_price,
            "price_change_pct": a.price_change_pct,
            "exclusive_area": a.exclusive_area,
            "household_count": a.household_count,
            "composite_score": a.composite_score,
        }

    @staticmethod
    def _build_markdown(
        date_str: str,
        date_range: str,
        days: int,
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
            macro_summary or "데이터 없음",
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
            name = c.get("apt_name", "?")
            score_pct = int(c.get("composite_score", 0) * 100)
            price_eok = c.get("avg_recent_price", 0) / 100_000_000
            change = c.get("price_change_pct", 0)
            trend = c.get("_trend")
            trend_area = c.get("_trend_area_sqm", 84)

            lines += [
                f"### {i}. {name} — composite {score_pct}점",
                "",
                f"**거래:** {c.get('recent_tx_count', 0)}건 | 평균 {price_eok:.1f}억 | 전월比 {change:+.1f}%",
                f"**위치:** {c.get('sigungu', '')} | **면적:** {c.get('exclusive_area', 84):.0f}㎡ | **세대수:** {c.get('household_count', 0)}세대",
            ]

            if c.get("build_year"):
                lines.append(
                    f"**건물:** {c['build_year']}년 준공 | "
                    f"용적률 {c.get('floor_area_ratio', '?')}% | "
                    f"건폐율 {c.get('building_coverage_ratio', '?')}%"
                )

            commute = c.get("commute_transit_minutes")
            lines.append(f"**출퇴근:** {'미수집' if commute is None else f'{commute}분 (대중교통)'}")

            poi = c.get("_poi")
            if poi:
                stations = poi.subway_stations[:2] if hasattr(poi, "subway_stations") else []
                s_str = ", ".join(f"{s.get('name','?')}({s.get('line','?')})" for s in stations) or "없음"
                lines.append(f"**역세권:** {s_str}")
                lines.append(f"**편의시설:** 학교 {poi.schools_count}개, 학원 {poi.academies_count}개, 마트 {poi.marts_count}개")

            if trend:
                lines.append(
                    f"**시세추세 ({trend_area:.0f}㎡):** 평균 {trend.avg_price / 10000:.0f}만원 | "
                    f"변동 {trend.price_change_pct:+.1f}% | 월거래 {trend.monthly_volume:.1f}건"
                )

            ins = insights_map.get(name, {})
            if ins:
                lines += [
                    "",
                    f"> **거래 동향:** {ins.get('trading_comment', '')}",
                    f"> **단지 특징:** {ins.get('characteristics_comment', '')}",
                    f"> **전략 제안:** {ins.get('strategy_comment', '')}",
                ]
            lines += ["", "---", ""]

        return "\n".join(lines)

    def _enrich_with_commute_quota(
        self,
        candidates: List[Dict],
        dest: Optional[str],
        dest_lat: Optional[float],
        dest_lng: Optional[float],
        max_new_calls: int,
    ) -> List[Dict]:
        """TMAP API 신규 호출을 max_new_calls 이내로 제한한다.

        캐시 히트(commute_cache DB에 이미 저장된 경로)는 quota 소모 없이 진행.
        캐시 미스는 max_new_calls 이내에서만 실제 API 호출.
        quota 초과 단지는 commute_transit_minutes=None으로 스킵.
        """
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

            # 캐시 사전 확인 (API 미호출)
            cached = self._commute_svc._repo.get(origin_key, dest, "transit")
            if cached is not None:
                result["commute_transit_minutes"] = cached.duration_minutes
                logger.debug("[DailyOrchestrator] 출퇴근 캐시 히트: %s", apt_name)
            elif new_calls_used < max_new_calls:
                try:
                    cr = self._commute_svc.get(
                        origin_key=origin_key,
                        road_address=road_address,
                        apt_name=apt_name,
                        district_code=district_code,
                        mode="transit",
                        dest_override=dest,
                        dest_lat_override=dest_lat,
                        dest_lng_override=dest_lng,
                    )
                    if cr:
                        result["commute_transit_minutes"] = cr.duration_minutes
                    new_calls_used += 1
                    logger.info("[DailyOrchestrator] 출퇴근 API 호출 %d/%d: %s", new_calls_used, max_new_calls, apt_name)
                except Exception as e:
                    logger.warning("[DailyOrchestrator] Commute 실패 %s: %s", apt_name, e)
            else:
                logger.info("[DailyOrchestrator] 출퇴근 quota 소진 (%d/%d), 스킵: %s", new_calls_used, max_new_calls, apt_name)

            enriched.append(result)
        return enriched

    def _empty_report(self, date_str: str, days: int, macro_summary: str) -> DailyReport:
        from datetime import datetime
        markdown = (
            f"# 데일리 부동산 브리핑 — {date_str}\n\n"
            f"최근 {days}일 간 분석 가능한 실거래 데이터가 없습니다.\n"
        )
        report = DailyReport(
            date=date_str,
            analysis_period=f"최근 {days}일",
            total_transactions=0,
            top_k=0,
            macro_summary=macro_summary,
            market_summary="",
            candidates=[],
            markdown=markdown,
            generated_at=datetime.now().isoformat(),
        )
        self._repo.save(report)
        return report
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/daily_report/ -v 2>&1 | tail -25
```

Expected: 모든 테스트 PASS.

- [ ] **Step 5: 커밋**

```bash
git add src/modules/real_estate/daily_report/daily_report_orchestrator.py \
        tests/modules/real_estate/daily_report/test_daily_report_orchestrator.py
git commit -m "feat(daily-report): DailyReportOrchestrator — enrich 파이프라인 + LLM + MD 조립"
```

---

## Task 7: API 엔드포인트

**Files:**
- Modify: `src/api/routers/real_estate.py`

- [ ] **Step 1: Request 모델 추가**

`src/api/routers/real_estate.py` 상단 Pydantic 모델 블록에 아래 추가 (기존 `class NewsAnalysisRequest` 아래):

```python
class DailyReportRequest(BaseModel):
    target_date: Optional[str] = Field(None, description="YYYY-MM-DD (기본: 오늘)")
    days: int = Field(3, ge=1, le=7, description="분석 기간 (일)")
    top_k: int = Field(5, ge=1, le=10, description="상위 단지 수")
    force: bool = Field(False, description="이미 오늘 리포트 있어도 재생성")
```

- [ ] **Step 2: POST /jobs/daily-report/generate 엔드포인트 추가**

`src/api/routers/real_estate.py` 파일 끝에 아래 엔드포인트 추가:

```python
@router.post("/jobs/daily-report/generate")
def generate_daily_report(req: DailyReportRequest = None):
    """최근 N일 실거래 기반 데일리 리포트 생성 + Slack 전송."""
    import os
    from datetime import date as _date
    from core.llm_pipeline import build_llm_pipeline
    from core.prompt_loader import PromptLoader
    from core.storage import get_storage_provider
    from core.notify.slack import SlackSender
    from modules.real_estate.config import RealEstateConfig
    from modules.real_estate.persona_manager import PersonaManager
    from modules.real_estate.geocoder import GeocoderService
    from modules.real_estate.poi_collector import PoiCollector
    from modules.real_estate.trend_analyzer import TrendAnalyzer
    from modules.real_estate.commute.commute_service import CommuteService
    from modules.real_estate.commute.commute_repository import CommuteRepository
    from modules.real_estate.commute.tmap_client import TmapClient
    from modules.real_estate.report_orchestrator import _calc_budget
    from modules.real_estate.daily_report.transaction_aggregator import TransactionAggregator
    from modules.real_estate.daily_report.daily_report_repository import DailyReportRepository
    from modules.real_estate.daily_report.daily_report_orchestrator import DailyReportOrchestrator
    from modules.macro.service import MacroCollectionService

    if req is None:
        req = DailyReportRequest()

    try:
        cfg = RealEstateConfig()
        re_db = cfg.get("real_estate_db_path", "data/real_estate.db")
        daily_cfg = cfg.get("daily_report", {})
        storage_path = daily_cfg.get("storage_path", "data/daily_reports")
        kakao_key = os.getenv("KAKAO_API_KEY", "")

        target_date = _date.fromisoformat(req.target_date) if req.target_date else _date.today()
        date_str = target_date.isoformat()

        # force=False이면 기존 리포트 재사용
        report_repo = DailyReportRepository(storage_path=storage_path)
        if not req.force and report_repo.exists(date_str):
            existing_md = report_repo.load_markdown(date_str)
            return {
                "status": "exists",
                "date": date_str,
                "report_path": f"{storage_path}/daily_{date_str}.md",
                "slack_sent": False,
            }

        # 페르소나 및 거시경제
        persona = PersonaManager().load()
        macro_db = cfg.get("macro_db_path", "data/macro.db")
        macro_svc = MacroCollectionService(db_path=macro_db)
        macro_latest = macro_svc.get_latest(domain="real_estate")
        macro_lines = [f"{m.get('name','')}: {m.get('value','')}{m.get('unit','')}" for m in (macro_latest or [])]
        macro_summary = " | ".join(macro_lines[:6])

        # 예산 계산
        budget_available = _calc_budget(persona, macro_summary)

        # LLM + PromptLoader
        llm = build_llm_pipeline()
        root_storage = get_storage_provider("local", root_path=".")
        prompt_loader = PromptLoader(root_storage, base_dir="src/modules/real_estate/prompts")

        # Geocoder
        geocode_cache = cfg.get("geocode_cache_path", "data/geocode_cache.db")
        geocoder = GeocoderService(api_key=kakao_key, cache_path=geocode_cache)

        # Commute
        commute_cfg = cfg.get("commute", {
            "destination": "삼성역",
            "destination_lat": 37.5088,
            "destination_lng": 127.0633,
            "cache_ttl_days": 90,
        })
        commute_db = cfg.get("commute_cache_db_path", "data/commute_cache.db")
        tmap_key = os.getenv("TMAP_API_KEY", "")
        commute_svc = CommuteService(
            repo=CommuteRepository(db_path=commute_db, ttl_days=int(commute_cfg.get("cache_ttl_days", 90))),
            tmap_client=TmapClient(api_key=tmap_key),
            geocoder=geocoder,
            config=commute_cfg,
        )

        # Orchestrator 조립
        max_commute_calls = daily_cfg.get("max_new_commute_api_calls", 5)
        orchestrator = DailyReportOrchestrator(
            llm=llm,
            prompt_loader=prompt_loader,
            aggregator=TransactionAggregator(db_path=re_db),
            report_repo=report_repo,
            db_path=re_db,
            poi_collector=PoiCollector(api_key=kakao_key, db_path=re_db),
            trend_analyzer=TrendAnalyzer(db_path=re_db),
            commute_svc=commute_svc,
            geocoder=geocoder,
            max_new_commute_api_calls=max_commute_calls,
        )

        report = orchestrator.generate(
            target_date=target_date,
            days=req.days,
            top_k=req.top_k,
            persona=persona,
            macro_summary=macro_summary,
            budget_available=budget_available,
        )

        # Slack 전송
        slack_sent = False
        try:
            slack = SlackSender()
            slack.send(report.markdown)
            slack_sent = True
            logger.info("[API] Slack 전송 완료 — daily report %s", date_str)
        except Exception as e:
            logger.warning("[API] Slack 전송 실패: %s", e)

        return {
            "status": "success",
            "date": date_str,
            "top_k": report.top_k,
            "total_transactions_analyzed": report.total_transactions,
            "report_path": f"{storage_path}/daily_{date_str}.md",
            "slack_sent": slack_sent,
        }

    except Exception as e:
        logger.error("[API] generate_daily_report 오류: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/real-estate/daily-report/list")
def list_daily_reports():
    """저장된 데일리 리포트 날짜 목록 반환."""
    from modules.real_estate.config import RealEstateConfig
    from modules.real_estate.daily_report.daily_report_repository import DailyReportRepository
    cfg = RealEstateConfig()
    storage_path = cfg.get("daily_report", {}).get("storage_path", "data/daily_reports")
    repo = DailyReportRepository(storage_path=storage_path)
    return {"dates": repo.list_dates()}


@router.get("/dashboard/real-estate/daily-report/{date_str}")
def get_daily_report(date_str: str):
    """특정 날짜 데일리 리포트 Markdown 반환."""
    from modules.real_estate.config import RealEstateConfig
    from modules.real_estate.daily_report.daily_report_repository import DailyReportRepository
    cfg = RealEstateConfig()
    storage_path = cfg.get("daily_report", {}).get("storage_path", "data/daily_reports")
    repo = DailyReportRepository(storage_path=storage_path)
    md = repo.load_markdown(date_str)
    if md is None:
        raise HTTPException(status_code=404, detail=f"리포트 없음: {date_str}")
    return {"date": date_str, "markdown": md}
```

- [ ] **Step 3: 기존 엔드포인트 deprecated 처리**

`src/api/routers/real_estate.py` — `@router.post("/jobs/professional-report/generate")` 함수 첫 줄에 아래 추가:

```python
@router.post("/jobs/professional-report/generate")
def generate_professional_report():
    """[DEPRECATED] /jobs/daily-report/generate 를 사용하세요."""
    raise HTTPException(
        status_code=410,
        detail="이 엔드포인트는 deprecated 되었습니다. POST /jobs/daily-report/generate 를 사용하세요."
    )
```

기존 generate_professional_report 함수 본문 전체를 위 한 줄로 교체한다.

- [ ] **Step 4: Docker 재빌드 및 엔드포인트 확인**

```bash
docker compose build api 2>&1 | tail -5
docker compose restart api
sleep 6
curl -s -X POST http://localhost:8000/jobs/daily-report/generate \
  -H "Content-Type: application/json" \
  -d '{"days": 3, "top_k": 5, "force": true}' | python3 -m json.tool
```

Expected:
```json
{"status": "success", "date": "...", "top_k": 5, "slack_sent": true}
```

- [ ] **Step 5: 커밋**

```bash
git add src/api/routers/real_estate.py
git commit -m "feat(api): POST /jobs/daily-report/generate 추가 + professional-report deprecated"
```

---

## Task 8: Streamlit "📰 데일리 리포트" 탭

**Files:**
- Modify: `src/dashboard/views/real_estate.py`

- [ ] **Step 1: 현재 real_estate.py에서 탭 구조 확인**

```bash
arch -arm64 .venv/bin/python3.12 -c "
import ast, sys
with open('src/dashboard/views/real_estate.py') as f:
    src = f.read()
print([l.strip() for l in src.split('\n') if 'tab' in l.lower() and ('\"' in l or \"'\" in l)][:20])
"
```

이 명령으로 현재 탭 정의 줄들을 파악한다.

- [ ] **Step 2: 데일리 리포트 렌더 함수 추가**

`src/dashboard/views/real_estate.py` 파일 끝에 아래 함수 추가:

```python
def _render_daily_report_tab(client: "DashboardClient"):
    """데일리 리포트 탭 — 날짜 선택 + 리포트 본문 렌더링."""
    st.subheader("📰 데일리 부동산 브리핑")

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 오늘 리포트 생성", use_container_width=True):
            with st.spinner("리포트 생성 중..."):
                try:
                    result = client.post("/jobs/daily-report/generate", json={"days": 3, "top_k": 5})
                    if result.get("status") in ("success", "exists"):
                        st.success(f"✅ 완료: {result.get('date')} | Slack {'전송됨' if result.get('slack_sent') else '전송 안됨'}")
                        st.rerun()
                    else:
                        st.error(f"생성 실패: {result}")
                except Exception as e:
                    st.error(f"오류: {e}")

    # 날짜 목록 조회
    try:
        dates_resp = client.get("/dashboard/real-estate/daily-report/list")
        dates = dates_resp.get("dates", [])
    except Exception:
        dates = []

    if not dates:
        st.info("저장된 데일리 리포트가 없습니다. '오늘 리포트 생성' 버튼을 눌러주세요.")
        return

    with col1:
        selected_date = st.selectbox("날짜 선택", options=dates, index=0)

    if selected_date:
        try:
            report_resp = client.get(f"/dashboard/real-estate/daily-report/{selected_date}")
            markdown = report_resp.get("markdown", "")
            if markdown:
                st.markdown(markdown)
            else:
                st.warning("리포트 내용이 비어있습니다.")
        except Exception as e:
            st.error(f"리포트 조회 실패: {e}")
```

- [ ] **Step 3: 기존 `show_real_estate` 함수에서 professional report 탭을 데일리 리포트 탭으로 교체**

`src/dashboard/views/real_estate.py` 의 `show_real_estate` 함수에서 탭 정의 부분을 찾는다. 기존 "📊 Professional Report" 또는 유사 탭 레이블을 "📰 데일리 리포트" 로 교체하고, 해당 탭 렌더링 코드를 `_render_daily_report_tab(client)` 호출로 교체한다.

```python
# 기존 탭 정의에서 Professional Report 탭을 찾아 교체
# 예: "📊 Professional Report" → "📰 데일리 리포트"
# 탭 본문: _render_daily_report_tab(client)
```

실제 교체할 정확한 줄은 Step 1의 확인 결과를 참고한다.

- [ ] **Step 4: DashboardClient에 post 메서드 존재 확인 및 추가**

```bash
arch -arm64 .venv/bin/python3.12 -c "
import ast
with open('src/dashboard/api_client.py') as f:
    src = f.read()
print('post' in src, 'get' in src)
"
```

`post` 메서드가 없으면 `src/dashboard/api_client.py`에 추가:

```python
def post(self, path: str, json: dict = None) -> dict:
    import requests
    resp = requests.post(f"{self.base_url}{path}", json=json or {}, timeout=120)
    resp.raise_for_status()
    return resp.json()
```

- [ ] **Step 5: Streamlit 재시작 후 탭 확인**

```bash
docker compose restart dashboard
sleep 5
```

브라우저에서 `http://localhost:8501` 접속 → 부동산 탭 → "📰 데일리 리포트" 탭 확인.

- [ ] **Step 6: 커밋**

```bash
git add src/dashboard/views/real_estate.py \
        src/dashboard/api_client.py
git commit -m "feat(dashboard): 📰 데일리 리포트 탭 추가 — 날짜 선택 + 리포트 본문 렌더링"
```

---

## Task 9: 전체 검증

- [ ] **Step 1: 전체 단위 테스트 실행**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/daily_report/ -v 2>&1 | tail -20
```

Expected: 모든 테스트 PASS.

- [ ] **Step 2: Docker 이미지 최종 재빌드**

```bash
docker compose build api dashboard 2>&1 | tail -5
docker compose up -d
sleep 8
docker compose ps
```

Expected: `api`, `dashboard` 컨테이너 모두 `Up`.

- [ ] **Step 3: 데일리 리포트 생성 E2E 검증**

```bash
curl -s -X POST http://localhost:8000/jobs/daily-report/generate \
  -H "Content-Type: application/json" \
  -d '{"days": 3, "top_k": 5, "force": true}' | python3 -m json.tool
```

아래 항목 체크:
- [ ] `status: "success"` 반환
- [ ] `data/daily_reports/daily_YYYY-MM-DD.md` 파일 생성됨
- [ ] `slack_sent: true` (Slack 전송 성공)
- [ ] 리포트 MD에 "오늘의 시장 신호" 섹션 포함
- [ ] 리포트 MD에 단지명과 거래 정보 포함
- [ ] Streamlit 데일리 리포트 탭에서 방금 생성한 리포트 확인 가능

- [ ] **Step 4: 기존 deprecated 엔드포인트 확인**

```bash
curl -s -X POST http://localhost:8000/jobs/professional-report/generate | python3 -m json.tool
```

Expected: `410 Gone` 응답.

- [ ] **Step 5: 로그에서 오류 확인**

```bash
docker compose logs api --tail=60 2>/dev/null | grep -E "(ERROR|WARNING|Aggregator|DailyOrchestrator)" | head -20
```

확인 항목:
- `[Aggregator] 최근 3일 거래 집계 완료 — 단지 ?개` 로그 있음
- `[DailyOrchestrator]` 관련 치명적 오류 없음
