# 데일리 리포트 카드 리디자인 설계 문서

**날짜:** 2026-05-10  
**작성자:** kks + Claude  
**상태:** 승인 완료

---

## 1. 배경 및 목표

현재 데일리 리포트는 단지별 정보를 단순 나열 수준으로 출력한다. `<!-- stats -->` 블록에
한 줄짜리 통계들이 쌓이는 구조라 스토리텔링이 없고, 판단 근거가 분산되어 있다.

**목표:**
- verdict-first 구조: 판단을 먼저, 근거는 뒤에
- 실거래 추세 스파크라인으로 가격 흐름 시각화
- 실거주 / 투자성 두 관점으로 점수 분리
- 출퇴근 정보를 패널로 표시
- 데이터·렌더러·출력을 레이어로 격리 → 한 곳 수정이 다른 곳에 영향 최소화

---

## 2. 아키텍처 — Approach A (TypedDict 계약)

```
① 데이터 레이어 (DB / API)
        ↓
② TransactionAggregator  ← recent_transactions 추가
        ↓
③ 데이터 계약 (report_types.py)  ← 레이어 간 유일한 접점
   TxPoint | TrendData | CommuteData | CandidateSummary
        ↓
④ 렌더러 함수 (report_formatter.py)
   render_trend() | render_commute() | render_scores()
   render_verdict() | render_keypoints()
        ↓
⑤ 조립
   build_candidate_card() | build_markdown() | build_slack()
        ↓
⑥ 출력 (Streamlit / Slack / .md 파일)
```

**핵심 규칙:** 렌더러 함수는 candidate `dict`를 직접 보지 않는다.  
`build_candidate_card()`가 dict에서 TypedDict를 추출해서 각 렌더러에 넘기는 유일한 지점.  
렌더러는 TypedDict만 알면 되고, dict 키 이름이 바뀌어도 렌더러는 무관.

---

## 3. 데이터 계약 (`report_types.py`)

**파일:** `src/modules/real_estate/daily_report/report_types.py` (신규)

```python
from typing import List, Optional
from typing_extensions import TypedDict

class TxPoint(TypedDict):
    price_eok: float        # 억 단위 (예: 8.8)
    deal_date: str          # "YYYY-MM-DD"

class TrendData(TypedDict):
    points: List[TxPoint]   # 날짜순 정렬, 최소 1개
    avg_eok: float          # 평균가 (억)
    change_pct: float       # 전월비 변동률 (%)
    area_sqm: float         # 전용면적 (㎡)

class CommuteData(TypedDict):
    transit_minutes: Optional[int]   # None = 미수집
    car_minutes: Optional[int]
    walk_minutes: Optional[int]
    route_summary: str               # 빈 문자열이면 표시 안 함

class CandidateSummary(TypedDict):
    apt_name: str
    sigungu: str
    area_sqm: float
    household_count: int
    composite_score: int             # 0~100 정수
    verdict: str                     # LLM 생성 한 줄 판단
    key_points: List[str]            # 핵심 포인트 불릿
    trend: TrendData
    commute: CommuteData
    residential_results: List        # List[DimensionResult]
    investment_results: List         # List[DimensionResult]
```

`ScoreData`는 별도 정의 없이 기존 `DimensionResult`를 그대로 재사용.

---

## 4. TransactionAggregator 변경

**파일:** `src/modules/real_estate/daily_report/transaction_aggregator.py`

건별 거래 목록을 가져오는 보조 SQL 추가:

```sql
-- _RECENT_TX_SQL
SELECT price, deal_date
FROM transactions
WHERE apt_master_id = :apt_master_id
  AND deal_date >= :date_from
ORDER BY deal_date ASC
LIMIT 10
```

`aggregate()` 내부, DB 연결이 열려 있는 동안 각 단지별 건별 거래를 조회해
`item["_recent_tx_points"]`에 주입:

```python
item["_recent_tx_points"] = [
    {
        "price_eok": round(r["price"] / 100_000_000, 2),
        "deal_date": r["deal_date"],
    }
    for r in rows_tx
]
```

`AggregatedTransaction` dataclass는 변경 없음. `_recent_tx_points`는 raw dict를 통해
candidate dict로 전달된다.

---

## 5. `report_formatter.py` 리팩터

**파일:** `src/modules/real_estate/daily_report/report_formatter.py`

