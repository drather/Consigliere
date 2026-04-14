# Spec: Real Estate 데이터 저장소 재설계

**Feature:** `real-estate-sqlite-redesign`
**Branch:** `feature/real-estate-sqlite-redesign`
**작성일:** 2026-04-12

---

## 배경 및 목표

### 문제
- 실거래가가 ChromaDB에 저장되어 있으나 벡터 검색을 전혀 사용하지 않음
- `apartment_master`(SQLite) ↔ `transactions`(ChromaDB) 간 JOIN 불가 → apt_name 불일치 우회로직 필요
- ChromaDB `get_transactions()`은 전체 로드 후 Python 필터 → O(N) 풀스캔
- `complex_code`(kaptCode) 링크 키가 거래 테이블에 없어 단지 특정 불가

### 목표
단지 마스터와 실거래가를 **단일 SQLite `real_estate.db`** 로 통합.  
`complex_code`를 공통 FK로 사용하여 신뢰할 수 있는 JOIN 제공.  
ChromaDB는 의미 검색이 실제로 필요한 용도(정책 팩트, 투어 노트)로만 한정.

---

## 신규 데이터 모델

### `real_estate.db` (SQLite)

#### `apartments` 테이블
기존 `apartment_master.db`의 `apartment_master` 테이블을 이관.  
PK를 `cache_key(TEXT)` → `complex_code(TEXT)`로 변경.

```sql
CREATE TABLE apartments (
    complex_code     TEXT PRIMARY KEY,   -- kaptCode (단지 고유 식별자)
    apt_name         TEXT NOT NULL,
    district_code    TEXT NOT NULL,      -- 5자리 시군구 코드
    sido             TEXT DEFAULT '',
    sigungu          TEXT DEFAULT '',
    eupmyeondong     TEXT DEFAULT '',
    ri               TEXT DEFAULT '',
    road_address     TEXT DEFAULT '',
    legal_address    TEXT DEFAULT '',
    household_count  INTEGER DEFAULT 0,
    building_count   INTEGER DEFAULT 0,
    parking_count    INTEGER DEFAULT 0,
    constructor      TEXT DEFAULT '',
    developer        TEXT DEFAULT '',
    approved_date    TEXT DEFAULT '',
    top_floor        INTEGER DEFAULT 0,
    base_floor       INTEGER DEFAULT 0,
    total_area       REAL DEFAULT 0.0,
    heat_type        TEXT DEFAULT '',
    elevator_count   INTEGER DEFAULT 0,
    units_60         INTEGER DEFAULT 0,
    units_85         INTEGER DEFAULT 0,
    units_135        INTEGER DEFAULT 0,
    units_136_plus   INTEGER DEFAULT 0,
    fetched_at       TEXT DEFAULT ''
);

CREATE INDEX idx_apartments_district ON apartments(district_code);
CREATE INDEX idx_apartments_sido     ON apartments(sido);
CREATE INDEX idx_apartments_sigungu  ON apartments(sigungu);
CREATE INDEX idx_apartments_name     ON apartments(apt_name);
```

#### `transactions` 테이블
기존 ChromaDB `real_estate_reports` 컬렉션의 거래 레코드를 이관.

```sql
CREATE TABLE transactions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    complex_code     TEXT,               -- FK → apartments.complex_code (nullable, 해소 후 채움)
    apt_name         TEXT NOT NULL,      -- 원본 API apt_name 보존
    district_code    TEXT NOT NULL,
    deal_date        TEXT NOT NULL,      -- YYYY-MM-DD
    price            INTEGER NOT NULL,   -- 원 단위
    floor            INTEGER DEFAULT 0,
    exclusive_area   REAL DEFAULT 0.0,
    build_year       INTEGER DEFAULT 0,
    road_name        TEXT DEFAULT '',
    FOREIGN KEY (complex_code) REFERENCES apartments(complex_code)
);

CREATE INDEX idx_transactions_complex   ON transactions(complex_code);
CREATE INDEX idx_transactions_district  ON transactions(district_code);
CREATE INDEX idx_transactions_date      ON transactions(deal_date);
```

---

## complex_code 해소 전략

