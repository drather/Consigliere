# PNU Building Master DB Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 건축HUB 건축물대장 API로 수도권 아파트 `building_master` 테이블을 구축하고, `apt_master.pnu` + `apt_master.mapping_score` 컬럼을 추가해 이름 유사도 기반 매핑을 수행한다.

**Architecture:** `BuildingRegisterClient`(API 호출) → `BuildingMasterService`(수집·매핑 오케스트레이션) → `BuildingMasterRepository`(SQLite 저장). 매핑은 `building_master.sigungu_code = apt_master.district_code` 필터 후 이름 유사도 ≥ 0.8로 확정한다. `parcel_pnu`(10자리 = sigungu+bjdong)를 인덱스로 저장해 향후 jibun 기반 정밀 매핑을 위한 확장 포인트를 남긴다.

**Tech Stack:** Python 3.12, sqlite3, requests, difflib, FastAPI, pytest, unittest.mock

**Working directory:** `/Users/kks/Desktop/Laboratory/Consigliere`
**Python:** `arch -arm64 /Users/kks/Desktop/Laboratory/Consigliere/.venv/bin/python3.12`

---

## File Map

| 파일 | 역할 | 변경 |
|------|------|------|
| `src/modules/real_estate/building_master/__init__.py` | 패키지 초기화 | 신규 |
| `src/modules/real_estate/building_master/models.py` | BuildingMaster dataclass | 신규 |
| `src/modules/real_estate/building_master/building_register_client.py` | 건축HUB API 클라이언트 | 신규 |
| `src/modules/real_estate/building_master/building_master_repository.py` | building_master SQLite CRUD | 신규 |
| `src/modules/real_estate/building_master/building_master_service.py` | 수집 + 매핑 오케스트레이션 | 신규 |
| `src/modules/real_estate/models.py` | AptMasterEntry에 pnu/mapping_score 필드 추가 | 수정 |
| `src/modules/real_estate/apt_master_repository.py` | pnu/mapping_score 컬럼 마이그레이션 + update_building_mapping() + get_all_for_mapping() | 수정 |
| `scripts/build_building_master.py` | CLI: --collect / --map / --rebuild | 신규 |
| `src/api/routers/real_estate.py` | POST /jobs/building-master/collect 엔드포인트 추가 | 수정 |
| `src/api/dependencies.py` | BuildingMasterService DI 팩토리 추가 | 수정 |
| `tests/modules/real_estate/building_master/__init__.py` | 테스트 패키지 | 신규 |
| `tests/modules/real_estate/building_master/test_building_register_client.py` | 클라이언트 단위 테스트 | 신규 |
| `tests/modules/real_estate/building_master/test_building_master_repository.py` | 레포지토리 단위 테스트 | 신규 |
| `tests/modules/real_estate/building_master/test_building_master_service.py` | 서비스 단위 테스트 | 신규 |
| `tests/modules/real_estate/test_apt_master_repository.py` | 마이그레이션 + 신규 메서드 테스트 추가 | 수정 |

---

## Task 1: BuildingMaster 모델 + 패키지 초기화

**Files:**
- Create: `src/modules/real_estate/building_master/__init__.py`
- Create: `src/modules/real_estate/building_master/models.py`
- Create: `tests/modules/real_estate/building_master/__init__.py`

- [ ] **Step 1: 패키지 파일 생성**

```python
# src/modules/real_estate/building_master/__init__.py
# (빈 파일)
```

```python
# tests/modules/real_estate/building_master/__init__.py
# (빈 파일)
```

- [ ] **Step 2: BuildingMaster dataclass 작성**

```python
# src/modules/real_estate/building_master/models.py
from dataclasses import dataclass
from typing import Optional


@dataclass
class BuildingMaster:
    mgm_pk: str                              # 관리건축물대장PK (22자리)
    building_name: str                       # 건물명
    sigungu_code: str                        # 시군구코드 5자리 (API 요청 코드)
    bjdong_code: str = ""                    # 법정동코드 5자리 (API 응답)
    parcel_pnu: str = ""                     # sigungu_code + bjdong_code = 10자리
    road_address: Optional[str] = None      # 도로명주소
    jibun_address: Optional[str] = None     # 지번주소
    completion_year: Optional[int] = None   # 준공연도
    total_units: Optional[int] = None       # 세대수
    total_buildings: Optional[int] = None   # 동수
    floor_area_ratio: Optional[float] = None    # 용적률
    building_coverage_ratio: Optional[float] = None  # 건폐율
    collected_at: str = ""
```

- [ ] **Step 3: 모델 임포트 확인 테스트 작성**

```python
# tests/modules/real_estate/building_master/test_building_register_client.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

from modules.real_estate.building_master.models import BuildingMaster


def test_building_master_construction():
    bm = BuildingMaster(
        mgm_pk="1234567890123456789012",
        building_name="래미안아파트",
        sigungu_code="11650",
    )
    assert bm.mgm_pk == "1234567890123456789012"
    assert bm.building_name == "래미안아파트"
    assert bm.sigungu_code == "11650"
    assert bm.bjdong_code == ""
    assert bm.total_units is None


def test_building_master_full_fields():
    bm = BuildingMaster(
        mgm_pk="9999999999999999999999",
        building_name="아크로리버파크",
        sigungu_code="11650",
        bjdong_code="10800",
        parcel_pnu="1165010800",
        completion_year=2016,
        total_units=1612,
        total_buildings=7,
        floor_area_ratio=299.9,
        building_coverage_ratio=19.9,
    )
    assert bm.parcel_pnu == "1165010800"
    assert bm.completion_year == 2016
    assert bm.total_units == 1612
```

- [ ] **Step 4: 테스트 실행 (PASS 확인)**

```bash
arch -arm64 /Users/kks/Desktop/Laboratory/Consigliere/.venv/bin/python3.12 \
  -m pytest tests/modules/real_estate/building_master/test_building_register_client.py::test_building_master_construction \
            tests/modules/real_estate/building_master/test_building_register_client.py::test_building_master_full_fields \
  -v
```

Expected: 2 passed

- [ ] **Step 5: 커밋**

```bash
git add src/modules/real_estate/building_master/__init__.py \
        src/modules/real_estate/building_master/models.py \
        tests/modules/real_estate/building_master/__init__.py \
        tests/modules/real_estate/building_master/test_building_register_client.py
git commit -m "feat(building-master): BuildingMaster dataclass + 패키지 초기화"
```

---

## Task 2: BuildingRegisterClient

**Files:**
- Create: `src/modules/real_estate/building_master/building_register_client.py`
- Modify: `tests/modules/real_estate/building_master/test_building_register_client.py`

- [ ] **Step 1: 클라이언트 실패 테스트 작성**

