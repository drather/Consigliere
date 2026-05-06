# 부동산 리포트 품질 개선 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 후보 선정 필터링·building 데이터 enrichment·출퇴근 enrichment·실거래가 면적 수정으로 리포트 점수 변별력과 데이터 완성도를 확보한다.

**Architecture:** 6개 독립 Task를 순서대로 구현. Task 1(모델·Repository)이 Task 2·3의 `road_address` / `household_count` 필드를 공급하므로 반드시 먼저 완료해야 한다. Task 4·5는 독립적으로 진행 가능. Task 6이 엔드포인트를 통합하고 Docker 재빌드 후 리포트를 재생성해 결과를 검증한다.

**Tech Stack:** Python 3.12, SQLite (real_estate.db / commute_cache.db), pytest, Docker Compose

---

## 파일 변경 범위

| 파일 | 역할 |
|------|------|
| `src/modules/real_estate/models.py` | AptMasterEntry에 household_count·road_address·approved_date 추가 |
| `src/modules/real_estate/apt_master_repository.py` | search()에 min_household_count 파라미터·apartments LEFT JOIN 추가 |
| `src/modules/real_estate/commute/commute_service.py` | get()에 dest_override·dest_lat_override·dest_lng_override 추가 |
| `src/modules/real_estate/report_orchestrator.py` | _enrich_with_building()·_resolve_workplace_coords()·_enrich_with_commute() 추가, _enrich_with_trend() 다중 면적, _build_markdown() 예산 섹션 개선, __init__ 파라미터 추가 |
| `src/modules/real_estate/poi_collector.py` | 학교 쿼리 분리 (초등·중학 별도 호출 + 중복 제거) |
| `src/api/routers/real_estate.py` | generate_professional_report() — persona 필터·CommuteService 주입·[:100]·re_db_path 전달 |
| `tests/modules/real_estate/test_apt_master_repository.py` | search() min_household_count 필터 테스트 추가 |
| `tests/modules/real_estate/commute/test_commute_service.py` | get() destination override 테스트 추가 |
| `tests/modules/real_estate/test_report_orchestrator.py` | orchestrator fixture 수정, 신규 enrich 함수 테스트 추가 |

---

## Task 1: AptMasterEntry 모델 필드 추가 + search() min_household_count 파라미터

**Files:**
- Modify: `src/modules/real_estate/models.py:43-60`
- Modify: `src/modules/real_estate/apt_master_repository.py:59-73` (_row_to_entry), `152-179` (search)
- Test: `tests/modules/real_estate/test_apt_master_repository.py`

**배경:**
- `AptMasterEntry`에 `household_count`, `road_address`, `approved_date` 필드가 없어 enrichment 불가.
- `search()`가 `apt_master` 단독 조회라 세대수 필터링 불가.
- 수정 후 `search(sigungu="강남구", min_household_count=500)` → `apartments` LEFT JOIN으로 필터링.
- `apartments` 테이블이 없는 환경(구 테스트 DB)에서도 동작하도록 fallback 처리.

- [ ] **Step 1: 실패 테스트 작성**

`tests/modules/real_estate/test_apt_master_repository.py` 파일 끝에 추가:

```python
import sqlite3 as _sqlite3


def _insert_apartment(db_path: str, complex_code: str, household_count: int, road_address: str = "", approved_date: str = ""):
    """테스트용 apartments 레코드 직접 삽입."""
    with _sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS apartments (
                complex_code TEXT PRIMARY KEY,
                household_count INTEGER DEFAULT 0,
                road_address TEXT DEFAULT '',
                approved_date TEXT DEFAULT '',
                apt_name TEXT DEFAULT '',
                district_code TEXT DEFAULT '',
                sido TEXT DEFAULT '',
                sigungu TEXT DEFAULT '',
                eupmyeondong TEXT DEFAULT '',
                ri TEXT DEFAULT '',
                legal_address TEXT DEFAULT '',
                building_count INTEGER DEFAULT 0,
                parking_count INTEGER DEFAULT 0,
                constructor TEXT DEFAULT '',
                developer TEXT DEFAULT '',
                top_floor INTEGER DEFAULT 0,
                base_floor INTEGER DEFAULT 0,
                total_area REAL DEFAULT 0.0,
                heat_type TEXT DEFAULT '',
                elevator_count INTEGER DEFAULT 0,
                units_60 INTEGER DEFAULT 0,
                units_85 INTEGER DEFAULT 0,
                units_135 INTEGER DEFAULT 0,
                units_136_plus INTEGER DEFAULT 0,
                fetched_at TEXT DEFAULT ''
            )
        """)
        conn.execute(
            "INSERT OR REPLACE INTO apartments (complex_code, household_count, road_address, approved_date) VALUES (?, ?, ?, ?)",
            (complex_code, household_count, road_address, approved_date),
        )


class TestSearchMinHousehold:
    def test_min_household_filters_below_threshold(self, tmp_path):
        """min_household_count=500 설정 시 세대수 500 미만 단지는 제외된다."""
        db_path = str(tmp_path / "test.db")
        repo = AptMasterRepository(db_path=db_path)
        # 단지 A: complex_code 있음, 세대수 293 (제외 대상)
        repo.upsert(_make_entry("소형단지", "11680", sigungu="강남구", complex_code="CC001"))
        _insert_apartment(db_path, "CC001", household_count=293, road_address="서울 강남구 테헤란로 1")
        # 단지 B: complex_code 있음, 세대수 1500 (포함 대상)
        repo.upsert(_make_entry("대형단지", "11680", sigungu="강남구", complex_code="CC002"))
        _insert_apartment(db_path, "CC002", household_count=1500, road_address="서울 강남구 역삼동 100")

        results = repo.search(sigungu="강남구", min_household_count=500)

        names = [r.apt_name for r in results]
        assert "대형단지" in names
        assert "소형단지" not in names

    def test_min_household_zero_returns_all(self, tmp_path):
        """min_household_count=0 (기본값)이면 세대수 무관 전부 반환."""
        db_path = str(tmp_path / "test.db")
        repo = AptMasterRepository(db_path=db_path)
        repo.upsert(_make_entry("소형단지", "11680", sigungu="강남구", complex_code="CC001"))
        _insert_apartment(db_path, "CC001", household_count=100)

        results = repo.search(sigungu="강남구", min_household_count=0)
        assert len(results) == 1

    def test_search_returns_road_address_from_apartments(self, tmp_path):
        """search() 결과에 apartments.road_address가 채워진다."""
        db_path = str(tmp_path / "test.db")
        repo = AptMasterRepository(db_path=db_path)
        repo.upsert(_make_entry("래미안", "11650", sigungu="서초구", complex_code="CC010"))
        _insert_apartment(db_path, "CC010", household_count=800, road_address="서울 서초구 반포대로 1")

        results = repo.search(sigungu="서초구")
        assert results[0].road_address == "서울 서초구 반포대로 1"

    def test_search_without_apartments_table_does_not_raise(self, tmp_path):
        """apartments 테이블이 없어도 search()는 정상 반환한다."""
        db_path = str(tmp_path / "fallback.db")
        repo = AptMasterRepository(db_path=db_path)
        repo.upsert(_make_entry("테스트단지", "11680", sigungu="강남구"))
        # apartments 테이블 미생성 상태

        results = repo.search(sigungu="강남구", min_household_count=0)
        assert len(results) == 1
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_apt_master_repository.py::TestSearchMinHousehold -v 2>&1 | tail -15
```