### 5-1. 삭제

- `format_stat_block()` — 기능을 새 렌더러들로 분산 이전
- `format_dimension_scores()` — `render_scores()`로 대체
- `<!-- stats -->` / `<!-- /stats -->` 태그 — 제거

### 5-2. 신규 렌더러

**`render_trend(trend: TrendData) -> str`**
- SVG 스파크라인 생성 (viewBox 560×90)
- 방향 판정: `points[0].price_eok` vs `points[-1].price_eok`
  - 상승: `#a6e3a1` (초록), 하락: `#f38ba8` (빨강)
- 고점 자동 강조 (filled circle + 가격 레이블)
- 최신 거래 ★ 표시 (파란색 circle)
- 평균가·변동률 헤더 표시
- points가 비어있으면 "거래 데이터 없음" 반환

**`render_commute(commute: CommuteData) -> str`**
- transit / car / walk 3카드 레이아웃
- 3개 모두 None이면 "출퇴근 정보 미수집" 한 줄 반환
- 있는 수단만 표시 (일부 None 허용)

**`render_scores(residential: List, investment: List) -> str`**
- 기존 `format_dimension_scores()` 로직 유지
- 시그니처만 LocationScore 객체 대신 두 리스트를 직접 받도록 변경

**`render_verdict(verdict: str) -> str`**
- `> 🔍 **오늘의 판단:** {verdict}` 형식
- 빈 문자열이면 빈 문자열 반환

**`render_keypoints(key_points: List[str]) -> str`**
- `**주목할 점**` 헤더 + 불릿 목록
- 빈 리스트이면 빈 문자열 반환

### 5-3. 조립 함수

**`build_candidate_card(c: dict) -> str`** — dict 접근의 유일한 지점:

```python
def build_candidate_card(c: dict) -> str:
    trend = _extract_trend(c)      # dict → TrendData
    commute = _extract_commute(c)  # dict → CommuteData
    ls = c.get("_location_score")

    parts = [
        _render_header(c),
        render_trend(trend),
        render_commute(commute),
        render_scores(
            ls.residential_results, ls.investment_results
        ) if ls else "",
        render_verdict(c.get("_verdict", "")),
        render_keypoints(c.get("_key_points", [])),
    ]
    return "\n\n".join(p for p in parts if p)
```

**`_extract_trend(c: dict) -> TrendData`**
```python
points = c.get("_recent_tx_points", [])
return TrendData(
    points=points,
    avg_eok=round(c.get("avg_recent_price", 0) / 100_000_000, 2),
    change_pct=c.get("price_change_pct", 0.0),
    area_sqm=c.get("exclusive_area", 84.0),
)
```

**`_extract_commute(c: dict) -> CommuteData`**
```python
return CommuteData(
    transit_minutes=c.get("commute_transit_minutes"),
    car_minutes=c.get("commute_car_minutes"),    # daily report는 항상 None (transit만 조회)
    walk_minutes=c.get("commute_walk_minutes"),  # daily report는 항상 None (transit만 조회)
    route_summary=c.get("_commute_route_summary", ""),
)
```

> **참고:** orchestrator 수정(섹션 6-2-b)으로 transit/car/walking 모두 주입된다.
> `render_commute()`는 각 값이 None일 경우 해당 카드를 생략하고 있는 수단만 표시한다.

**`build_markdown(...) -> str`** — 기존 시그니처 유지, 내부 루프를 `build_candidate_card(c)` 호출로 단순화.

**`build_slack(candidates: List[dict]) -> str`** — 신규:
- Slack은 SVG 불가 → 텍스트 스파크라인 (`▁▂▄▇▅` 유니코드 블록)
- `_slack_candidate_block(c: dict) -> str` 내부 헬퍼로 분리

---

## 6. `daily_report_orchestrator.py` 변경

**파일:** `src/modules/real_estate/daily_report/daily_report_orchestrator.py`

### 6-1. LLM insights 필드 추가

LLM 프롬프트에 `verdict`와 `key_points` 필드를 요청에 추가.  
현재 `trading_bullets`, `characteristics_bullets`, `strategy_bullets`에 더해:

```json
{
  "verdict": "관망 — 하락 추세 중, 역세권 없어 삼성역 출퇴근 부적합",
  "key_points": [
    "📉 고점(9.5억) 대비 -7.4% 하락 추세",
    "✅ 공원 198m · 병원 15개",
    "❌ 역세권 없음"
  ]
}
```

