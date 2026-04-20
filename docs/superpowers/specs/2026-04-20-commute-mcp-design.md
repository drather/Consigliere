# 출퇴근 시간 실시간 계산 — 설계 문서

**작성일:** 2026-04-20
**상태:** 승인됨

---

## 1. 문제 정의

현재 `_enrich_transactions()`는 `data/static/area_intel.json`의 동(洞) 단위 수작업 값을 출퇴근 시간으로 사용한다. 이 방식은 두 가지 근본적 결함이 있다:

1. **동 단위 단일값** — 같은 동 내 모든 아파트가 동일한 값을 받음 (단지별 위치 차이 무시)
2. **수작업 오류** — 수작업 입력으로 실제와 크게 다를 수 있음 (예: 송파파크데일1단지 19분 표기 vs 실제 59분)

결과적으로 LLM이 잘못된 값을 리포트에 그대로 인용하여 할루시네이션처럼 보이는 오류가 발생한다.

---

## 2. 목표

- 아파트 단지별 실제 주소 기반 출퇴근 시간을 T-map API로 계산
- 대중교통·자차·도보 3가지 교통수단 모두 지원
- 하이브리드 캐시로 API 호출 최소화 (캐시 히트 → DB 반환, 만료/미스 → API 호출 후 저장)
- Claude Code 대화 세션에서도 MCP 도구로 즉시 조회 가능

---

## 3. 아키텍처

### 3.1 신규 패키지

```
src/modules/real_estate/commute/
  __init__.py
  models.py              # CommuteResult dataclass
  tmap_client.py         # T-map REST API 래퍼
  commute_repository.py  # SQLite 캐시 CRUD
  commute_service.py     # 오케스트레이터
```

### 3.2 MCP 서버

```
src/mcp_servers/commute_server.py  # CommuteService 얇은 래퍼
```

### 3.3 데이터 흐름

```
[자동화] Job4
  → _enrich_transactions()
      → CommuteService.get(apt_master_id, road_address, mode)
            → commute_repository: 캐시 유효하면 즉시 반환
            → (캐시 없음/만료) GeocoderService.geocode(road_address)
            → TmapClient.route(origin_lat, origin_lng, dest_lat, dest_lng, mode)
            → commute_repository.upsert(결과 저장)
            → CommuteResult 반환

[대화형] Claude Code
  → MCP Server (commute_server.py)
      → CommuteService (동일 코어, 동일 캐시 DB 공유)
```

---

## 4. 컴포넌트 상세

### 4.1 models.py

```python
@dataclass
class CommuteResult:
    origin_key: str          # apt_master_id
    destination: str         # "삼성역"
    mode: str                # "transit" | "car" | "walking"
    duration_minutes: int
    distance_meters: int
    cached: bool             # 캐시에서 반환된 경우 True
```

### 4.2 tmap_client.py

| mode | 엔드포인트 |
|------|-----------|
| `transit` | `POST https://apis.openapi.sk.com/transit/routes` |
| `car` | `POST https://apis.openapi.sk.com/tmap/routes` |
| `walking` | `POST https://apis.openapi.sk.com/tmap/routes/pedestrian` |

- 공통 헤더: `appKey: ${TMAP_API_KEY}`
- 응답 파싱:
  - `transit`: `metaData.plan.itineraries[0].totalTime` (초 → 분)
  - `car`: `features[0].properties.totalTime` (초 → 분)
  - `walking`: `features[0].properties.totalTime` (초 → 분)

### 4.3 commute_repository.py

```sql
CREATE TABLE IF NOT EXISTS commute_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    origin_key TEXT NOT NULL,      -- apt_master_id
    destination TEXT NOT NULL,     -- "삼성역"
    mode TEXT NOT NULL,            -- "transit" | "car" | "walking"
    duration_minutes INTEGER NOT NULL,
    distance_meters INTEGER,
    cached_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    UNIQUE(origin_key, destination, mode)
)
```

메서드:
- `get(origin_key, destination, mode) -> Optional[CommuteResult]` — 만료된 경우 None 반환
- `upsert(result: CommuteResult)` — 존재하면 갱신, 없으면 삽입

> **origin_key 결정 규칙:** `apt_master_id`가 있으면 해당 값 사용. 없으면 `road_address`를 정규화(공백 제거, 소문자)하여 사용.

### 4.4 commute_service.py

```python
class CommuteService:
    def get(self, apt_master_id, road_address, mode) -> CommuteResult:
        ...
    def get_all_modes(self, apt_master_id, road_address) -> dict[str, CommuteResult]:
        """transit/car/walking 3가지 동시 반환"""
        ...
```

### 4.5 commute_server.py (MCP)

노출 도구:

```python
@mcp.tool()
def get_commute_time(address: str, mode: str = "transit") -> dict:
    """도로명주소 → 삼성역 출퇴근 시간 조회 (캐시 우선)"""
```

등록 위치: `~/.claude.json` mcpServers

```json
"commute": {
  "command": "arch",
  "args": ["-arm64", ".venv/bin/python3.12", "src/mcp_servers/commute_server.py"],
  "cwd": "/Users/kks/Desktop/Laboratory/Consigliere"
}
```

---

## 5. 기존 코드 변경

### 5.1 `_enrich_transactions()` (service.py)

| 변경 전 | 변경 후 |
|--------|--------|
| `area_intel.json` dong 단위 `commute_minutes` 조회 | `CommuteService.get_all_modes(apt_master_id, road_address)` 호출 |
| 출력: `commute_minutes` (단일) | 출력: `commute_transit_minutes`, `commute_car_minutes`, `commute_walk_minutes` |

`area_intel.json`의 `commute_minutes` 필드는 사용 중단. `nearest_stations`, `school_zone_notes` 등 나머지 필드는 유지.

### 5.2 `scoring.py`

`_score_commute()`: `commute_transit_minutes` 우선 사용, 없으면 `commute_minutes` fallback.

### 5.3 프롬프트 (`context_analyst.md`, `insight_parser.md`)

`commute_minutes_to_samsung` → `commute_transit_minutes` (대중교통), `commute_car_minutes` (자차) 필드명 업데이트.

---

## 6. 설정

### 6.1 config.yaml 추가

```yaml
commute:
  destination: "삼성역"
  destination_lat: 37.5088
  destination_lng: 127.0633
  cache_ttl_days: 90
```

### 6.2 .env 추가

```
TMAP_API_KEY=<T-map 개발자 콘솔에서 발급>
```

---

## 7. 테스트 전략

| 테스트 파일 | 커버 범위 |
|------------|----------|
| `tests/modules/real_estate/commute/test_tmap_client.py` | 응답 파싱, 모드별 분기 (mock HTTP) |
| `tests/modules/real_estate/commute/test_commute_repository.py` | DB CRUD, TTL 만료 판정, UPSERT |
| `tests/modules/real_estate/commute/test_commute_service.py` | 캐시 히트/미스, geocoder 연동 |
| `tests/modules/real_estate/test_service_enrich.py` | `_enrich_transactions()` 필드 변경 하위호환 |

외부 T-map API는 unittest.mock으로 처리. Repository 테스트는 `:memory:` SQLite 사용.

---

## 8. 구현 제외 범위 (YAGNI)

- 목적지 다양화 (현재 삼성역 단일 고정, 추후 persona 연동은 별도 이슈)
- 실시간 교통 상황 반영 (정적 경로 기준)
- 경유지/환승 상세 UI 표시