```python
# tests/modules/real_estate/building_master/test_building_register_client.py 에 추가
import json
from unittest.mock import MagicMock, patch

from modules.real_estate.building_master.building_register_client import (
    BuildingRegisterClient,
)


_SAMPLE_RESPONSE = {
    "response": {
        "body": {
            "totalCount": 2,
            "items": {
                "item": [
                    {
                        "mgmBldrgstPk": "1100000000000001000001",
                        "bldNm": "래미안아파트",
                        "sigunguCd": "11650",
                        "bjdongCd": "10100",
                        "newPlatPlc": "서울특별시 서초구 반포대로 23",
                        "platPlc": "서울특별시 서초구 반포동 10-1",
                        "useAprDay": "20050320",
                        "hhldCnt": "1000",
                        "dongCnt": "5",
                        "vlRat": "250.0",
                        "bcRat": "20.0",
                        "mainPurpsCdNm": "아파트",
                    },
                    {
                        "mgmBldrgstPk": "1100000000000001000002",
                        "bldNm": "상가건물",
                        "sigunguCd": "11650",
                        "bjdongCd": "10100",
                        "newPlatPlc": "서울특별시 서초구 어딘가 1",
                        "platPlc": "서울특별시 서초구 반포동 20",
                        "useAprDay": "20100101",
                        "hhldCnt": "0",
                        "dongCnt": "1",
                        "vlRat": "400.0",
                        "bcRat": "60.0",
                        "mainPurpsCdNm": "근린생활시설",
                    },
                ]
            },
        }
    }
}


def test_fetch_page_calls_correct_url():
    client = BuildingRegisterClient(api_key="testkey")
    mock_resp = MagicMock()
    mock_resp.json.return_value = _SAMPLE_RESPONSE
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_resp) as mock_get:
        result = client.fetch_page("11650", page_no=1)

    call_kwargs = mock_get.call_args
    assert call_kwargs[1]["params"]["sigunguCd"] == "11650"
    assert call_kwargs[1]["params"]["serviceKey"] == "testkey"
    assert call_kwargs[1]["params"]["_type"] == "json"
    assert result == _SAMPLE_RESPONSE


def test_fetch_apartments_filters_non_apt():
    client = BuildingRegisterClient(api_key="testkey")
    mock_resp = MagicMock()
    mock_resp.json.return_value = _SAMPLE_RESPONSE
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_resp):
        items = client.fetch_apartments_by_sigungu("11650")

    assert len(items) == 1
    assert items[0]["bldNm"] == "래미안아파트"


def test_parse_item_extracts_fields():
    raw = {
        "mgmBldrgstPk": "1100000000000001000001",
        "bldNm": "래미안아파트",
        "sigunguCd": "11650",
        "bjdongCd": "10100",
        "newPlatPlc": "서울특별시 서초구 반포대로 23",
        "platPlc": "서울특별시 서초구 반포동 10-1",
        "useAprDay": "20050320",
        "hhldCnt": "1000",
        "dongCnt": "5",
        "vlRat": "250.0",
        "bcRat": "20.0",
        "mainPurpsCdNm": "아파트",
    }
    parsed = BuildingRegisterClient.parse_item(raw)
    assert parsed["mgm_pk"] == "1100000000000001000001"
    assert parsed["building_name"] == "래미안아파트"
    assert parsed["sigungu_code"] == "11650"
    assert parsed["bjdong_code"] == "10100"
    assert parsed["completion_year"] == 2005
    assert parsed["total_units"] == 1000
    assert parsed["total_buildings"] == 5
    assert parsed["floor_area_ratio"] == 250.0
    assert parsed["building_coverage_ratio"] == 20.0


def test_parse_item_handles_missing_fields():
    raw = {"mgmBldrgstPk": "9999", "bldNm": "테스트", "sigunguCd": "11110"}
    parsed = BuildingRegisterClient.parse_item(raw)
    assert parsed["completion_year"] is None
    assert parsed["total_units"] is None
    assert parsed["bjdong_code"] == ""


def test_extract_items_handles_single_dict():
    data = {
        "response": {
            "body": {
                "totalCount": 1,
                "items": {"item": {"mgmBldrgstPk": "001", "bldNm": "단독", "mainPurpsCdNm": "아파트"}},
            }
        }
    }
    items = BuildingRegisterClient._extract_items(data)
    assert len(items) == 1
    assert items[0]["mgmBldrgstPk"] == "001"


def test_extract_items_handles_empty():
    data = {"response": {"body": {"totalCount": 0, "items": {"item": None}}}}
    assert BuildingRegisterClient._extract_items(data) == []
```

- [ ] **Step 2: 테스트 실행 (FAIL 확인)**

```bash
arch -arm64 /Users/kks/Desktop/Laboratory/Consigliere/.venv/bin/python3.12 \
  -m pytest tests/modules/real_estate/building_master/test_building_register_client.py -v 2>&1 | tail -5
```

Expected: ImportError (building_register_client not yet created)

- [ ] **Step 3: BuildingRegisterClient 구현**

```python
# src/modules/real_estate/building_master/building_register_client.py
import os
import logging
import requests
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_BASE_URL = "https://apis.data.go.kr/1613000/BldRgstHubService/getBrBasisOulnInfo"


class BuildingRegisterClient:
    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or os.getenv("HUB_API_KEY", "")

    def fetch_page(self, sigungu_cd: str, page_no: int = 1, num_of_rows: int = 100) -> dict:
        params = {
            "serviceKey": self._api_key,
            "sigunguCd": sigungu_cd,
            "numOfRows": num_of_rows,
            "pageNo": page_no,
            "_type": "json",
        }
        resp = requests.get(_BASE_URL, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def fetch_apartments_by_sigungu(self, sigungu_cd: str) -> List[dict]:
        """시군구 전체 아파트 수집 (페이지네이션). 아파트 용도만 반환."""
        page_no = 1
        results: List[dict] = []
        while True:
            data = self.fetch_page(sigungu_cd, page_no=page_no)
            items = self._extract_items(data)
            if not items:
                break
            results.extend(i for i in items if "아파트" in str(i.get("mainPurpsCdNm", "")))
            total = _safe_int(
                data.get("response", {}).get("body", {}).get("totalCount", 0)
            )
            if page_no * 100 >= total:
                break
            page_no += 1
        return results

    @staticmethod
    def _extract_items(data: dict) -> List[dict]:
        try:
            items = data["response"]["body"]["items"]["item"]
            if items is None:
                return []
            if isinstance(items, dict):
                return [items]
            return list(items)
        except (KeyError, TypeError):
            return []

    @staticmethod
    def parse_item(item: dict) -> dict:
        use_apr = str(item.get("useAprDay", "") or "")
        sigungu = str(item.get("sigunguCd", "") or "")
        bjdong = str(item.get("bjdongCd", "") or "")
        return {
            "mgm_pk": str(item.get("mgmBldrgstPk", "") or ""),
            "building_name": str(item.get("bldNm", "") or ""),
            "sigungu_code": sigungu,
            "bjdong_code": bjdong,
            "parcel_pnu": sigungu + bjdong,
            "road_address": str(item.get("newPlatPlc", "") or "") or None,
            "jibun_address": str(item.get("platPlc", "") or "") or None,
            "completion_year": int(use_apr[:4]) if len(use_apr) >= 4 and use_apr[:4].isdigit() else None,
            "total_units": _to_int(item.get("hhldCnt")),
            "total_buildings": _to_int(item.get("dongCnt")),
            "floor_area_ratio": _to_float(item.get("vlRat")),
            "building_coverage_ratio": _to_float(item.get("bcRat")),
        }


def _safe_int(val) -> int:
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0


def _to_int(val) -> Optional[int]:
    try:
        v = str(val).strip()
        return int(v) if v and v != "None" else None
    except (ValueError, TypeError):
        return None


def _to_float(val) -> Optional[float]:
    try:
        v = str(val).strip()
        return float(v) if v and v != "None" else None
    except (ValueError, TypeError):
        return None
```

