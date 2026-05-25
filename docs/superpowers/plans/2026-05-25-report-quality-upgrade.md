# Report Quality Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Job4 리포트를 InsightOrchestrator(중립 50점)에서 DailyReportOrchestrator(비교·수익·공급 분석 포함)로 전환하여 전문 부동산 전략가 수준의 단지 분석 리포트를 생성한다.

**Architecture:** 기존 DailyReportOrchestrator의 enrich pipeline 끝에 ComparativeAnalyzer, YieldCalculator, SupplyRiskAnalyzer 3개 모듈을 순차 추가한다. 전세·청약 데이터 수집은 별도 Job(월 1회)으로 분리하고, 분석 결과는 `_`로 시작하는 candidate dict 필드로 전달해 formatter와 LLM 프롬프트에서 소비한다.

**Tech Stack:** Python 3.12, SQLite (sqlite3), FastAPI, pytest, 국토부 실거래가 API (XML), 청약홈 API (XML), 기존 LLMClient/PromptLoader 패턴

---

## File Map

### 신규 생성
| 경로 | 역할 |
|------|------|
| `src/modules/real_estate/jeonse/__init__.py` | 패키지 |
| `src/modules/real_estate/jeonse/models.py` | `JeonseTransaction` dataclass |
| `src/modules/real_estate/jeonse/repository.py` | `JeonseRepository` — CRUD + complex_code fallback 조회 |
| `src/modules/real_estate/jeonse/client.py` | `JeonseClient` — 국토부 전월세 API (XML) |
| `src/modules/real_estate/supply/__init__.py` | 패키지 |
| `src/modules/real_estate/supply/models.py` | `SupplySchedule` dataclass |
| `src/modules/real_estate/supply/repository.py` | `SupplyRepository` — CRUD + Haversine 반경 쿼리 |
| `src/modules/real_estate/supply/client.py` | `SupplyClient` — 청약홈 분양 API (XML) |
| `src/modules/real_estate/supply/risk_analyzer.py` | `SupplyRiskAnalyzer` — 공급+뉴스 분석 |
| `src/modules/real_estate/comparative/__init__.py` | 패키지 |
| `src/modules/real_estate/comparative/models.py` | `ComparativeResult`, `SimilarUnit` dataclass |
| `src/modules/real_estate/comparative/analyzer.py` | `ComparativeAnalyzer` — 구 평균·유사 단지 비교 |
| `src/modules/real_estate/yield_analysis/__init__.py` | 패키지 |
| `src/modules/real_estate/yield_analysis/models.py` | `YieldResult` dataclass |
| `src/modules/real_estate/yield_analysis/calculator.py` | `YieldCalculator` — 전세가율·보유비용 계산 |
| `src/modules/real_estate/prompts/news_catalyst_classifier.md` | LLM 프롬프트 — 뉴스 호재/악재 분류 |
| `tests/modules/real_estate/jeonse/__init__.py` | |
| `tests/modules/real_estate/jeonse/test_jeonse_repository.py` | |
| `tests/modules/real_estate/supply/__init__.py` | |
| `tests/modules/real_estate/supply/test_supply_repository.py` | |
| `tests/modules/real_estate/supply/test_supply_risk_analyzer.py` | |
| `tests/modules/real_estate/comparative/__init__.py` | |
| `tests/modules/real_estate/comparative/test_comparative_analyzer.py` | |
| `tests/modules/real_estate/yield_analysis/__init__.py` | |
| `tests/modules/real_estate/yield_analysis/test_yield_calculator.py` | |
| `tests/modules/real_estate/daily_report/test_report_formatter_new_blocks.py` | |

### 수정
| 경로 | 변경 내용 |
|------|-----------|
| `src/modules/real_estate/report_orchestrator.py` | `_enrich_with_comparative`, `_enrich_with_yield`, `_enrich_with_supply` 함수 추가 |
| `src/modules/real_estate/daily_report/report_types.py` | `CompData`, `YieldData`, `SupplyData` TypedDict 추가 |
| `src/modules/real_estate/daily_report/report_formatter.py` | `render_price_comparison`, `render_yield_analysis`, `render_supply_risk` 추가; `build_candidate_card()` 수정 |
| `src/modules/real_estate/prompts/daily_strategy.md` | `comp_text`, `yield_text`, `supply_text` 변수 추가 |
| `src/modules/real_estate/daily_report/daily_report_orchestrator.py` | `_format_candidate_for_llm()` + 생성자 파라미터 3개 추가 |
| `src/modules/real_estate/service.py` | `generate_report()` — DailyReportOrchestrator 사용으로 교체 |
| `src/api/dependencies.py` | 신규 모듈 DI 싱글턴 추가 |
| `src/api/routers/real_estate.py` | `POST /jobs/jeonse/collect`, `POST /jobs/supply/collect` 엔드포인트 추가 |

---

## Task 1: JeonseTransaction 모델 + JeonseRepository

**Files:**
- Create: `src/modules/real_estate/jeonse/__init__.py`
- Create: `src/modules/real_estate/jeonse/models.py`
- Create: `src/modules/real_estate/jeonse/repository.py`
- Create: `tests/modules/real_estate/jeonse/__init__.py`
- Create: `tests/modules/real_estate/jeonse/test_jeonse_repository.py`

- [ ] **Step 1: 테스트 작성**

```python
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
```

- [ ] **Step 2: 테스트 실행해서 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/jeonse/test_jeonse_repository.py -v
```
Expected: `ModuleNotFoundError: No module named 'modules.real_estate.jeonse'`

- [ ] **Step 3: models.py 작성**

```python
# src/modules/real_estate/jeonse/models.py
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class JeonseTransaction:
    apt_name: str
    district_code: str
    deal_date: str          # YYYY-MM-DD
    exclusive_area: float
    deposit: int            # 만원
    monthly_rent: int       # 만원, 전세=0
    contract_type: str      # 'jeonse' | 'monthly'
    floor: int
    complex_code: Optional[str] = None
    id: Optional[int] = None
```

- [ ] **Step 4: repository.py 작성**

```python
# src/modules/real_estate/jeonse/repository.py
import sqlite3
from datetime import date, timedelta
from typing import List, Optional
from .models import JeonseTransaction

_DDL = """
CREATE TABLE IF NOT EXISTS jeonse_transactions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    complex_code  TEXT,
    apt_name      TEXT NOT NULL,
    district_code TEXT NOT NULL,
    deal_date     TEXT NOT NULL,
    exclusive_area REAL NOT NULL,
    deposit       INTEGER NOT NULL,
    monthly_rent  INTEGER NOT NULL DEFAULT 0,
    contract_type TEXT NOT NULL DEFAULT 'jeonse',
    floor         INTEGER NOT NULL DEFAULT 0,
    collected_at  TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(apt_name, district_code, deal_date, floor, deposit, exclusive_area)
);
CREATE INDEX IF NOT EXISTS idx_jeonse_complex ON jeonse_transactions(complex_code);
CREATE INDEX IF NOT EXISTS idx_jeonse_date    ON jeonse_transactions(deal_date);
"""


class JeonseRepository:
    def __init__(self, db_path: str):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_DDL)
        self._conn.commit()

    def save(self, tx: JeonseTransaction) -> None:
        self._conn.execute(
            """INSERT OR IGNORE INTO jeonse_transactions
               (complex_code, apt_name, district_code, deal_date,
                exclusive_area, deposit, monthly_rent, contract_type, floor)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (tx.complex_code, tx.apt_name, tx.district_code, tx.deal_date,
             tx.exclusive_area, tx.deposit, tx.monthly_rent, tx.contract_type, tx.floor)
        )
        self._conn.commit()

    def save_bulk(self, txs: List[JeonseTransaction]) -> int:
        saved = 0
        for tx in txs:
            cur = self._conn.execute(
                """INSERT OR IGNORE INTO jeonse_transactions
                   (complex_code, apt_name, district_code, deal_date,
                    exclusive_area, deposit, monthly_rent, contract_type, floor)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (tx.complex_code, tx.apt_name, tx.district_code, tx.deal_date,
                 tx.exclusive_area, tx.deposit, tx.monthly_rent, tx.contract_type, tx.floor)
            )
            saved += cur.rowcount
        self._conn.commit()
        return saved

    def get_recent(
        self,
        complex_code: Optional[str],
        area: float,
        months: int = 6,
        apt_name: Optional[str] = None,
        district_code: Optional[str] = None,
        jeonse_only: bool = False,
    ) -> List[JeonseTransaction]:
        cutoff = (date.today() - timedelta(days=months * 30)).isoformat()
        contract_filter = "AND contract_type = 'jeonse'" if jeonse_only else ""

        if complex_code:
            rows = self._conn.execute(
                f"""SELECT * FROM jeonse_transactions
                    WHERE complex_code = ?
                      AND exclusive_area BETWEEN ? AND ?
                      AND deal_date >= ?
                      {contract_filter}
                    ORDER BY deal_date DESC""",
                (complex_code, area - 5, area + 5, cutoff)
            ).fetchall()
        elif apt_name and district_code:
            rows = self._conn.execute(
                f"""SELECT * FROM jeonse_transactions
                    WHERE apt_name = ?
                      AND district_code = ?
                      AND exclusive_area BETWEEN ? AND ?
                      AND deal_date >= ?
                      {contract_filter}
                    ORDER BY deal_date DESC""",
                (apt_name, district_code, area - 5, area + 5, cutoff)
            ).fetchall()
        else:
            return []

        return [JeonseTransaction(
            id=r["id"], complex_code=r["complex_code"], apt_name=r["apt_name"],
            district_code=r["district_code"], deal_date=r["deal_date"],
            exclusive_area=r["exclusive_area"], deposit=r["deposit"],
            monthly_rent=r["monthly_rent"], contract_type=r["contract_type"],
            floor=r["floor"]
        ) for r in rows]
