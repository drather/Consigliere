# PNU 기반 Building Master DB 설계

**Date:** 2026-04-23  
**Status:** Approved  
**Scope:** 수도권(서울·경기·인천) 공동주택

---

## 1. 목표

현재 `apt_master`는 실거래가 API에서 파생되어 단지명 불일치·중복·분석 필드 부족 문제를 내재하고 있다. 건축물대장 API(공공데이터포털)를 통해 PNU(필지고유번호) 기반의 `building_master` 테이블을 별도 구축하고, `apt_master`와 매핑하여 투자 분석 필드(준공연도·세대수·용적률 등)를 보강한다.

---

## 2. 아키텍처 및 데이터 흐름

```
건축물대장 API (data.go.kr)
        ↓
BuildingRegisterClient        ← 법정동 코드별 일괄 조회, 페이지네이션
        ↓
BuildingMasterService         ← 수집 + 매핑 오케스트레이션
        ↓                           ↓
BuildingMasterRepository    AptMasterRepository
  (building_master 저장)      (apt_master.pnu 업데이트)
        ↓
  real_estate.db
  └── building_master (PNU PK)
        ↑
  apt_master.pnu (FK, NULLABLE) ← 매핑 성공 시만 채움
```

**수집 흐름 (5단계):**
1. 수도권 법정동 코드 목록 로드 (서울 25구 + 경기 31시군 + 인천 8구)
2. 법정동 코드별 건축물대장 API 호출 → 공동주택(아파트) 필터링
3. `building_master`에 PNU + 분석 필드 저장 (`parcel_pnu` = PNU 앞 15자리 인덱스)
4. `apt_master` 항목별 `parcel_pnu` 파생 → `building_master` 후보 조회 → 단지명 유사도 계산
5. 유사도 ≥ 0.8 → `apt_master.pnu` + `mapping_score` 업데이트, 미달 → NULL 보존

---

## 3. 매핑 전략

**핵심 원칙:** 이름 유사도만으로 매핑하지 않는다. 필지 레벨 PNU로 후보를 먼저 좁힌다.

```
apt_master.bjdong_code(8자리) + apt_master.jibun
  → parcel_pnu 앞 15자리 파생
    (시도2 + 시군구3 + 법정동5 + 지목1 + 지번4자리 zero-padding)
  → building_master WHERE parcel_pnu = ? (통상 1~2개 후보)
  → 단지명 정규화 후 SequenceMatcher 유사도
  → 유사도 ≥ 0.8 → apt_master.pnu 확정
```

**매핑 불가 케이스 처리:**
- 후보 없음 (필지 불일치): `pnu = NULL`, `mapping_score = NULL`
- 유사도 < 0.8: `pnu = NULL`, `mapping_score = best_score` (진단용 보존)
- 후보 다수 + 유사도 동점: NULL 보존 (오매핑 방지 우선)

---

## 4. 스키마

### `building_master` (신규)

```sql
CREATE TABLE building_master (
    mgm_pk                  TEXT PRIMARY KEY,   -- 관리건축물대장PK (22자리, 건축HUB 신규PK)
    building_name           TEXT NOT NULL,      -- 건축물대장 원본 건물명
    sigungu_code            TEXT NOT NULL,      -- 시군구 코드 5자리
    parcel_pnu              TEXT NOT NULL,      -- 지번주소 파생 15자리 (join 인덱스)
    road_address            TEXT,
    jibun_address           TEXT,
    completion_year         INTEGER,            -- 준공연도 (useAprDay 앞 4자리)
    total_units             INTEGER,            -- 총 세대수
    total_buildings         INTEGER,            -- 동수
    floor_area_ratio        REAL,               -- 용적률 (%)
    building_coverage_ratio REAL,               -- 건폐율 (%)
    collected_at            TEXT NOT NULL       -- ISO8601
);

CREATE INDEX idx_building_master_parcel ON building_master(parcel_pnu);
```

### `apt_master` (기존 테이블 — 컬럼 추가)

```sql
ALTER TABLE apt_master ADD COLUMN pnu TEXT;           -- FK → building_master (NULLABLE)
ALTER TABLE apt_master ADD COLUMN mapping_score REAL; -- 매핑 신뢰도 0.0~1.0
```

---

## 5. 컴포넌트 구성

```
src/modules/real_estate/
└── building_master/
    ├── __init__.py
    ├── models.py                      # BuildingMaster dataclass
    ├── building_register_client.py    # 건축물대장 API HTTP 클라이언트
    ├── building_master_repository.py  # SQLite CRUD
    └── building_master_service.py     # 수집 + 매핑 오케스트레이션

scripts/
└── build_building_master.py           # --collect / --map / --rebuild

src/api/routers/real_estate.py
└── POST /jobs/building-master/collect
```

| 컴포넌트 | 책임 |
|---|---|
| `BuildingRegisterClient` | 법정동 코드 → API 호출, 페이지네이션, 응답 파싱 |
| `BuildingMasterRepository` | `building_master` CRUD, `parcel_pnu` 인덱스 조회, `apt_master.pnu` 업데이트 |
| `BuildingMasterService` | 수집 루프 + 매핑 로직 (parcel_pnu 필터 → 유사도 계산) |
| `build_building_master.py` | `--collect` 수집만 / `--map` 매핑만 / `--rebuild` 전체 재실행 |

