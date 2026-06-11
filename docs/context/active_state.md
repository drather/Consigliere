# Project Consigliere: Active State
**Last Updated:** 2026-06-11

## 현재 포커스
- **Branch:** `master`
- **Status:** ✅ 전세가율/공급리스크 None 버그 수정 완료 (2026-06-11)

## 최근 완료 (2026-06-11)

- **전세가율(jeonse_ratio)/공급리스크(supply_risk_summary) None 버그 수정** (`docs/features/apt-analysis-jeonse-supply-fix/`)
  - 근본 원인 3가지:
    1. `_get_supply_risk()`가 `SupplyRiskAnalyzer`에 `news_service`/`llm`/`prompt_loader` 누락 → `TypeError` → `None`
    2. `_calc_jeonse_ratio()`가 항상 NULL인 `jeonse_transactions.complex_code`로 조회 + 원/만원 단위 불일치
    3. **`JeonseClient._parse()`가 한글 XML 태그(`아파트`/`년`/`보증금액` 등)를 조회하지만 실제 국토부 API 응답은 영문 태그(`aptNm`/`dealYear`/`deposit` 등)** → `jeonse_transactions` 0건 (1차 원인)
  - `JeonseRepository.get_by_apt_name()` 신규, `AptAnalysisOrchestrator` DI 확장(`news_service`/`prompt_loader`),
    `dependencies.py`에서 `_apt_orchestrator`를 `_geocoder_service`/`_prompt_loader` 정의 이후로 이동
  - `POST /jobs/jeonse/collect` 실행 → `jeonse_transactions` 0 → 8,180건, `docker restart consigliere_api`
  - E2E 검증(A10025850 헬리오시티): `jeonse_ratio` null→37.9, `supply_risk_summary` null→정상 문자열
  - 테스트: 889 passed (신규 13개 포함), pre-existing 7 failed는 무관 (stash 비교 확인)

## 최근 완료 (2026-06-10)

- **LLM 호출 전면 로컬화: 유료 API → `gemini` CLI (gemini-3-flash-preview)**
  - 배경: 유료 LLM API 호출 전면 금지, 로컬 설치된 gemini CLI로 대체 (요약/종합 용도)
  - `~/.gemini/GEMINI.md` 전역 메모리에서 Consigliere 전용 지시 제거
    - 원인: gemini CLI가 매 실행마다 `gemini-superpowers` 익스텐션 로드 + 프로젝트 워크스페이스 스캔 (81초 소요)
    - 제거 후 `cwd=/tmp` + `--extensions ""` 조합으로 ~9-12초로 단축
  - `GeminiCliClient` (`src/core/llm.py`) 재작성: `--model`/`--extensions ""` 플래그 + `cwd=/tmp` 서브프로세스 호출
    - `GEMINI_CLI_MODEL` 환경변수로 모델 지정 (기본값 `gemini-3-flash-preview`)
    - TDD 5개 신규 테스트 추가, `TestGeminiCliClient` 10/10 pass
  - **Docker 통합 (당초 계획 수정)**
    - 당초: 호스트 `node`/`gemini` 바이너리를 컨테이너에 바인드 마운트 → **실패** (호스트 바이너리가 macOS Mach-O, Linux 컨테이너에서 실행 불가 + `/usr/local` 경로는 Docker Desktop 공유 대상 아님)
    - 변경: `Dockerfile`에 Node.js 20 + `@google/gemini-cli@0.24.0`을 apt/npm으로 직접 설치 (Linux 네이티브)
    - `~/.gemini` (OAuth 자격증명)만 컨테이너에 **read-write**로 마운트 (`:ro` 시 토큰 갱신/세션 임시파일 쓰기 실패 → EROFS 에러)
    - `docker-compose.yml`: `LLM_PROVIDER=gemini-cli`, `GEMINI_CLI_MODEL=gemini-3-flash-preview` 환경변수 추가
  - 빌드 트러블슈팅: BuildKit 캐시 손상(`lease does not exist`)으로 빌드 반복 실패 → `docker buildx prune -a -f`로 해결
  - 검증: 컨테이너 내 `gemini` CLI 단독 호출 성공 (9.5초, "ok" 응답), `LLMFactory.create()` → `GeminiCliClient` → `generate_json()` E2E 정상 동작 확인
  - 테스트: 893 tests (9 신규), 10 failed = 기존 9개 flaky 실패와 동일 계열 (test_career.py/dashboard 등, 우리 변경과 무관 — stash 비교로 확인)