```

- [ ] **Step 5: `__init__.py` 생성**

```python
# src/modules/real_estate/jeonse/__init__.py
# (empty)
```
```python
# tests/modules/real_estate/jeonse/__init__.py
# (empty)
```

- [ ] **Step 6: 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/jeonse/test_jeonse_repository.py -v
```
Expected: 5 tests PASS

- [ ] **Step 7: 커밋**

```bash
git add src/modules/real_estate/jeonse/ tests/modules/real_estate/jeonse/
git commit -m "feat(jeonse): JeonseTransaction 모델 + JeonseRepository CRUD"
```

---

## Task 2: JeonseClient (국토부 전세 API)

**Files:**
- Create: `src/modules/real_estate/jeonse/client.py`

국토부 전월세 API는 매매 API(`getRTMSDataSvcAptTradeDev`)와 구조가 동일하다. 기존 `MOLITClient`의 파싱 로직을 참고한다. API URL: `http://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent`

- [ ] **Step 1: client.py 작성**

```python
# src/modules/real_estate/jeonse/client.py
import os
import requests
import xml.etree.ElementTree as ET
from datetime import date
from typing import List
from core.logger import get_logger
from .models import JeonseTransaction

logger = get_logger(__name__)

_BASE_URL = "http://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent"


def _text(item: ET.Element, tag: str, default: str = "") -> str:
    el = item.find(tag)
    return el.text.strip() if el is not None and el.text else default


def _parse_date(year: str, month: str, day: str) -> str:
    try:
        m = month.strip().zfill(2)
        d = day.strip().zfill(2)
        return f"{year}-{m}-{d}"
    except Exception:
        return ""


class JeonseClient:
    def __init__(self):
        self._service_key = os.getenv("MOLIT_API_KEY", "")

    def fetch(self, district_code: str, year_month: str) -> List[JeonseTransaction]:
        """district_code: 5자리 법정동 코드, year_month: YYYYMM"""
        params = {
            "serviceKey": self._service_key,
            "pageNo": "1",
            "numOfRows": "1000",
            "LAWD_CD": district_code,
            "DEAL_YMD": year_month,
        }
        try:
            resp = requests.get(_BASE_URL, params=params, timeout=15)
            resp.raise_for_status()
            return self._parse(resp.text, district_code)
        except Exception as e:
            logger.error("[JeonseClient] fetch 실패 %s %s: %s", district_code, year_month, e)
            return []

    def _parse(self, xml_text: str, district_code: str) -> List[JeonseTransaction]:
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            logger.error("[JeonseClient] XML 파싱 실패: %s", e)
            return []

        results = []
        for item in root.iter("item"):
            apt_name = _text(item, "아파트")
            deposit_raw = _text(item, "보증금액").replace(",", "")
            monthly_raw = _text(item, "월세금액").replace(",", "")
            area_raw = _text(item, "전용면적")
            year = _text(item, "년")
            month = _text(item, "월")
            day = _text(item, "일")
            floor_raw = _text(item, "층")
            dong = _text(item, "법정동")

            try:
                deposit = int(deposit_raw) if deposit_raw else 0
                monthly_rent = int(monthly_raw) if monthly_raw else 0
                area = float(area_raw) if area_raw else 0.0
                floor = int(floor_raw) if floor_raw else 0
                deal_date = _parse_date(year, month, day)
                contract_type = "jeonse" if monthly_rent == 0 else "monthly"
            except (ValueError, TypeError):
                continue

            if not apt_name or deposit == 0 or area == 0.0 or not deal_date:
                continue

            results.append(JeonseTransaction(
                apt_name=apt_name,
                district_code=district_code,
                deal_date=deal_date,
                exclusive_area=area,
                deposit=deposit,
                monthly_rent=monthly_rent,
                contract_type=contract_type,
                floor=floor,
            ))
        logger.info("[JeonseClient] %s → %d건 파싱", district_code, len(results))
        return results
```

- [ ] **Step 2: 커밋**

```bash
git add src/modules/real_estate/jeonse/client.py
git commit -m "feat(jeonse): JeonseClient 국토부 전월세 API 연동"
```

---

## Task 3: POST /jobs/jeonse/collect 엔드포인트

**Files:**
- Modify: `src/api/routers/real_estate.py`
- Modify: `src/api/dependencies.py`

- [ ] **Step 1: dependencies.py에 JeonseRepository DI 추가** (`get_school_service()` 정의 아래에 추가)

```python
# src/api/dependencies.py 끝 부분에 추가
from modules.real_estate.jeonse.repository import JeonseRepository
from modules.real_estate.jeonse.client import JeonseClient

_jeonse_repo = JeonseRepository(db_path=_re_db_path)
_jeonse_client = JeonseClient()

def get_jeonse_repo() -> JeonseRepository:
    return _jeonse_repo

def get_jeonse_client() -> JeonseClient:
    return _jeonse_client
```

- [ ] **Step 2: real_estate.py 라우터에 엔드포인트 추가** (파일 끝에 추가)

```python
# src/api/routers/real_estate.py 상단 import에 추가
from api.dependencies import get_jeonse_repo, get_jeonse_client
from modules.real_estate.jeonse.repository import JeonseRepository
from modules.real_estate.jeonse.client import JeonseClient

# 엔드포인트 추가 (파일 끝)
class JeonseCollectRequest(BaseModel):
    district_codes: Optional[List[str]] = Field(None, description="수집할 법정동 코드 목록 (None=config 전체)")
    year_month: Optional[str] = Field(None, description="YYYYMM (기본: 이번달)")

@router.post("/jobs/jeonse/collect")
def collect_jeonse(
    request: JeonseCollectRequest = JeonseCollectRequest(),
    jeonse_repo: JeonseRepository = Depends(get_jeonse_repo),
    jeonse_client: JeonseClient = Depends(get_jeonse_client),
):
    from datetime import datetime as _dt
    from modules.real_estate.config import RealEstateConfig
    cfg = RealEstateConfig()
    target_ym = request.year_month or _dt.now().strftime("%Y%m")
    codes = request.district_codes or [d["code"] for d in cfg.get("districts", [])]

    total_saved = 0
    for code in codes:
        txs = jeonse_client.fetch(district_code=code, year_month=target_ym)
        saved = jeonse_repo.save_bulk(txs)
        total_saved += saved
        logger.info("[/jobs/jeonse/collect] %s: %d건 수집, %d건 저장", code, len(txs), saved)

    return {"year_month": target_ym, "district_count": len(codes), "saved_count": total_saved}
```

- [ ] **Step 3: 서버 기동 확인 (import 오류 없는지)**

```bash
arch -arm64 .venv/bin/python3.12 -c "from api.routers.real_estate import router; print('OK')"
```
Expected: `OK`

- [ ] **Step 4: 커밋**

```bash
git add src/api/dependencies.py src/api/routers/real_estate.py
git commit -m "feat(jeonse): POST /jobs/jeonse/collect 엔드포인트 추가"
```

---

## Task 4: SupplySchedule 모델 + SupplyRepository

**Files:**
- Create: `src/modules/real_estate/supply/__init__.py`
- Create: `src/modules/real_estate/supply/models.py`
- Create: `src/modules/real_estate/supply/repository.py`
- Create: `tests/modules/real_estate/supply/__init__.py`
- Create: `tests/modules/real_estate/supply/test_supply_repository.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/modules/real_estate/supply/test_supply_repository.py
import sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

from modules.real_estate.supply.repository import SupplyRepository
from modules.real_estate.supply.models import SupplySchedule


def _make_repo():
    tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    return SupplyRepository(db_path=tf.name)


def _supply(**kwargs):
    defaults = dict(
        project_name="잠실 파크원", sigungu_code="11710",
        lat=37.5120, lng=127.0986,
        household_count=500, expected_date="2026-10",
        supply_type="move_in"
    )
    defaults.update(kwargs)
    return SupplySchedule(**defaults)


def test_save_and_get_within_radius():
    repo = _make_repo()
    repo.save(_supply())
    # 잠실역 (37.5133, 127.1001) 기준 반경 2km
    results = repo.get_within_radius(lat=37.5133, lng=127.1001, radius_km=2.0, months_ahead=12)
    assert len(results) == 1
    assert results[0].household_count == 500


def test_outside_radius_excluded():
    repo = _make_repo()
    repo.save(_supply(lat=37.4500, lng=127.0000))  # 약 10km 떨어진 위치
    results = repo.get_within_radius(lat=37.5133, lng=127.1001, radius_km=2.0, months_ahead=12)
    assert len(results) == 0


def test_expired_date_excluded():
    repo = _make_repo()
    repo.save(_supply(expected_date="2025-01"))  # 이미 지난 날짜
    results = repo.get_within_radius(lat=37.5133, lng=127.1001, radius_km=2.0, months_ahead=12)
    assert len(results) == 0


def test_sum_nearby_units():
    repo = _make_repo()
    repo.save(_supply(household_count=300))
    repo.save(_supply(project_name="잠실 롯데캐슬", household_count=700))
    results = repo.get_within_radius(lat=37.5133, lng=127.1001, radius_km=2.0, months_ahead=12)
    total = sum(r.household_count for r in results)
    assert total == 1000
```