- [ ] **Step 4: 테스트 실행 (PASS 확인)**

```bash
arch -arm64 /Users/kks/Desktop/Laboratory/Consigliere/.venv/bin/python3.12 \
  -m pytest tests/modules/real_estate/building_master/test_building_register_client.py -v
```

Expected: 8 passed

- [ ] **Step 5: 커밋**

```bash
git add src/modules/real_estate/building_master/building_register_client.py \
        tests/modules/real_estate/building_master/test_building_register_client.py
git commit -m "feat(building-master): BuildingRegisterClient — 건축HUB API 클라이언트"
```

---

## Task 3: BuildingMasterRepository

**Files:**
- Create: `src/modules/real_estate/building_master/building_master_repository.py`
- Create: `tests/modules/real_estate/building_master/test_building_master_repository.py`

- [ ] **Step 1: 레포지토리 실패 테스트 작성**

```python
# tests/modules/real_estate/building_master/test_building_master_repository.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

from modules.real_estate.building_master.models import BuildingMaster
from modules.real_estate.building_master.building_master_repository import (
    BuildingMasterRepository,
)


def _make_bm(**kwargs) -> BuildingMaster:
    defaults = dict(
        mgm_pk="1100000000000001000001",
        building_name="래미안아파트",
        sigungu_code="11650",
        bjdong_code="10100",
        parcel_pnu="1165010100",
        road_address="서울 서초구 반포대로 23",
        jibun_address="서울 서초구 반포동 10",
        completion_year=2005,
        total_units=1000,
        total_buildings=5,
        floor_area_ratio=250.0,
        building_coverage_ratio=20.0,
        collected_at="2026-04-23T00:00:00+00:00",
    )
    defaults.update(kwargs)
    return BuildingMaster(**defaults)


def test_upsert_and_count():
    repo = BuildingMasterRepository(db_path=":memory:")
    assert repo.count() == 0
    repo.upsert(_make_bm())
    assert repo.count() == 1


def test_upsert_idempotent():
    repo = BuildingMasterRepository(db_path=":memory:")
    bm = _make_bm()
    repo.upsert(bm)
    repo.upsert(bm)  # 두 번 upsert → 1건 유지
    assert repo.count() == 1


def test_upsert_updates_fields():
    repo = BuildingMasterRepository(db_path=":memory:")
    repo.upsert(_make_bm(total_units=1000))
    repo.upsert(_make_bm(total_units=1200))  # 갱신
    results = repo.get_by_sigungu("11650")
    assert results[0].total_units == 1200


def test_get_by_sigungu_returns_only_matching():
    repo = BuildingMasterRepository(db_path=":memory:")
    repo.upsert(_make_bm(mgm_pk="A001", sigungu_code="11650"))
    repo.upsert(_make_bm(mgm_pk="A002", sigungu_code="11680"))
    results = repo.get_by_sigungu("11650")
    assert len(results) == 1
    assert results[0].mgm_pk == "A001"


def test_count_by_sigungu():
    repo = BuildingMasterRepository(db_path=":memory:")
    repo.upsert(_make_bm(mgm_pk="A001", sigungu_code="11650"))
    repo.upsert(_make_bm(mgm_pk="A002", sigungu_code="11650"))
    assert repo.count_by_sigungu("11650") == 2
    assert repo.count_by_sigungu("11680") == 0


def test_get_by_sigungu_returns_all_fields():
    repo = BuildingMasterRepository(db_path=":memory:")
    bm = _make_bm()
    repo.upsert(bm)
    results = repo.get_by_sigungu("11650")
    r = results[0]
    assert r.building_name == "래미안아파트"
    assert r.completion_year == 2005
    assert r.total_units == 1000
    assert r.floor_area_ratio == 250.0
```

- [ ] **Step 2: 테스트 실행 (FAIL 확인)**

```bash
arch -arm64 /Users/kks/Desktop/Laboratory/Consigliere/.venv/bin/python3.12 \
  -m pytest tests/modules/real_estate/building_master/test_building_master_repository.py -v 2>&1 | tail -5
```

Expected: ImportError (repository not yet created)

- [ ] **Step 3: BuildingMasterRepository 구현**

