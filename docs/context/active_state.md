# Project Consigliere: Active State
**Last Updated:** 2026-05-31

## 현재 포커스
- **Branch:** `master`
- **Status:** ✅ Real Estate 아키텍처 리팩토링 완료 (2026-05-31)

## 오늘 완료 (2026-05-31)

- **아키텍처 리팩토링:** Layered Architecture + DI 패턴 도입 완료
  - `docs/guidelines/architecture.md` 신규 — 계층 규칙·DI·체크리스트 (CLAUDE.md 필독 4번째)
  - `LocationService` 신규 (TDD 5개 테스트), `dashboard/services.py` 진입점 확립
  - `dependencies.py` LocationService + AptAnalysis 싱글톤 등록
  - `routers/real_estate.py` apt_analyze Depends() 전환, 내부 빌더 제거
  - `dashboard/views/real_estate.py` sqlite3·LocationRepository 직접 접근 제거

## 최근 완료 작업 (2026-05-30)

- **apt-analysis:** 개별 아파트 심층 분석 기능 구현 완료 (LLM CLI 기반, DB 저장, Slack, 대시보드)
  - POST /jobs/apt/analyze + GET /dashboard/apt/analysis 엔드포인트
  - Tab1 🔬 심층 분석 / 📋 이전 분석 보기 버튼 추가

## 다음 작업 로드맵

### 1순위 — 아키텍처 후속 정리 (이번 리팩토링에서 미처리)
- Tab1 Repository 직접 인스턴스화 제거 → `dashboard/services.py` 확장
- `_get_report_repo()` (router line 561) → `dependencies.py` factory 등록
- `collect_poi` 엔드포인트 → `get_location_service()` 활용으로 교체
- `generate_daily_report` 내 대규모 로컬 빌더 → `DailyReportOrchestrator` factory 등록

### 2순위 — POI 입지분석 고도화
- 설계 문서: `docs/superpowers/plans/2026-05-09-location-scoring-redesign.md`
- `enrich_and_save()` 호출하여 POI → LocationScore 파이프라인 완성

### 3순위 — E2E 테스트 코드 업데이트
- Tab1 AptMasterRepository 기반 UX 시나리오 업데이트

### 4순위 — Career SOLID 장기 개선
- Processor Protocol 정의 (ISP/DIP 강화)
- CareerAgent 의존성 주입 패턴 적용

### 5순위 — Finance LLM Pipeline 통합
- `finance/service.py` → `build_llm_pipeline()` 교체

## 알려진 후속 과제
- `PoiCollector.get_cached()` 이중 만료 체크 (minor): `_load_cache()`가 이미 만료 체크 → `get_cached()` 조건 단순화 가능
- `CommuteRepository` 이중 인스턴스화 (`dependencies.py:102` vs `199`): 싱글톤으로 공유 필요
- `enrich_and_save` 테스트: complex_code 없는 candidate로 주입 동작 명시 검증 추가 필요