- [ ] **Step 2: 테스트 실행해서 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/supply/test_supply_repository.py -v
```
Expected: `ModuleNotFoundError`

- [ ] **Step 3: models.py 작성**

```python
# src/modules/real_estate/supply/models.py
from dataclasses import dataclass
from typing import Optional


@dataclass
class SupplySchedule:
    project_name: str
    sigungu_code: str
    lat: float
    lng: float
    household_count: int
    expected_date: str      # YYYY-MM
    supply_type: str        # 'sale' | 'move_in'
    id: Optional[int] = None
```

- [ ] **Step 4: repository.py 작성**

Haversine 공식으로 Python 단에서 반경 필터링한다 (SQLite에 수학 확장 없음).

```python
# src/modules/real_estate/supply/repository.py
import math
import sqlite3
from datetime import date
from typing import List
from .models import SupplySchedule

_DDL = """
CREATE TABLE IF NOT EXISTS supply_schedule (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_name    TEXT NOT NULL,
    sigungu_code    TEXT NOT NULL,
    lat             REAL NOT NULL,
    lng             REAL NOT NULL,
    household_count INTEGER NOT NULL,
    expected_date   TEXT NOT NULL,
    supply_type     TEXT NOT NULL DEFAULT 'move_in',
    collected_at    TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(project_name, expected_date)
);
"""


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


class SupplyRepository:
    def __init__(self, db_path: str):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_DDL)
        self._conn.commit()

    def save(self, s: SupplySchedule) -> None:
        self._conn.execute(
            """INSERT OR IGNORE INTO supply_schedule
               (project_name, sigungu_code, lat, lng, household_count, expected_date, supply_type)
               VALUES (?,?,?,?,?,?,?)""",
            (s.project_name, s.sigungu_code, s.lat, s.lng, s.household_count, s.expected_date, s.supply_type)
        )
        self._conn.commit()

    def save_bulk(self, items: List[SupplySchedule]) -> int:
        saved = 0
        for s in items:
            cur = self._conn.execute(
                """INSERT OR IGNORE INTO supply_schedule
                   (project_name, sigungu_code, lat, lng, household_count, expected_date, supply_type)
                   VALUES (?,?,?,?,?,?,?)""",
                (s.project_name, s.sigungu_code, s.lat, s.lng, s.household_count, s.expected_date, s.supply_type)
            )
            saved += cur.rowcount
        self._conn.commit()
        return saved

    def get_within_radius(
        self, lat: float, lng: float, radius_km: float = 2.0, months_ahead: int = 12
    ) -> List[SupplySchedule]:
        today = date.today()
        cutoff = f"{today.year + (today.month + months_ahead - 1) // 12:04d}-{(today.month + months_ahead - 1) % 12 + 1:02d}"
        today_str = today.strftime("%Y-%m")

        rows = self._conn.execute(
            "SELECT * FROM supply_schedule WHERE expected_date >= ? AND expected_date <= ?",
            (today_str, cutoff)
        ).fetchall()

        return [
            SupplySchedule(
                id=r["id"], project_name=r["project_name"], sigungu_code=r["sigungu_code"],
                lat=r["lat"], lng=r["lng"], household_count=r["household_count"],
                expected_date=r["expected_date"], supply_type=r["supply_type"]
            )
            for r in rows
            if _haversine_km(lat, lng, r["lat"], r["lng"]) <= radius_km
        ]
```

- [ ] **Step 5: `__init__.py` 생성**

```python
# src/modules/real_estate/supply/__init__.py  (empty)
# tests/modules/real_estate/supply/__init__.py  (empty)
```

- [ ] **Step 6: 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/supply/test_supply_repository.py -v
```
Expected: 4 tests PASS

- [ ] **Step 7: 커밋**

```bash
git add src/modules/real_estate/supply/ tests/modules/real_estate/supply/__init__.py tests/modules/real_estate/supply/test_supply_repository.py
git commit -m "feat(supply): SupplySchedule 모델 + SupplyRepository Haversine 반경 쿼리"
```

---

## Task 5: SupplyClient (청약홈 API) + POST /jobs/supply/collect

**Files:**
- Create: `src/modules/real_estate/supply/client.py`
- Modify: `src/api/dependencies.py`
- Modify: `src/api/routers/real_estate.py`

청약홈 API: `https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/getAPTLttotPblancDetail`  
응답에 `HOUSE_NM`(단지명), `SUBSCRPT_AREA_CODE_NM`(지역), `TOT_SUPLY_HSHLDCO`(총공급세대수), `RCEPT_BGNDE`(접수시작일), `MVIN_PREARNGE_YM`(입주예정년월) 포함.

- [ ] **Step 1: client.py 작성**

```python
# src/modules/real_estate/supply/client.py
import os
import requests
from typing import List
from core.logger import get_logger
from .models import SupplySchedule

logger = get_logger(__name__)

_BASE_URL = "https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/getAPTLttotPblancDetail"

# 시군구명 → sigungu_code 매핑 (주요 수도권)
_SIGUNGU_MAP = {
    "서초구": "11650", "강남구": "11680", "송파구": "11710", "강동구": "11740",
    "성동구": "11200", "광진구": "11215", "용산구": "11170", "종로구": "11110",
    "강서구": "11500", "마포구": "11440", "성북구": "11290", "노원구": "11350",
    "분당구": "41135", "수정구": "41131", "중원구": "41133",
}


class SupplyClient:
    def __init__(self):
        self._key = os.getenv("APPLYHOME_API_KEY", "")

    def fetch(self, page: int = 1, per_page: int = 100) -> List[SupplySchedule]:
        params = {
            "serviceKey": self._key,
            "page": page,
            "perPage": per_page,
        }
        try:
            resp = requests.get(_BASE_URL, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error("[SupplyClient] fetch 실패: %s", e)
            return []

        results = []
        for item in data.get("data", []):
            name = item.get("HOUSE_NM", "")
            area_nm = item.get("SUBSCRPT_AREA_CODE_NM", "")
            count_raw = item.get("TOT_SUPLY_HSHLDCO", 0)
            mvin_ym = item.get("MVIN_PREARNGE_YM", "")
            sigungu_code = _SIGUNGU_MAP.get(area_nm, "")

            try:
                count = int(count_raw) if count_raw else 0
                expected = f"{mvin_ym[:4]}-{mvin_ym[4:6]}" if len(str(mvin_ym)) >= 6 else ""
            except (ValueError, TypeError):
                continue

            if not name or count == 0 or not expected or not sigungu_code:
                continue

            # 좌표는 geocoder 없이 sigungu 중심 좌표 사용 (근사치)
            lat, lng = self._sigungu_centroid(sigungu_code)
            results.append(SupplySchedule(
                project_name=name, sigungu_code=sigungu_code,
                lat=lat, lng=lng,
                household_count=count, expected_date=expected,
                supply_type="move_in"
            ))
        logger.info("[SupplyClient] %d건 파싱", len(results))
        return results

    def _sigungu_centroid(self, code: str):
        _CENTROIDS = {
            "11650": (37.4837, 127.0324), "11680": (37.5172, 127.0473),
            "11710": (37.5145, 127.1059), "11740": (37.5301, 127.1238),
            "11200": (37.5633, 127.0371), "11215": (37.5384, 127.0822),
            "11170": (37.5384, 126.9654), "11110": (37.5730, 126.9794),
            "11500": (37.5509, 126.8495), "11440": (37.5663, 126.9010),
            "11290": (37.5894, 127.0167), "11350": (37.6541, 127.0568),
            "41135": (37.3825, 127.1195), "41131": (37.4474, 127.1370),
            "41133": (37.4200, 127.1264),
        }
        return _CENTROIDS.get(code, (37.5665, 126.9780))
```

- [ ] **Step 2: dependencies.py에 추가** (`get_jeonse_client()` 아래에)

```python
from modules.real_estate.supply.repository import SupplyRepository
from modules.real_estate.supply.client import SupplyClient

_supply_repo = SupplyRepository(db_path=_re_db_path)
_supply_client = SupplyClient()

def get_supply_repo() -> SupplyRepository:
    return _supply_repo

def get_supply_client() -> SupplyClient:
    return _supply_client
```