```python
# src/modules/real_estate/building_master/building_master_repository.py
import sqlite3
from datetime import datetime, timezone
from typing import List, Optional

try:
    from modules.real_estate.building_master.models import BuildingMaster
except ImportError:
    from src.modules.real_estate.building_master.models import BuildingMaster

_DDL = """
CREATE TABLE IF NOT EXISTS building_master (
    mgm_pk                  TEXT PRIMARY KEY,
    building_name           TEXT NOT NULL,
    sigungu_code            TEXT NOT NULL,
    bjdong_code             TEXT NOT NULL DEFAULT '',
    parcel_pnu              TEXT NOT NULL DEFAULT '',
    road_address            TEXT,
    jibun_address           TEXT,
    completion_year         INTEGER,
    total_units             INTEGER,
    total_buildings         INTEGER,
    floor_area_ratio        REAL,
    building_coverage_ratio REAL,
    collected_at            TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_bm_sigungu ON building_master(sigungu_code);
CREATE INDEX IF NOT EXISTS idx_bm_parcel  ON building_master(parcel_pnu);
CREATE INDEX IF NOT EXISTS idx_bm_name    ON building_master(building_name);
"""

_UPSERT_SQL = """
INSERT INTO building_master
    (mgm_pk, building_name, sigungu_code, bjdong_code, parcel_pnu,
     road_address, jibun_address, completion_year, total_units,
     total_buildings, floor_area_ratio, building_coverage_ratio, collected_at)
VALUES
    (:mgm_pk, :building_name, :sigungu_code, :bjdong_code, :parcel_pnu,
     :road_address, :jibun_address, :completion_year, :total_units,
     :total_buildings, :floor_area_ratio, :building_coverage_ratio, :collected_at)
ON CONFLICT(mgm_pk) DO UPDATE SET
    building_name           = excluded.building_name,
    completion_year         = excluded.completion_year,
    total_units             = excluded.total_units,
    total_buildings         = excluded.total_buildings,
    floor_area_ratio        = excluded.floor_area_ratio,
    building_coverage_ratio = excluded.building_coverage_ratio,
    road_address            = excluded.road_address,
    jibun_address           = excluded.jibun_address,
    collected_at            = excluded.collected_at
"""


class BuildingMasterRepository:
    def __init__(self, db_path: str = "data/real_estate.db"):
        self._db_path = db_path
        if db_path == ":memory:":
            self._shared_conn: Optional[sqlite3.Connection] = sqlite3.connect(":memory:")
            self._shared_conn.row_factory = sqlite3.Row
        else:
            self._shared_conn = None
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        if self._shared_conn is not None:
            return self._shared_conn
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        conn = self._conn()
        conn.executescript(_DDL)
        conn.commit()

    def upsert(self, bm: BuildingMaster) -> None:
        params = {
            "mgm_pk": bm.mgm_pk,
            "building_name": bm.building_name,
            "sigungu_code": bm.sigungu_code,
            "bjdong_code": bm.bjdong_code,
            "parcel_pnu": bm.parcel_pnu,
            "road_address": bm.road_address,
            "jibun_address": bm.jibun_address,
            "completion_year": bm.completion_year,
            "total_units": bm.total_units,
            "total_buildings": bm.total_buildings,
            "floor_area_ratio": bm.floor_area_ratio,
            "building_coverage_ratio": bm.building_coverage_ratio,
            "collected_at": bm.collected_at or datetime.now(timezone.utc).isoformat(),
        }
        with self._conn() as conn:
            conn.execute(_UPSERT_SQL, params)

    def get_by_sigungu(self, sigungu_code: str) -> List[BuildingMaster]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM building_master WHERE sigungu_code = ?",
                (sigungu_code,),
            ).fetchall()
        return [_row_to_bm(r) for r in rows]

    def count_by_sigungu(self, sigungu_code: str) -> int:
        with self._conn() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM building_master WHERE sigungu_code = ?",
                (sigungu_code,),
            ).fetchone()[0]

    def count(self) -> int:
        with self._conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM building_master").fetchone()[0]


def _row_to_bm(row: sqlite3.Row) -> BuildingMaster:
    return BuildingMaster(
        mgm_pk=row["mgm_pk"],
        building_name=row["building_name"],
        sigungu_code=row["sigungu_code"],
        bjdong_code=row["bjdong_code"],
        parcel_pnu=row["parcel_pnu"],
        road_address=row["road_address"],
        jibun_address=row["jibun_address"],
        completion_year=row["completion_year"],
        total_units=row["total_units"],
        total_buildings=row["total_buildings"],
        floor_area_ratio=row["floor_area_ratio"],
        building_coverage_ratio=row["building_coverage_ratio"],
        collected_at=row["collected_at"],
    )
```

- [ ] **Step 4: 테스트 실행 (PASS 확인)**

```bash
arch -arm64 /Users/kks/Desktop/Laboratory/Consigliere/.venv/bin/python3.12 \
  -m pytest tests/modules/real_estate/building_master/test_building_master_repository.py -v
```

Expected: 6 passed

- [ ] **Step 5: 커밋**

```bash
git add src/modules/real_estate/building_master/building_master_repository.py \
        tests/modules/real_estate/building_master/test_building_master_repository.py
git commit -m "feat(building-master): BuildingMasterRepository — SQLite CRUD"
```

---

## Task 4: AptMasterRepository — pnu/mapping_score 마이그레이션

**Files:**
- Modify: `src/modules/real_estate/models.py`
- Modify: `src/modules/real_estate/apt_master_repository.py`
- Modify: `tests/modules/real_estate/test_apt_master_repository.py`

- [ ] **Step 1: AptMasterEntry에 새 필드 추가**

`src/modules/real_estate/models.py`의 `AptMasterEntry` 클래스에 아래 두 필드를 추가한다 (기존 필드 끝 바로 다음):

```python
    pnu: Optional[str] = None               # FK → building_master.mgm_pk (NULLABLE)
    mapping_score: Optional[float] = None   # 매핑 신뢰도 0.0~1.0
```

- [ ] **Step 2: AptMasterRepository 마이그레이션 SQL 추가**

`src/modules/real_estate/apt_master_repository.py`의 `_DDL` 상수 **아래** (클래스 정의 위)에 추가:

```python
_MIGRATE_ADD_PNU_COLS = [
    "ALTER TABLE apt_master ADD COLUMN pnu TEXT",
    "ALTER TABLE apt_master ADD COLUMN mapping_score REAL",
]
```

그리고 `_init_db` 메서드를 아래처럼 교체 (기존 `conn.executescript(_DDL)` 한 줄짜리를 확장):

```python
    def _init_db(self) -> None:
        conn = self._conn()
        conn.executescript(_DDL)
        for sql in _MIGRATE_ADD_PNU_COLS:
            try:
                conn.execute(sql)
            except Exception:
                pass  # 이미 컬럼 존재 시 무시
        conn.commit()
```

- [ ] **Step 3: _row_to_entry 함수 갱신**

`_row_to_entry` 함수에서 반환하는 `AptMasterEntry(...)` 생성자에 두 필드 추가:

```python
def _row_to_entry(row: sqlite3.Row) -> AptMasterEntry:
    return AptMasterEntry(
        id=row["id"],
        apt_name=row["apt_name"],
        district_code=row["district_code"],
        sido=row["sido"],
        sigungu=row["sigungu"],
        complex_code=row["complex_code"],
        tx_count=row["tx_count"],
        first_traded=row["first_traded"],
        last_traded=row["last_traded"],
        created_at=row["created_at"],
        pnu=row["pnu"] if "pnu" in row.keys() else None,
        mapping_score=row["mapping_score"] if "mapping_score" in row.keys() else None,
    )
```

- [ ] **Step 4: 신규 메서드 추가**

`AptMasterRepository` 클래스 끝에 두 메서드를 추가한다:

