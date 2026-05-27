# POI 입지 점수 DB 저장 연결

**작성일:** 2026-05-27  
**브랜치:** master (feature/poi-location-db-persist 없이 직접 작업)

## 목표

`DailyReportOrchestrator.generate()` 실행 시 LocationScore가 `location_scores` 테이블에 저장되어
대시보드 단지 클릭 시 실거주/투자 점수 카드가 정상 표시되도록 한다.

## 배경

- `location/` 패키지 및 `LocationScorer`는 구현 완료 (63 tests PASS)
- `report_orchestrator.py`에는 `upsert_score()` 호출이 존재하지만
- `daily_report_orchestrator.py`에는 누락 → 대시보드 항상 "리포트 생성 후 표시됩니다" 표시

## 변경 내용

수정 파일: `src/modules/real_estate/daily_report/daily_report_orchestrator.py`
1. `_try_load_loc_repo(db_path)` 모듈 레벨 헬퍼 추가 (방어적 초기화, `_load_scorer` 패턴 적용)
2. `loc_repo=None` 생성자 파라미터 추가 (DIP 준수 — 다른 의존성들과 동일 패턴)
3. `self._loc_repo = loc_repo or _try_load_loc_repo(db_path)` 초기화
4. Step 4 scorer 루프에 `if self._loc_repo: self._loc_repo.upsert_score(loc_score)` 추가

## 아키텍처

```
DailyReportOrchestrator.generate()
  └── Step 4: scorer.score(c)
        └── loc_score → c["_location_score"]
        └── loc_repo.upsert_score(loc_score) → location_scores 테이블
```

대시보드(`views/real_estate.py`)는 `LocationRepository.get_score()`로 읽음 — 별도 수정 불필요.