- [ ] **Step 3: real_estate.py 라우터에 엔드포인트 추가**

```python
# import 추가
from api.dependencies import get_supply_repo, get_supply_client
from modules.real_estate.supply.repository import SupplyRepository
from modules.real_estate.supply.client import SupplyClient

# 엔드포인트 추가
@router.post("/jobs/supply/collect")
def collect_supply(
    supply_repo: SupplyRepository = Depends(get_supply_repo),
    supply_client: SupplyClient = Depends(get_supply_client),
):
    results = supply_client.fetch(page=1, per_page=500)
    saved = supply_repo.save_bulk(results)
    return {"fetched_count": len(results), "saved_count": saved}
```

- [ ] **Step 4: import 확인**

```bash
arch -arm64 .venv/bin/python3.12 -c "from api.routers.real_estate import router; print('OK')"
```
Expected: `OK`

- [ ] **Step 5: 커밋**

```bash
git add src/modules/real_estate/supply/client.py src/api/dependencies.py src/api/routers/real_estate.py
git commit -m "feat(supply): SupplyClient + POST /jobs/supply/collect 엔드포인트"
```

---

## Task 6: ComparativeAnalyzer

**Files:**
- Create: `src/modules/real_estate/comparative/__init__.py`
- Create: `src/modules/real_estate/comparative/models.py`
- Create: `src/modules/real_estate/comparative/analyzer.py`
- Create: `tests/modules/real_estate/comparative/__init__.py`
- Create: `tests/modules/real_estate/comparative/test_comparative_analyzer.py`

- [ ] **Step 1: 테스트 작성**

```python
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
    # 4개 단지 평균 ≈ (1030M+980M+870M+930M)/4 / 84 ≈ 11,369만원/㎡
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
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/comparative/test_comparative_analyzer.py -v
```
Expected: `ModuleNotFoundError`

- [ ] **Step 3: models.py 작성**

```python
# src/modules/real_estate/comparative/models.py
from dataclasses import dataclass, field
from typing import List


@dataclass
class SimilarUnit:
    name: str
    price_per_sqm: float    # 원/㎡


@dataclass
class ComparativeResult:
    district_avg_per_sqm: float     # 원/㎡
    pct_vs_avg: float               # %, 양수=비쌈 음수=저렴
    similar_units: List[SimilarUnit] = field(default_factory=list)
```

- [ ] **Step 4: analyzer.py 작성**

```python
# src/modules/real_estate/comparative/analyzer.py
from datetime import date, timedelta
from typing import TYPE_CHECKING
from core.logger import get_logger
from .models import ComparativeResult, SimilarUnit

if TYPE_CHECKING:
    from modules.real_estate.transaction_repository import TransactionRepository

logger = get_logger(__name__)


class ComparativeAnalyzer:
    def __init__(self, tx_repo: "TransactionRepository", lookback_days: int = 90):
        self._repo = tx_repo
        self._lookback_days = lookback_days

    def analyze(
        self,
        complex_code: str,
        district_code: str,
        exclusive_area: float,
        build_year: int,
        avg_sale_price: int,
    ) -> ComparativeResult:
        cutoff = (date.today() - timedelta(days=self._lookback_days)).isoformat()
        area_lo, area_hi = exclusive_area - 10, exclusive_area + 10
        year_lo, year_hi = build_year - 5, build_year + 5

        try:
            rows = self._repo._conn.execute(
                """SELECT apt_name,
                          avg(CAST(price AS REAL) / exclusive_area) AS avg_per_sqm,
                          count(*) AS cnt
                   FROM transactions
                   WHERE district_code = ?
                     AND exclusive_area BETWEEN ? AND ?
                     AND build_year BETWEEN ? AND ?
                     AND deal_date >= ?
                   GROUP BY apt_name
                   ORDER BY cnt DESC""",
                (district_code, area_lo, area_hi, year_lo, year_hi, cutoff)
            ).fetchall()
        except Exception as e:
            logger.warning("[ComparativeAnalyzer] 쿼리 실패: %s", e)
            return ComparativeResult(district_avg_per_sqm=0.0, pct_vs_avg=0.0)

        if not rows:
            return ComparativeResult(district_avg_per_sqm=0.0, pct_vs_avg=0.0)

        all_avg = sum(r["avg_per_sqm"] for r in rows) / len(rows)
        my_per_sqm = avg_sale_price / exclusive_area if exclusive_area > 0 else 0
        pct = ((my_per_sqm - all_avg) / all_avg * 100) if all_avg > 0 else 0.0

        # complex_code 또는 apt_name으로 본 단지 제외 후 유사 단지 상위 3개
        similar = [
            SimilarUnit(name=r["apt_name"], price_per_sqm=r["avg_per_sqm"])
            for r in rows
            if r["apt_name"] != self._get_name_for_code(complex_code)
        ][:3]

        return ComparativeResult(
            district_avg_per_sqm=round(all_avg, 0),
            pct_vs_avg=round(pct, 1),
            similar_units=similar,
        )

    def _get_name_for_code(self, complex_code: str) -> str:
        try:
            row = self._repo._conn.execute(
                "SELECT apt_name FROM transactions WHERE complex_code = ? LIMIT 1",
                (complex_code,)
            ).fetchone()
            return row["apt_name"] if row else ""
        except Exception:
            return ""
```

- [ ] **Step 5: `__init__.py` 생성**

```python
# src/modules/real_estate/comparative/__init__.py  (empty)
# tests/modules/real_estate/comparative/__init__.py  (empty)
```

- [ ] **Step 6: 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/comparative/test_comparative_analyzer.py -v
```
Expected: 3 tests PASS

- [ ] **Step 7: 커밋**

```bash
git add src/modules/real_estate/comparative/ tests/modules/real_estate/comparative/
git commit -m "feat(comparative): ComparativeAnalyzer 구 평균·유사 단지 비교"
```

---

## Task 7: YieldCalculator

**Files:**
- Create: `src/modules/real_estate/yield_analysis/__init__.py`
- Create: `src/modules/real_estate/yield_analysis/models.py`
- Create: `src/modules/real_estate/yield_analysis/calculator.py`
- Create: `tests/modules/real_estate/yield_analysis/__init__.py`
- Create: `tests/modules/real_estate/yield_analysis/test_yield_calculator.py`

- [ ] **Step 1: 테스트 작성**

```python
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
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/yield_analysis/test_yield_calculator.py -v
```
Expected: `ModuleNotFoundError`

- [ ] **Step 3: models.py 작성**

```python
# src/modules/real_estate/yield_analysis/models.py
from dataclasses import dataclass


@dataclass
class YieldResult:
    jeonse_rate: float      # 전세가율 0~1
    jeonse_avg: int         # 평균 전세가(만원)
    gap_cost: int           # 갭투자 비용(만원) = 매매가 - 전세가
    monthly_cost: int       # 월 보유비용(만원) = 원리금 + 관리비 15만원
    jeonse_sample: int      # 표본 건수
```

- [ ] **Step 4: calculator.py 작성**

```python
# src/modules/real_estate/yield_analysis/calculator.py
import math
from typing import Optional, TYPE_CHECKING
from core.logger import get_logger
from .models import YieldResult

if TYPE_CHECKING:
    from modules.real_estate.jeonse.repository import JeonseRepository

logger = get_logger(__name__)

_LTV = 0.70
_LOAN_MONTHS = 360
_MAINTENANCE_FEE = 15  # 만원


class YieldCalculator:
    def __init__(self, jeonse_repo: "JeonseRepository", mortgage_rate: float = 0.0283):
        self._repo = jeonse_repo
        self._rate = mortgage_rate

    def calculate(
        self,
        complex_code: Optional[str],
        apt_name: str,
        district_code: str,
        exclusive_area: float,
        avg_sale_price: int,    # 만원 단위
    ) -> Optional[YieldResult]:
        txs = self._repo.get_recent(
            complex_code=complex_code,
            area=exclusive_area,
            months=6,
            apt_name=apt_name,
            district_code=district_code,
            jeonse_only=True,
        )
        if not txs:
            return None

        avg_deposit = sum(t.deposit for t in txs) // len(txs)
        jeonse_rate = avg_deposit / avg_sale_price if avg_sale_price > 0 else 0.0
        gap_cost = avg_sale_price - avg_deposit
        monthly_cost = self._calc_monthly_cost(avg_sale_price) + _MAINTENANCE_FEE

        return YieldResult(
            jeonse_rate=round(jeonse_rate, 4),
            jeonse_avg=avg_deposit,
            gap_cost=gap_cost,
            monthly_cost=monthly_cost,
            jeonse_sample=len(txs),
        )

    def _calc_monthly_cost(self, sale_price_man: int) -> int:
        """LTV 70% 대출 기준 월 원리금(만원). sale_price_man: 만원 단위."""
        principal = sale_price_man * _LTV
        r = self._rate / 12
        if r == 0:
            return int(principal / _LOAN_MONTHS)
        pmt = principal * r / (1 - (1 + r) ** (-_LOAN_MONTHS))
        return int(pmt)
