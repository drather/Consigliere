# Issues: Real Estate 데이터 저장소 재설계

**Feature:** `real-estate-sqlite-redesign`
**브랜치:** `feature/real-estate-sqlite-redesign`

---

## Issue 1: ChromaDB에서 아파트명 불일치로 실거래가 조회 실패

**현상:** 모든 아파트에 "실거래가 없음" 표시.

**원인:**
- 마스터 DB (공동주택 API): `중계무지개아파트`
- 거래 DB (국토부 실거래가 API): `중계무지개`
- 기존 필터: `apt_name LIKE %keyword%` → 단방향 substring이라 역방향 매칭 불가

**해결:**
- `complex_code`를 FK로 두는 SQLite 재설계로 근본 해결
- 임시 fallback: 클라이언트 사이드 양방향 substring 매칭
  ```python
  tx_nm in master_nm or master_nm in tx_nm
  ```

---

## Issue 2: 지도에 마커가 표시되지 않음

**현상:** 지도 로드 시 마커 없음 (geocode 결과 0건).

**원인:**
- geocode 캐시가 거래 API apt_name 기준으로 구축됨
- 마스터 DB apt_name은 캐시 미스율 ~100%
- 카카오 API에 `"중계무지개아파트"` 검색 → 결과 없음 (풀네임 불인식)

**해결:**
- `geocoder.py`에 `address` 파라미터 추가
- 마스터 DB의 `road_address`(도로명) 또는 `legal_address`(법정동)를 Kakao 검색 쿼리로 사용
- 주소 기반 geocoding은 이름 기반보다 정확도 대폭 향상

---

## Issue 3: ChromaDB에 거래 데이터를 저장하는 것의 구조적 한계

**현상:** 성능 저하, 필터링 불능, 정렬 불가.

**원인/한계:**
- ChromaDB는 벡터 검색용이나 실거래가에는 벡터 검색 미사용 (O(N) 풀스캔)
- `.get()` API는 `$eq` 필터만 지원 → 날짜 범위 (`$gte`, `$lte`) 불가
- `ORDER BY`/`LIMIT` 미지원 → Python 레벨 후처리 필수
- 12,085건 데이터에도 불구하고 페이지네이션/정렬이 모두 메모리에서 처리됨

**해결:**
- 실거래가 저장소를 SQLite `transactions` 테이블로 이전
- UNIQUE INDEX로 dedup, INDEX on `deal_date`/`district_code`/`complex_code`로 성능 확보

---

## Issue 4: Python namespace package 충돌 (AppTest)

**현상:** `No module named 'modules.real_estate.apartment_master'` — 4/4 AppTest 실패.

**원인:**
- `src/modules/`와 `src/modules/real_estate/` 에 `__init__.py` 없음 (namespace package)
- AppTest 환경에서 `modules.real_estate` vs `src.modules.real_estate` 이중 등록

**해결:**
- `apartment_master/repository.py`, `apartment_master/service.py` 에 `try/except ImportError` 패턴 적용
- `tests/conftest.py` 신규: `sys.path`에 `src/` 경로 추가

---

## Issue 5: `:memory:` SQLite 테스트 격리 실패

**현상:** `no such table: transactions` — `save()` 호출 시 에러.

**원인:**
- `sqlite3.connect(":memory:")` 호출마다 새 DB 인스턴스 생성
- `_init_db()`와 `save()`가 서로 다른 커넥션 사용

**해결:**
- `:memory:` 경로 감지 시 `_shared_conn` 단일 커넥션 보관
- 모든 메서드에서 `_conn()` 헬퍼를 통해 공유 커넥션 사용