Expected: `FAILED` — `search()` has no `min_household_count` parameter.

- [ ] **Step 3: AptMasterEntry 모델에 필드 추가**

`src/modules/real_estate/models.py` — `AptMasterEntry` dataclass에 3개 필드 추가:

```python
@dataclass
class AptMasterEntry:
    apt_name: str
    district_code: str
    sido: str = ""
    sigungu: str = ""
    complex_code: Optional[str] = None
    tx_count: int = 0
    first_traded: Optional[str] = None
    last_traded: Optional[str] = None
    created_at: str = ""
    id: Optional[int] = None
    pnu: Optional[str] = None
    mapping_score: Optional[float] = None
    # apartments JOIN으로 채워지는 선택 필드
    household_count: Optional[int] = None
    road_address: Optional[str] = None
    approved_date: Optional[str] = None
```

- [ ] **Step 4: _row_to_entry() 업데이트**

`src/modules/real_estate/apt_master_repository.py` — `_row_to_entry()` 함수 전체 교체:

```python
def _row_to_entry(row: sqlite3.Row) -> AptMasterEntry:
    keys = row.keys()
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
        pnu=row["pnu"] if "pnu" in keys else None,
        mapping_score=row["mapping_score"] if "mapping_score" in keys else None,
        household_count=row["household_count"] if "household_count" in keys else None,
        road_address=row["road_address"] if "road_address" in keys else None,
        approved_date=row["approved_date"] if "approved_date" in keys else None,
    )
```

- [ ] **Step 5: search() 메서드 교체**

`src/modules/real_estate/apt_master_repository.py` — `search()` 메서드 전체를 아래 코드로 교체:

```python
def search(
    self,
    apt_name: str = "",
    sido: str = "",
    sigungu: str = "",
    min_household_count: int = 0,
    limit: int = 500,
) -> List[AptMasterEntry]:
    """apt_name(부분일치) / sido / sigungu 필터 검색.

    min_household_count > 0이면 apartments 테이블 LEFT JOIN으로 세대수 필터링.
    apartments 테이블이 없는 환경에서는 JOIN 없이 fallback.
    """
    clauses: list = []
    params: list = []

    if apt_name:
        clauses.append("am.apt_name LIKE ?")
        params.append(f"%{apt_name}%")
    if sido:
        clauses.append("am.sido = ?")
        params.append(sido)
    if sigungu:
        clauses.append("am.sigungu = ?")
        params.append(sigungu)
    if min_household_count > 0:
        clauses.append("(a.household_count >= ? OR a.household_count IS NULL AND ? = 0)")
        params.extend([min_household_count, min_household_count])

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    order = "ORDER BY COALESCE(a.household_count, 0) DESC" if min_household_count > 0 else "ORDER BY am.apt_name"
    sql = (
        f"SELECT am.*, a.household_count, a.road_address, a.approved_date "
        f"FROM apt_master am "
        f"LEFT JOIN apartments a ON am.complex_code = a.complex_code "
        f"{where} {order} LIMIT ?"
    )
    params.append(limit)

    try:
        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_row_to_entry(r) for r in rows]
    except sqlite3.OperationalError:
        # apartments 테이블이 없는 환경 fallback — JOIN 없이 재시도
        plain_clauses: list = []
        plain_params: list = []
        if apt_name:
            plain_clauses.append("apt_name LIKE ?")
            plain_params.append(f"%{apt_name}%")
        if sido:
            plain_clauses.append("sido = ?")
            plain_params.append(sido)
        if sigungu:
            plain_clauses.append("sigungu = ?")
            plain_params.append(sigungu)
        plain_where = ("WHERE " + " AND ".join(plain_clauses)) if plain_clauses else ""
        plain_sql = f"SELECT * FROM apt_master {plain_where} ORDER BY apt_name LIMIT ?"
        plain_params.append(limit)
        with self._conn() as conn:
            rows = conn.execute(plain_sql, plain_params).fetchall()
        return [_row_to_entry(r) for r in rows]
```