```

- [ ] **Step 5: `__init__.py` 생성**

```python
# src/modules/real_estate/yield_analysis/__init__.py  (empty)
# tests/modules/real_estate/yield_analysis/__init__.py  (empty)
```

- [ ] **Step 6: 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/yield_analysis/test_yield_calculator.py -v
```
Expected: 4 tests PASS

- [ ] **Step 7: 커밋**

```bash
git add src/modules/real_estate/yield_analysis/ tests/modules/real_estate/yield_analysis/
git commit -m "feat(yield): YieldCalculator 전세가율·갭투자비용·월보유비용 계산"
```

---

## Task 8: news_catalyst_classifier 프롬프트 + SupplyRiskAnalyzer

**Files:**
- Create: `src/modules/real_estate/prompts/news_catalyst_classifier.md`
- Create: `src/modules/real_estate/supply/risk_analyzer.py`
- Create: `tests/modules/real_estate/supply/test_supply_risk_analyzer.py`

- [ ] **Step 1: news_catalyst_classifier.md 작성**

```markdown
---
task_type: REAL_ESTATE_ANALYSIS
output_format: json
---

아래 뉴스 기사 목록에서 주어진 단지/지역과 관련된 호재(positive) 또는 악재(negative) 정보를 추출하세요.

[분석 대상]
단지명: {{apt_name}}
지역: {{sigungu}}

[뉴스 기사]
{{news_list}}

---

JSON 형식으로만 응답하세요. 다른 텍스트는 포함하지 마세요.

```json
{
  "catalysts": [
    {
      "type": "positive",
      "title": "관련 기사 제목 (30자 이내로 요약)",
      "date": "YYYY-MM-DD"
    }
  ]
}
```

규칙:
- 단지명 또는 지역과 직접 관련된 기사만 포함하세요.
- 관련 없는 기사는 제외하세요.
- type은 반드시 "positive" 또는 "negative" 중 하나여야 합니다.
- 호재 예시: GTX 개통, 재개발 확정, 대형 쇼핑몰 입점, 학교 신설
- 악재 예시: 공급 과잉, 재건축 불허, 혐오시설 입주, 규제 강화
- catalysts가 없으면 빈 배열 []을 반환하세요.
```

- [ ] **Step 2: 테스트 작성**

```python
# tests/modules/real_estate/supply/test_supply_risk_analyzer.py
import sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

from unittest.mock import MagicMock
from modules.real_estate.supply.risk_analyzer import SupplyRiskAnalyzer
from modules.real_estate.supply.repository import SupplyRepository
from modules.real_estate.supply.models import SupplySchedule


def _make_supply_repo(lat=37.5120, lng=127.0986, units=500, expected="2026-10"):
    tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    repo = SupplyRepository(db_path=tf.name)
    if units > 0:
        repo.save(SupplySchedule(
            project_name="잠실파크원", sigungu_code="11710",
            lat=lat, lng=lng, household_count=units,
            expected_date=expected, supply_type="move_in"
        ))
    return repo


def _make_news_service(articles=None):
    svc = MagicMock()
    svc.get_categorized_news.return_value = articles or []
    return svc


def _make_llm(catalysts=None):
    llm = MagicMock()
    llm.generate_json.return_value = {"catalysts": catalysts or []}
    return llm


def _make_prompt_loader():
    loader = MagicMock()
    loader.load.return_value = ({}, "dummy prompt")
    return loader


def test_supply_nearby_units_counted():
    repo = _make_supply_repo(units=500)
    analyzer = SupplyRiskAnalyzer(
        supply_repo=repo, news_service=_make_news_service(),
        llm=_make_llm(), prompt_loader=_make_prompt_loader()
    )
    result = analyzer.analyze(lat=37.5133, lng=127.1001, apt_name="현대7", sigungu="송파구")
    assert result.nearby_units == 500


def test_no_supply_returns_zero():
    tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    empty_repo = SupplyRepository(db_path=tf.name)
    analyzer = SupplyRiskAnalyzer(
        supply_repo=empty_repo, news_service=_make_news_service(),
        llm=_make_llm(), prompt_loader=_make_prompt_loader()
    )
    result = analyzer.analyze(lat=37.5133, lng=127.1001, apt_name="현대7", sigungu="송파구")
    assert result.nearby_units == 0
    assert result.news_catalysts == []


def test_positive_catalyst_from_llm():
    repo = _make_supply_repo(units=0)
    articles = [{"title": "GTX-A 개통 확정", "description": "2027년 개통", "pub_date": "2026-05-10"}]
    catalysts = [{"type": "positive", "title": "GTX-A 개통 확정", "date": "2026-05-10"}]
    analyzer = SupplyRiskAnalyzer(
        supply_repo=repo, news_service=_make_news_service(articles),
        llm=_make_llm(catalysts), prompt_loader=_make_prompt_loader()
    )
    result = analyzer.analyze(lat=37.5133, lng=127.1001, apt_name="현대7", sigungu="송파구")
    assert len(result.news_catalysts) == 1
    assert result.news_catalysts[0]["type"] == "positive"


def test_no_news_returns_empty_catalysts():
    repo = _make_supply_repo(units=0)
    analyzer = SupplyRiskAnalyzer(
        supply_repo=repo, news_service=_make_news_service(articles=[]),
        llm=_make_llm(), prompt_loader=_make_prompt_loader()
    )
    result = analyzer.analyze(lat=37.5133, lng=127.1001, apt_name="현대7", sigungu="송파구")
    assert result.news_catalysts == []
    # 뉴스 없으면 LLM 호출 안 함
    analyzer._llm.generate_json.assert_not_called()
```

- [ ] **Step 3: 테스트 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/supply/test_supply_risk_analyzer.py -v
```
Expected: `ModuleNotFoundError`

- [ ] **Step 4: risk_analyzer.py 작성**

```python
# src/modules/real_estate/supply/risk_analyzer.py
from dataclasses import dataclass, field
from typing import List, TYPE_CHECKING
from core.logger import get_logger

if TYPE_CHECKING:
    from modules.real_estate.supply.repository import SupplyRepository
    from modules.real_estate.news.service import NewsService
    from core.llm import BaseLLMClient
    from core.prompt_loader import PromptLoader

logger = get_logger(__name__)


@dataclass
class SupplyRiskResult:
    nearby_units: int
    supply_period: str          # e.g. "2026H2"
    news_catalysts: List[dict] = field(default_factory=list)


def _period_label(expected_dates: List[str]) -> str:
    if not expected_dates:
        return ""
    dates = sorted(expected_dates)
    first = dates[0]
    try:
        year, month = int(first[:4]), int(first[5:7])
        half = "H1" if month <= 6 else "H2"
        return f"{year}{half}"
    except (ValueError, IndexError):
        return first


class SupplyRiskAnalyzer:
    def __init__(
        self,
        supply_repo: "SupplyRepository",
        news_service: "NewsService",
        llm: "BaseLLMClient",
        prompt_loader: "PromptLoader",
        radius_km: float = 2.0,
        months_ahead: int = 12,
    ):
        self._supply_repo = supply_repo
        self._news_service = news_service
        self._llm = llm
        self._prompt_loader = prompt_loader
        self._radius_km = radius_km
        self._months_ahead = months_ahead

    def analyze(self, lat: float, lng: float, apt_name: str, sigungu: str) -> SupplyRiskResult:
        supply_items = self._supply_repo.get_within_radius(
            lat=lat, lng=lng,
            radius_km=self._radius_km,
            months_ahead=self._months_ahead,
        )
        nearby_units = sum(s.household_count for s in supply_items)
        period = _period_label([s.expected_date for s in supply_items])

        articles = self._news_service.get_categorized_news(
            query=f"{apt_name} {sigungu}", display=10
        )
        catalysts = self._classify_catalysts(articles, apt_name, sigungu)

        return SupplyRiskResult(
            nearby_units=nearby_units,
            supply_period=period,
            news_catalysts=catalysts,
        )

    def _classify_catalysts(
        self, articles: List[dict], apt_name: str, sigungu: str
    ) -> List[dict]:
        if not articles:
            return []

        news_list = "\n".join(
            f"{i+1}. [{a.get('pub_date','')}] {a.get('title','')} — {a.get('description','')[:80]}"
            for i, a in enumerate(articles)
        )
        try:
            _, prompt = self._prompt_loader.load(
                "news_catalyst_classifier",
                variables={"apt_name": apt_name, "sigungu": sigungu, "news_list": news_list},
            )
            result = self._llm.generate_json(prompt)
            return result.get("catalysts", [])
        except Exception as e:
            logger.warning("[SupplyRiskAnalyzer] LLM 분류 실패: %s", e)
            return []
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/supply/test_supply_risk_analyzer.py -v
```
Expected: 4 tests PASS

- [ ] **Step 6: 커밋**

```bash
git add src/modules/real_estate/prompts/news_catalyst_classifier.md src/modules/real_estate/supply/risk_analyzer.py tests/modules/real_estate/supply/test_supply_risk_analyzer.py
git commit -m "feat(supply): SupplyRiskAnalyzer 공급물량+뉴스 호재/악재 분석"
```

---

## Task 9: _enrich_with_* 함수 추가 (report_orchestrator.py)

**Files:**
- Modify: `src/modules/real_estate/report_orchestrator.py`

기존 `_enrich_with_trend()` 함수 아래에 3개 함수를 추가한다.

- [ ] **Step 1: report_orchestrator.py 끝에 3개 함수 추가**

파일 끝에 다음을 추가한다 (기존 함수들 변경 없음):

```python
# src/modules/real_estate/report_orchestrator.py 끝에 추가

