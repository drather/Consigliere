# 부동산 리포트 품질 개선 설계 (Report Quality Overhaul)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 부동산 전략가가 고객의 예산·출퇴근·투자성향에 맞는 아파트를 추천하는 리포트 품질을 "내놓을 수 있는 수준"으로 끌어올린다.

**Architecture:** 4개 레이어(후보 선정 → 데이터 enrichment → 출퇴근 enrichment → 실거래가 추세) 각각을 독립적으로 수정하여 스코어링 변별력과 리포트 데이터 완성도를 확보한다.

**Tech Stack:** SQLite (real_estate.db, commute_cache.db), Python dataclasses, CommuteService (캐시-퍼스트 MCP), TrendAnalyzer, ScoringEngine, ReportOrchestrator

---

## 현황 진단 (Before)

### 데이터 현황

| 테이블 | 레코드 수 | 주요 필드 채움률 | apt_master 연결 |
|--------|-----------|-----------------|-----------------|
| transactions | 19,387건 | apt_master_id 100% | 100% (6,346단지) |
| apartments | 9,267건 | household_count 99%, road_address 98% | complex_code 기준 69% (4,383건) |
| building_master | 6,269건 | FAR 90%, BCR 90%, completion_year 62% | pnu 기준 46% (2,908건) |
| commute_cache | 0건 | — | — |

### 리포트 품질 저해 요인

| # | 문제 | 원인 | 영향 |
|---|------|------|------|
| 1 | 후보 단지가 페르소나와 무관 (소형 오피스텔 Top1) | persona 필터(min_household=500, min_area=59㎡) 미적용 | 부적합 단지 추천 |
| 2 | 5개 단지 전부 동점(59/100) | commute·liquidity·price_potential 3개 항목 neutral(50점) | 점수로 우열 판별 불가 |
| 3 | 실거래가 전부 "미수집" | TrendAnalyzer가 84㎡ 고정 조회, 실거래 면적(30~67㎡)과 미스매치 | 가격 정보 없는 리포트 |
| 4 | 출퇴근 전부 "?분" | report_orchestrator가 CommuteService 미호출 | 핵심 조건 누락 |
| 5 | household_count·용적률·준공연도 없음 | scoring 시 apartments/building_master JOIN 없음 | liquidity·price_potential neutral |

---

## 수정 설계 (After)

### Layer 1 — 후보 선정 필터링

**파일:** `src/modules/real_estate/apt_master_repository.py`

`search()` 메서드에 persona 조건 파라미터를 추가하고, `apartments` 테이블과 LEFT JOIN으로 household_count 필터링을 DB 레이어에서 처리한다.

```python
def search(
    self,
    sigungu: Optional[str] = None,
    min_household_count: int = 0,          # 신규: persona.min_household_count
    min_exclusive_area_sqm: float = 0.0,   # 신규: persona.min_exclusive_area_sqm
    limit: int = 200,
) -> List[AptMasterEntry]:
```

쿼리 변경:
```sql
SELECT am.*, a.household_count, a.road_address, a.approved_date
FROM apt_master am
LEFT JOIN apartments a ON am.complex_code = a.complex_code
WHERE (am.sigungu = ? OR ? IS NULL)
  AND (a.household_count >= ? OR ? = 0)
ORDER BY a.household_count DESC NULLS LAST
LIMIT ?
```

`apartments.total_area`는 단지 전체 면적이므로 세대 면적 필터(`min_exclusive_area_sqm`)는 SQL에서 처리하지 않는다. 대신 Layer 4 trend 조회에서 preferred_area_sqm 범위 거래가 전혀 없으면 해당 단지를 추천 제외하는 방식으로 처리한다.

`AptMasterEntry` 모델에 3개 필드 추가:
```python
household_count: Optional[int] = None
road_address: Optional[str] = None      # commute enrichment용
approved_date: Optional[str] = None     # build_year 파생용
```

**API 엔드포인트 변경** (`src/api/routers/real_estate.py`):
```python
min_hh = persona.get("apartment_preferences", {}).get("min_household_count", 0)
candidates.extend(apt_repo.search(sigungu=area, min_household_count=min_hh, limit=200))
candidate_dicts = [...candidates[:100]]  # [:50] → [:100]
```

