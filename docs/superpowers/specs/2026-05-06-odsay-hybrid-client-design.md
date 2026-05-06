# ODsay Hybrid Commute Client — 설계 문서

**날짜:** 2026-05-06
**목적:** Tmap 대중교통 API(일 10회 제한)를 ODsay LAB API(일 1,000회)로 교체

---

## 배경

`CommuteService`는 Tmap API 3가지 모드(transit/car/walking)를 호출한다.
- `transit` 엔드포인트: 일 10회 제한 → ODsay로 교체
- `car` / `walking` 엔드포인트: 별도 쿼터, 제한 넉넉 → Tmap 유지

ODsay는 대중교통(transit) 경로만 제공하므로, 두 클라이언트를 모드별로 라우팅하는 `HybridCommuteClient`를 도입한다.

---

## 파일 구조

```
src/modules/real_estate/commute/
├── tmap_client.py            # 기존 유지 — car/walking 담당
├── odsay_client.py           # NEW — ODsay transit 전용 클라이언트
├── hybrid_commute_client.py  # NEW — 모드별 클라이언트 라우팅
├── commute_service.py        # 변경 없음 (타입 힌트만 교체)
└── models.py                 # 변경 없음
```

**주입처 수정 (클라이언트 교체만):**
- `.env`
- `src/api/dependencies.py`
- `src/api/routers/real_estate.py`
- `src/modules/real_estate/service.py`
- `src/mcp_servers/commute_server.py`

---

## OdsayClient

### API
- 엔드포인트: `GET https://api.odsay.com/v1/api/searchPubTransPathT`
- 인증: query parameter `apiKey`
- 좌표계: WGS84 (경도=SX, 위도=SY)

### 인터페이스
```python
class OdsayClient:
    def __init__(self, api_key: str, timeout: int = 10): ...

    def route_with_legs(
        self,
        origin_lat: float, origin_lng: float,
        dest_lat: float, dest_lng: float,
        mode: str = "transit",
    ) -> Tuple[int, int, List[dict], str]:
        """Returns (duration_minutes, distance_meters, legs, route_summary)."""

    def route(
        self,
        origin_lat: float, origin_lng: float,
        dest_lat: float, dest_lng: float,
        mode: str = "transit",
    ) -> Tuple[int, int]:
        """Returns (duration_minutes, distance_meters)."""
```

### 응답 파싱

ODsay 응답 구조:
```json
{
  "result": {
    "path": [{
      "info": { "totalTime": 45, "totalWalk": 800 },
      "subPath": [{
        "trafficType": 1,
        "sectionTime": 10,
        "startName": "강남역",
        "endName": "서울역",
        "lane": [{"name": "2호선"}],
        "passStopList": { "stations": [...] }
      }]
    }]
  }
}
```

| ODsay `trafficType` | legs `mode` |
|---|---|
| 1 (지하철) | `SUBWAY` |
| 2 (버스) | `BUS` |
| 3 (도보) | `WALK` |

- `totalTime` → `duration_minutes` (분 단위, 올림)
- `totalWalk` → `distance_meters` (도보 거리)
- `subPath[]` → legs (TmapClient `_parse_transit_legs()` 출력과 동일 구조)
- `route_summary` → TmapClient `_build_summary()` 로직과 동일 포맷

### 에러 처리
- `result.path` 없거나 비어있으면 `ValueError` raise
- HTTP 에러는 `raise_for_status()`로 처리
- Rate limit 여유 있으므로 별도 throttle 불필요 (단순 GET 요청)

---

## HybridCommuteClient

```python
class HybridCommuteClient:
    def __init__(self, odsay: OdsayClient, tmap: TmapClient): ...

    def route_with_legs(
        self,
        origin_lat, origin_lng,
        dest_lat, dest_lng,
        mode: str,
    ) -> Tuple[int, int, List[dict], str]:
        if mode == "transit":
            return self._odsay.route_with_legs(...)
        return self._tmap.route_with_legs(...)

    def route(
        self,
        origin_lat, origin_lng,
        dest_lat, dest_lng,
        mode: str,
    ) -> Tuple[int, int]:
        if mode == "transit":
            return self._odsay.route(...)
        return self._tmap.route(...)
```

`CommuteService`는 기존 `tmap_client` 파라미터명 유지, 타입 힌트만 `HybridCommuteClient`로 교체.

---

## 주입처 변경 패턴

모든 주입처에서 동일한 패턴으로 교체:

```python
# Before
from .commute.tmap_client import TmapClient
tmap_client = TmapClient(api_key=os.getenv("TMAP_API_KEY", ""))

# After
from .commute.odsay_client import OdsayClient
from .commute.tmap_client import TmapClient
from .commute.hybrid_commute_client import HybridCommuteClient

tmap_client = HybridCommuteClient(
    odsay=OdsayClient(api_key=os.getenv("ODSAY_API_KEY", "")),
    tmap=TmapClient(api_key=os.getenv("TMAP_API_KEY", "")),
)
```

---

## 환경 변수

`.env`에 추가:
```
ODSAY_API_KEY=<ODsay LAB 발급 API 키>
```

---

## 테스트 전략

TDD 원칙에 따라 구현 전 테스트 작성.

### OdsayClient 단위 테스트 (`tests/unit/commute/test_odsay_client.py`)
- 정상 응답 파싱 (지하철/버스/도보 혼합 경로)
- `path` 빈 경우 ValueError
- `trafficType` 1/2/3 legs 매핑 정확성
- `route_summary` 포맷 검증

### HybridCommuteClient 단위 테스트 (`tests/unit/commute/test_hybrid_commute_client.py`)
- `transit` 모드 → OdsayClient 호출 확인
- `car` / `walking` 모드 → TmapClient 호출 확인
- 각 클라이언트가 상대방 모드에서 호출되지 않음을 검증

---

## 비고

- ODsay Basic: 일 1,000회 무료 (6개월), 개인 프로젝트 자격 충족
- 6개월 후 앱 재등록으로 갱신 예정
- car/walking은 Tmap 기존 쿼터 사용 (변경 없음)
