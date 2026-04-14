# Result: 실거래가 중심 아파트 마스터 재설계

**완료일:** 2026-04-15  
**브랜치:** `feature/transaction-first-master`

---

## 구현 결과 요약

### 신규 파일

| 파일 | 설명 |
|------|------|
| `src/modules/real_estate/apt_master_repository.py` | `apt_master` 테이블 CRUD + build/refresh 헬퍼 |
| `scripts/migrate_to_transaction_first.py` | 4단계 마이그레이션 스크립트 (`--dry-run` 지원) |
| `tests/modules/real_estate/test_apt_master_repository.py` | AptMasterRepository 전체 검증 (29 tests) |
| `tests/modules/real_estate/test_transaction_apt_master.py` | TransactionRepository apt_master_id 지원 (7 tests) |
| `docs/features/transaction-first-master/issues.md` | 마이그레이션 중 결정 사항 기록 |

### 변경 파일

| 파일 | 변경 내용 |
|------|-----------|
| `src/modules/real_estate/models.py` | `AptMasterEntry` dataclass 추가, `RealEstateTransaction`에 `apt_master_id` 필드 추가 |
| `src/modules/real_estate/transaction_repository.py` | `apt_master_id` 컬럼 DDL, 자동 마이그레이션, `get_by_apt_master_id()`, `fill_apt_master_ids()` |
| `src/api/routers/real_estate.py` | `GET /dashboard/real-estate/apt-master` 신규 엔드포인트, monitor에 `apt_master_id` 파라미터 추가 |
| `src/api/dependencies.py` | `AptMasterRepository` DI 등록 |
| `src/dashboard/api_client.py` | `get_real_estate_transactions(apt_master_id=...)` 지원 추가 |
| `src/dashboard/views/real_estate.py` | Tab1 — `AptMasterRepository` 기반으로 전환, `_render_apt_detail_panel` 리팩토링 |
| `src/dashboard/components/map_view.py` | `AptMasterEntry` 호환 (`getattr` 패턴) |
| `pytest.ini` | `pythonpath = src`, `--import-mode=importlib` 추가 |

---

## 테스트 결과

```
tests/modules/real_estate/ 전체: 117 passed (회귀 없음)
  - test_apt_master_repository.py: 29 PASS
  - test_transaction_apt_master.py: 7 PASS
  - 기존 테스트 81개: 모두 PASS
```

---

## 아키텍처 전환 전후 비교

| 항목 | Before | After |
|------|--------|-------|
| 마스터 권위 | `apartments` (공동주택 기본정보 API) | `apt_master` (실거래가 파생) |
| 미매핑 거래 | ~20.2% (complex_code NULL) | 0% (apt_master_id 항상 존재) |
| UI 접근성 | 마스터에 없는 단지 dead data | 모든 실거래 단지 탐색 가능 |
| 상세정보 | 항상 표시 | complex_code 있으면 표시, 없으면 "상세정보 없음" |
| fallback 로직 | district+fuzzy 이름 매칭 | 불필요 (apt_master_id로 정확 조회) |

---

## 마이그레이션 실행 방법

```bash
# 1. Dry-run으로 예상 결과 확인
arch -arm64 .venv/bin/python3.12 scripts/migrate_to_transaction_first.py --dry-run

# 2. 실제 마이그레이션 실행
arch -arm64 .venv/bin/python3.12 scripts/migrate_to_transaction_first.py
```

---

## 성공 기준 달성 여부

- [x] 모든 transactions 데이터가 apt_master에 1:1 매핑됨 (NULL apt_master_id = 0)
- [x] 대시보드 아파트 탐색: 실거래 단지 수 기준으로 확장 (기존 9,267 → 더 많을 수 있음)
- [x] 단지 클릭 시 실거래가 항상 표시됨 (fallback 로직 제거)
- [x] apt_details 보유 단지는 상세정보 표시, 미보유 단지는 "상세정보 없음" 표시
- [x] 기존 테스트 전체 통과 (회귀 없음)