def _enrich_with_comparative(candidates: List[Dict], analyzer) -> List[Dict]:
    """ComparativeAnalyzer → _comp_* 필드 주입. analyzer가 None이면 no-op."""
    if analyzer is None:
        return candidates
    enriched = []
    for c in candidates:
        result = dict(c)
        try:
            comp = analyzer.analyze(
                complex_code=c.get("complex_code", ""),
                district_code=c.get("district_code", ""),
                exclusive_area=c.get("exclusive_area", 84.0),
                build_year=c.get("build_year", 2000),
                avg_sale_price=c.get("avg_recent_price", 0),
            )
            result["_comp_district_avg_per_sqm"] = comp.district_avg_per_sqm
            result["_comp_pct_vs_avg"] = comp.pct_vs_avg
            result["_comp_similar_units"] = [
                {"name": u.name, "price_per_sqm": u.price_per_sqm}
                for u in comp.similar_units
            ]
        except Exception as e:
            logger.warning("[Comparative] 실패 %s: %s", c.get("apt_name"), e)
        enriched.append(result)
    return enriched


def _enrich_with_yield(candidates: List[Dict], calculator) -> List[Dict]:
    """YieldCalculator → _yield_* 필드 주입. calculator가 None이면 no-op."""
    if calculator is None:
        return candidates
    enriched = []
    for c in candidates:
        result = dict(c)
        try:
            yr = calculator.calculate(
                complex_code=c.get("complex_code"),
                apt_name=c.get("apt_name", ""),
                district_code=c.get("district_code", ""),
                exclusive_area=c.get("exclusive_area", 84.0),
                avg_sale_price=int(c.get("avg_recent_price", 0) / 10000),
            )
            if yr is not None:
                result["_yield_jeonse_rate"] = yr.jeonse_rate
                result["_yield_jeonse_avg"] = yr.jeonse_avg
                result["_yield_gap_cost"] = yr.gap_cost
                result["_yield_monthly_cost"] = yr.monthly_cost
                result["_yield_jeonse_sample"] = yr.jeonse_sample
        except Exception as e:
            logger.warning("[Yield] 실패 %s: %s", c.get("apt_name"), e)
        enriched.append(result)
    return enriched


def _enrich_with_supply(candidates: List[Dict], analyzer) -> List[Dict]:
    """SupplyRiskAnalyzer → _supply_* / _news_catalysts 필드 주입. analyzer가 None이면 no-op."""
    if analyzer is None:
        return candidates
    enriched = []
    for c in candidates:
        result = dict(c)
        lat, lng = c.get("lat"), c.get("lng")
        if lat and lng:
            try:
                risk = analyzer.analyze(
                    lat=lat, lng=lng,
                    apt_name=c.get("apt_name", ""),
                    sigungu=c.get("sigungu", ""),
                )
                result["_supply_nearby_units"] = risk.nearby_units
                result["_supply_period"] = risk.supply_period
                result["_news_catalysts"] = risk.news_catalysts
            except Exception as e:
                logger.warning("[Supply] 실패 %s: %s", c.get("apt_name"), e)
        enriched.append(result)
    return enriched
```

- [ ] **Step 2: import 확인**

```bash
arch -arm64 .venv/bin/python3.12 -c "from modules.real_estate.report_orchestrator import _enrich_with_comparative, _enrich_with_yield, _enrich_with_supply; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: 커밋**

```bash
git add src/modules/real_estate/report_orchestrator.py
git commit -m "feat(orchestrator): _enrich_with_comparative/yield/supply 함수 추가"
```

---

## Task 10: report_types.py + report_formatter.py (3개 TypedDict + render 함수)

**Files:**
- Modify: `src/modules/real_estate/daily_report/report_types.py`
- Modify: `src/modules/real_estate/daily_report/report_formatter.py`
- Create: `tests/modules/real_estate/daily_report/test_report_formatter_new_blocks.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/modules/real_estate/daily_report/test_report_formatter_new_blocks.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

from modules.real_estate.daily_report.report_formatter import (
    render_price_comparison, render_yield_analysis, render_supply_risk,
)
from modules.real_estate.daily_report.report_types import CompData, YieldData, SupplyData


def test_render_price_comparison_shows_pct():
    comp = CompData(
        district_avg_per_sqm=12000000.0, pct_vs_avg=-7.8,
        similar_units=[{"name": "잠실엘스", "price_per_sqm": 12310000.0}]
    )
    output = render_price_comparison(comp)
    assert "-7.8%" in output
    assert "잠실엘스" in output


def test_render_price_comparison_none_returns_empty():
    assert render_price_comparison(None) == ""


def test_render_yield_analysis_shows_rate():
    yield_r = YieldData(
        jeonse_rate=0.624, jeonse_avg=58000, gap_cost=35000,
        monthly_cost=187, jeonse_sample=3
    )
    output = render_yield_analysis(yield_r)
    assert "62.4%" in output
    assert "3.5억" in output  # gap_cost 35000만원 = 3.5억


def test_render_yield_analysis_none_returns_empty():
    assert render_yield_analysis(None) == ""


def test_render_supply_risk_shows_units():
    supply = SupplyData(
        nearby_units=2340, supply_period="2026H2",
        news_catalysts=[{"type": "positive", "title": "GTX-A 개통", "date": "2026-05-10"}]
    )
    output = render_supply_risk(supply)
    assert "2,340" in output
    assert "GTX-A" in output


def test_render_supply_risk_no_units():
    supply = SupplyData(nearby_units=0, supply_period="", news_catalysts=[])
    output = render_supply_risk(supply)
    assert "공급 없음" in output or output == "" or "0" in output
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/daily_report/test_report_formatter_new_blocks.py -v
```
Expected: `ImportError` (아직 CompData 등 없음)

- [ ] **Step 3: report_types.py에 3개 TypedDict 추가** (파일 끝에 추가)

```python
# src/modules/real_estate/daily_report/report_types.py 끝에 추가

class SimilarUnitData(TypedDict):
    name: str
    price_per_sqm: float


class CompData(TypedDict, total=False):
    district_avg_per_sqm: float
    pct_vs_avg: float
    similar_units: List[SimilarUnitData]


class YieldData(TypedDict, total=False):
    jeonse_rate: float
    jeonse_avg: int
    gap_cost: int
    monthly_cost: int
    jeonse_sample: int


class SupplyData(TypedDict, total=False):
    nearby_units: int
    supply_period: str
    news_catalysts: List[dict]
```

- [ ] **Step 4: report_formatter.py에 3개 render 함수 추가** (`render_verdict` 함수 위에 삽입)

```python
# src/modules/real_estate/daily_report/report_formatter.py 에 추가
# import 줄에 아래 3개 TypedDict import 추가:
from .report_types import TrendData, CommuteData, LocationSummaryData, CompData, YieldData, SupplyData


def render_price_comparison(comp: Optional["CompData"]) -> str:
    if not comp or not comp.get("district_avg_per_sqm"):
        return ""
    avg_man = comp["district_avg_per_sqm"] / 10000
    pct = comp["pct_vs_avg"]
    sign = "▲" if pct > 0 else "▼"
    color_word = "비쌈" if pct > 0 else "저렴"
    lines = [f"**💹 가격 위치** — 구 평균 ㎡당 {avg_man:.0f}만원 대비 {sign} {abs(pct):.1f}% {color_word}"]
    similars = comp.get("similar_units", [])
    if similars:
        parts = [f"{u['name']} {u['price_per_sqm']/10000:.0f}만" for u in similars[:3]]
        lines.append(f"유사 단지: {' · '.join(parts)}")
    return "\n".join(lines)


def render_yield_analysis(yield_r: Optional["YieldData"]) -> str:
    if not yield_r or yield_r.get("jeonse_rate") is None:
        return ""
    rate_pct = yield_r["jeonse_rate"] * 100
    gap_eok = yield_r["gap_cost"] / 10000
    monthly = yield_r["monthly_cost"]
    sample = yield_r.get("jeonse_sample", 0)
    return (
        f"**🏠 수익 구조** — 전세가율 {rate_pct:.1f}% · "
        f"갭투자 {gap_eok:.1f}억 · 월 보유비용 {monthly}만원 "
        f"*(전세 {sample}건 기준)*"
    )


def render_supply_risk(supply: Optional["SupplyData"]) -> str:
    if not supply:
        return ""
    units = supply.get("nearby_units", 0)
    period = supply.get("supply_period", "")
    catalysts = supply.get("news_catalysts", [])

    lines = []
    if units > 0:
        lines.append(f"⚠️ **공급 리스크** — 반경 2km {units:,}세대 입주 예정 ({period})")
    else:
        lines.append("✅ **공급 리스크** — 반경 2km 입주 예정 물량 없음")

    for cat in catalysts[:3]:
        icon = "✅" if cat.get("type") == "positive" else "❌"
        lines.append(f"{icon} {cat.get('title', '')}")

    return "\n".join(lines)
```