```python
    def update_building_mapping(
        self, apt_id: int, mgm_pk: str, score: float
    ) -> None:
        """apt_master 행에 building_master PK + 매핑 점수 기록."""
        with self._conn() as conn:
            conn.execute(
                "UPDATE apt_master SET pnu = ?, mapping_score = ? WHERE id = ?",
                (mgm_pk, score, apt_id),
            )

    def get_all_for_mapping(self) -> list:
        """pnu가 NULL인 모든 단지 반환 (매핑 대상)."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM apt_master WHERE pnu IS NULL"
            ).fetchall()
        return [_row_to_entry(r) for r in rows]
```

- [ ] **Step 5: 마이그레이션 + 신규 메서드 테스트 작성**

`tests/modules/real_estate/test_apt_master_repository.py` 파일 끝에 아래 테스트를 추가한다:

```python
def test_pnu_columns_exist_after_init():
    from modules.real_estate.apt_master_repository import AptMasterRepository
    repo = AptMasterRepository(db_path=":memory:")
    # pnu, mapping_score 컬럼이 존재하면 upsert가 작동한다
    from modules.real_estate.models import AptMasterEntry
    from datetime import datetime, timezone
    entry = AptMasterEntry(
        apt_name="테스트아파트", district_code="11650",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    repo.upsert(entry)
    assert repo.count() == 1


def test_update_building_mapping():
    from modules.real_estate.apt_master_repository import AptMasterRepository
    from modules.real_estate.models import AptMasterEntry
    from datetime import datetime, timezone
    repo = AptMasterRepository(db_path=":memory:")
    entry = AptMasterEntry(
        apt_name="래미안아파트", district_code="11650",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    repo.upsert(entry)
    saved = repo.get_by_name_district("래미안아파트", "11650")
    assert saved is not None

    repo.update_building_mapping(saved.id, "1100000000000001000001", 0.95)
    updated = repo.get_by_name_district("래미안아파트", "11650")
    assert updated.pnu == "1100000000000001000001"
    assert abs(updated.mapping_score - 0.95) < 0.001


def test_get_all_for_mapping_returns_unmapped_only():
    from modules.real_estate.apt_master_repository import AptMasterRepository
    from modules.real_estate.models import AptMasterEntry
    from datetime import datetime, timezone
    repo = AptMasterRepository(db_path=":memory:")

    now = datetime.now(timezone.utc).isoformat()
    repo.upsert(AptMasterEntry(apt_name="A아파트", district_code="11650", created_at=now))
    repo.upsert(AptMasterEntry(apt_name="B아파트", district_code="11650", created_at=now))

    all_unmapped = repo.get_all_for_mapping()
    assert len(all_unmapped) == 2

    a = repo.get_by_name_district("A아파트", "11650")
    repo.update_building_mapping(a.id, "MGM001", 0.9)

    unmapped = repo.get_all_for_mapping()
    assert len(unmapped) == 1
    assert unmapped[0].apt_name == "B아파트"
```

- [ ] **Step 6: 테스트 실행 (PASS 확인)**

```bash
arch -arm64 /Users/kks/Desktop/Laboratory/Consigliere/.venv/bin/python3.12 \
  -m pytest tests/modules/real_estate/test_apt_master_repository.py -v 2>&1 | tail -10
```

Expected: 기존 테스트 모두 PASS + 신규 3개 PASS

- [ ] **Step 7: 커밋**

```bash
git add src/modules/real_estate/models.py \
        src/modules/real_estate/apt_master_repository.py \
        tests/modules/real_estate/test_apt_master_repository.py
git commit -m "feat(building-master): apt_master에 pnu/mapping_score 컬럼 마이그레이션 + update/get_all_for_mapping"
```

---

## Task 5: BuildingMasterService.collect()

**Files:**
- Create: `src/modules/real_estate/building_master/building_master_service.py`
- Create: `tests/modules/real_estate/building_master/test_building_master_service.py`

- [ ] **Step 1: collect() 실패 테스트 작성**

```python
# tests/modules/real_estate/building_master/test_building_master_service.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../src"))

from unittest.mock import MagicMock, patch
from modules.real_estate.building_master.building_master_service import (
    BuildingMasterService,
)
from modules.real_estate.building_master.models import BuildingMaster
from modules.real_estate.building_master.building_master_repository import (
    BuildingMasterRepository,
)
from modules.real_estate.apt_master_repository import AptMasterRepository


def _make_client_stub(items_by_code: dict):
    client = MagicMock()
    def _fetch(code):
        return items_by_code.get(code, [])
    client.fetch_apartments_by_sigungu.side_effect = _fetch
    client.parse_item.side_effect = lambda item: item  # passthrough
    return client


def test_collect_inserts_items():
    bm_repo = BuildingMasterRepository(db_path=":memory:")
    apt_repo = AptMasterRepository(db_path=":memory:")

    raw_item = {
        "mgm_pk": "1100000000000001000001",
        "building_name": "래미안아파트",
        "sigungu_code": "11650",
        "bjdong_code": "10100",
        "parcel_pnu": "1165010100",
        "road_address": "서울 서초구 반포대로 23",
        "jibun_address": "서울 서초구 반포동 10",
        "completion_year": 2005,
        "total_units": 1000,
        "total_buildings": 5,
        "floor_area_ratio": 250.0,
        "building_coverage_ratio": 20.0,
    }
    client = _make_client_stub({"11650": [raw_item]})
    svc = BuildingMasterService(client, bm_repo, apt_repo)

    result = svc.collect(sigungu_codes=["11650"])
    assert result["collected"] == 1
    assert result["failed"] == []
    assert bm_repo.count() == 1


def test_collect_skips_already_collected():
    bm_repo = BuildingMasterRepository(db_path=":memory:")
    apt_repo = AptMasterRepository(db_path=":memory:")
    # 미리 1개 삽입
    bm_repo.upsert(BuildingMaster(
        mgm_pk="EXISTING", building_name="기존아파트",
        sigungu_code="11650", collected_at="2026-01-01T00:00:00+00:00",
    ))
    client = _make_client_stub({"11650": []})  # 호출되지 않아야 함
    svc = BuildingMasterService(client, bm_repo, apt_repo)

    result = svc.collect(sigungu_codes=["11650"])
    assert result["skipped"] == 1
    assert result["collected"] == 0
    client.fetch_apartments_by_sigungu.assert_not_called()


def test_collect_isolates_failed_sigungu():
    bm_repo = BuildingMasterRepository(db_path=":memory:")
    apt_repo = AptMasterRepository(db_path=":memory:")
    client = MagicMock()
    client.fetch_apartments_by_sigungu.side_effect = Exception("API error")
    svc = BuildingMasterService(client, bm_repo, apt_repo)

    result = svc.collect(sigungu_codes=["11650", "11680"])
    assert "11650" in result["failed"]
    assert "11680" in result["failed"]
    assert result["collected"] == 0


def test_collect_skips_items_missing_mgm_pk():
    bm_repo = BuildingMasterRepository(db_path=":memory:")
    apt_repo = AptMasterRepository(db_path=":memory:")
    raw_item = {
        "mgm_pk": "",  # 빈 PK → 저장 불가
        "building_name": "이름없는아파트",
        "sigungu_code": "11650",
        "bjdong_code": "",
        "parcel_pnu": "",
        "road_address": None,
        "jibun_address": None,
        "completion_year": None,
        "total_units": None,
        "total_buildings": None,
        "floor_area_ratio": None,
        "building_coverage_ratio": None,
    }
    client = _make_client_stub({"11650": [raw_item]})
    svc = BuildingMasterService(client, bm_repo, apt_repo)

    result = svc.collect(sigungu_codes=["11650"])
    assert result["collected"] == 0
    assert bm_repo.count() == 0
```