- [ ] **Step 6: 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_apt_master_repository.py -v 2>&1 | tail -20
```

Expected: 모든 테스트 PASS (기존 + 신규 TestSearchMinHousehold).

- [ ] **Step 7: 커밋**

```bash
git add src/modules/real_estate/models.py \
        src/modules/real_estate/apt_master_repository.py \
        tests/modules/real_estate/test_apt_master_repository.py
git commit -m "feat(apt-master): search()에 min_household_count 파라미터 추가 및 apartments JOIN"
```

---

## Task 2: _enrich_with_building() 추가 (building_master → 용적률·건폐율·준공연도)

**Files:**
- Modify: `src/modules/real_estate/report_orchestrator.py`
- Test: `tests/modules/real_estate/test_report_orchestrator.py`

**배경:**
- `apt_master.pnu` → `building_master.mgm_pk` 조인으로 `floor_area_ratio`, `building_coverage_ratio`, `completion_year` 획득.
- pnu 없는 단지는 `apartments.approved_date`(YYYYMMDD)에서 `build_year`를 파생.
- `ReportOrchestrator.__init__`에 `re_db_path: str` 추가.

- [ ] **Step 1: 실패 테스트 작성**

`tests/modules/real_estate/test_report_orchestrator.py` — 파일 끝에 추가:

```python
import sqlite3 as _sqlite3
from modules.real_estate.report_orchestrator import _enrich_with_building