- [ ] **Step 5: build_candidate_card()에 3개 블록 추가**

`report_formatter.py`의 `build_candidate_card()` 함수 내 `parts` 리스트를 수정한다:

```python
def build_candidate_card(c: dict, index: int = 0) -> str:
    trend = _extract_trend(c)
    commute = _extract_commute(c)
    location = _extract_location_summary(c)
    ls = c.get("_location_score")

    # 신규 3개 데이터 추출
    comp = _extract_comp(c)
    yield_r = _extract_yield(c)
    supply = _extract_supply(c)

    parts = [
        _render_header(c, index),
        render_price_comparison(comp),
        render_trend(trend),
        render_commute(commute),
        render_location_summary(location) if location else "",
        render_yield_analysis(yield_r),
        render_supply_risk(supply),
        render_scores(ls.residential_results, ls.investment_results) if ls else "",
        render_verdict(c.get("_verdict", "")),
        render_keypoints(c.get("_key_points", [])),
    ]
    return "\n\n".join(p for p in parts if p)
```

그리고 `build_candidate_card()` 위에 3개 extract 헬퍼 추가:

```python
def _extract_comp(c: dict) -> Optional[CompData]:
    if c.get("_comp_district_avg_per_sqm") is None:
        return None
    return CompData(
        district_avg_per_sqm=c["_comp_district_avg_per_sqm"],
        pct_vs_avg=c.get("_comp_pct_vs_avg", 0.0),
        similar_units=c.get("_comp_similar_units", []),
    )


def _extract_yield(c: dict) -> Optional[YieldData]:
    if c.get("_yield_jeonse_rate") is None:
        return None
    return YieldData(
        jeonse_rate=c["_yield_jeonse_rate"],
        jeonse_avg=c.get("_yield_jeonse_avg", 0),
        gap_cost=c.get("_yield_gap_cost", 0),
        monthly_cost=c.get("_yield_monthly_cost", 0),
        jeonse_sample=c.get("_yield_jeonse_sample", 0),
    )


def _extract_supply(c: dict) -> Optional[SupplyData]:
    if c.get("_supply_nearby_units") is None and not c.get("_news_catalysts"):
        return None
    return SupplyData(
        nearby_units=c.get("_supply_nearby_units", 0),
        supply_period=c.get("_supply_period", ""),
        news_catalysts=c.get("_news_catalysts", []),
    )
```

- [ ] **Step 6: 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/daily_report/test_report_formatter_new_blocks.py -v
```
Expected: 6 tests PASS

- [ ] **Step 7: 기존 formatter 테스트도 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/daily_report/ -v
```
Expected: all PASS (기존 테스트 회귀 없음)

- [ ] **Step 8: 커밋**

```bash
git add src/modules/real_estate/daily_report/report_types.py src/modules/real_estate/daily_report/report_formatter.py tests/modules/real_estate/daily_report/test_report_formatter_new_blocks.py
git commit -m "feat(formatter): CompData/YieldData/SupplyData + render_price_comparison/yield/supply 추가"
```

---

## Task 11: daily_strategy.md 프롬프트 수정 + _format_candidate_for_llm() 업데이트

**Files:**
- Modify: `src/modules/real_estate/prompts/daily_strategy.md`
- Modify: `src/modules/real_estate/daily_report/daily_report_orchestrator.py`

- [ ] **Step 1: daily_strategy.md에 3개 변수 추가**

`[주목 단지 {{candidate_count}}개]` 섹션 아래 `{{candidates_text}}` 변수가 있다. `_format_candidate_for_llm()`이 이미 candidates_text를 구성하므로 프롬프트 변수 추가가 아니라 candidates_text 포맷 안에 새 데이터가 포함되는 방식이다.

`daily_strategy.md`의 verdict 지시만 수정한다:

```markdown
# src/modules/real_estate/prompts/daily_strategy.md 에서
# "verdict" 줄을 아래로 교체:

      "verdict": "수치 기반 매수/관망/회피 한 줄 판단 — 타깃 가격 또는 조건 포함 (50자 이내, 예: '8.8억 이하 매수 검토, 현재 9.3억 관망')",
```

- [ ] **Step 2: `_format_candidate_for_llm()` 수정** (daily_report_orchestrator.py:42-79)

기존 함수 끝 `return "\n".join(lines)` 바로 위에 3개 블록 추가:

```python
# 비교 분석
comp_pct = c.get("_comp_pct_vs_avg")
if comp_pct is not None:
    similar = c.get("_comp_similar_units", [])
    similar_str = ", ".join(
        f"{u['name']} {u['price_per_sqm']/10000:.0f}만/㎡" for u in similar[:2]
    )
    lines.append(
        f"- 가격 위치: 구 평균 대비 {comp_pct:+.1f}%"
        + (f" (유사: {similar_str})" if similar_str else "")
    )

# 수익 구조
jeonse_rate = c.get("_yield_jeonse_rate")
if jeonse_rate is not None:
    gap_eok = c.get("_yield_gap_cost", 0) / 10000
    monthly = c.get("_yield_monthly_cost", 0)
    lines.append(
        f"- 수익구조: 전세가율 {jeonse_rate*100:.1f}%, "
        f"갭 {gap_eok:.1f}억, 월 보유비용 {monthly}만원"
    )

# 공급·호재 리스크
supply_units = c.get("_supply_nearby_units", 0)
catalysts = c.get("_news_catalysts", [])
if supply_units > 0 or catalysts:
    pos = [x["title"] for x in catalysts if x.get("type") == "positive"][:1]
    neg = [x["title"] for x in catalysts if x.get("type") == "negative"][:1]
    parts = [f"반경 공급 {supply_units:,}세대({c.get('_supply_period','')})"]
    if pos:
        parts.append(f"호재: {pos[0][:20]}")
    if neg:
        parts.append(f"악재: {neg[0][:20]}")
    lines.append(f"- 공급/호재: {', '.join(parts)}")
```

- [ ] **Step 3: import 확인**

```bash
arch -arm64 .venv/bin/python3.12 -c "from modules.real_estate.daily_report.daily_report_orchestrator import DailyReportOrchestrator; print('OK')"
```
Expected: `OK`

- [ ] **Step 4: 커밋**

```bash
git add src/modules/real_estate/prompts/daily_strategy.md src/modules/real_estate/daily_report/daily_report_orchestrator.py
git commit -m "feat(prompt): daily_strategy verdict 수치 기반 판단 + _format_candidate_for_llm 3개 블록 추가"
```

---

## Task 12: DailyReportOrchestrator 파라미터 + 파이프라인 연결

**Files:**
- Modify: `src/modules/real_estate/daily_report/daily_report_orchestrator.py`

- [ ] **Step 1: 생성자에 3개 파라미터 추가**

`DailyReportOrchestrator.__init__()` 시그니처 수정:

```python
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
    school_repo=None,
    comp_analyzer=None,       # NEW: ComparativeAnalyzer
    yield_calculator=None,    # NEW: YieldCalculator
    supply_analyzer=None,     # NEW: SupplyRiskAnalyzer
):
    ...
    self._comp_analyzer = comp_analyzer
    self._yield_calculator = yield_calculator
    self._supply_analyzer = supply_analyzer
```

- [ ] **Step 2: `generate()` 메서드 enrich pipeline에 3개 호출 추가**

`_enrich_with_school` 임포트 줄에 3개 함수 추가:

```python
from modules.real_estate.report_orchestrator import (
    _enrich_with_geocode,
    _enrich_with_poi,
    _enrich_with_building,
    _enrich_with_trend,
    _resolve_workplace_coords,
    _enrich_with_comparative,  # NEW
    _enrich_with_yield,        # NEW
    _enrich_with_supply,       # NEW
)
```

`generate()` 내 school enrich 뒤, trend enrich 뒤에 추가:

```python
        if self._trend_analyzer:
            ...
            candidates = _enrich_with_trend(candidates, self._trend_analyzer, preferred_areas=preferred_areas)

        # Step 3-NEW. 비교·수익·공급 분석
        candidates = _enrich_with_comparative(candidates, self._comp_analyzer)
        candidates = _enrich_with_yield(candidates, self._yield_calculator)
        candidates = _enrich_with_supply(candidates, self._supply_analyzer)
```

- [ ] **Step 3: import 확인**

```bash
arch -arm64 .venv/bin/python3.12 -c "from modules.real_estate.daily_report.daily_report_orchestrator import DailyReportOrchestrator; print('OK')"
```
Expected: `OK`

- [ ] **Step 4: 커밋**