- [ ] **Step 2: 테스트 실행 (FAIL 확인)**

```bash
arch -arm64 /Users/kks/Desktop/Laboratory/Consigliere/.venv/bin/python3.12 \
  -m pytest tests/modules/real_estate/building_master/test_building_master_service.py -v 2>&1 | tail -5
```

Expected: ImportError (service not yet created)

- [ ] **Step 3: BuildingMasterService 구현 (collect 부분)**

```python
# src/modules/real_estate/building_master/building_master_service.py
import logging
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import List, Optional, Tuple

try:
    from modules.real_estate.building_master.models import BuildingMaster
    from modules.real_estate.building_master.building_register_client import BuildingRegisterClient
    from modules.real_estate.building_master.building_master_repository import BuildingMasterRepository
    from modules.real_estate.apt_master_repository import AptMasterRepository
except ImportError:
    from src.modules.real_estate.building_master.models import BuildingMaster
    from src.modules.real_estate.building_master.building_register_client import BuildingRegisterClient
    from src.modules.real_estate.building_master.building_master_repository import BuildingMasterRepository
    from src.modules.real_estate.apt_master_repository import AptMasterRepository

logger = logging.getLogger(__name__)

METRO_SIGUNGU_CODES = [
    # 서울 25개 구
    "11110", "11140", "11170", "11200", "11215", "11230", "11260",
    "11290", "11305", "11320", "11350", "11380", "11410", "11440",
    "11470", "11500", "11530", "11545", "11560", "11590", "11620",
    "11650", "11680", "11710", "11740",
    # 인천 10개 구·군
    "28110", "28140", "28177", "28185", "28200", "28237", "28245",
    "28260", "28710", "28720",
    # 경기 44개 (구 단위 분리)
    "41111", "41113", "41115", "41117",
    "41131", "41133", "41135",
    "41150",
    "41171", "41173",
    "41192", "41194", "41196",
    "41210", "41220", "41250",
    "41271", "41273",
    "41281", "41285", "41287",
    "41290", "41310", "41360", "41370", "41390", "41410", "41430",
    "41450",
    "41461", "41463", "41465",
    "41480", "41500", "41550", "41570", "41590", "41610", "41630",
    "41650", "41670", "41800", "41820", "41830",
]


def _normalize_name(name: str) -> str:
    n = re.sub(r"[()（）\s·\-_]", "", name)
    n = n.replace("아파트", "").replace("APT", "").replace("apt", "")
    return n.lower()


def _name_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize_name(a), _normalize_name(b)).ratio()


def _best_match(
    apt_name: str, candidates: List[BuildingMaster]
) -> Tuple[Optional[BuildingMaster], float]:
    best: Optional[BuildingMaster] = None
    best_score = 0.0
    for bm in candidates:
        score = _name_similarity(apt_name, bm.building_name)
        if score > best_score:
            best_score = score
            best = bm
    return best, best_score


class BuildingMasterService:
    def __init__(
        self,
        client: BuildingRegisterClient,
        bm_repo: BuildingMasterRepository,
        apt_master_repo: AptMasterRepository,
    ):
        self._client = client
        self._bm_repo = bm_repo
        self._apt_master_repo = apt_master_repo

    def collect(self, sigungu_codes: Optional[List[str]] = None) -> dict:
        """수도권 시군구별 아파트 수집. 이미 수집된 시군구는 스킵 (이어받기 지원)."""
        codes = sigungu_codes or METRO_SIGUNGU_CODES
        result = {"collected": 0, "failed": [], "skipped": 0}
        for code in codes:
            if self._bm_repo.count_by_sigungu(code) > 0:
                result["skipped"] += 1
                logger.info(f"[Collect] {code}: skip (already collected)")
                continue
            try:
                raw_items = self._client.fetch_apartments_by_sigungu(code)
                for raw in raw_items:
                    parsed = self._client.parse_item(raw)
                    if not parsed.get("mgm_pk") or not parsed.get("building_name"):
                        continue
                    bm = BuildingMaster(
                        mgm_pk=parsed["mgm_pk"],
                        building_name=parsed["building_name"],
                        sigungu_code=parsed.get("sigungu_code") or code,
                        bjdong_code=parsed.get("bjdong_code", ""),
                        parcel_pnu=parsed.get("parcel_pnu", ""),
                        road_address=parsed.get("road_address"),
                        jibun_address=parsed.get("jibun_address"),
                        completion_year=parsed.get("completion_year"),
                        total_units=parsed.get("total_units"),
                        total_buildings=parsed.get("total_buildings"),
                        floor_area_ratio=parsed.get("floor_area_ratio"),
                        building_coverage_ratio=parsed.get("building_coverage_ratio"),
                        collected_at=datetime.now(timezone.utc).isoformat(),
                    )
                    self._bm_repo.upsert(bm)
                    result["collected"] += 1
                logger.info(f"[Collect] {code}: {len(raw_items)} items")
            except Exception as e:
                logger.error(f"[Collect] {code} failed: {e}")
                result["failed"].append(code)
        return result

    def map_to_apt_master(self) -> dict:
        """apt_master 항목을 building_master와 매핑. 유사도 ≥ 0.8이면 pnu 업데이트."""
        entries = self._apt_master_repo.get_all_for_mapping()
        result = {"mapped": 0, "no_candidates": 0, "below_threshold": 0, "total": len(entries)}
        for entry in entries:
            candidates = self._bm_repo.get_by_sigungu(entry.district_code)
            if not candidates:
                result["no_candidates"] += 1
                continue
            best_bm, best_score = _best_match(entry.apt_name, candidates)
            if best_bm and best_score >= 0.8:
                self._apt_master_repo.update_building_mapping(
                    entry.id, best_bm.mgm_pk, best_score
                )
                result["mapped"] += 1
            else:
                result["below_threshold"] += 1
        return result
```

- [ ] **Step 4: collect() 테스트 실행 (PASS 확인)**

```bash
arch -arm64 /Users/kks/Desktop/Laboratory/Consigliere/.venv/bin/python3.12 \
  -m pytest tests/modules/real_estate/building_master/test_building_master_service.py -v
```

