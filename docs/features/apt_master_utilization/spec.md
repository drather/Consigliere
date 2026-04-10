# Feature Spec: 아파트 마스터 데이터 활용 고도화

**작성일:** 2026-04-10
**Feature Branch:** `feature/apt_master_utilization`
**담당 작업:** 1-A 실거래가 분석 품질 향상 + 1-B Streamlit 마스터 조회 탭

---

## 1. 배경 및 목표

수도권 9,261개 단지 아파트 마스터 DB가 구축되었으나(2026-04-09),
실제 리포트 생성 파이프라인에서 활용도가 낮은 상태다.

| 문제 | 현황 | 목표 |
|------|------|------|
| 유동성 점수 항상 LOW | `_score_liquidity()`가 `household_count=0` 기본값으로 계산됨 | 마스터 DB 실값 반영 |
| 리포트에 건설사/준공연도 없음 | `_enrich_transactions()` 결과가 LLM 프롬프트에 미전달 | 서술에 자동 포함 |
| 마스터 DB 조회 UI 없음 | Streamlit에 탭 없음 | 검색/필터링 탭 추가 |

---

## 2. 작업 범위

### 2-A. 실거래가 분석 품질 향상

#### 2-A-1. `_score_liquidity()` 검증
- `_enrich_transactions()`에서 `household_count`가 정상적으로 부착되는지 확인
- `ScoringEngine._score_liquidity()` 로직: `household_count=0`이면 항상 `_LOW` (20점)
- 마스터 DB 조회 실패 시 `household_count`가 기본값 `0`으로 남는 케이스 처리

**실제 문제:** `get_or_fetch`는 DB 조회 실패 시 API를 재호출하는데, 이미 마스터 DB가 구축된 상태라면 SQLite 조회가 우선 성공해야 한다. `household_count=0`이 남는 원인은 두 가지:
1. `apt_name`이 DB의 key와 불일치 (공백/특수문자 차이)
2. API 응답에서 `hoCnt=0` 또는 빈 값

**개선:** `_enrich_transactions()`에서 마스터 조회 결과가 `household_count=0`일 때 경고 로그 추가 + 테스트로 커버리지 확인

#### 2-A-2. 리포트 서술에 건설사·준공연도 자동 포함
- `InsightOrchestrator.generate_strategy()`로 넘기는 `candidates` dict에 이미 `constructor`, `approved_date` 필드가 부착됨
- LLM 프롬프트(`src/modules/real_estate/prompts/`)에서 해당 필드를 활용하도록 수정
- Python 포맷터에서도 후보 서술 시 "건설사 시공, YYYY년 준공" 형식으로 포함

**구현 대상:**
- `src/modules/real_estate/insight_orchestrator.py` — candidates 직렬화 시 constructor/approved_date 포함 확인
- `src/modules/real_estate/prompts/` — 관련 프롬프트에 필드 활용 지시 추가

---

### 2-B. Streamlit 마스터 조회 탭

#### 요구사항
- `src/dashboard/views/real_estate.py`의 `show_real_estate()` 에 새 탭 추가
- 탭 이름: `🏗️ 단지 검색`

#### 기능 목록
| 기능 | 상세 |
|------|------|
| 지구 드롭다운 | config.yaml districts 기반 선택 (전체 포함) |
| 아파트명 텍스트 검색 | 부분일치 (LIKE 쿼리) |
| 세대수 범위 필터 | min_household ~ max_household 슬라이더 |
| 건설사 필터 | 드롭다운 (DB에서 distinct 조회) |
| 준공연도 범위 필터 | 연도 슬라이더 |
| 결과 테이블 | apt_name, district_code, household_count, building_count, constructor, approved_date |
| 단지 상세 보기 | 선택 시 expander로 전체 필드 표시 |

#### 데이터 접근
- Streamlit → `ApartmentMasterRepository`를 직접 임포트하여 SQLite 조회
- API 경유 불필요 (동일 컨테이너 내 파일 접근)
- `ApartmentMasterRepository`에 `search()` 메서드 추가

---

## 3. 아키텍처 설계

### 신규 메서드: `ApartmentMasterRepository.search()`

```python
def search(
    self,
    apt_name: str = "",
    district_code: str = "",
    min_household: int = 0,
    max_household: int = 99999,
    constructor: str = "",
    approved_year_start: int = 1970,
    approved_year_end: int = 2030,
) -> List[ApartmentMaster]:
    ...
```

- SQLite `WHERE` 조건 동적 조합 (비어 있는 필터는 무시)
- `approved_date` 필드 형식: `YYYYMMDD` 또는 `YYYY-MM-DD` → 연도만 추출하여 BETWEEN 필터
- 최대 결과 500건 제한 (UI 성능)

### Insight Orchestrator 개선
- `candidates` dict 직렬화 시 `constructor` / `approved_date` 필드가 포함되는지 확인
- LLM에 전달하는 후보 텍스트 표현에 해당 정보 포함 (예: `"래미안 퍼스티지 (삼성물산, 2009년)"`)

---

## 4. 데이터 모델

기존 `ApartmentMaster` dataclass (models.py) 변경 없음:
```
apt_name, district_code, complex_code,
household_count, building_count, parking_count,
constructor, approved_date, floor_area_ratio,
building_coverage_ratio, fetched_at
```

---

## 5. 테스트 계획

| 테스트 파일 | 케이스 |
|------------|--------|
| `tests/modules/real_estate/test_apt_master_search.py` | search() 필터 조합, 빈 결과, 결과 500건 제한 |
| `tests/modules/real_estate/test_scoring_liquidity.py` | household_count 실값 반영 시 점수 검증 |
| `tests/modules/real_estate/test_enrich_constructor.py` | enriched dict에 constructor/approved_date 포함 확인 |

---

## 6. 참조 문서
- `docs/master_plan.md` — SOLID, Zero Hardcoding 원칙
- `src/modules/real_estate/apartment_master/repository.py` — 기존 Repository 구조
- `src/modules/real_estate/scoring.py` — `_score_liquidity()` 현황
- `src/modules/real_estate/service.py:530` — `_enrich_transactions()` 현황