---

## 6. API 연동

**건축HUB 건축물대장 기본개요 조회**
- Base URL: `https://apis.data.go.kr/1613000/BldRgstHubService`
- Operation: `GET /getBrBasisOulnInfo`
- 인증키: `.env` → `HUB_API_KEY` (확인 완료)
- 참고: `OpenAPI활용가이드-_건축HUB_건축물대장_1.0.hwp` (상세 필드명 구현 시 확인)

**요청 파라미터:**

| 파라미터 | 설명 | 비고 |
|---|---|---|
| `serviceKey` | 인증키 | `HUB_API_KEY` |
| `sigunguCd` | 시군구코드 5자리 | 아래 목록 참고 |
| `bjdongCd` | 법정동코드 5자리 | 생략 시 시군구 전체 |
| `numOfRows` | 페이지당 건수 | 100 권장 |
| `pageNo` | 페이지 번호 | 1부터 시작 |
| `_type` | 응답 형식 | `json` |

**주요 응답 필드 (구현 시 HWP 가이드로 검증):**

| 필드 | 설명 |
|---|---|
| `mgmBldrgstPk` | 관리건축물대장PK (22자리, 건축HUB 신규PK) |
| `platPlc` | 지번주소 (parcel_pnu 파생 원천) |
| `newPlatPlc` | 도로명주소 |
| `bldNm` | 건물명 |
| `useAprDay` | 사용승인일 (YYYYMMDD → 연도만 추출) |
| `hhldCnt` | 세대수 |
| `dongCnt` | 동수 |
| `vlRat` | 용적률 |
| `bcRat` | 건폐율 |
| `mainPurpsCdNm` | 주요용도명 (아파트 필터링용) |

> **PK 주의:** 건축HUB 신규PK는 22자리 일련번호(`mgmBldrgstPk`)이며, 이를 `building_master`의 PK로 사용한다. `parcel_pnu`(15자리)는 지번주소에서 파생하여 `apt_master` 매핑용 인덱스로 별도 관리한다.

**수도권 sigunguCd 목록 (첨부2 기준):**

```python
METRO_SIGUNGU_CODES = [
    # 서울 (25개 구)
    "11110", "11140", "11170", "11200", "11215", "11230", "11260",
    "11290", "11305", "11320", "11350", "11380", "11410", "11440",
    "11470", "11500", "11530", "11545", "11560", "11590", "11620",
    "11650", "11680", "11710", "11740",
    # 인천 (10개 구·군)
    "28110", "28140", "28177", "28185", "28200", "28237", "28245",
    "28260", "28710", "28720",
    # 경기 (구 단위 분리 포함, 총 44개)
    "41111", "41113", "41115", "41117",  # 수원시 4구
    "41131", "41133", "41135",           # 성남시 3구
    "41150",                             # 의정부시
    "41171", "41173",                    # 안양시 2구
    "41192", "41194", "41196",           # 부천시 3구
    "41210", "41220", "41250",           # 광명, 평택, 동두천
    "41271", "41273",                    # 안산시 2구
    "41281", "41285", "41287",           # 고양시 3구
    "41290", "41310", "41360", "41370", "41390", "41410", "41430",
    "41450",
    "41461", "41463", "41465",           # 용인시 3구
    "41480", "41500", "41550", "41570", "41590", "41610", "41630",
    "41650", "41670", "41800", "41820", "41830",
]
```

---

## 7. 테스트 전략 (TDD)

| 테스트 대상 | 방식 | 검증 항목 |
|---|---|---|
| `BuildingRegisterClient` | API fixture mock | 응답 파싱, 페이지네이션, 빈 결과 처리 |
| `BuildingMasterRepository` | in-memory SQLite | CRUD, parcel_pnu 인덱스 조회, apt_master.pnu 업데이트 |
| `BuildingMasterService.collect()` | mock client + mock repo | 법정동 코드 순회, 저장 호출 횟수, 오류 격리 |
| `BuildingMasterService.map()` | mock repo | 유사도 ≥ 0.8 매핑 확정, < 0.8 NULL 보존, 동점 NULL 보존 |
| `build_building_master.py` | subprocess or direct call | --collect / --map / --rebuild 플래그 동작 |

---

## 8. 제약 및 리스크

| 항목 | 내용 |
|---|---|
| API 키 | `.env`의 `HUB_API_KEY` 확인 완료 |
| 일일 쿼터 | 기본 1,000건 → 수도권 법정동 수천 개 → 수일에 걸쳐 수집 or 쿼터 확장 신청. `--collect` 스크립트는 429/오류 응답 시 해당 법정동 코드를 실패 목록에 기록하고 계속 진행 (재실행 시 미수집분만 처리). |
| 매핑률 | 실거래가 지번 데이터 품질에 따라 매핑률 변동 — 목표 70% 이상 |
| apt_master 미머지 | `feature/real-estate-sqlite-redesign` 브랜치 머지 후 구현 권장 |