Expected: 4 passed

- [ ] **Step 5: 커밋**

```bash
git add src/modules/real_estate/building_master/building_master_service.py \
        tests/modules/real_estate/building_master/test_building_master_service.py
git commit -m "feat(building-master): BuildingMasterService.collect() — 수도권 수집 + 이어받기"
```

---

## Task 6: BuildingMasterService.map_to_apt_master()

**Files:**
- Modify: `tests/modules/real_estate/building_master/test_building_master_service.py`

- [ ] **Step 1: map_to_apt_master() 테스트 추가**

`test_building_master_service.py` 끝에 아래 테스트를 추가한다:

```python
from modules.real_estate.models import AptMasterEntry
from datetime import datetime, timezone as tz


def _seed_apt_master(repo, name: str, district_code: str) -> AptMasterEntry:
    now = datetime.now(tz.utc).isoformat()
    entry = AptMasterEntry(apt_name=name, district_code=district_code, created_at=now)
    repo.upsert(entry)
    return repo.get_by_name_district(name, district_code)


def _seed_building(repo, mgm_pk: str, name: str, sigungu_code: str) -> None:
    repo.upsert(BuildingMaster(
        mgm_pk=mgm_pk, building_name=name, sigungu_code=sigungu_code,
        collected_at=datetime.now(tz.utc).isoformat(),
    ))


def test_map_high_similarity_sets_pnu():
    bm_repo = BuildingMasterRepository(db_path=":memory:")
    apt_repo = AptMasterRepository(db_path=":memory:")
    _seed_apt_master(apt_repo, "래미안아파트", "11650")
    _seed_building(bm_repo, "MGM001", "래미안아파트", "11650")

    svc = BuildingMasterService(MagicMock(), bm_repo, apt_repo)
    result = svc.map_to_apt_master()

    assert result["mapped"] == 1
    mapped = apt_repo.get_by_name_district("래미안아파트", "11650")
    assert mapped.pnu == "MGM001"
    assert mapped.mapping_score >= 0.8


def test_map_low_similarity_leaves_pnu_null():
    bm_repo = BuildingMasterRepository(db_path=":memory:")
    apt_repo = AptMasterRepository(db_path=":memory:")
    _seed_apt_master(apt_repo, "래미안아파트", "11650")
    _seed_building(bm_repo, "MGM002", "현대아이파크", "11650")  # 완전히 다른 이름

    svc = BuildingMasterService(MagicMock(), bm_repo, apt_repo)
    result = svc.map_to_apt_master()

    assert result["mapped"] == 0
    assert result["below_threshold"] == 1
    entry = apt_repo.get_by_name_district("래미안아파트", "11650")
    assert entry.pnu is None


def test_map_no_candidates_in_sigungu():
    bm_repo = BuildingMasterRepository(db_path=":memory:")
    apt_repo = AptMasterRepository(db_path=":memory:")
    _seed_apt_master(apt_repo, "래미안아파트", "11650")
    _seed_building(bm_repo, "MGM003", "래미안아파트", "11680")  # 다른 시군구

    svc = BuildingMasterService(MagicMock(), bm_repo, apt_repo)
    result = svc.map_to_apt_master()

    assert result["no_candidates"] == 1
    assert result["mapped"] == 0


def test_map_skips_already_mapped():
    bm_repo = BuildingMasterRepository(db_path=":memory:")
    apt_repo = AptMasterRepository(db_path=":memory:")
    entry = _seed_apt_master(apt_repo, "래미안아파트", "11650")
    apt_repo.update_building_mapping(entry.id, "EXISTING_MGM", 0.95)
    _seed_building(bm_repo, "MGM004", "래미안아파트", "11650")

    svc = BuildingMasterService(MagicMock(), bm_repo, apt_repo)
    result = svc.map_to_apt_master()

    assert result["total"] == 0  # get_all_for_mapping은 pnu IS NULL만 반환
    assert result["mapped"] == 0
```

- [ ] **Step 2: 테스트 실행 (PASS 확인)**

```bash
arch -arm64 /Users/kks/Desktop/Laboratory/Consigliere/.venv/bin/python3.12 \
  -m pytest tests/modules/real_estate/building_master/test_building_master_service.py -v
```

Expected: 8 passed (이전 4 + 신규 4)

- [ ] **Step 3: 전체 테스트 회귀 확인**

```bash
arch -arm64 /Users/kks/Desktop/Laboratory/Consigliere/.venv/bin/python3.12 \
  -m pytest tests/modules/real_estate/ -v --ignore=tests/modules/real_estate/commute 2>&1 | tail -15
```

Expected: 전체 PASS, 실패 없음

- [ ] **Step 4: 커밋**

```bash
git add tests/modules/real_estate/building_master/test_building_master_service.py
git commit -m "test(building-master): map_to_apt_master() 유사도 매핑 테스트"
```

---

## Task 7: build_building_master.py 스크립트

**Files:**
- Create: `scripts/build_building_master.py`

- [ ] **Step 1: 스크립트 작성**

```python
# scripts/build_building_master.py
"""
수도권 아파트 Building Master DB 구축 스크립트.

사용법:
    arch -arm64 .venv/bin/python3.12 scripts/build_building_master.py --collect
    arch -arm64 .venv/bin/python3.12 scripts/build_building_master.py --map
    arch -arm64 .venv/bin/python3.12 scripts/build_building_master.py --rebuild

옵션:
    --collect  : 건축물대장 API 수집만 수행 (이어받기 지원)
    --map      : building_master → apt_master 매핑만 수행
    --rebuild  : DB 초기화 후 전체 재수집 + 매핑
"""
import os
import sys
import logging
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from modules.real_estate.config import RealEstateConfig
from modules.real_estate.building_master.building_register_client import BuildingRegisterClient
from modules.real_estate.building_master.building_master_repository import BuildingMasterRepository
from modules.real_estate.apt_master_repository import AptMasterRepository
from modules.real_estate.building_master.building_master_service import BuildingMasterService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Building Master DB 구축")
    parser.add_argument("--collect", action="store_true", help="건축물대장 수집")
    parser.add_argument("--map", action="store_true", help="apt_master 매핑")
    parser.add_argument("--rebuild", action="store_true", help="전체 재수집 + 매핑")
    args = parser.parse_args()

    if not any([args.collect, args.map, args.rebuild]):
        parser.print_help()
        sys.exit(1)

    config = RealEstateConfig()
    db_path = config.get("real_estate_db_path", "data/real_estate.db")

    client = BuildingRegisterClient()
    bm_repo = BuildingMasterRepository(db_path=db_path)
    apt_repo = AptMasterRepository(db_path=db_path)
    svc = BuildingMasterService(client, bm_repo, apt_repo)

    if args.rebuild:
        logger.info("=== REBUILD: building_master 초기화 ===")
        import sqlite3
        with sqlite3.connect(db_path) as conn:
            conn.execute("DROP TABLE IF EXISTS building_master")
        bm_repo._init_db()
        _run_collect(svc)
        _run_map(svc)
        return

    if args.collect:
        _run_collect(svc)

    if args.map:
        _run_map(svc)


def _run_collect(svc: BuildingMasterService) -> None:
    logger.info("=== COLLECT 시작 ===")
    result = svc.collect()
    logger.info(
        f"완료 — collected={result['collected']} "
        f"skipped={result['skipped']} "
        f"failed={len(result['failed'])}"
    )
    if result["failed"]:
        logger.warning(f"실패 코드: {result['failed']}")


def _run_map(svc: BuildingMasterService) -> None:
    logger.info("=== MAP 시작 ===")
    result = svc.map_to_apt_master()
    logger.info(
        f"완료 — mapped={result['mapped']} "
        f"below_threshold={result['below_threshold']} "
        f"no_candidates={result['no_candidates']} "
        f"total={result['total']}"
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 스크립트 임포트 확인**

```bash
arch -arm64 /Users/kks/Desktop/Laboratory/Consigliere/.venv/bin/python3.12 \
  scripts/build_building_master.py --help
