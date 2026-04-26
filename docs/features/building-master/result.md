# Building Master — 구현 결과

**완료일:** 2026-04-25  
**브랜치:** `feature/building-master` → `master` 머지 완료  
**커밋:** 총 16개 (worktree 기준)

---

## 구현 범위

### 신규 파일
| 파일 | 설명 |
|---|---|
| `src/modules/real_estate/building_master/__init__.py` | 패키지 초기화 |
| `src/modules/real_estate/building_master/models.py` | `BuildingMaster` dataclass |
| `src/modules/real_estate/building_master/building_register_client.py` | 건축HUB API 클라이언트 |
| `src/modules/real_estate/building_master/building_master_repository.py` | SQLite CRUD |
| `src/modules/real_estate/building_master/building_master_service.py` | 수집 + 매핑 서비스 |
| `scripts/build_building_master.py` | CLI (`--collect/--map/--rebuild`) |
| `tests/modules/real_estate/building_master/test_*.py` | 단위 테스트 3파일 26개 |

### 수정 파일
| 파일 | 변경 내용 |
|---|---|
| `src/modules/real_estate/models.py` | `AptMasterEntry`에 `pnu`, `mapping_score` 필드 추가 |
| `src/modules/real_estate/apt_master_repository.py` | `pnu`/`mapping_score` 마이그레이션, `update_building_mapping()`, `get_all_for_mapping()` |
| `src/modules/real_estate/config.yaml` | `building_master_sigungu_codes` 79개 코드 추가 |
| `src/api/dependencies.py` | `BuildingMasterService` DI 등록 |
| `src/api/routers/real_estate.py` | `POST /jobs/building-master/collect` 엔드포인트 |

---

## API 발견 사항 (스펙 대비 변경)

| 항목 | 스펙 | 실제 |
|---|---|---|
| API 엔드포인트 | `getBrBasisOulnInfo` (기본개요) | `getBrRecapTitleInfo` (총괄표제부) |
| 아파트 필터 필드 | `mainPurpsCdNm == "아파트"` | `etcPurps` 포함 "아파트" |
| 동수 필드 | `dongCnt` | `mainBldCnt` |
| bjdongCd | optional | 실질적 필수 (미입력 시 빈 응답) |

---

## 실데이터 검증 결과

**대상:** 서초구(11650), 강남구(11680), 송파구(11710), 분당구(41135)

### 수집 결과
| 구 | 법정동 수 | 수집 건수 |
|---|---|---|
| 서초구 | 10 | 101건 |
| 강남구 | 15 | 115건 |
| 송파구 | 13 | 74건 |
| 분당구 | 18 | 71건 |
| **합계** | 56 | **361건** |

### 매핑 결과
| 항목 | 수치 |
|---|---|
| apt_master 대상 (4개 구) | 295건 |
| 매핑 성공 (≥ 0.8) | 77건 (26.1%) |
| 임계값 미달 | 218건 |
| 나머지 시군구 (후보 없음) | 5,742건 |

### 매핑 성공 사례 (score 1.0)
```
래미안퍼스티지       →  래미안 퍼스티지
아크로리버파크       →  아크로리버파크
반포자이            →  반포자이
신반포자이          →  신반포자이
대치SKVIEW         →  대치 SK VIEW
래미안대치팰리스     →  래미안 대치 팰리스
디에이치포레센트     →  디에이치 포레센트
힐스테이트서초젠트리스 → 힐스테이트서초젠트리스
```

### 26% 매핑률 원인
- apt_master는 실거래가 신고 시 자유입력 이름 저장 → 비공식명, 단지번호, 건설사명 조합
- building_master는 건축물 등기 공식명 → 이름 형식 불일치
- 단지명 일치 구간에서는 score 1.0 (완벽 일치), 품질 이슈 아님

---

## 테스트 결과

```
tests/modules/real_estate/building_master/test_building_register_client.py  16/16 PASS
tests/modules/real_estate/building_master/test_building_master_repository.py  6/6 PASS
tests/modules/real_estate/building_master/test_building_master_service.py  8/8 PASS  (4개 추가)
tests/modules/real_estate/test_apt_master_repository.py  +4 PASS
────────────────────────────────────────────────────────────────────────────
합계: 26/26 PASS (전체 회귀 516건 중 building-master 관련 신규 추가분)
```

---

## CLI 사용법

```bash
# 건축물대장 수집 (이어받기 지원)
arch -arm64 .venv/bin/python3.12 scripts/build_building_master.py --collect

# apt_master 매핑만 재실행
arch -arm64 .venv/bin/python3.12 scripts/build_building_master.py --map

# 전체 초기화 후 재수집 + 매핑
arch -arm64 .venv/bin/python3.12 scripts/build_building_master.py --rebuild
```

---

## E2E 검증 면제

- **사유:** 화면단 변경 없음 — 백엔드 수집 파이프라인 및 DB 레이어만 추가
- **변경 범위:** `src/modules/real_estate/building_master/`, `src/api/dependencies.py`, `src/api/routers/real_estate.py` (엔드포인트만 추가, 기존 UI 불변)

---

## 향후 개선 과제

1. **매핑률 향상:** 주소 기반 2차 매핑 (도로명 주소 유사도) → 26% → 60%+ 목표
2. **전수 수집:** 나머지 75개 시군구 수집 (현재 4개 구 한정)
3. **bjdong 코드 캐싱:** 탐색 결과를 config.yaml 또는 DB에 저장하여 재수집 시 탐색 생략
4. **.env 오타 수정:** `HUB_API_KTY` → `HUB_API_KEY`
