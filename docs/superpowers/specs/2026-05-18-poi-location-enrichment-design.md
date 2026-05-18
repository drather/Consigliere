# POI 기반 입지분석 고도화 Design Spec

**Goal:** 데일리 리포트 카드에 "📍 입지 현황" 블록을 추가하여 교통·생활편의·의료·학군 데이터를 구조화된 형태로 표시한다. 학교알리미 품질 데이터(전입률)를 orchestrator enrichment 파이프라인에 통합한다.

**Architecture:** 기존 TypedDict 계약 패턴(`TrendData`, `CommuteData`)을 따라 `LocationSummaryData`를 추가. `report_formatter.py`에 `_extract_location_summary()` + `render_location_summary()` 추가. `daily_report_orchestrator.py`에 `_enrich_with_school()` 스텝 추가.

**Tech Stack:** Python TypedDict, SQLite (poi_cache, school_scores), Kakao Local API (기존 PoiCollector), 학교알리미 DB (기존 SchoolRepository)

---

## 변경 파일 목록

| 파일 | 변경 유형 | 책임 |
|------|-----------|------|
| `src/modules/real_estate/daily_report/report_types.py` | Modify | `LocationSummaryData` TypedDict 추가 |
| `src/modules/real_estate/daily_report/report_formatter.py` | Modify | `_extract_location_summary()`, `render_location_summary()`, `render_scores()` 단순화, `build_candidate_card()` 순서 변경 |
| `src/modules/real_estate/daily_report/daily_report_orchestrator.py` | Modify | `_enrich_with_school()` 스텝 추가, SchoolRepository/SchoolService 의존성 주입 |
| `tests/modules/real_estate/daily_report/test_report_formatter_location.py` | Create | `render_location_summary()` 단위 테스트 |
| `tests/modules/real_estate/daily_report/test_enrich_school.py` | Create | `_enrich_with_school()` 단위 테스트 |

---

## Section 1: `LocationSummaryData` TypedDict

`report_types.py`에 추가. 모든 필드 `total=False` (데이터 부재 시 키 없음).

```python
class SubwayStation(TypedDict):
    name: str           # "강남"
    line: str           # "2호선"
    walk_minutes: int   # 도보 분

class LocationSummaryData(TypedDict, total=False):
    # 역세권
    subway_stations: List[SubwayStation]   # 최대 2개, 도보 시간순
    # 생활편의
    mart_count: int
    convenience_count: int
    cafe_count: int
    restaurant_count: int
    pharmacy_count: int
    medical_count: int
    # 자연
    park_nearest_m: int     # 0 = 반경 내 없음
    # 학군
    school_nearby_count: int
    school_transfer_rate: float   # 0.0~1.0 (전입생/총학생)
    school_avg_per_teacher: float # 교사 1인당 학생 수
    school_score: int             # 0~100
    school_label: str             # "학군 우수" / "학군 양호" / "학군 평이" / "학군 정보 없음"
    # 혐오시설
    nuisance_high_count: int
    nuisance_mid_count: int
```

---

## Section 2: `report_formatter.py` — `_extract_location_summary()`

`c` dict에서 `_poi` (PoiData) + school enrichment 필드를 읽어 `LocationSummaryData`를 반환.

```python
def _extract_location_summary(c: dict) -> Optional[LocationSummaryData]:
    poi: Optional[PoiData] = c.get("_poi")
    if poi is None:
        return None

    # 역세권 — 도보 시간순 최대 2개
    stations = sorted(poi.subway_stations, key=lambda s: s.get("walk_minutes", 99))[:2]
    subway = [
        SubwayStation(
            name=s.get("name", "?"),
            line=s.get("line", "?"),
            walk_minutes=s.get("walk_minutes", 0),
        )
        for s in stations
    ]

    loc: LocationSummaryData = {
        "subway_stations": subway,
        "mart_count": poi.marts_count,
        "convenience_count": poi.convenience_count,
        "cafe_count": poi.cafe_count,
        "restaurant_count": poi.restaurant_count,
        "pharmacy_count": poi.pharmacy_count,
        "medical_count": poi.medical_count,
        "park_nearest_m": poi.park_nearest_m,
        "nuisance_high_count": poi.nuisance_high_count,
        "nuisance_mid_count": poi.nuisance_mid_count,
    }

    # 학군 — _enrich_with_school()이 주입한 필드
    school_score = c.get("school_score")
    if school_score is not None:
        loc["school_nearby_count"] = c.get("school_nearby_count", 0)
        loc["school_transfer_rate"] = c.get("school_transfer_rate", 0.0)
        loc["school_avg_per_teacher"] = c.get("school_avg_per_teacher", 0.0)
        loc["school_score"] = school_score
        loc["school_label"] = _school_label(
            c.get("school_transfer_rate", 0.0),
            c.get("school_nearby_count", 0),
        )

    return loc
```

### `_school_label()` — rule-based (config 값과 동일 기준)

```python
def _school_label(transfer_rate: float, nearby: int) -> str:
    # thresholds: config.yaml school.transfer_rate_high=0.06, transfer_rate_medium=0.03
    if transfer_rate >= 0.06 or nearby >= 3:
        return "학군 우수"
    elif transfer_rate >= 0.03 or nearby >= 1:
        return "학군 양호"
    else:
        return "학군 평이"
```