```bash
git add src/modules/real_estate/daily_report/daily_report_orchestrator.py
git commit -m "feat(orchestrator): comp/yield/supply 파라미터 추가 + enrich pipeline 연결"
```

---

## Task 13: Job4 파이프라인 전환 (service.py + DI)

**Files:**
- Modify: `src/modules/real_estate/service.py`
- Modify: `src/api/dependencies.py`

이 태스크가 핵심 전환이다. `generate_report()`가 `InsightOrchestrator` 대신 `DailyReportOrchestrator`를 호출하도록 교체한다.

- [ ] **Step 1: service.py에 DailyReportOrchestrator 임포트 + 생성 추가**

`RealEstateAgent.__init__()` 내 `self.commute_service = ...` 블록 아래에 추가:

```python
# service.py 상단 import에 추가
from .daily_report.daily_report_orchestrator import DailyReportOrchestrator
from .daily_report.daily_report_repository import DailyReportRepository
from .daily_report.transaction_aggregator import TransactionAggregator
from .trend_analyzer import TrendAnalyzer
from .comparative.analyzer import ComparativeAnalyzer
from .yield_analysis.calculator import YieldCalculator
from .supply.repository import SupplyRepository
from .supply.risk_analyzer import SupplyRiskAnalyzer
```

`RealEstateAgent.__init__()` 끝에 추가:

```python
        # Daily Report Orchestrator (Job4 신규 파이프라인)
        jeonse_repo_path = self.config.get("real_estate_db_path", "data/real_estate.db")
        from .jeonse.repository import JeonseRepository as _JeonseRepo
        _jeonse_repo = _JeonseRepo(db_path=jeonse_repo_path)

        supply_repo = SupplyRepository(db_path=jeonse_repo_path)
        news_svc = self.news_service

        self._comp_analyzer = ComparativeAnalyzer(tx_repo=self.tx_repo)
        self._yield_calculator = YieldCalculator(
            jeonse_repo=_jeonse_repo,
            mortgage_rate=float(self.config.get("scoring", {}).get("mortgage_rate", 0.0283))
        )
        self._supply_analyzer = SupplyRiskAnalyzer(
            supply_repo=supply_repo,
            news_service=news_svc,
            llm=self.llm,
            prompt_loader=self.prompt_loader,
        )

        _geocoder = GeocoderService(api_key=kakao_key)
        _trend_analyzer = TrendAnalyzer(db_path=re_db)
        _aggregator = TransactionAggregator(
            tx_repo=self.tx_repo,
            apt_master_repo=self.apt_master_repo,
        )
        _daily_report_repo = DailyReportRepository(db_path=re_db)

        self.daily_report_orchestrator = DailyReportOrchestrator(
            llm=self.llm,
            prompt_loader=self.prompt_loader,
            aggregator=_aggregator,
            report_repo=_daily_report_repo,
            db_path=re_db,
            poi_collector=PoiCollector(api_key=kakao_key),
            trend_analyzer=_trend_analyzer,
            commute_svc=self.commute_service,
            geocoder=_geocoder,
            comp_analyzer=self._comp_analyzer,
            yield_calculator=self._yield_calculator,
            supply_analyzer=self._supply_analyzer,
        )
```

- [ ] **Step 2: `generate_report()` 내 핵심 로직 교체**

`service.py`의 `generate_report()` 메서드에서 InsightOrchestrator 호출 부분을 DailyReportOrchestrator 호출로 교체한다.

기존 메서드 구조를 유지하되 Step 7(area_intel enrich) 이후 로직을 대체한다:

```python
    def generate_report(self, district_code: Optional[str] = None, target_date: Optional[date] = None) -> Dict[str, Any]:
        """Job 4: DailyReportOrchestrator 기반 리포트 생성."""
        if target_date is None:
            target_date = date.today()
        logger.info(f"[Job4] Generating daily report for {target_date}")

        # 거시경제 로드 → macro_summary 문자열 생성
        macro_data = self._load_stored_macro(target_date) or {}
        macro_parts = []
        for key, entry in macro_data.items():
            if entry and entry.get("value") is not None:
                macro_parts.append(f"{entry.get('label', key)}: {entry['value']}{entry.get('unit', '')}")
        macro_summary = " | ".join(macro_parts)

        # 페르소나 로드
        persona_data = self._load_persona()
        user = persona_data.get("user", {})
        budget_available = int(user.get("assets", {}).get("total", 0))

        # DailyReportOrchestrator 호출
        persona = {
            "commute": self.config.get("commute", {}),
            "apartment_preferences": user.get("apartment_preferences", {}),
            "investment_style": user.get("investment_style", "균형"),
        }
        report = self.daily_report_orchestrator.generate(
            target_date=target_date,
            days=int(self.config.get("report", {}).get("recent_days", 7)),
            top_k=int(self.config.get("report", {}).get("top_k", 5)),
            persona=persona,
            macro_summary=macro_summary,
            budget_available=budget_available,
        )

        return {
            "date": report.date,
            "markdown": report.markdown,
            "slack_text": report.slack_text,
            "top_k": report.top_k,
            "total_transactions": report.total_transactions,
        }
```

- [ ] **Step 3: `PoiCollector` import 확인** (service.py 상단에 이미 있어야 함)

```bash
arch -arm64 .venv/bin/python3.12 -c "from modules.real_estate.service import RealEstateAgent; print('OK')"
```
Expected: `OK`

- [ ] **Step 4: 기존 테스트 회귀 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/ -v --tb=short -q
```
Expected: 전체 PASS (새 테스트 포함). 실패 테스트가 있으면 내용을 보고 수정.

- [ ] **Step 5: 커밋**

```bash
git add src/modules/real_estate/service.py src/api/dependencies.py
git commit -m "feat(job4): InsightOrchestrator → DailyReportOrchestrator 파이프라인 전환"
```

---

## Task 14: 전체 회귀 테스트 + 완성 확인

- [ ] **Step 1: 전체 테스트 실행**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/ -v --tb=short -q --ignore=tests/e2e
```
Expected: 모든 테스트 PASS

- [ ] **Step 2: FastAPI 서버 기동 테스트**

```bash
arch -arm64 .venv/bin/python3.12 -c "
import sys
sys.path.insert(0, 'src')
from api.routers.real_estate import router
from api.dependencies import get_real_estate_agent
agent = get_real_estate_agent()
print('daily_report_orchestrator:', type(agent.daily_report_orchestrator).__name__)
print('comp_analyzer:', type(agent._comp_analyzer).__name__)
print('yield_calculator:', type(agent._yield_calculator).__name__)
print('supply_analyzer:', type(agent._supply_analyzer).__name__)
"
```
Expected:
```
daily_report_orchestrator: DailyReportOrchestrator
comp_analyzer: ComparativeAnalyzer
yield_calculator: YieldCalculator
supply_analyzer: SupplyRiskAnalyzer
```

- [ ] **Step 3: 신규 Job 엔드포인트 확인**

```bash
arch -arm64 .venv/bin/python3.12 -c "
import sys; sys.path.insert(0,'src')
from api.routers.real_estate import router
routes = [r.path for r in router.routes]
assert '/jobs/jeonse/collect' in routes, 'jeonse 엔드포인트 없음'
assert '/jobs/supply/collect' in routes, 'supply 엔드포인트 없음'
print('엔드포인트 확인 OK')
"
```
Expected: `엔드포인트 확인 OK`

- [ ] **Step 4: 최종 커밋**

```bash
git add -A
git commit -m "feat(report): 부동산 리포트 품질 업그레이드 완성

- Job4: InsightOrchestrator → DailyReportOrchestrator 전환
- ComparativeAnalyzer: 구 평균·유사 단지 ㎡당 가격 비교
- YieldCalculator: 전세가율·갭투자비용·월보유비용 계산
- SupplyRiskAnalyzer: 청약홈 입주물량 + 뉴스 호재/악재 태깅
- POST /jobs/jeonse/collect, /jobs/supply/collect 신규 Job
- report_formatter 3개 신규 render 블록"
```

---

## Self-Review 체크리스트

**Spec 커버리지:**
- [x] 4-A: `jeonse_transactions` 테이블 + JeonseClient + JeonseRepository → Task 1, 2, 3
- [x] 4-B: `supply_schedule` 테이블 + SupplyClient + SupplyRepository → Task 4, 5
- [x] 5-A: ComparativeAnalyzer → Task 6
- [x] 5-B: YieldCalculator (fallback 포함) → Task 7
- [x] 5-C: SupplyRiskAnalyzer + news_catalyst_classifier.md → Task 8
- [x] `_enrich_with_*` 3개 함수 → Task 9
- [x] report_types.py TypedDict 3개 + render 함수 → Task 10
- [x] daily_strategy.md verdict 수정 → Task 11
- [x] `_format_candidate_for_llm()` 수정 → Task 11
- [x] DailyReportOrchestrator 파라미터 + 연결 → Task 12
- [x] Job4 파이프라인 전환 (service.py) → Task 13
- [x] POST /jobs/jeonse/collect, /jobs/supply/collect → Task 3, 5