def _setup_building_db(db_path: str):
    """테스트용 building_master 테이블 생성."""
    with _sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS building_master (
                mgm_pk TEXT PRIMARY KEY,
                building_name TEXT,
                sigungu_code TEXT,
                floor_area_ratio REAL,
                building_coverage_ratio REAL,
                completion_year INTEGER,
                collected_at TEXT
            )
        """)
        conn.execute(
            "INSERT INTO building_master VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("BM001", "래미안테스트", "11650", 247.3, 21.8, 2002, "2026-01-01"),
        )


class TestEnrichWithBuilding:
    def test_pnu_match_fills_far_bcr_build_year(self, tmp_path):
        """pnu가 있고 building_master에 매칭되면 FAR·BCR·build_year가 채워진다."""
        db_path = str(tmp_path / "re.db")
        _setup_building_db(db_path)
        candidates = [{"apt_name": "래미안", "pnu": "BM001"}]

        result = _enrich_with_building(candidates, db_path)

        assert result[0]["floor_area_ratio"] == pytest.approx(247.3)
        assert result[0]["building_coverage_ratio"] == pytest.approx(21.8)
        assert result[0]["build_year"] == 2002

    def test_no_pnu_uses_approved_date_fallback(self, tmp_path):
        """pnu 없고 approved_date가 있으면 앞 4자리로 build_year 파생."""
        db_path = str(tmp_path / "re.db")
        _setup_building_db(db_path)
        candidates = [{"apt_name": "기타단지", "pnu": None, "approved_date": "20050315"}]

        result = _enrich_with_building(candidates, db_path)

        assert result[0]["build_year"] == 2005
        assert result[0].get("floor_area_ratio") is None

    def test_no_match_returns_candidate_unchanged(self, tmp_path):
        """pnu가 있지만 building_master에 없으면 원본 그대로 반환."""
        db_path = str(tmp_path / "re.db")
        _setup_building_db(db_path)
        candidates = [{"apt_name": "미매핑단지", "pnu": "UNKNOWN_PNU"}]

        result = _enrich_with_building(candidates, db_path)

        assert result[0].get("floor_area_ratio") is None
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_report_orchestrator.py::TestEnrichWithBuilding -v 2>&1 | tail -10
```

Expected: `ImportError` — `_enrich_with_building` not in `report_orchestrator`.

- [ ] **Step 3: _enrich_with_building() 구현**

`src/modules/real_estate/report_orchestrator.py` 상단 import에 `import sqlite3` 추가 (없는 경우).

기존 `_enrich_with_trend` 함수 바로 위에 아래 함수 추가:

```python
def _enrich_with_building(candidates: List[Dict], db_path: str) -> List[Dict]:
    """pnu → building_master JOIN으로 용적률·건폐율·준공연도를 채운다.
    pnu 없으면 approved_date 앞 4자리에서 build_year를 파생한다."""
    import sqlite3 as _sqlite3
    pnu_list = [c.get("pnu") for c in candidates if c.get("pnu")]
    bm_map: Dict[str, Dict] = {}
    if pnu_list:
        try:
            placeholders = ",".join("?" * len(pnu_list))
            with _sqlite3.connect(db_path) as conn:
                rows = conn.execute(
                    f"SELECT mgm_pk, floor_area_ratio, building_coverage_ratio, completion_year "
                    f"FROM building_master WHERE mgm_pk IN ({placeholders})",
                    pnu_list,
                ).fetchall()
            bm_map = {
                r[0]: {
                    "floor_area_ratio": r[1],
                    "building_coverage_ratio": r[2],
                    "build_year": r[3],
                }
                for r in rows
            }
        except Exception as e:
            logger.warning(f"[Orchestrator] building_master 조회 실패: {e}")

    enriched = []
    for c in candidates:
        result = dict(c)
        pnu = c.get("pnu")
        if pnu and pnu in bm_map:
            result.update(bm_map[pnu])
        if not result.get("build_year") and result.get("approved_date"):
            try:
                result["build_year"] = int(str(result["approved_date"])[:4])
            except (ValueError, TypeError):
                pass
        enriched.append(result)
    return enriched
```

- [ ] **Step 4: ReportOrchestrator.__init__에 re_db_path 추가**

`ReportOrchestrator.__init__` 시그니처 변경:

```python
class ReportOrchestrator:
    def __init__(
        self,
        llm: BaseLLMClient,
        prompt_loader: PromptLoader,
        poi_collector: PoiCollector,
        trend_analyzer: TrendAnalyzer,
        report_repository: ReportRepository,
        re_db_path: str = "",        # ← 신규 (building_master 조회용)
        commute_svc=None,            # ← 신규 (Task 3에서 사용, 미리 추가)
        geocoder=None,               # ← 신규 (Task 3에서 사용, 미리 추가)
    ):
        self._llm = llm
        self._prompt_loader = prompt_loader
        self._poi_collector = poi_collector
        self._trend_analyzer = trend_analyzer
        self._repo = report_repository
        self._re_db_path = re_db_path
        self._commute_svc = commute_svc
        self._geocoder = geocoder
```

`generate()` 파이프라인에 `_enrich_with_building` 호출 추가 (`_enrich_with_poi` 바로 다음):

```python
enriched = _enrich_with_poi(candidates, self._poi_collector)
enriched = _enrich_with_building(enriched, self._re_db_path)   # ← 신규
enriched = _enrich_with_trend(enriched, self._trend_analyzer)
```

- [ ] **Step 5: 기존 orchestrator fixture 수정**

`tests/modules/real_estate/test_report_orchestrator.py` — `orchestrator` fixture 변경:

```python
@pytest.fixture
def orchestrator(mock_llm, mock_prompt_loader, mock_poi_collector, mock_trend_analyzer, tmp_path):
    from modules.real_estate.report_repository import ReportRepository
    report_repo = ReportRepository(storage_path=str(tmp_path))
    return ReportOrchestrator(
        llm=mock_llm,
        prompt_loader=mock_prompt_loader,
        poi_collector=mock_poi_collector,
        trend_analyzer=mock_trend_analyzer,
        report_repository=report_repo,
        re_db_path=str(tmp_path / "re.db"),  # ← 추가
    )
```

- [ ] **Step 6: 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_report_orchestrator.py -v 2>&1 | tail -20
```

Expected: 모든 테스트 PASS.

- [ ] **Step 7: 커밋**

```bash
git add src/modules/real_estate/report_orchestrator.py \
        tests/modules/real_estate/test_report_orchestrator.py
git commit -m "feat(orchestrator): _enrich_with_building() 추가 — building_master에서 FAR·BCR·준공연도 enrichment"
```

---

## Task 3: CommuteService.get() destination override + _enrich_with_commute()

**Files:**
- Modify: `src/modules/real_estate/commute/commute_service.py:33-71`
- Modify: `src/modules/real_estate/report_orchestrator.py`
- Test: `tests/modules/real_estate/commute/test_commute_service.py`
- Test: `tests/modules/real_estate/test_report_orchestrator.py`

**배경:**
- `CommuteService.get()`에 `dest_override`/`dest_lat_override`/`dest_lng_override` 추가.
- `_resolve_workplace_coords()` — persona의 `commute.workplace_station`을 Geocoder로 좌표 변환.
- `_enrich_with_commute()` — 각 candidate에 `commute_transit_minutes` 채움.
- `road_address`는 Task 1에서 `AptMasterEntry`에 추가된 필드를 사용.

- [ ] **Step 1: CommuteService 실패 테스트 작성**

`tests/modules/real_estate/commute/test_commute_service.py` — 파일 끝에 추가:

```python
class TestCommuteServiceDestOverride:
    def test_dest_override_uses_different_destination_for_cache(self):
        """dest_override가 다르면 기본 destination 캐시와 별개로 조회한다."""
        repo = CommuteRepository(db_path=":memory:", ttl_days=90)
        # 기본 destination(삼성역) 캐시 저장
        from modules.real_estate.commute.models import CommuteResult
        repo.upsert(CommuteResult(
            origin_key="11680__테스트",
            destination="삼성역",
            mode="transit",
            duration_minutes=20,
            distance_meters=1000,
        ))
        mock_geocoder = MagicMock()
        mock_geocoder.geocode.return_value = (37.4942, 127.0611)
        mock_client = MagicMock()
        mock_client.route_with_legs.return_value = (35, 5000, [], "판교역 경유")
        svc = make_service(repo=repo, tmap_client=mock_client, geocoder=mock_geocoder)

        # dest_override를 판교역으로 지정 → 캐시 미스 → API 호출
        result = svc.get(
            origin_key="11680__테스트",
            road_address="서울 강남구 역삼동 123",
            apt_name="테스트",
            district_code="11680",
            mode="transit",
            dest_override="판교역",
            dest_lat_override=37.3952,
            dest_lng_override=127.1109,
        )

        assert result.duration_minutes == 35
        assert result.destination == "판교역"
        mock_client.route_with_legs.assert_called_once()

    def test_dest_override_none_uses_default(self):
        """dest_override=None이면 초기화 시 설정한 기본 destination을 사용한다."""
        repo = CommuteRepository(db_path=":memory:", ttl_days=90)
        from modules.real_estate.commute.models import CommuteResult
        repo.upsert(CommuteResult(
            origin_key="11680__래미안",
            destination="삼성역",
            mode="transit",
            duration_minutes=18,
            distance_meters=900,
        ))
        svc = make_service(repo=repo)

        result = svc.get(
            origin_key="11680__래미안",
            road_address="서울 강남구 역삼동 1",
            apt_name="래미안",
            district_code="11680",
            mode="transit",
            dest_override=None,
        )

        assert result.duration_minutes == 18
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/commute/test_commute_service.py::TestCommuteServiceDestOverride -v 2>&1 | tail -10
```

Expected: `FAILED` — `get()` does not accept `dest_override`.

- [ ] **Step 3: CommuteService.get() 수정**

`src/modules/real_estate/commute/commute_service.py` — `get()` 메서드 전체 교체:

```python
def get(
    self,
    origin_key: str,
    road_address: str,
    apt_name: str,
    district_code: str,
    mode: str,
    dest_override: Optional[str] = None,
    dest_lat_override: Optional[float] = None,
    dest_lng_override: Optional[float] = None,
) -> Optional[CommuteResult]:
    """단일 모드 출퇴근 시간 반환. 실패 시 None.

    dest_override 제공 시 초기화 destination 대신 사용.
    캐시 키는 (origin_key, destination, mode) 복합키.
    """
    dest = dest_override or self._dest
    dest_lat = dest_lat_override if dest_lat_override is not None else self._dest_lat
    dest_lng = dest_lng_override if dest_lng_override is not None else self._dest_lng

    cached = self._repo.get(origin_key, dest, mode)
    if cached is not None:
        return cached

    coords = self._geocoder.geocode(apt_name, district_code, address=road_address)
    if coords is None:
        logger.warning("[CommuteService] geocode 실패: %s / %s", apt_name, road_address)
        return None

    origin_lat, origin_lng = coords
    try:
        duration, distance, legs, route_summary = self._client.route_with_legs(
            origin_lat, origin_lng, dest_lat, dest_lng, mode=mode
        )
    except Exception as exc:
        logger.warning("[CommuteService] T-map %s 실패 (%s): %s", mode, apt_name, exc)
        return None

    result = CommuteResult(
        origin_key=origin_key,
        destination=dest,
        mode=mode,
        duration_minutes=duration,
        distance_meters=distance,
        cached=False,
        legs=legs,
        route_summary=route_summary,
    )
    self._repo.upsert(result)
    return result
```

- [ ] **Step 4: CommuteService 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/commute/test_commute_service.py -v 2>&1 | tail -15
```

Expected: 모든 테스트 PASS.

- [ ] **Step 5: orchestrator에 _resolve_workplace_coords() + _enrich_with_commute() 추가 테스트**

`tests/modules/real_estate/test_report_orchestrator.py` 끝에 추가:

```python
from modules.real_estate.report_orchestrator import _resolve_workplace_coords, _enrich_with_commute
from modules.real_estate.commute.models import CommuteResult


class TestResolveWorkplaceCoords:
    def test_returns_station_and_coords_when_geocode_succeeds(self):
        mock_geocoder = MagicMock()
        mock_geocoder.geocode.return_value = (37.5088, 127.0633)
        persona = {"commute": {"workplace_station": "삼성역"}}

        name, lat, lng = _resolve_workplace_coords(persona, mock_geocoder)

        assert name == "삼성역"
        assert lat == pytest.approx(37.5088)
        assert lng == pytest.approx(127.0633)

    def test_returns_none_triple_when_geocode_fails(self):
        mock_geocoder = MagicMock()
        mock_geocoder.geocode.return_value = None
        persona = {"commute": {"workplace_station": "없는역"}}

        name, lat, lng = _resolve_workplace_coords(persona, mock_geocoder)

        assert name is None and lat is None and lng is None

    def test_returns_none_triple_when_no_workplace_station(self):
        mock_geocoder = MagicMock()
        persona = {"commute": {}}

        name, lat, lng = _resolve_workplace_coords(persona, mock_geocoder)

        assert name is None and lat is None and lng is None


class TestEnrichWithCommute:
    def test_fills_commute_transit_minutes(self):
        mock_svc = MagicMock()
        mock_svc.get.return_value = CommuteResult(
            origin_key="11680__래미안",
            destination="삼성역",
            mode="transit",
            duration_minutes=22,
            distance_meters=1500,
        )
        candidates = [{"apt_name": "래미안", "district_code": "11680", "road_address": "서울 강남구 역삼동 1"}]

        result = _enrich_with_commute(candidates, mock_svc, "삼성역", 37.5088, 127.0633)

        assert result[0]["commute_transit_minutes"] == 22

    def test_skips_when_no_road_address(self):
        mock_svc = MagicMock()
        candidates = [{"apt_name": "주소없는단지", "district_code": "11680", "road_address": ""}]

        result = _enrich_with_commute(candidates, mock_svc, "삼성역", 37.5088, 127.0633)

        assert result[0].get("commute_transit_minutes") is None
        mock_svc.get.assert_not_called()

    def test_handles_commute_service_exception_gracefully(self):
        mock_svc = MagicMock()
        mock_svc.get.side_effect = RuntimeError("T-map API 실패")
        candidates = [{"apt_name": "에러단지", "district_code": "11680", "road_address": "서울 강남구 1"}]

        result = _enrich_with_commute(candidates, mock_svc, "삼성역", 37.5088, 127.0633)

        assert result[0].get("commute_transit_minutes") is None  # 예외 삼켜짐
```

- [ ] **Step 6: 테스트 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_report_orchestrator.py::TestResolveWorkplaceCoords tests/modules/real_estate/test_report_orchestrator.py::TestEnrichWithCommute -v 2>&1 | tail -10
```

Expected: `ImportError` — `_resolve_workplace_coords`, `_enrich_with_commute` not defined.

- [ ] **Step 7: _resolve_workplace_coords() + _enrich_with_commute() 구현**

`src/modules/real_estate/report_orchestrator.py` — `_enrich_with_building` 바로 아래에 두 함수 추가:

```python
def _resolve_workplace_coords(persona_data: Dict, geocoder) -> tuple:
    """persona의 commute.workplace_station을 lat/lng로 변환.
    실패하면 (None, None, None) 반환."""
    station = persona_data.get("commute", {}).get("workplace_station", "")
    if not station:
        return None, None, None
    try:
        coords = geocoder.geocode(apt_name=station, district_code="", address=station)
        if coords:
            return station, coords[0], coords[1]
    except Exception as e:
        logger.warning(f"[Orchestrator] workplace_station 좌표 변환 실패 ({station}): {e}")
    return None, None, None


def _enrich_with_commute(
    candidates: List[Dict],
    commute_svc,
    dest: Optional[str],
    dest_lat: Optional[float],
    dest_lng: Optional[float],
) -> List[Dict]:
    """각 candidate에 commute_transit_minutes 를 채운다.
    road_address 없으면 스킵. CommuteService 예외는 로그 후 무시."""
    enriched = []
    for c in candidates:
        result = dict(c)
        road_address = c.get("road_address") or ""
        if road_address and commute_svc is not None:
            apt_name = c.get("apt_name", "")
            district_code = c.get("district_code", "")
            origin_key = f"{district_code}__{apt_name}"
            try:
                cr = commute_svc.get(
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
            except Exception as e:
                logger.warning(f"[Orchestrator] Commute 실패 {apt_name}: {e}")
        enriched.append(result)
    return enriched
```

`generate()` 파이프라인 수정 — `_enrich_with_building` 호출 다음 줄에 추가:

```python
enriched = _enrich_with_poi(candidates, self._poi_collector)
enriched = _enrich_with_building(enriched, self._re_db_path)
if self._commute_svc and self._geocoder:
    dest, dest_lat, dest_lng = _resolve_workplace_coords(persona_data, self._geocoder)
    enriched = _enrich_with_commute(enriched, self._commute_svc, dest, dest_lat, dest_lng)
enriched = _enrich_with_trend(enriched, self._trend_analyzer)
```

- [ ] **Step 8: 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_report_orchestrator.py tests/modules/real_estate/commute/test_commute_service.py -v 2>&1 | tail -20
```

Expected: 모든 테스트 PASS.

- [ ] **Step 9: 커밋**

```bash
git add src/modules/real_estate/commute/commute_service.py \
        src/modules/real_estate/report_orchestrator.py \
        tests/modules/real_estate/commute/test_commute_service.py \
        tests/modules/real_estate/test_report_orchestrator.py
git commit -m "feat(commute): dest_override 파라미터 추가 + _enrich_with_commute() — persona 기반 동적 목적지"
```

---

## Task 4: _enrich_with_trend() 다중 면적 시도

**Files:**
- Modify: `src/modules/real_estate/report_orchestrator.py:73-87` (_enrich_with_trend)
- Test: `tests/modules/real_estate/test_report_orchestrator.py`

**배경:**
- 현재 `_enrich_with_trend(candidates, trend_analyzer)`는 `c.get("exclusive_area", 84.0)` 단일 면적으로 조회.
- persona의 `preferred_area_sqm: [84, 99]`를 받아 순서대로 시도, 데이터 있는 면적대를 사용.
- 모든 면적대에서 데이터 없으면 `_trend=None` (이 단지는 스코어링에서 자연 탈락).

- [ ] **Step 1: 실패 테스트 작성**

`tests/modules/real_estate/test_report_orchestrator.py` 끝에 추가:

```python
from modules.real_estate.report_orchestrator import _enrich_with_trend


class TestEnrichWithTrendMultiArea:
    def test_tries_first_area_and_returns_on_hit(self):
        """preferred_areas=[84, 99]일 때 84㎡ 데이터 있으면 84 기준 trend 반환."""
        mock_analyzer = MagicMock()
        mock_analyzer.get_trend.side_effect = lambda apt_master_id, area_sqm: (
            TrendData(apt_master_id=1, area_sqm=area_sqm, avg_price=2_800_000_000,
                      price_change_pct=1.5, monthly_volume=3.0,
                      price_min=2_700_000_000, price_max=2_900_000_000, sample_count=5)
            if area_sqm == 84.0 else None
        )
        candidates = [{"apt_name": "래미안", "id": 1}]

        result = _enrich_with_trend(candidates, mock_analyzer, preferred_areas=[84.0, 99.0])

        assert result[0]["_trend"].area_sqm == 84.0
        assert result[0]["_trend_area_sqm"] == 84.0
        # 84로 히트했으니 99는 시도 안 함
        assert mock_analyzer.get_trend.call_count == 1

    def test_falls_back_to_second_area_when_first_empty(self):
        """84㎡ 데이터 없고 99㎡ 데이터 있으면 99 기준 trend 반환."""
        mock_analyzer = MagicMock()
        mock_analyzer.get_trend.side_effect = lambda apt_master_id, area_sqm: (
            TrendData(apt_master_id=1, area_sqm=area_sqm, avg_price=3_200_000_000,
                      price_change_pct=0.5, monthly_volume=1.2,
                      price_min=3_100_000_000, price_max=3_300_000_000, sample_count=3)
            if area_sqm == 99.0 else None
        )
        candidates = [{"apt_name": "팰리스", "id": 1}]

        result = _enrich_with_trend(candidates, mock_analyzer, preferred_areas=[84.0, 99.0])

        assert result[0]["_trend"].area_sqm == 99.0
        assert result[0]["_trend_area_sqm"] == 99.0
        assert mock_analyzer.get_trend.call_count == 2  # 84 실패 후 99 시도

    def test_no_data_in_any_area_returns_no_trend(self):
        """모든 면적대에서 None이면 _trend 키 없음."""
        mock_analyzer = MagicMock()
        mock_analyzer.get_trend.return_value = None
        candidates = [{"apt_name": "미수집단지", "id": 1}]

        result = _enrich_with_trend(candidates, mock_analyzer, preferred_areas=[84.0, 99.0])

        assert result[0].get("_trend") is None
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_report_orchestrator.py::TestEnrichWithTrendMultiArea -v 2>&1 | tail -10
```

Expected: `TypeError` — `_enrich_with_trend()` takes 2 args, 3 given.

- [ ] **Step 3: _enrich_with_trend() 교체**

`src/modules/real_estate/report_orchestrator.py` — 기존 `_enrich_with_trend` 함수 전체를 아래로 교체:

```python
def _enrich_with_trend(
    candidates: List[Dict],
    trend_analyzer: TrendAnalyzer,
    preferred_areas: Optional[List[float]] = None,
) -> List[Dict]:
    """preferred_areas 순서대로 면적대를 시도해 실거래 추세를 채운다.
    preferred_areas 미제공 시 기존 동작(84㎡ 단일) 유지."""
    if preferred_areas is None:
        preferred_areas = [84.0]

    enriched = []
    for c in candidates:
        result = dict(c)
        apt_master_id = c.get("id") or c.get("apt_master_id")
        area_sqm = c.get("exclusive_area") or c.get("area_sqm")

        if apt_master_id:
            try:
                trend = None
                areas_to_try = preferred_areas if preferred_areas else ([area_sqm] if area_sqm else [84.0])
                for area in areas_to_try:
                    trend = trend_analyzer.get_trend(apt_master_id=apt_master_id, area_sqm=area)
                    if trend:
                        result["_trend_area_sqm"] = area
                        break
                if trend:
                    result["_trend"] = trend
            except Exception as e:
                logger.warning(f"[Orchestrator] 추세 실패 {c.get('apt_name')}: {e}")
        enriched.append(result)
    return enriched
```

`generate()` 내 `_enrich_with_trend` 호출부 수정:

```python
preferred_areas = persona_data.get("apartment_preferences", {}).get("preferred_area_sqm", [84.0])
enriched = _enrich_with_trend(enriched, self._trend_analyzer, preferred_areas=preferred_areas)
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/test_report_orchestrator.py -v 2>&1 | tail -20
```

Expected: 모든 테스트 PASS.

- [ ] **Step 5: 커밋**

```bash
git add src/modules/real_estate/report_orchestrator.py \
        tests/modules/real_estate/test_report_orchestrator.py
git commit -m "feat(trend): _enrich_with_trend() 다중 면적대 순서 시도 — persona.preferred_area_sqm 기반"
```

---

## Task 5: poi_collector 학교 쿼리 분리

**Files:**
- Modify: `src/modules/real_estate/poi_collector.py:102-117` (_fetch_and_cache)
- Test: (기존 poi_collector 테스트 있으면 수정, 없으면 수동 검증)

**배경:**
- `"초등학교 중학교"` 단일 쿼리가 Kakao API에서 AND 동작해 결과가 0건.
- 분리 호출 후 place_id 기준 중복 제거.
- POI 캐시는 `complex_code`로 저장되므로 기존 캐시 만료 전까지는 이전 값 사용. 강제 갱신 필요 시 poi_cache 테이블에서 해당 단지 삭제 필요.

- [ ] **Step 1: _fetch_and_cache 수정**

`src/modules/real_estate/poi_collector.py` — `_fetch_and_cache()` 내 schools 조회 부분만 교체:

```python
def _fetch_and_cache(self, complex_code: str, lat: float, lng: float) -> PoiData:
    stations = self._search("지하철역", lat, lng, self.STATION_RADIUS, size=5)
    elem = self._search("초등학교", lat, lng, self.SCHOOL_RADIUS, size=15)
    middle = self._search("중학교", lat, lng, self.SCHOOL_RADIUS, size=15)
    seen: set = set()
    schools: list = []
    for doc in elem + middle:
        key = doc.get("id") or doc.get("place_name", "")
        if key not in seen:
            seen.add(key)
            schools.append(doc)
    academies = self._search("학원", lat, lng, self.ACADEMY_RADIUS, size=15)
    marts = self._search("대형마트 백화점", lat, lng, self.MART_RADIUS, size=15)

    poi = PoiData(
        complex_code=complex_code,
        subway_stations=self._parse_stations(stations),
        schools_count=len(schools),
        academies_count=len(academies),
        marts_count=len(marts),
        collected_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    self._save_cache(complex_code, lat, lng, poi)
    return poi
```

- [ ] **Step 2: 기존 POI 캐시 삭제 (현재 단지들 재수집 위해)**

```bash
sqlite3 /Users/kks/Desktop/Laboratory/Consigliere/data/real_estate.db \
  "DELETE FROM poi_cache WHERE schools_count = 0;"
echo "삭제된 행: $(sqlite3 /Users/kks/Desktop/Laboratory/Consigliere/data/real_estate.db 'SELECT changes()')"
```

- [ ] **Step 3: 커밋**

```bash
git add src/modules/real_estate/poi_collector.py
git commit -m "fix(poi): 학교 쿼리 초등학교·중학교 분리 호출로 변경 — Kakao AND 동작 우회"
```

---

## Task 6: 엔드포인트 통합 + _build_markdown() 개선 + 리포트 재생성 검증

**Files:**
- Modify: `src/api/routers/real_estate.py:585-678` (generate_professional_report)
- Modify: `src/modules/real_estate/report_orchestrator.py:163-264` (_build_markdown)

**배경:**
- 엔드포인트에서 persona 필터(min_household_count), CommuteSvc 주입, [:100], re_db_path, geocoder 전달.
- `_build_markdown()` 예산 적합성 섹션을 `trend.avg_price`로 교체 (0.0억 제거).
- Docker 재빌드 후 리포트 재생성, 결과 검증.

- [ ] **Step 1: generate_professional_report() 엔드포인트 수정**

`src/api/routers/real_estate.py` — `generate_professional_report()` 함수 내 아래 3곳 수정:

**(A) import 추가** — 함수 상단 import 블록에:
```python
from modules.real_estate.commute.commute_service import CommuteService
from modules.real_estate.commute.commute_repository import CommuteRepository
from modules.real_estate.commute.tmap_client import TmapClient
```

**(B) candidates 수집 부분 교체** (기존 `candidates.extend(apt_repo.search(sigungu=area, limit=200))` 부분):
```python
min_hh = persona.get("apartment_preferences", {}).get("min_household_count", 0)

if interest_areas:
    candidates = []
    for area in interest_areas:
        candidates.extend(apt_repo.search(sigungu=area, min_household_count=min_hh, limit=200))
else:
    candidates = apt_repo.search(min_household_count=min_hh, limit=500)
candidate_dicts = [c.__dict__ if hasattr(c, "__dict__") else dict(c) for c in candidates[:100]]
```

**(C) orchestrator 생성 부분 교체** (기존 `orchestrator = ReportOrchestrator(...)` 블록):
```python
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

orchestrator = ReportOrchestrator(
    llm=llm,
    prompt_loader=prompt_loader,
    poi_collector=PoiCollector(api_key=kakao_key, db_path=re_db),
    trend_analyzer=TrendAnalyzer(db_path=re_db),
    report_repository=ReportRepository(storage_path=report_path),
    re_db_path=re_db,
    commute_svc=commute_svc,
    geocoder=geocoder,
)
```

- [ ] **Step 2: _build_markdown() 예산 적합성 섹션 수정**

`src/modules/real_estate/report_orchestrator.py` — `_build_markdown()` 내 예산 섹션 교체:

기존:
```python
budget_ok = budget_available >= c.get("price", 0)
lines.append("**예산 적합성**")
price_eok = c.get("price", 0) / 100_000_000
lines.append(f"- 최근 실거래가: {price_eok:.1f}억 vs 구매 가능 {budget_str}")
lines.append(f"- {'예산 범위 내' if budget_ok else '예산 초과 — 추가 조달 필요'}")
```

교체 후:
```python
lines.append("**예산 적합성**")
if trend and trend.avg_price > 0:
    budget_ok = budget_available >= trend.avg_price
    area_label = f"{c.get('_trend_area_sqm', 84):.0f}㎡"
    lines.append(f"- 최근 실거래가: {trend.avg_price_eok()} ({area_label} 기준) vs 구매 가능 {budget_str}")
    lines.append(f"- {'예산 범위 내' if budget_ok else '예산 초과 — 추가 조달 필요'}")
else:
    lines.append(f"- 최근 실거래가: 미수집 vs 구매 가능 {budget_str}")
```

- [ ] **Step 3: Docker 이미지 재빌드**

```bash
docker compose build api 2>&1 | tail -5
```

Expected: `Image consigliere-api Built`

- [ ] **Step 4: 컨테이너 재시작**

```bash
docker compose restart api && sleep 6 && docker compose ps api
```

Expected: `Up` 상태.

- [ ] **Step 5: 리포트 재생성**

```bash
curl -s -X POST http://localhost:8000/jobs/professional-report/generate \
  -H "Content-Type: application/json" \
  -d '{"target_date": "2026-05-02", "force": true}' | python3 -m json.tool
```

Expected:
```json
{"status": "success", "date": "2026-05-02", "candidates_count": 5}
```

- [ ] **Step 6: 로그에서 WARNING 확인**

```bash
docker compose logs api --tail=60 2>/dev/null | grep -E "(WARNING|ERROR|Orchestrator|Commute|Building|Trend)" | head -30
```

확인 항목:
- `Commute 실패` 경고가 모든 단지에서 뜨면 T-map API 키 문제
- `building_master 조회 실패` 없어야 함

- [ ] **Step 7: 생성된 리포트 품질 확인**

```bash
cat /Users/kks/Desktop/Laboratory/Consigliere/data/real_estate_reports/2026-05-02.md
```

아래 항목 체크:
- [ ] Top5 단지 이름이 500세대 이상인가 (소형 오피스텔 없음)
- [ ] 단지별 점수가 서로 다른가 (전부 59점 동점이 아닌가)
- [ ] `**출퇴근**` 섹션에 `?분` 대신 숫자가 표시되는가 (T-map 연결 시)
- [ ] `**실거래가 추세**` 섹션에 데이터가 있는가 (84㎡ 또는 99㎡ 기준)
- [ ] `**재건축/투자 잠재력**` 섹션에 건축연도·용적률이 있는가
- [ ] `**예산 적합성**` 섹션에 `0.0억` 대신 실거래가가 표시되는가
- [ ] `**학군 분석**` 섹션에 학교 수가 0이 아닌가

- [ ] **Step 8: 전체 테스트 실행**

```bash
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/real_estate/ tests/api/ -v --tb=short 2>&1 | tail -30
```

Expected: 모든 테스트 PASS.

- [ ] **Step 9: 커밋**

```bash
git add src/api/routers/real_estate.py \
        src/modules/real_estate/report_orchestrator.py
git commit -m "feat(report): 엔드포인트 통합 — commute/building enrichment 주입, 예산 섹션 실거래가 기반으로 개선"
```