---

## Section 3: `render_location_summary()` — HTML/Markdown 렌더링

```
📍 입지 현황
🚇 역세권    강남(2호선) 도보 8분 · 선릉(2·분당) 도보 12분
🛒 생활편의  마트 2 · 편의점 6 · 카페 11 · 식당 38 · 약국 4
🏥 의료      병원·의원 7곳
🌳 자연      공원 300m 이내
🏫 학군      반경 1km 학교 5곳 · 전입률 7.2% · 교사1인당 학생 14명 → 학군 우수
⚠️ 혐오시설  [표시: 고위험 1곳]  (없으면 이 행 생략)
```

**렌더링 규칙:**
- 역세권: 없으면 "역 없음"
- 생활편의: 0인 항목은 표시하지 않음
- 의료: `medical_count == 0`이면 행 생략
- 자연: `park_nearest_m > 0`이면 "공원 {m}m 이내", 0이면 "반경 내 공원 없음"
- 학군: school_score 없으면 "학교 정보 수집 전"
- 혐오시설: high=0 and mid=0이면 행 전체 생략

---

## Section 4: `render_scores()` 단순화

현재 `render_scores()`는 각 차원 아래 evidence bullets를 표시한다. 이 bullets는 대부분 POI 카운트 정보이며, 새 "입지 현황" 블록에서 더 가독성 좋게 표시되므로 중복.

**변경:** evidence bullets 제거 → 점수 숫자만 표시.

```python
def render_scores(residential: List, investment: List) -> str:
    if not residential and not investment:
        return ""
    lines = ["**실거주 점수 분석**"]
    for dr in residential:
        lines.append(f"- {dr.label}: **{dr.score}점**")
    lines += ["", "**투자성 점수 분석**"]
    for dr in investment:
        lines.append(f"- {dr.label}: **{dr.score}점**")
    return "\n".join(lines)
```

---

## Section 5: `build_candidate_card()` 순서 변경

```python
def build_candidate_card(c: dict, index: int = 0) -> str:
    trend = _extract_trend(c)
    commute = _extract_commute(c)
    location = _extract_location_summary(c)   # NEW
    ls = c.get("_location_score")

    parts = [
        _render_header(c, index),
        render_trend(trend),
        render_commute(commute),
        render_location_summary(location) if location else "",   # NEW (3번째)
        render_scores(ls.residential_results, ls.investment_results) if ls else "",
        render_verdict(c.get("_verdict", "")),
        render_keypoints(c.get("_key_points", [])),
    ]
    return "\n\n".join(p for p in parts if p)
```

---

## Section 6: `daily_report_orchestrator.py` — `_enrich_with_school()`

### DailyReportOrchestrator `__init__` 변경

```python
def __init__(
    self,
    ...
    school_repo=None,      # NEW: SchoolRepository (Optional)
):
    ...
    self._school_repo = school_repo
```

### `generate()` 파이프라인 순서

```
_enrich_with_geocode
→ _enrich_with_poi
→ _enrich_with_building
→ _enrich_with_commute_quota
→ [NEW] _enrich_with_school    ← poi 다음, trend 전
→ _enrich_with_trend
```

### `_enrich_with_school()` 구현

SchoolService는 외부 API를 호출하지 않고 DB만 읽음 (학교 데이터는 Job3에서 수집).
따라서 quota 제한 없이 모든 candidate에 대해 실행.

`complex_code`는 `transaction_aggregator.py`의 SQL 쿼리에서 `am.complex_code`로 select되어 candidate dict에 포함됨.

```python
def _enrich_with_school(self, candidates: List[Dict]) -> List[Dict]:
    if self._school_repo is None:
        return candidates

    enriched = []
    for c in candidates:
        result = dict(c)
        complex_code = c.get("complex_code", "")
        if not complex_code:
            enriched.append(result)
            continue

        try:
            cached = self._school_repo.get_score(complex_code, "total")
            if cached is not None:
                result["school_score"] = cached.score
                result["school_nearby_count"] = cached.nearby_school_count
                result["school_avg_per_teacher"] = cached.avg_students_per_teacher
                result["school_transfer_rate"] = cached.avg_transfer_rate  # SchoolScore에 추가된 필드
        except Exception as e:
            logger.warning("[DailyOrchestrator] school enrich 실패 %s: %s",
                           c.get("apt_name"), e)

        enriched.append(result)
    return enriched
```

**SchoolScore 모델 변경 필요:**
- 현재 `SchoolScore` 모델에 `avg_transfer_rate` 필드가 없음
- `SchoolScore` dataclass에 `avg_transfer_rate: float = 0.0` 추가
- `SchoolService.calculate_score()` — 계산된 `avg_transfer_rate` 값을 `SchoolScore`에 저장
- `SchoolRepository.upsert_school_score()` — `avg_transfer_rate` 컬럼 persist
- `SchoolRepository` DDL — `school_scores` 테이블 마이그레이션 (ALTER TABLE)

