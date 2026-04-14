# Result: Real Estate 데이터 저장소 재설계

**Feature:** `real-estate-sqlite-redesign`
**브랜치:** `feature/real-estate-sqlite-redesign`
**완료일:** 2026-04-12

---

## 목표 달성 여부

| 목표 | 결과 |
|------|------|
| 실거래가 ChromaDB → SQLite 이전 | ✅ TransactionRepository 구현 완료 |
| complex_code FK로 apt_name 불일치 해결 | ✅ resolve_complex_codes() fuzzy 매칭 |
| 지도 geocoding 성공률 개선 | ✅ road_address 기반 Kakao 검색 |
| API/Dashboard complex_code 기반 조회 | ✅ api_client + _render_apt_detail_panel 업데이트 |
| 마이그레이션 스크립트 작성 | ✅ scripts/migrate_to_real_estate_db.py |
| 전체 테스트 통과 | ✅ 24/24 PASS |

---

## 변경 파일 목록

### 신규 파일
| 파일 | 역할 |
|------|------|
| `src/modules/real_estate/apartment_repository.py` | real_estate.db/apartments CRUD (PK: complex_code) |
| `src/modules/real_estate/transaction_repository.py` | real_estate.db/transactions CRUD (FK: complex_code) |
| `scripts/migrate_to_real_estate_db.py` | ChromaDB → SQLite 마이그레이션 스크립트 |
| `tests/test_apartment_repository.py` | ApartmentRepository 단위 테스트 10개 |
| `tests/test_transaction_repository.py` | TransactionRepository 단위 테스트 10개 |
| `tests/conftest.py` | AppTest용 sys.path 설정 |
| `docs/features/real-estate-sqlite-redesign/spec.md` | 스키마 설계 명세 |

### 수정 파일
| 파일 | 변경 내용 |
|------|----------|
| `src/modules/real_estate/models.py` | RealEstateTransaction → dataclass + complex_code 필드 |
| `src/modules/real_estate/service.py` | fetch_transactions(): SQLite 저장 + FK 해소 |
| `src/modules/real_estate/geocoder.py` | geocode(address=) 파라미터 추가 |
| `src/modules/real_estate/config.yaml` | real_estate_db_path, apt_search_tx_limit, apt_search_map_limit 추가 |
| `src/modules/real_estate/apartment_master/repository.py` | try/except ImportError 패턴 적용 |
| `src/modules/real_estate/apartment_master/service.py` | try/except ImportError 패턴 적용 |
| `src/api/dependencies.py` | TransactionRepository, ApartmentRepository 싱글턴 등록 |
| `src/api/routers/real_estate.py` | /dashboard/real-estate/monitor: SQLite 기반으로 교체 |
| `src/dashboard/api_client.py` | get_real_estate_transactions(): complex_code 지원, apt_name 제거 |
| `src/dashboard/views/real_estate.py` | _render_apt_detail_panel: complex_code 기반 조회 우선 |
| `src/dashboard/components/map_view.py` | render_master_map_view: 양방향 apt_name 매칭, address geocoding |

---

## 아키텍처 변화

### Before (ChromaDB 단일 저장)
```
실거래가 API → ChromaDB (real_estate_reports)
마스터 API   → SQLite (apartment_master.db)
Dashboard    → ChromaDB GET → Python 필터 → O(N) 스캔
             → 아파트명 기반 매칭 (불일치 다수)
```

### After (역할 분리)
```
실거래가 API → SQLite real_estate.db/transactions (INDEX, UNIQUE)
마스터 API   → SQLite apartment_master.db (기존) + real_estate.db/apartments (복제)
Dashboard    → complex_code 기반 O(1) 조회
             → 지도: road_address 기반 geocoding
```

---

## 테스트 결과

```
tests/test_apartment_repository.py    10/10 PASS
tests/test_transaction_repository.py 10/10 PASS
tests/test_real_estate_tab5.py         4/4 PASS
────────────────────────────────────
합계: 24/24 PASS
```

---

## 잔여 작업 (Phase 4)

1. `scripts/migrate_to_real_estate_db.py` 실제 실행 (운영 데이터 이관)
   ```bash
   arch -arm64 .venv/bin/python3.12 scripts/migrate_to_real_estate_db.py --dry-run
   arch -arm64 .venv/bin/python3.12 scripts/migrate_to_real_estate_db.py
   ```
2. Docker 재기동 후 화면 E2E 확인
3. `repository.py`에서 거래 관련 메서드 제거 (하위 호환 해소 후)
4. `master` 브랜치 머지
