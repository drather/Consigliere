# Project Consigliere: Active State
**Last Updated:** 2026-06-01

## 현재 포커스
- **Branch:** `master`
- **Status:** ✅ 아키텍처 후속 정리 완료 (2026-05-31)

## 최근 완료 (2026-05-31 후속)

- **아키텍처 후속 정리:** Tab1 DI 전환 + collect_poi DI 전환 + ReportRepository DI 등록
  - Tab1 `AptMasterRepository / ApartmentRepository / BuildingMasterRepository` 직접 인스턴스화 제거
  - `dashboard/services.py` Tab1 래퍼 7개 추가
  - `_get_report_repo()` 로컬 팩토리 제거 → `Depends(get_report_repo)` 전환
  - `collect_poi` 엔드포인트 — PoiCollector/GeocoderService/sqlite3 로컬 생성 제거 → DI 전환
  - `poi_collector.get_fresh_complex_codes()` 추가 (SQLite 999변수 청크 처리)
  - `location_service.collect_poi()` + `get_stale_complex_codes()` 추가
  - `dependencies.py` — `get_bm_repo / get_report_repo / get_geocoder_service` 싱글톤 등록
  - 테스트: 856 pass, 9 pre-existing failures

## 직전 완료 (2026-05-31)

- **아키텍처 리팩토링:** Layered Architecture + DI 패턴 도입 완료
  - `docs/guidelines/architecture.md` 신규 — 계층 규칙·DI·체크리스트 (CLAUDE.md 필독 4번째)
  - `LocationService` 신규 (TDD 5개 테스트), `dashboard/services.py` 진입점 확립
  - `dependencies.py` LocationService + AptAnalysis 싱글톤 등록
  - `routers/real_estate.py` apt_analyze Depends() 전환, 내부 빌더 제거
  - `dashboard/views/real_estate.py` sqlite3·LocationRepository 직접 접근 제거

## 최근 완료 (2026-06-06)

- **아키텍처 DI 최종 정리** (`arch-di-final-cleanup`)
  - `CommuteRepository` 이중 인스턴스화 제거 → `_commute_repo` 싱글톤으로 `_commute_service`/`_apt_orchestrator` 공유
  - `generate_daily_report` 20+ 로컬 빌더 → `Depends(get_daily_report_orchestrator)` 전환
  - `list_daily_reports` 로컬 Config/Repo 생성 → `Depends(get_daily_report_repo)` 전환
  - `dependencies.py` DailyReport 섹션 신규 (orchestrator, report_repo, llm, prompt_loader 싱글톤)
  - 테스트: 858 passed, 신규 실패 없음

## 다음 작업 로드맵

### 1순위 — POI 입지분석 고도화
- 설계 문서: `docs/superpowers/plans/2026-05-09-location-scoring-redesign.md`
- `enrich_and_save()` 호출하여 POI → LocationScore 파이프라인 완성

### 2순위 — 남은 아키텍처 정리 (minor)
- `generate_daily_report` 엔드포인트 내 대규모 로컬 빌더 → DI 전환
- `CommuteRepository` 이중 인스턴스화 (`dependencies.py` 두 곳) → 싱글톤 공유

### 3순위 — E2E 테스트 코드 업데이트
- Tab1 AptMasterRepository 기반 UX 시나리오 업데이트

### 4순위 — Career SOLID 장기 개선
- Processor Protocol 정의 (ISP/DIP 강화)
- CareerAgent 의존성 주입 패턴 적용

### 5순위 — Finance LLM Pipeline 통합
- `finance/service.py` → `build_llm_pipeline()` 교체

## 알려진 후속 과제
- `PoiCollector.get_cached()` 이중 만료 체크 (minor): `_load_cache()`가 이미 만료 체크 → `get_cached()` 조건 단순화 가능
- `enrich_and_save` 테스트: complex_code 없는 candidate로 주입 동작 명시 검증 추가 필요
- `apt_master_repo.search(limit=10000)` in collect_poi — config 기반으로 교체 필요 (현재 하드코딩)