---

### Layer 2 — 데이터 Enrichment (building_master JOIN)

**파일:** `src/modules/real_estate/report_orchestrator.py`

새 함수 `_enrich_with_building()` 추가:

```python
def _enrich_with_building(candidates: List[Dict], db_path: str) -> List[Dict]:
    """pnu 기준으로 building_master에서 용적률·건폐율·준공연도를 가져온다."""
    pnu_list = [c.get("pnu") for c in candidates if c.get("pnu")]
    if not pnu_list:
        return candidates
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            f"SELECT mgm_pk, floor_area_ratio, building_coverage_ratio, completion_year "
            f"FROM building_master WHERE mgm_pk IN ({','.join('?'*len(pnu_list))})",
            pnu_list,
        ).fetchall()
    bm_map = {r[0]: {"floor_area_ratio": r[1], "building_coverage_ratio": r[2], "build_year": r[3]} for r in rows}
    enriched = []
    for c in candidates:
        result = dict(c)
        if c.get("pnu") and c["pnu"] in bm_map:
            result.update(bm_map[c["pnu"]])
        # approved_date(YYYYMMDD) → build_year(int) fallback
        if not result.get("build_year") and result.get("approved_date"):
            result["build_year"] = int(str(result["approved_date"])[:4])
        enriched.append(result)
    return enriched
```

orchestrator `generate()` 파이프라인에 추가:
```python
enriched = _enrich_with_poi(candidates, self._poi_collector)
enriched = _enrich_with_building(enriched, re_db_path)       # ← 신규
enriched = _enrich_with_commute(enriched, self._commute_svc) # ← 신규 (Layer 3)
enriched = _enrich_with_trend(enriched, self._trend_analyzer)
```

`ReportOrchestrator.__init__`에 `re_db_path: str` 파라미터 추가.

---

### Layer 3 — 출퇴근 Enrichment (CommuteService 연동)

**파일:** `src/modules/real_estate/report_orchestrator.py`

새 함수 `_enrich_with_commute()` 추가:

```python
def _enrich_with_commute(
    candidates: List[Dict],
    commute_svc,          # CommuteService 인스턴스 (destination은 초기화 시 설정)
) -> List[Dict]:
    enriched = []
    for c in candidates:
        result = dict(c)
        road_address = c.get("road_address", "")
        apt_name = c.get("apt_name", "")
        district_code = c.get("district_code", "")
        if road_address:
            try:
                origin_key = f"{district_code}__{apt_name}"
                cr = commute_svc.get(
                    origin_key=origin_key,
                    road_address=road_address,
                    apt_name=apt_name,
                    district_code=district_code,
                    mode="transit",
                )
                if cr:
                    result["commute_transit_minutes"] = cr.duration_minutes
            except Exception as e:
                logger.warning(f"[Orchestrator] Commute 실패 {apt_name}: {e}")
        enriched.append(result)
    return enriched
```

`generate()` 메서드 시그니처에 `commute_svc` 주입. 엔드포인트(`real_estate.py`)에서 `CommuteService` 생성 후 전달.

---

### Layer 4 — 실거래가 추세 (TrendAnalyzer 면적 수정)

**파일:** `src/modules/real_estate/report_orchestrator.py`, `src/modules/real_estate/trend_analyzer.py`

**문제:** `area_sqm=84.0` 고정 → 실거래 면적(30~67㎡) 미스매치

**수정:** persona의 `preferred_area_sqm: [84, 99]`를 orchestrator에서 읽어 TrendAnalyzer에 전달. 복수 면적대를 순서대로 시도해 데이터가 있는 면적대를 반환.

```python
def _enrich_with_trend(candidates: List[Dict], trend_analyzer, preferred_areas: List[float]) -> List[Dict]:
    enriched = []
    for c in candidates:
        result = dict(c)
        apt_master_id = c.get("id") or c.get("apt_master_id")
        if apt_master_id:
            trend = None
            for area in preferred_areas:  # [84, 99] 순서로 시도
                trend = trend_analyzer.get_trend(apt_master_id=apt_master_id, area_sqm=area)
                if trend:
                    result["_trend_area_sqm"] = area
                    break
            if trend:
                result["_trend"] = trend
        enriched.append(result)
    return enriched
```

