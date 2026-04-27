# Address Mapping (2차 매핑) — 구현 결과

**완료일:** 2026-04-27  
**브랜치:** `feature/address-mapping` → `master` 머지 완료  

---

## 구현 범위

### 수정 파일
| 파일 | 변경 내용 |
|---|---|
| `src/modules/real_estate/building_master/building_master_service.py` | `_normalize_addr()` 함수 추가, `map_by_address()` 메서드 추가 |
| `src/modules/real_estate/apt_master_repository.py` | `get_apt_addresses_by_complex()` 메서드 추가 |
| `scripts/build_building_master.py` | `--map-address` CLI 플래그 추가 |

### 신규 파일
| 파일 | 설명 |
|---|---|
| `tests/modules/real_estate/building_master/test_address_mapping.py` | 주소 매핑 단위 테스트 8개 |

---

## 알고리즘

1. `get_all_for_mapping()` — `pnu IS NULL` 미매핑 항목 조회
2. `get_apt_addresses_by_complex()` — `apartments.road_address` 로드 (complex_code 인덱스)
3. `_normalize_addr()` — 괄호 `(동명)` 제거 + 마지막 2토큰 추출 → "도로명 번지"
4. `get_by_sigungu()` 후보군 필터 → normalized 주소 완전 일치
5. 이름 유사도 `>= 0.6` (1차 매핑 0.8 대비 낮은 임계값) → `update_building_mapping()`

---

## 실행 결과 (production, 2026-04-27)

### 2차 매핑 단독 결과
| 항목 | 수치 |
|---|---|
| 대상 (미매핑 항목) | 3,336건 |
| 주소 없음 (no_address) | 1,415건 |
| 주소 불일치 (no_match) | 1,714건 |
| **매핑 성공** | **207건** |

### 누적 매핑 현황
| 단계 | 매핑 건수 | 누적 | 전체 대비 |
|---|---|---|---|
| 1차 매핑 (이름 유사도 ≥ 0.8) | 2,701건 | 2,701건 | 44.7% |
| 2차 매핑 (주소 일치 + 이름 ≥ 0.6) | 207건 | 2,908건 | **48.2%** |

### no_address 1,415건 분석
- `complex_code` 없는 apt_master 항목 (apt_name 자유입력, 단지코드 미확인)
- `apartments` 테이블에 `road_address` 없는 경우 (신규 수집 필요)

---

## 테스트 결과

```
tests/modules/real_estate/building_master/test_address_mapping.py  8/8 PASS
  - test_normalize_addr_strips_parens
  - test_normalize_addr_no_parens
  - test_normalize_addr_empty
  - test_normalize_addr_single_token
  - test_map_by_address_matches_exact_road
  - test_map_by_address_skips_no_complex_code
  - test_map_by_address_skips_address_mismatch
  - test_map_by_address_skips_already_mapped

관련 모듈 전체: 73/73 PASS
```

---

## CLI 사용법

```bash
# 2차 매핑만 실행 (미매핑 항목 대상)
arch -arm64 .venv/bin/python3.12 scripts/build_building_master.py --map-address
```

---

## E2E 검증 면제

- **사유:** 화면단 변경 없음 — 백엔드 매핑 로직만 추가
- **변경 범위:** `building_master_service.py`, `apt_master_repository.py`, `scripts/`

---

## 향후 개선 과제

1. **no_address 1,415건 해소:** `apartments` 테이블 road_address 공백 항목 재수집
2. **no_match 1,714건:** 건축물대장 미등록 단지 또는 주소 불일치 — 수동 검수 필요
3. **3차 매핑:** 지번주소(jibun_address) 기반 보완 매핑 검토
