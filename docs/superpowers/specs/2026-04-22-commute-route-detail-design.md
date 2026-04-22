# 출퇴근 경로 상세 정보 추가 — 설계 문서

**작성일:** 2026-04-22  
**상태:** 승인됨  
**선행 작업:** `2026-04-20-commute-mcp-design.md` (T-map 출퇴근 시간 실시간 계산)

---

## 1. 문제 정의

현재 `CommuteResult`는 `duration_minutes`와 `distance_meters`만 반환한다. 사용자는 시간뿐 아니라 **실제 이동 경로**(버스 번호, 환승역, 주요 도로명)를 대시보드와 LLM 리포트에서 보고 싶다.

예: 송파파크데일1단지 → 삼성역
- 대중교통: "도보 5분 → 302번 버스 → 잠실역 → 2호선 → 삼성역 (59분)"
- 자가용: "올림픽대로 → 잠실대교 → 테헤란로 (35분 · 15.0km)"
- 도보: "가락로 → 송파대로 (90분 · 5.0km)"

---

## 2. 목표

- T-map API 응답에서 경유 단계(legs) 파싱하여 구조화 저장
- 대시보드: 대중교통·자가용·도보 3단 카드로 경로 표시
- LLM 리포트: 한 줄 요약(`route_summary`)만 프롬프트에 주입
- 기존 `route()` 메서드 및 테스트 18개 변경 없음 (비파괴적 확장)

---

## 3. 아키텍처

### 3.1 접근 방식

**Approach A — `route_with_legs()` 신규 메서드 추가**

기존 `TmapClient.route()` 유지. 새 `route_with_legs()` 메서드가 `(duration, distance, legs, route_summary)` 반환. `CommuteService.get()` 내부에서만 호출.

### 3.2 변경 파일

| 파일 | 변경 내용 |
|------|----------|
| `commute/models.py` | `legs`, `route_summary` 필드 추가 |
| `commute/tmap_client.py` | `route_with_legs()` + `_parse_transit_legs()` + `_parse_feature_legs()` + `_build_summary()` 추가 |
| `commute/commute_repository.py` | `route_json`, `route_summary` 컬럼 추가 + `_migrate()` |
| `commute/commute_service.py` | `route()` → `route_with_legs()` 호출로 교체 |
| `api/routers/real_estate.py` | `GET /dashboard/real-estate/commute` 응답에 legs/summary 추가 |
| `dashboard/views/real_estate.py` | 단지 상세 패널 3단 카드 컴포넌트 추가 |
| `prompts/insight_parser.md` | `route_summary` 3개 필드 프롬프트 추가 |
| `prompts/context_analyst.md` | `route_summary` 언급 추가 |

---

## 4. 컴포넌트 상세

### 4.1 models.py

```python
@dataclass
class CommuteResult:
    origin_key: str
    destination: str
    mode: str
    duration_minutes: int
    distance_meters: int
    cached: bool = field(default=False)
    legs: List[dict] = field(default_factory=list)      # 구조화 단계 목록
    route_summary: str = ""                              # LLM용 한 줄 요약
```

**leg 구조:**

대중교통 (transit):
```python
{
    "mode": "WALK" | "BUS" | "SUBWAY" | "RAIL",
    "route": "302" | "2호선" | None,
    "from_name": "가락시장",
    "to_name": "잠실역",
    "duration_minutes": 12,
    "stop_count": 4          # BUS/SUBWAY만 포함, WALK는 키 없음
}
```

자가용/도보 (car, walking):
```python
{
    "mode": "ROAD",
    "road_name": "올림픽대로",
    "distance_meters": 2500
}
```

### 4.2 tmap_client.py — 신규 메서드

```python
def route_with_legs(
    self, origin_lat, origin_lng, dest_lat, dest_lng, mode
) -> Tuple[int, int, List[dict], str]:
    """Returns (duration_minutes, distance_meters, legs, route_summary)"""
```

파싱 규칙:

| 모드 | API 필드 | 추출 |
|------|---------|------|
| `transit` | `itineraries[0].legs[]` | mode, route, sectionTime/60, passStopList 개수 |
| `car` | `features[]` where `geometry.type="LineString"` | `properties.name` 비어있지 않은 도로명 — features 배열 순서대로 앞 5개 |
| `walking` | 동일 | features 배열 순서대로 도로명 앞 5개 |