거래 API는 `complex_code`를 제공하지 않으므로 다음 순서로 매핑:

1. **신규 수집 시**: `district_code` + `apt_name` substring 매칭으로 `apartments` 테이블 조회 → `complex_code` 즉시 기록
2. **기존 데이터 마이그레이션**: migration script가 동일한 fuzzy match로 일괄 해소
3. **매칭 실패 시**: `complex_code = NULL` 허용 (거래 데이터 유실 없음)

매칭 규칙:
```python
# district_code 일치 + (tx_name ⊂ apt_name OR apt_name ⊂ tx_name)
master_nm = apt.apt_name.strip().lower()
tx_nm = tx.apt_name.strip().lower()
match = (tx_nm in master_nm) or (master_nm in tx_nm)
```

---

## 저장소 역할 최종 정리

| 저장소 | 용도 | 근거 |
|--------|------|------|
| `real_estate.db` (SQLite) | apartments + transactions | 관계형, JOIN, ORDER BY, 소규모 |
| `geocode_cache.db` (SQLite) | 좌표 캐시 | key-value, 현행 유지 |
| ChromaDB `policy_knowledge` | 정책 팩트 의미 검색 | 자연어 쿼리 필요 |
| ChromaDB `real_estate_reports` | 투어 노트 의미 검색 | TourService 용도 |

---

## 레이어별 변경 범위

### `models.py`
- `ApartmentMaster` dataclass: `cache_key` 필드 제거, `complex_code` PK로 명시
- `RealEstateTransaction` Pydantic → dataclass 전환, `complex_code: Optional[str]` 추가

### `modules/real_estate/apartment_master/repository.py` → `ApartmentRepository`
- DB: `apartment_master.db` → `real_estate.db`, 테이블: `apartment_master` → `apartments`
- PK: `cache_key` → `complex_code`
- 기존 메서드 전부 유지 (`get`, `save`, `search`, `get_distinct_sidos` 등)

### `modules/real_estate/` 신규 파일: `transaction_repository.py`
- DB: `real_estate.db`, 테이블: `transactions`
- `save(tx)`, `save_batch(txs)`, `get_by_complex(complex_code, limit)`, `get_by_district(district_code, limit)`, `delete_before(cutoff_date)`, `resolve_complex_codes(apt_repo)` 포함

### `modules/real_estate/repository.py` (ChromaDB)
- `save_transaction` / `save_transactions_batch` / `get_transactions` / `delete_old_transactions` 제거
- 거래 관련 컬렉션 초기화 제거 (`real_estate_transactions` 컬렉션 삭제)
- `policy_knowledge`, `real_estate_reports`(투어) 전용으로 유지

### `modules/real_estate/service.py`
- `fetch_transactions()`: ChromaDB 저장 → `TransactionRepository.save_batch()` 로 교체
- `complex_code` 해소 호출 추가

### `api/routers/real_estate.py`
- `/dashboard/real-estate/monitor`: `chroma_repo.get_transactions()` → `tx_repo.get_by_district()` 교체
- `/jobs/real-estate/fetch-transactions`: ChromaDB → SQLite 경로로 전환

### `dashboard/api_client.py`
- API 계약 변경 없음 (HTTP 인터페이스 유지)

### `dashboard/views/real_estate.py`
- `_render_apt_detail_panel`: apt_name fuzzy 필터 제거 → `complex_code` 기반 조회
- 지도 뷰: 동일

---

## 마이그레이션 계획

### `scripts/migrate_to_real_estate_db.py`
1. `real_estate.db` 생성 + DDL 실행
2. `apartment_master.db` → `apartments` 테이블 복사 (PK 변환)
3. ChromaDB `real_estate_reports` → `transactions` 테이블 복사
4. `resolve_complex_codes()` 실행 (fuzzy match)
5. 완료 리포트 출력

---

## 비기능 요건

- 마이그레이션은 멱등(idempotent): 재실행해도 중복 없음
- `apartment_master.db`는 마이그레이션 완료 후 deprecate (삭제는 수동)
- ChromaDB `real_estate_reports`의 투어 노트 레코드 보존 (거래 레코드만 이관)
- 기존 테스트 전부 통과 유지
