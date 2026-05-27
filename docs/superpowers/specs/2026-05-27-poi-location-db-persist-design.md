# POI 입지 점수 DB 저장 연결 설계

**Date:** 2026-05-27  
**Feature:** `feature/poi-location-db-persist`  
**Status:** 설계 확정

---

## 배경

`location/` 패키지와 `LocationScorer`는 이미 구현 완료(63 tests PASS)되어 있고,  
`DailyReportOrchestrator`에서 `scorer.score(c)` 호출로 점수 계산도 되고 있다.

그러나 계산된 `LocationScore`가 `LocationRepository.upsert_score()`를 통해 DB에 저장되지 않아  
대시보드 단지 클릭 시 항상 "리포트 생성 후 표시됩니다" 안내만 표시된다.

`report_orchestrator.py`에는 이미 `upsert_score()` 호출이 있지만,  
`daily_report_orchestrator.py`에는 누락된 상태.

---

## 목표

`DailyReportOrchestrator`가 LocationScore를 계산한 직후 `LocationRepository`에 저장하여,  
대시보드에서 실거주/투자 점수 카드가 정상 표시되도록 한다.

---

## 변경 범위

### 수정 파일: `src/modules/real_estate/daily_report/daily_report_orchestrator.py`

**변경 1 — import 추가:**
```python
from modules.real_estate.location.location_repository import LocationRepository
```

**변경 2 — `__init__` 생성자에 `_loc_repo` 초기화:**
```python
self._loc_repo = LocationRepository(self._db_path)
```
`db_path`는 기존 파라미터로 이미 존재.

**변경 3 — Step 4 scorer 루프 내 upsert 호출:**
```python
# 기존
c["_location_score"] = scorer.score(c)

# 변경 후
loc_score = scorer.score(c)
c["_location_score"] = loc_score
self._loc_repo.upsert_score(loc_score)
```

### 신규 테스트: `tests/modules/real_estate/daily_report/test_daily_report_orchestrator_location.py`

`DailyReportOrchestrator`가 scorer 실행 후 `upsert_score()`를 호출하는지 mock으로 검증.

---

## 아키텍처

기존 `report_orchestrator.py`와 동일한 패턴:

```
DailyReportOrchestrator.generate()
  └── Step 4: scorer.score(c)
        └── loc_score → c["_location_score"]
        └── loc_repo.upsert_score(loc_score)   ← 신규
              └── SQLite: location_scores 테이블 upsert
```

대시보드(`views/real_estate.py`)는 이미 `LocationRepository.get_score()`를 통해 읽는 코드가 구현되어 있음 → 별도 수정 불필요.

---

## 데이터 모델

변경 없음. `LocationScore` dataclass와 `location_scores` 테이블은 기존 그대로.

```
location_scores
  complex_code         TEXT (PK)
  residential_total    INTEGER
  residential_results  TEXT (JSON: List[DimensionResult])
  investment_total     INTEGER
  investment_results   TEXT (JSON: List[DimensionResult])
  scored_at            TEXT
```

---

## 에러 처리

기존 try/except 블록 내에서 upsert 호출:

```python
try:
    loc_score = scorer.score(c)
    c["_location_score"] = loc_score
    self._loc_repo.upsert_score(loc_score)   # DB 저장 실패 시에도 리포트 생성 계속
except Exception as e:
    logger.warning("[DailyOrchestrator] scorer.score 실패 %s: %s", ...)
```

upsert 실패가 리포트 생성을 막지 않도록 기존 except 범위 내에 포함.

---

## 테스트 전략

1. **기존 회귀:** `tests/modules/real_estate/location/` 63개 PASS 확인
2. **신규 단위 테스트:** `DailyReportOrchestrator`에서 `upsert_score()` 호출 검증 (mock)
3. **검증 기준:**
   - 전체 테스트 PASS
   - `location_scores` 테이블에 단지별 점수 저장 확인
   - 대시보드 단지 클릭 시 실거주/투자 점수 카드 정상 표시

---

## SOP 체크리스트

- [ ] Phase 0: `feature/poi-location-db-persist` 브랜치 생성
- [ ] Phase 1: `docs/features/poi-location-db-persist/spec.md` 작성
- [ ] Phase 2: TDD — 테스트 먼저 (Red → Green)
- [ ] Phase 2.5: SOLID Review
- [ ] Phase 3: `result.md` 작성, `history.md` 업데이트
- [ ] Phase 4: 전체 테스트 PASS, 머지

---

## E2E 면제 여부

화면단 변경 없음 (대시보드 코드는 이미 `loc_score` 표시 준비됨). E2E 테스트 추가 불필요.  
`result.md`에 면제 사유 기록 후 Phase 4-2 스킵.
