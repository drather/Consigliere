# Spec: 아키텍처 DI 최종 정리

**작성일:** 2026-06-06  
**Feature:** `arch-di-final-cleanup`  
**Branch:** master (직접 작업)

---

## 목표

이전 아키텍처 리팩토링(2026-05-31)에서 "future work"로 남긴 2개 위반 사항을 완전 제거한다.

1. **CommuteRepository 이중 인스턴스화**  
   `dependencies.py`에서 `_commute_service`와 `_apt_orchestrator`가 각각 독립된 `CommuteRepository` 인스턴스를 생성 → 동일 SQLite DB에 2개의 커넥션 객체, 싱글톤 원칙 위반

2. **`generate_daily_report` 로컬 빌더**  
   엔드포인트 함수 본문에 20개 이상 인라인 import와 직접 빌더 로직이 집중 → DI 원칙 위반, 테스트 불가

---

## 아키텍처

```
[ 기존 위반 구조 ]
generate_daily_report()
  └── import CommuteRepository, PoiCollector, GeocoderService, ...  ← 20+ local import
  └── DailyReportOrchestrator(...) 직접 생성

[ 수정 후 구조 ]
generate_daily_report(orchestrator=Depends(get_daily_report_orchestrator), ...)
  └── dependencies.py._daily_report_orchestrator  ← 싱글톤
        ├── _commute_service (= _commute_repo 공유)
        ├── _geocoder_service
        ├── _poi_collector
        ├── _loc_repo
        └── ...
```

---

## 변경 파일

| 파일 | 변경 |
|------|------|
| `src/api/dependencies.py` | `_commute_repo` 싱글톤 추출, `get_commute_repo()` 추가, DailyReport 섹션 신규 |
| `src/api/routers/real_estate.py` | `generate_daily_report` DI 전환, `list_daily_reports` DI 전환 |
