# Spec: 실거래가 중심 아파트 마스터 재설계 (Transaction-First Master)

**작성일:** 2026-04-14  
**브랜치:** `feature/transaction-first-master`  
**관련 브랜치:** `feature/real-estate-sqlite-redesign` (선행 작업)

---

## 1. 배경 및 문제 정의

### 현재 구조의 한계

현재 시스템은 **공동주택 기본정보 API(국토교통부)**를 "마스터"로 놓고, 실거래가 데이터를 거기에 끼워 맞추는 구조다.

```
apartment_master (공동주택 기본정보 API)
    ↑ 마스터 권위
    |
transactions (국토부 실거래가 API)
    → complex_code로 매핑 시도
    → 실패 시 complex_code = NULL (2,441건, 20.2%)
```

**근본 문제:**
- 두 API의 단지명 체계가 다름: `"래미안 대치 팰리스"` vs `"래미안대치팰리스"`
- 공동주택 기본정보 API가 수록하지 않은 단지(구형, 소형, 명칭변경 등)는 영구 미매핑
- 데이터 클렌징·fuzzy match 개선으로도 20.2% NULL 해소 불가 (데이터 소스 자체의 차이)
- 마스터에 없는 단지의 거래 데이터는 UI에서 접근조차 불가 → dead data

### 핵심 통찰

> **실거래가 데이터(국토부)가 더 권위 있는 소스다.**
>
> 거래가 실제로 일어난 단지 = 현실에 존재하는 단지.  
> 공동주택 기본정보 API는 등록 상태에 따라 누락이 있을 수 있으나,  
> 실거래가 API는 실제 계약된 거래만을 수록한다.

---

## 2. 목표

1. **마스터 완전성 보장**: 실거래가에 등장한 모든 단지가 마스터에 존재
2. **UI 접근성 100%**: 모든 실거래가 데이터를 대시보드에서 탐색 가능
3. **상세정보 선택적 표시**: 공동주택 API 정보가 있으면 표시, 없으면 "상세정보 없음"
4. **기존 데이터 보존**: 이미 수집된 공동주택 마스터 정보 (세대수, 건설사 등) 재활용

---

## 3. 신규 아키텍처

### 3.1 레이어 구조

```
[실거래가 API]              [공동주택 기본정보 API]
      |                              |
      ↓                              ↓ (optional)
 transactions               apt_details
      |                      (complex_code PK)
      ↓                              |
  apt_master  ←── complex_code ──────┘
 (거래 단지 마스터)  nullable FK
```

### 3.2 테이블 설계

#### `apt_master` (신규 — 마스터 권위)

실거래가 데이터에서 파생되는 모든 단지 목록. 거래가 한 건이라도 있으면 마스터에 존재.

```sql
CREATE TABLE apt_master (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    apt_name      TEXT NOT NULL,         -- 국토부 API 단지명 (정규화된)
    district_code TEXT NOT NULL,         -- 5자리 시군구코드
    sido          TEXT NOT NULL DEFAULT '',
    sigungu       TEXT NOT NULL DEFAULT '',
    complex_code  TEXT,                  -- NULL 허용 — apt_details FK
    tx_count      INTEGER DEFAULT 0,     -- 보유 거래 건수 (캐싱)
    first_traded  TEXT,                  -- 최초 거래일
    last_traded   TEXT,                  -- 최근 거래일
    created_at    TEXT NOT NULL,
    UNIQUE(apt_name, district_code)
);
```

#### `apt_details` (기존 `apartments` 테이블 역할 변경)

공동주택 기본정보 API에서 수집한 상세정보. 선택적 조인 대상.

```sql
-- 기존 apartments 테이블을 apt_details로 rename (스키마 동일)
-- PK: complex_code
-- apt_master.complex_code → apt_details.complex_code (nullable)
```

#### `transactions` (기존 — FK 변경)

```sql
-- 기존: complex_code TEXT (FK → apartments, nullable)
-- 변경: apt_master_id INTEGER (FK → apt_master.id, NOT NULL)
--       complex_code TEXT 는 apt_details 조인용으로 apt_master에서 관리
```

### 3.3 데이터 관계

```
apt_master (1) ──── (N) transactions
apt_master (N) ──── (0..1) apt_details  [via complex_code]
```

---

## 4. 마이그레이션 전략

### Step 1: `apt_master` 테이블 생성 및 초기 데이터 적재