`_build_summary(legs, distance, mode)` 헬퍼:
- transit: `"도보 N분 → {BUS route}번 버스 → {to} → {SUBWAY route} → {목적지}"`
- car: `"{road1} → {road2} → ... ({distance:.1f}km)"`
- walking: `"{road1} → {road2} → ... ({distance:.1f}km)"`

### 4.3 commute_repository.py — DB 마이그레이션

```sql
-- 기존 캐시 DB 호환: 컬럼 없으면 추가
ALTER TABLE commute_cache ADD COLUMN route_json TEXT DEFAULT '[]';
ALTER TABLE commute_cache ADD COLUMN route_summary TEXT DEFAULT '';
```

`_migrate()` 메서드: `__init__` 시 `PRAGMA table_info(commute_cache)` 조회 → `route_json` 없으면 ALTER TABLE 실행.

### 4.4 commute_service.py

`get()` 메서드 내부에서 `self._client.route()` → `self._client.route_with_legs()` 로 교체. 반환된 legs, route_summary를 `CommuteResult`에 담아 저장.

### 4.5 FastAPI 응답 확장

`GET /dashboard/real-estate/commute` 응답:

```json
{
  "apt_name": "송파파크데일1단지",
  "destination": "삼성역",
  "transit": 59,
  "car": 35,
  "walking": 90,
  "transit_legs": [
    {"mode": "WALK", "from_name": "출발지", "to_name": "가락시장 정류장", "duration_minutes": 5},
    {"mode": "BUS", "route": "302", "from_name": "가락시장", "to_name": "잠실역", "duration_minutes": 12, "stop_count": 4},
    {"mode": "SUBWAY", "route": "2호선", "from_name": "잠실역", "to_name": "삼성역", "duration_minutes": 8, "stop_count": 2}
  ],
  "car_legs": [
    {"mode": "ROAD", "road_name": "올림픽대로", "distance_meters": 8000},
    {"mode": "ROAD", "road_name": "테헤란로", "distance_meters": 3000}
  ],
  "walking_legs": [...],
  "transit_summary": "도보 5분 → 302번 버스 → 잠실역 → 2호선 → 삼성역",
  "car_summary": "올림픽대로 → 잠실대교 → 테헤란로 (15.0km)",
  "walking_summary": "가락로 → 송파대로 (5.0km)",
  "cached": true
}
```

### 4.6 대시보드 UI

`src/dashboard/views/real_estate.py` — 단지 상세 패널 하단에 3단 카드 추가:

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ 🚌 대중교통  │  │ 🚗 자가용    │  │ 🚶 도보      │
│   59분      │  │   35분      │  │   90분      │
│             │  │             │  │             │
│ 도보 5분     │  │ 올림픽대로   │  │ 가락로       │
│ → 302번 버스│  │ → 잠실대교  │  │ → 송파대로  │
│ → 잠실역    │  │ → 테헤란로  │  │ → 삼성역    │
│ → 2호선     │  │ (15.0km)   │  │ (5.0km)    │
│ → 삼성역    │  │             │  │             │
└─────────────┘  └─────────────┘  └─────────────┘
```

### 4.7 LLM 프롬프트

`insight_parser.md` 교통 섹션:
```
⚡ 교통 — 대중교통 [commute_transit_minutes]분 / 자차 [commute_car_minutes]분 / 도보 [commute_walk_minutes]분 (삼성역 기준)
경로: 대중교통 [transit_summary] / 자차 [car_summary]
```

`context_analyst.md` 역세권 분석 섹션:
- `transit_summary`, `car_summary` 필드를 근거 인용 목록에 추가

---

## 5. 테스트 전략

| 테스트 파일 | 커버 범위 |
|------------|----------|
| `tests/modules/real_estate/commute/test_tmap_client.py` | `route_with_legs()` 파싱, legs 구조 검증, summary 생성 (mock HTTP) |
| `tests/modules/real_estate/commute/test_commute_repository.py` | route_json 저장/복원, 기존 DB 마이그레이션 |
| `tests/modules/real_estate/commute/test_commute_service.py` | legs가 CommuteResult에 포함되는지 확인 |
| `tests/api/test_commute_api.py` | FastAPI 응답에 legs/summary 포함 여부 |

기존 테스트(`route()` 호출) 변경 없음.

---

## 6. 구현 제외 범위 (YAGNI)

- 지도 위 경로 시각화 (폴리라인 렌더링)
- 정류장 목록 전체 저장 (stop_count만 저장)
- 실시간 버스 도착 정보 연동
- 복수 경로 옵션 제공 (최적 1개만)