### 6-2. candidate dict에 verdict/key_points 주입

```python
for c in candidates:
    name = c.get("apt_name", "")
    ins = insights_map.get(name, {})
    c["_verdict"] = ins.get("verdict", "")
    c["_key_points"] = ins.get("key_points", [])
```

### 6-2-b. orchestrator — car/walking 모드 추가 (누락 수정)

현재 `_enrich_with_commute_quota()`는 `mode="transit"`만 호출한다.
`CommuteService.get()`은 mode별로 독립 호출 가능하고 캐시도 mode별로 독립 저장된다.

**수정 내용:**
- 캐시 히트 시: transit/car/walking 3모드 모두 `get_cached()` 시도
- 캐시 미스 + quota 여유 시: 3모드 각각 `get()` 호출 (quota 1단위 = 1단지 = 3 API 호출)
- candidate dict에 `commute_car_minutes`, `commute_walk_minutes` 추가 주입

```python
for mode in ("transit", "car", "walking"):
    cached = self._commute_svc.get_cached(origin_key, dest, mode)
    if cached is not None:
        result[f"commute_{mode}_minutes"] = cached.duration_minutes
        if mode == "transit":
            result["_commute_route_summary"] = cached.route_summary
    elif new_calls_used < max_new_calls:
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
            result[f"commute_{mode}_minutes"] = cr.duration_minutes
            if mode == "transit":
                result["_commute_route_summary"] = cr.route_summary
new_calls_used += 1  # 단지 단위 카운트
```

> **참고:** `commute_walk_minutes`는 walking 모드 키. `commute_car_minutes`는 car 모드 키.
> `service.py`의 기존 main pipeline과 동일한 키 이름으로 일관성 유지.

### 6-3. `<!-- stats -->` 태그 제거

`build_markdown()` 호출 전에 더 이상 stats 블록을 별도 생성하지 않음.
모든 카드 콘텐츠는 `build_candidate_card()`를 통해 생성된다.

---

## 7. 영향도 매트릭스

| 변경 시나리오 | Aggregator | report_types | 렌더러 | build_markdown |
|---|---|---|---|---|
| 거래 데이터 컬럼 추가 | 수정 | TxPoint 수정 | render_trend만 | 무관 |
| 스파크라인 디자인 교체 | 무관 | 무관 | render_trend만 | 무관 |
| 출퇴근 API 교체 | 무관 | CommuteData만 | render_commute만 | 무관 |
| 차원 점수 추가/제거 | 무관 | 무관 (DimensionResult 재사용) | 무관 | 무관 |
| Slack 포맷 전면 교체 | 무관 | 무관 | 무관 | build_slack만 |
| 새 섹션 추가 (예: 전세가율) | 필드 추가 | NewData 추가 | render_new() 추가 | 호출 1줄 추가 |

---

## 8. 파일 변경 요약

| 파일 | 변경 종류 |
|------|----------|
| `src/modules/real_estate/daily_report/report_types.py` | 신규 생성 |
| `src/modules/real_estate/daily_report/transaction_aggregator.py` | 수정 (SQL + `_recent_tx_points` 주입) |
| `src/modules/real_estate/daily_report/report_formatter.py` | 수정 (렌더러 분리, `build_slack` 추가) |
| `src/modules/real_estate/daily_report/daily_report_orchestrator.py` | 수정 (`_verdict`, `_key_points` 주입, LLM 프롬프트 추가) |
| LLM 프롬프트 파일 (daily_report 관련) | 수정 (`verdict`, `key_points` 필드 추가) |

---

## 9. 테스트 전략

- `test_report_types.py`: TypedDict 인스턴스 생성 검증 (타입 체커 통과 확인)
- `test_render_trend.py`: 상승/하락 색상, 고점 강조, ★ 표시 SVG 출력 검증
- `test_render_commute.py`: 전체 있음 / 일부 없음 / 전부 없음 3케이스
- `test_render_scores.py`: DimensionResult 리스트 → 마크다운 렌더링
- `test_build_candidate_card.py`: dict에서 TypedDict 추출 후 각 렌더러 호출 통합 테스트
- `test_transaction_aggregator.py`: `_recent_tx_points` 필드 존재 및 날짜순 정렬 확인