```sql
INSERT INTO apt_master (apt_name, district_code, sido, sigungu, tx_count, first_traded, last_traded, created_at)
SELECT
    t.apt_name,
    t.district_code,
    COALESCE(a.sido, '')     AS sido,
    COALESCE(a.sigungu, '')  AS sigungu,
    COUNT(*)                 AS tx_count,
    MIN(t.deal_date)         AS first_traded,
    MAX(t.deal_date)         AS last_traded,
    datetime('now')          AS created_at
FROM transactions t
LEFT JOIN apartments a ON t.complex_code = a.complex_code
GROUP BY t.apt_name, t.district_code;
```

### Step 2: `apt_master.complex_code` 채우기

```sql
UPDATE apt_master SET complex_code = (
    SELECT complex_code FROM transactions
    WHERE apt_name = apt_master.apt_name
      AND district_code = apt_master.district_code
      AND complex_code IS NOT NULL
    LIMIT 1
);
```

### Step 3: `apartments` → `apt_details` 리네임

기존 `apartments` 테이블을 `apt_details`로 rename. 스키마 변경 없음.

### Step 4: `transactions.apt_master_id` FK 추가

```sql
ALTER TABLE transactions ADD COLUMN apt_master_id INTEGER;
UPDATE transactions SET apt_master_id = (
    SELECT id FROM apt_master
    WHERE apt_name = transactions.apt_name
      AND district_code = transactions.district_code
);
```

---

## 5. 코드 변경 범위

### 신규 파일

| 파일 | 설명 |
|------|------|
| `src/modules/real_estate/apt_master_repository.py` | `apt_master` 테이블 CRUD |
| `scripts/migrate_to_transaction_first.py` | 마이그레이션 스크립트 |

### 변경 파일

| 파일 | 변경 내용 |
|------|-----------|
| `src/modules/real_estate/transaction_repository.py` | `apt_master_id` FK 지원, 마스터 기반 조회 |
| `src/dashboard/views/real_estate.py` | `apt_master` 기반 탐색, 상세정보 optional 표시 |
| `src/dashboard/api_client.py` | `apt_master` 조회 API 호출 |
| `src/api/routers/real_estate.py` | `apt_master` 조회 엔드포인트 추가 |
| `src/api/dependencies.py` | `AptMasterRepository` DI 등록 |

### 제거/단순화

| 항목 | 내용 |
|------|------|
| `_render_apt_detail_panel` district+fuzzy fallback | `apt_master`에 항상 존재하므로 불필요 |
| `resolve_complex_codes()` 의존 | 마스터 결정 로직이 `apt_master` 빌드 시점으로 이동 |
| `backfill_missing_apartments.py` | 불필요 (transaction-first이면 backfill 자체가 사라짐) |

---

## 6. UI 변경

### 아파트 탐색 탭 (Tab 1)

**현재:**
- `ApartmentMasterRepository` 기반 검색
- 단지 선택 → complex_code 있으면 정확 조회, 없으면 district+fuzzy fallback

**변경 후:**
- `AptMasterRepository` 기반 검색 (모든 거래 단지 포함)
- 단지 선택 → `apt_master_id`로 정확 조회 (항상 성공)
- 상세정보 패널: `complex_code` 있으면 apt_details 표시, 없으면 "상세정보 없음" 표시

### 필터 옵션

| 항목 | 현재 소스 | 변경 소스 |
|------|-----------|-----------|
| 시도/시군구 | apartment_master.sido/sigungu | apt_master.sido/sigungu |
| 아파트명 검색 | apartment_master.apt_name LIKE | apt_master.apt_name LIKE |
| 세대수 필터 | apartment_master.household_count | apt_details.household_count (조인) |
| 건설사 필터 | apartment_master.constructor | apt_details.constructor (조인) |

> 세대수/건설사 필터는 `apt_details`에 없는 단지를 제외할 수 있음을 UI에 안내.

---

## 7. SOLID 원칙 적용 계획

- **SRP:** `AptMasterRepository`는 `apt_master` CRUD만, `AptDetailsRepository`는 상세정보만
- **OCP:** 상세정보 소스 추가 시 `AptDetailsRepository` 구현체만 확장
- **DIP:** `render_apt_detail_panel`은 `AptMasterProtocol`, `AptDetailsProtocol` 인터페이스에 의존

---

## 8. 성공 기준

- [ ] 모든 transactions 데이터가 apt_master에 1:1 매핑됨 (NULL apt_master_id = 0)
- [ ] 대시보드 아파트 탐색: 기존 9,267건 → 실거래 단지 수 기준으로 확장
- [ ] 단지 클릭 시 실거래가 항상 표시됨 (fallback 로직 불필요)
- [ ] apt_details 보유 단지는 상세정보 표시, 미보유 단지는 "상세정보 없음" 표시
- [ ] 기존 테스트 전체 통과 (회귀 없음)
