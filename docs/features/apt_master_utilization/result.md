# Result: apt_master_utilization

**완료일:** 2026-04-11
**브랜치:** `feature/apt_master_utilization`

---

## 구현 요약

### 1-A. 실거래가 분석 품질 향상

#### 버그 수정: `_enrich_transactions()` early return

**파일:** `src/modules/real_estate/service.py`

**문제:** `area_intel={}` 일 때 `if not area_intel: return txs` 로 함수가 조기 반환되어
마스터 DB 조회 블록 전체가 실행되지 않았음.
→ 리포트 파이프라인 전체에서 `household_count=0`, `constructor=""`, `approved_date=""` 상태 유지
→ `_score_liquidity()` 항상 LOW (20점) 반환

**수정:** 마스터 DB 조회 로직을 루프 맨 앞으로 이동, `area_intel` 유무와 무관하게 항상 실행.

#### 리포트 서술: 건설사·준공연도 자동 포함

**파일:** `src/modules/real_estate/prompts/report_synthesizer.md`

각 단지 서술 템플릿에 다음 항목 추가:
```
단지 정보: [constructor] 시공, [approved_date 앞 4자리]년 준공, [household_count]세대 / [building_count]개동
```

---

### 1-B. Streamlit 마스터 조회 탭

#### `ApartmentMasterRepository.search()` 메서드 추가

**파일:** `src/modules/real_estate/apartment_master/repository.py`

동적 WHERE 조건 조합으로 SQLite 검색:
- `apt_name`: cache_key LIKE 부분일치
- `district_code`: cache_key prefix 매칭
- `sido` / `sigungu`: 시도/시군구 완전일치
- `min_household` / `max_household`: 세대수 범위
- `constructor`: LIKE 부분일치
- `approved_year_start` / `approved_year_end`: SUBSTR(approved_date,1,4) BETWEEN

추가 메서드: `get_distinct_constructors()`, `get_distinct_sidos()`, `get_distinct_sigungus(sido="")`,
`truncate()` (전체 재구축용)

#### Streamlit `🏗️ 단지 검색` 탭 추가

**파일:** `src/dashboard/views/real_estate.py`

tab5 추가:
- 아파트명 텍스트 입력 (부분일치)
- 시도 드롭다운 → 시군구 드롭다운 (cascading)
- 세대수 범위 슬라이더 (0 ~ 5000)
- 건설사 드롭다운 (DB distinct)
- 준공연도 범위 슬라이더 (1970 ~ 2030)
- 결과 테이블 (클릭 선택 → 단지 상세 expander)

---

### 마스터 DB 필드 전면 확장

**배경:** 최초 구축 시 핵심 필드만 수집했으나, 마스터 DB는 최대한 많은 정보를 담아두는 것이 적합.

#### `ApartmentMaster` dataclass 확장 (10 → 26 필드)

| 신규 필드 | API | 비고 |
|-----------|-----|------|
| `road_address` | API2 `doroJuso` | 도로명주소 |
| `legal_address` | API2 `kaptAddr` | 법정동주소 |
| `top_floor` | API2 `kaptTopFloor` | 최고층수 |
| `base_floor` | API2 `kaptBaseFloor` | 지하층수 |
| `total_area` | API2 `kaptTarea` | 연면적(㎡) |
| `heat_type` | API2 `codeHeatNm` | 난방방식 |
| `developer` | API2 `kaptAcompany` | 시행사 |
| `elevator_count` | API2 `kaptdEcntp` | 승강기 대수 |
| `units_60` | API2 `kaptMparea60` | 60㎡ 이하 세대수 |
| `units_85` | API2 `kaptMparea85` | 60~85㎡ 세대수 |
| `units_135` | API2 `kaptMparea135` | 85~135㎡ 세대수 |
| `units_136_plus` | API2 `kaptMparea136` | 135㎡ 초과 세대수 |
| `sido` | API1 `as1` | 시도 (필터링용) |
| `sigungu` | API1 `as2` | 시군구 (필터링용) |
| `eupmyeondong` | API1 `as3` | 읍면동 |
| `ri` | API1 `as4` | 리 |

#### DB 마이그레이션 전략

- SQLite `ALTER TABLE ADD COLUMN` 방식으로 기존 9,261건 레코드 보존
- `_NEW_COLUMNS` 리스트 + `_migrate()` 메서드로 자동 마이그레이션

#### 전체 재수집 (--rebuild)

- `scripts/build_apartment_master.py --rebuild`: DB 초기화 후 전체 재수집
- 결과: **9,275건 저장, 0건 오류** (71/71 지구 완료)
- 모든 레코드에 신규 16개 필드 완전 수집

---

## 테스트 결과

| 파일 | 케이스 수 | 결과 |
|------|-----------|------|
| `test_scoring_liquidity.py` | 8 | ✅ 전원 PASS |
| `test_enrich_constructor.py` | 7 | ✅ 전원 PASS |
| `test_apt_master_search.py` | 14 | ✅ 전원 PASS |
| **신규 합계** | **29** | ✅ |
| modules/ 전체 | 81 | ✅ passed |

---

## 변경 파일 목록

| 파일 | 변경 내용 |
|------|-----------|
| `src/modules/real_estate/models.py` | `ApartmentMaster` 10→26 필드 확장 |
| `src/modules/real_estate/service.py` | `_enrich_transactions()` 구조 개선 |
| `src/modules/real_estate/apartment_master/client.py` | `_parse_info()` 확장 필드 파싱 |
| `src/modules/real_estate/apartment_master/repository.py` | DDL 확장, `_migrate()`, `search()`, `get_distinct_*()`, `truncate()` |
| `src/modules/real_estate/apartment_master/service.py` | `_parse_info()` 전체 필드 + `list_item` 지원, `_match_name_with_item()` |
| `src/modules/real_estate/prompts/report_synthesizer.md` | 건설사·준공연도 서술 지시 추가 |
| `src/dashboard/views/real_estate.py` | `🏗️ 단지 검색` 탭(tab5) 추가 |
| `scripts/build_apartment_master.py` | `--rebuild` 플래그 추가 |
| `tests/modules/real_estate/test_scoring_liquidity.py` | 신규 |
| `tests/modules/real_estate/test_enrich_constructor.py` | 신규 |
| `tests/modules/real_estate/test_apt_master_search.py` | 신규 |
| `tests/modules/real_estate/test_apartment_master.py` | 확장 필드 테스트 추가 |