### SchoolScore 모델 변경

```python
@dataclass
class SchoolScore:
    complex_code: str
    school_kind: str
    nearby_school_count: int
    avg_students_per_class: float
    avg_students_per_teacher: float
    score: int
    collected_at: str
    avg_transfer_rate: float = 0.0   # NEW
```

### SchoolRepository — `school_scores` 테이블 마이그레이션

`avg_transfer_rate REAL NOT NULL DEFAULT 0` 컬럼 추가 (ALTER TABLE 패턴, 기존 데이터 호환).

### `service.py` — DailyReportOrchestrator 생성 시 `school_repo` 주입

```python
from modules.real_estate.school.school_repository import SchoolRepository

orchestrator = DailyReportOrchestrator(
    ...
    school_repo=SchoolRepository(db_path=re_db),   # NEW
)
```

---

## Section 7: 테스트 전략

### `test_report_formatter_location.py`

```python
def test_render_location_summary_full():
    """역세권+생활편의+학군 모두 있는 케이스"""
    loc = LocationSummaryData(
        subway_stations=[{"name": "강남", "line": "2호선", "walk_minutes": 8}],
        mart_count=2, cafe_count=5, restaurant_count=20, pharmacy_count=3,
        medical_count=4, park_nearest_m=250,
        school_nearby_count=3, school_transfer_rate=0.07,
        school_avg_per_teacher=14.5, school_score=85, school_label="학군 우수",
        nuisance_high_count=0, nuisance_mid_count=0,
    )
    html = render_location_summary(loc)
    assert "강남(2호선)" in html
    assert "도보 8분" in html
    assert "학군 우수" in html
    assert "⚠️" not in html  # 혐오시설 없음 → 행 생략

def test_render_location_summary_no_subway():
    loc = LocationSummaryData(subway_stations=[], mart_count=0, ...)
    html = render_location_summary(loc)
    assert "역 없음" in html

def test_render_location_summary_nuisance():
    loc = LocationSummaryData(..., nuisance_high_count=1, nuisance_mid_count=0)
    html = render_location_summary(loc)
    assert "⚠️" in html
    assert "고위험 1곳" in html

def test_school_label_high():
    assert _school_label(0.08, 5) == "학군 우수"

def test_school_label_medium():
    assert _school_label(0.04, 2) == "학군 양호"

def test_school_label_low():
    assert _school_label(0.01, 0) == "학군 평이"
```

### `test_enrich_school.py`

```python
def test_enrich_with_school_cache_hit():
    mock_repo = Mock()
    mock_repo.get_score.return_value = SchoolScore(
        complex_code="TEST001", school_kind="total",
        nearby_school_count=4, avg_students_per_class=0.0,
        avg_students_per_teacher=15.2, score=78,
        collected_at="2026-05-18T00:00:00", avg_transfer_rate=0.065,
    )
    orchestrator = DailyReportOrchestrator(..., school_repo=mock_repo)
    candidates = [{"complex_code": "TEST001", "apt_name": "테스트아파트"}]
    result = orchestrator._enrich_with_school(candidates)
    assert result[0]["school_score"] == 78
    assert result[0]["school_nearby_count"] == 4
    assert result[0]["school_transfer_rate"] == 0.065

def test_enrich_with_school_no_repo():
    """school_repo=None → candidates 그대로 반환"""
    orchestrator = DailyReportOrchestrator(..., school_repo=None)
    candidates = [{"complex_code": "TEST001"}]
    result = orchestrator._enrich_with_school(candidates)
    assert "school_score" not in result[0]

def test_enrich_with_school_cache_miss():
    """캐시 없음 → school_score 주입 안 됨"""
    mock_repo = Mock()
    mock_repo.get_score.return_value = None
    orchestrator = DailyReportOrchestrator(..., school_repo=mock_repo)
    candidates = [{"complex_code": "UNKNOWN"}]
    result = orchestrator._enrich_with_school(candidates)
    assert "school_score" not in result[0]
```

---

## 구현 순서 (태스크 분해 예고)

1. `SchoolScore` 모델 + Repository — `avg_transfer_rate` 필드 추가 및 마이그레이션
2. `report_types.py` — `LocationSummaryData`, `SubwayStation` TypedDict 추가
3. `report_formatter.py` — `_school_label()`, `_extract_location_summary()`, `render_location_summary()` 구현
4. `report_formatter.py` — `render_scores()` evidence 제거, `build_candidate_card()` 순서 변경
5. `daily_report_orchestrator.py` — `school_repo` 파라미터 추가, `_enrich_with_school()` 구현
6. `service.py` — `SchoolRepository` 주입 추가

---

## 완료 기준

- [ ] `render_location_summary()` 테스트 전체 통과
- [ ] `_enrich_with_school()` 테스트 전체 통과
- [ ] `build_candidate_card()` 출력에 "📍 입지 현황" 블록 포함 (commute 다음, scores 전)
- [ ] `render_scores()`에서 evidence bullets 제거 확인
- [ ] `school_score`가 없는 candidate에서 오류 없이 렌더링
- [ ] `<!-- stats -->` 태그 등 오염된 HTML 코멘트 출력 없음