`generate()` 호출부:
```python
preferred_areas = persona_data.get("apartment_preferences", {}).get("preferred_area_sqm", [84])
enriched = _enrich_with_trend(enriched, self._trend_analyzer, preferred_areas)
```

---

### 리포트 마크다운 개선

**파일:** `src/modules/real_estate/report_orchestrator.py` — `_build_markdown()`

- **재건축/투자 잠재력 섹션:** `build_year` + `floor_area_ratio` + `building_coverage_ratio` 표시 (데이터 있을 때)
- **출퇴근 섹션:** `commute_transit_minutes` 실데이터 표시
- **예산 적합성 섹션:** `_trend.avg_price_eok()` 값으로 "최근 실거래가" 표시 (0.0억 대신)
- **학군 섹션:** 학교 쿼리 분리 ("초등학교" / "중학교" 별도 호출) — poi_collector.py 수정

---

### poi_collector 학교 쿼리 분리

**파일:** `src/modules/real_estate/poi_collector.py`

```python
# 수정 전
schools = self._search("초등학교 중학교", lat, lng, self.SCHOOL_RADIUS, size=15)

# 수정 후
elem = self._search("초등학교", lat, lng, self.SCHOOL_RADIUS, size=15)
middle = self._search("중학교", lat, lng, self.SCHOOL_RADIUS, size=15)
seen = set()
schools = []
for s in elem + middle:
    key = s.get("id") or s.get("place_name")
    if key not in seen:
        seen.add(key)
        schools.append(s)
```

---

## 파일 변경 범위

| 파일 | 변경 내용 |
|------|-----------|
| `src/modules/real_estate/apt_master_repository.py` | `search()` 파라미터 추가, apartments JOIN, AptMasterEntry 필드 추가 |
| `src/modules/real_estate/report_orchestrator.py` | `_enrich_with_building()` 추가, `_enrich_with_commute()` 추가, `_enrich_with_trend()` 면적 다중시도, `_build_markdown()` 개선, `ReportOrchestrator.__init__` 파라미터 추가 |
| `src/modules/real_estate/poi_collector.py` | 학교 쿼리 분리 (초등/중학 별도 호출 + 중복 제거) |
| `src/api/routers/real_estate.py` | persona 필터 파라미터 전달, `CommuteService` 생성·주입, `candidate[:100]` |
| `tests/unit/real_estate/test_apt_master_repository.py` | `search()` 신규 파라미터 테스트 |
| `tests/unit/real_estate/test_report_orchestrator.py` | `_enrich_with_building()`, `_enrich_with_commute()`, 다중 면적 trend 테스트 |

---

## 기대 결과 (After)

```
리포트 예시:
### 1위. 래미안대치팰리스 — 총점 78/100

**입지 분석**
- 역세권: 대치역 3호선 도보 4분
- 반경 1km 내 대형마트/백화점 2개

**학군 분석**
- 반경 1km 내 초등학교 2개, 중학교 1개, 학원 30개+

**실거래가 추세**
- 6개월 평균가: 28.3억 (84㎡ 기준)
- 3개월 전 대비: +2.1% / 월 평균 거래량 3.4건

**재건축/투자 잠재력**
- 건축연도: 2002년 (24년), 용적률: 247%, 건폐율: 22%

**출퇴근** (삼성역 기준)
- 대중교통 18분

**예산 적합성**
- 최근 실거래가: 28.3억 vs 구매 가능 13.5억
- 예산 초과 — 추가 조달 필요
```

---

## 구현 순서 (의존성 고려)

1. **Task 1:** `AptMasterEntry` 모델 필드 추가 + `apt_master_repository.search()` 수정 (Layer 1)
2. **Task 2:** `_enrich_with_building()` 구현 (Layer 2) — Task 1 완료 후
3. **Task 3:** `_enrich_with_commute()` 구현 (Layer 3) — Task 1 완료 후 (road_address 필요)
4. **Task 4:** `_enrich_with_trend()` 다중 면적 시도 (Layer 4)
5. **Task 5:** `poi_collector` 학교 쿼리 분리
6. **Task 6:** `_build_markdown()` 및 엔드포인트 통합 + 리포트 재생성 검증
