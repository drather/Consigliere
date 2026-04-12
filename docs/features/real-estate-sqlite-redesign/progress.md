# Progress: Real Estate 데이터 저장소 재설계

**Feature:** `real-estate-sqlite-redesign`
**Branch:** `feature/real-estate-sqlite-redesign`
**시작일:** 2026-04-12

---

## Phase 0: Preparation ✅
- [x] `docs/context/active_state.md` 업데이트
- [x] `git checkout -b feature/real-estate-sqlite-redesign`
- [x] 현황 분석 완료 (ChromaDB 12,085건 거래, SQLite 9,267건 마스터)

---

## Phase 1: Planning ✅
- [x] 저장소 적합성 분석 (SQLite vs ChromaDB vs NoSQL)
- [x] `spec.md` 작성
- [x] `progress.md` 작성

---

## Phase 2: Implementation (TDD) ✅

### Step 1 — 테스트 작성 (Red) ✅
- [x] `tests/test_apartment_repository.py` — 10개 테스트
- [x] `tests/test_transaction_repository.py` — 10개 테스트
- [x] `tests/conftest.py` — AppTest import 경로 설정

### Step 2 — 모델 업데이트 ✅
- [x] `models.py`: `RealEstateTransaction` → dataclass + `complex_code` 필드
- [x] `to_chroma_format()`, `naver_map_url` 제거 (ChromaDB 의존 제거)

### Step 3 — Repository 레이어 ✅
- [x] `apartment_repository.py` 신규 — `real_estate.db/apartments` (PK: complex_code)
- [x] `transaction_repository.py` 신규 — `real_estate.db/transactions`
  - [x] `save_batch()` — UNIQUE INDEX 기반 dedup
  - [x] `get_by_complex()` / `get_by_district()` / `get_by_districts()` / `get_all()`
  - [x] `delete_before()` — 1년 이상 데이터 삭제
  - [x] `resolve_complex_codes()` — fuzzy 매칭으로 FK NULL 해소

### Step 4 — ChromaDB Repository 정리 ✅ (부분)
- [x] `service.py` 신규 경로 전환 (거래는 SQLite 사용)
- [ ] `repository.py`: 거래 관련 메서드 제거 (하위 호환 유지 중)

### Step 5 — Service 레이어 업데이트 ✅
- [x] `service.py` `fetch_transactions()`: SQLite 저장으로 교체
- [x] `complex_code` 해소 호출 추가 (`resolve_complex_codes`)

### Step 6 — API 라우터 교체 ✅
- [x] `/dashboard/real-estate/monitor`: `TransactionRepository` 사용
- [x] `complex_code` 파라미터 추가 (primary lookup key)
- [x] `api/dependencies.py`: `TransactionRepository`, `ApartmentRepository` 의존성 등록

### Step 7 — Dashboard 화면 단순화 ✅
- [x] `api_client.py`: `get_real_estate_transactions()` — `complex_code` 지원, `apt_name`/`price_min`/`price_max` 제거
- [x] `_render_apt_detail_panel`: `complex_code` 있으면 정확 조회, 없으면 fallback fuzzy
- [x] geocoder.py: `address` 파라미터 추가 — road_address로 Kakao 검색

### Step 8 — 마이그레이션 스크립트 ✅
- [x] `scripts/migrate_to_real_estate_db.py`
  - [x] `apartment_master.db → real_estate.db/apartments`
  - [x] `ChromaDB → real_estate.db/transactions`
  - [x] `resolve_complex_codes()` 실행
  - [x] `--dry-run` / `--skip-masters` / `--skip-transactions` 옵션

### Step 9 — 회귀 테스트 ✅
- [x] `tests/test_apartment_repository.py` — 10/10 PASS
- [x] `tests/test_transaction_repository.py` — 10/10 PASS
- [x] `tests/test_real_estate_tab5.py` — 4/4 PASS
- [ ] Docker 재기동 후 화면 확인 (Phase 4에서)

---

## Phase 2.5: SOLID Review ✅
- [x] `TransactionRepository`: 단일 책임 (저장/조회/FK해소)
- [x] `ApartmentRepository`: 독립 인터페이스, ApartmentMasterRepository 비침해
- [x] Zero Hardcoding: `real_estate_db_path`, `apt_search_tx_limit`, `apt_search_map_limit` → `config.yaml`
- [x] `_render_apt_detail_panel` SRP 추출 (Tab1 블록에서 분리)

---

## Phase 3: Documentation
- [ ] `issues.md` 작성
- [ ] `result.md` 작성
- [ ] `docs/context/history.md` 업데이트
- [ ] `docs/context/active_state.md` 업데이트

---

## Phase 4: Release
- [ ] `git merge feature/real-estate-sqlite-redesign → master`
- [ ] 전체 테스트 통과
- [ ] 마이그레이션 스크립트 실행 (운영 데이터 이관)
- [ ] `apartment_master.db` deprecate