```

Expected: usage 메시지 출력 (--collect / --map / --rebuild 설명)

- [ ] **Step 3: 커밋**

```bash
git add scripts/build_building_master.py
git commit -m "feat(building-master): build_building_master.py 스크립트 — --collect/--map/--rebuild"
```

---

## Task 8: FastAPI 엔드포인트 + DI 연결

**Files:**
- Modify: `src/api/dependencies.py`
- Modify: `src/api/routers/real_estate.py`

- [ ] **Step 1: dependencies.py에 팩토리 추가**

`src/api/dependencies.py` 파일의 기존 import 블록 끝에 추가:

```python
from modules.real_estate.building_master.building_register_client import BuildingRegisterClient
from modules.real_estate.building_master.building_master_repository import BuildingMasterRepository
from modules.real_estate.building_master.building_master_service import BuildingMasterService
```

그리고 기존 전역 인스턴스 선언 블록 끝에 추가:

```python
_bm_repo = BuildingMasterRepository(db_path=_re_db_path)
_bm_service = BuildingMasterService(
    client=BuildingRegisterClient(),
    bm_repo=_bm_repo,
    apt_master_repo=_apt_master_repo,
)
```

그리고 팩토리 함수 추가:

```python
def get_building_master_service() -> BuildingMasterService:
    return _bm_service
```

- [ ] **Step 2: 엔드포인트 추가**

`src/api/routers/real_estate.py` 파일에서 기존 import에 추가:

```python
from api.dependencies import (
    ...
    get_building_master_service,
)
from modules.real_estate.building_master.building_master_service import BuildingMasterService
```

그리고 라우터 맨 끝에 엔드포인트를 추가한다:

```python
@router.post("/jobs/building-master/collect")
def collect_building_master(
    rebuild: bool = False,
    bm_service: BuildingMasterService = Depends(get_building_master_service),
):
    """건축물대장 수집 + apt_master 매핑 실행. rebuild=true 시 기존 데이터 초기화."""
    try:
        if rebuild:
            import sqlite3
            from modules.real_estate.config import RealEstateConfig
            db_path = RealEstateConfig().get("real_estate_db_path", "data/real_estate.db")
            with sqlite3.connect(db_path) as conn:
                conn.execute("DROP TABLE IF EXISTS building_master")
            bm_service._bm_repo._init_db()

        collect_result = bm_service.collect()
        map_result = bm_service.map_to_apt_master()
        return {
            "status": "success",
            "collect": collect_result,
            "map": map_result,
        }
    except Exception as e:
        logger.error(f"[BuildingMaster] collect error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 3: 서버 임포트 확인**

```bash
arch -arm64 /Users/kks/Desktop/Laboratory/Consigliere/.venv/bin/python3.12 \
  -c "import sys; sys.path.insert(0,'src'); from api.routers.real_estate import router; print('OK')"
```

Expected: `OK` 출력 (ImportError 없음)

- [ ] **Step 4: 전체 테스트 최종 확인**

```bash
arch -arm64 /Users/kks/Desktop/Laboratory/Consigliere/.venv/bin/python3.12 \
  -m pytest tests/modules/real_estate/building_master/ \
            tests/modules/real_estate/test_apt_master_repository.py \
  -v 2>&1 | tail -20
```

Expected: 모든 테스트 PASS

- [ ] **Step 5: 커밋**

```bash
git add src/api/dependencies.py \
        src/api/routers/real_estate.py
git commit -m "feat(building-master): FastAPI POST /jobs/building-master/collect 엔드포인트"
```

---

## Self-Review

**Spec coverage 점검:**
- ✅ `building_master` 테이블 신규 생성 (Task 3)
- ✅ `apt_master.pnu` + `mapping_score` 컬럼 추가 (Task 4)
- ✅ 건축HUB API 클라이언트 (Task 2)
- ✅ 수도권 sigunguCd 목록 (Task 5 — `METRO_SIGUNGU_CODES`)
- ✅ `mainPurpsCdNm` 아파트 필터링 (Task 2)
- ✅ 매핑 전략 (sigungu 필터 + 이름 유사도 ≥ 0.8) (Task 5, 6)
- ✅ 이어받기 지원 (`count_by_sigungu` 체크) (Task 5)
- ✅ `--collect / --map / --rebuild` 스크립트 (Task 7)
- ✅ API 엔드포인트 (Task 8)
- ✅ `mgm_pk` (22자리 건축HUB PK) → `building_master` PK (Task 3)
- ✅ `parcel_pnu` = sigungu + bjdong 10자리 (Task 5)

**Spec vs 현실 차이 (구현 시 유의):**
- 스펙은 `parcel_pnu` 15자리(sigungu+bjdong+지목+지번)를 사용하는 필지 레벨 매핑을 설명했으나, `apt_master`에 `jibun`(지번) 필드가 없어 10자리 법정동 레벨 + 이름 유사도로 구현함. 향후 `transactions`에 `jibun` 컬럼이 추가되면 매핑 정밀도를 높일 수 있음.

**Type consistency:**
- `BuildingMaster.mgm_pk` → `update_building_mapping(apt_id, mgm_pk, score)` → `apt_master.pnu` 컬럼 ✅
- `BuildingMasterRepository.get_by_sigungu(sigungu_code)` → `BuildingMasterService.map_to_apt_master()` → `entry.district_code` ✅
- `AptMasterEntry.id` → `update_building_mapping(apt_id, ...)` ✅
