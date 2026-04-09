# Spec: 아파트 마스터 DB 구축

**작성일:** 2026-04-09  
**브랜치:** `feature/apartment-master-db`

## 목표

공공 API를 통해 수도권 아파트 단지 마스터 정보(세대수·동수·건설사·사용승인일)를 전수 수집하고 SQLite에 저장한다.
이후 실거래가 수신 시 마스터 정보를 자동으로 enrich하여 scoring·filtering의 실효성을 높인다.

## 배경 / 문제

| 항목 | 현황 | 문제 |
|------|------|------|
| `household_count` | 항상 0 | `_score_liquidity()` 무의미, `min_household_count` 규칙 무력화 |
| 세대수 기반 환금성 | scoring에서 활용 불가 | 상위 추천 단지의 환금성 점수 0점 |
| 건설사·준공일 | 없음 | 브랜드 아파트 여부, 실제 건축연령 확인 불가 |

## 데이터 소스

### Phase 1 (이번 구현)
| API | 호스트 | 파라미터 | 응답 |
|-----|--------|---------|------|
| 공동주택 단지 목록 | `apis.data.go.kr/1613000/AptListService3/getSigunguAptList3` | `sigunguCd` (5자리) | `kaptCode`, `kaptName` |
| 공동주택 기본정보 | `apis.data.go.kr/1613000/AtclService/getAphusBassInfoV4` | `kaptCode` | `hhldCnt`, `bdNum`, 건설사, 사용승인일 |

### Phase 2 (추후)
- 건축물대장 기본개요 → 용적률(`vlRat`), 건폐율(`bcRat`)

## 아키텍처

```
src/modules/real_estate/apartment_master/
  __init__.py
  client.py       # 공공 API 클라이언트
  repository.py   # SQLite CRUD (geocoder.py 패턴)
  service.py      # 전수 구축(build_initial) + 온디맨드(get_or_fetch)
```

## 데이터 모델

```python
@dataclass
class ApartmentMaster:
    apt_name: str
    district_code: str           # 5자리 sigunguCd
    complex_code: str            # kaptCode
    household_count: int         # hhldCnt
    building_count: int          # bdNum
    parking_count: int           # 주차대수
    constructor: str             # 시공사
    approved_date: str           # 사용승인일 YYYYMMDD
    floor_area_ratio: Optional[float] = None   # Phase 2
    building_coverage_ratio: Optional[float] = None  # Phase 2
    fetched_at: str = ""
```

## 저장소

- **엔진:** SQLite (`data/apartment_master.db`)
- **테이블:** `apartment_master`
- **PK:** `cache_key = f"{district_code}__{apt_name}"`
- **경로:** `config.yaml`의 `apartment_master_db_path`

## 수집 전략

### 초기 전수 구축 (`build_initial`)
1. `config.yaml` districts 71개 sigunguCd 순회
2. 각 지구 → 단지 목록 API (kaptCode 목록 수신)
3. 각 kaptCode → 기본정보 API (세대수·동수 등 수신)
4. SQLite 저장 (이미 있으면 스킵)
5. Rate limiting: 0.3s sleep per request

### 온디맨드 보완 (`get_or_fetch`)
- `_enrich_transactions()` 호출 시 apt_name → SQLite 조회
- 없으면 해당 지구 단지 목록 → 이름 매칭 → 기본정보 → 저장

## 통합 포인트

- `service.py` `_enrich_transactions()`: 마스터 조회 후 `household_count`, `building_count`, `constructor`, `approved_date` 부착
- `service.py` `RealEstateAgent.__init__()`: `ApartmentMasterService` 주입
- `routers/real_estate.py`: `POST /jobs/real-estate/build-apartment-master`

## Zero Hardcoding

| 값 | 위치 |
|----|------|
| DB 경로 | `config.yaml: apartment_master_db_path` |
| API 키 | `.env: MOLIT_APT_LIST_API_KEY` (없으면 `MOLIT_API_KEY` fallback) |
| Rate limit sleep | `config.yaml: apartment_master_rate_limit_sec` |
| API URL | `client.py` 상수 (환경변수 override 가능) |