## 최근 완료 (2026-06-08)

- **`enrich_and_save()` 리포트 생성 플로우 연결** (`apt_analysis_orchestrator`)
  - `AptAnalysisOrchestrator`: `loc_repo` → `location_service` (LocationService) DI 전환
  - `_get_location_score()`: 점수 미존재 시 `_build_location_candidate()` → `enrich_and_save()` 자동 계산·저장
  - `_build_location_candidate()` 신규: POI 캐시 + 통근(transit) + household_count → candidate dict 구성
  - 계산 실패 시 로그 후 `location_score=None`으로 graceful degrade (LLM 인사이트는 계속 진행)
  - `dependencies.py`: `_apt_orchestrator`에 `_location_service` 싱글톤 주입
  - 테스트: 11개 신규/수정 (TDD), 전체 588 passed

## 알려진 후속 과제 (이어서)
- 문정시영(A13820007) 등 POI 캐시가 오래된(2026-05-03) 단지는 `POST /jobs/poi/collect`로 재수집 필요 — 캐시 만료 시 자동 트리거는 미포함 (on-demand 수집은 범위 외)

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

## 발견된 이슈: apt_master complex_code 매핑 오류 (2026-06-11 조사완료, 수정대기)

- **증상**: "목련마을2단지대우선경"(apt_master id=2902) → complex_code=`A43106007`로 매핑되어 있으나, `A43106007`은 실제로 "동편마을2단지"(LH, 관양동, 2012)의 코드. `/jobs/apt/analyze` 호출 시 200 OK로 "성공"하지만 전혀 다른 건물의 입지/통근/POI 데이터로 분석됨 (조용한 오답).
- **근본원인**: `TransactionRepository._name_fuzzy_match()` (`src/modules/real_estate/transaction_repository.py:246-261`)의 2차 suffix 매칭 규칙("짧은 쪽 끝 4글자 이상이 긴 쪽에 포함되면 매칭")이 "OO마을N단지" 같은 흔한 작명 패턴에서 거짓 양성 발생.
  - 재현: `_name_fuzzy_match("목련마을2단지대우선경", "동편마을2단지")` → `True` ("을2단지" 4글자 공통)
  - 반면 실제 의도 단지로 추정되는 "평촌목련2단지아파트"(`A43177507`, 994세대, 대우+선경건설 1992 — 이름의 "대우선경"과 일치)는 현재 규칙으로 **전혀 매칭 안 됨**
- **영향범위**: `apt_master.complex_code` 매핑 5,066건 중 **1,027건(~20%)**이 1차 substring이 아닌 2차 suffix 규칙으로만 매칭됨. 일부는 정상(단어순서 차이, 예: "길음뉴타운9단지래미안"↔"래미안길음뉴타운9단지")이나, 다음과 같은 명백한 오매핑도 다수 확인:
  - `신내대림아파트` → `면목풍림아파트`
  - `신내두산아파트` → `면목1차두산아파트`
  - `현대아이파크` → `사가정센트럴아이파크아파트`
  - `샹그레빌아파트`(2건, district 다름) → `정은스카이빌아파트` / `종암sh빌아파트`
  - `자양강변I-Park` → `광진We'vePark`
- **TODO**:
  1. 1,027건 분류(정상 vs 오매핑) — 자동 검증 기준 마련 (주소/세대수/시공사 등 보조 정보 활용)
  2. `_name_fuzzy_match` 2차 suffix 규칙 수정 또는 제거 (단순 이름 매칭만으로는 한계 — alias 테이블/주소 기반 매칭 검토)
  3. 오매핑 confirm 건은 `apt_master.complex_code` / `transactions.complex_code` 재계산
  4. SOP 4단계(spec/progress/issues/result) + Phase 2.5 SOLID Review 적용 — 영향범위가 커서 별도 작업으로 진행

## 다음 작업 로드맵

### 1순위 — POI 캐시 재수집 (문정시영 외 만료 단지)
- `POST /jobs/poi/collect` 호출 또는 데일리 Job으로 만료 캐시(30일+) 재수집
- ~~`enrich_and_save()` 파이프라인 연결~~ → 2026-06-08 완료

### 2순위 — E2E 테스트 코드 업데이트
- Tab1 AptMasterRepository 기반 UX 시나리오 업데이트

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
