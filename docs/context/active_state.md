# Project Consigliere: Active State
**Last Updated:** 2026-06-12

## 현재 포커스
- **Branch:** `worktree-dashboard-redesign` (worktree, master 미머지)
- **Status:** ✅ 아파트 상세 카드 UI/UX 5건 개선 완료, 머지 대기 (2026-06-12)

## 최근 완료 (2026-06-12)

- **아파트 상세 카드 UI/UX 5건 개선** (`docs/features/apt-detail-card-redesign/result.md`)
  - 출퇴근 경로(legs) 상세 expander 추가, 입지점수/교육환경 AI 인사이트 중복 제거
  - 입지점수 카드를 2열 그리드 + 클릭형 `근거 보기` expander로 전환
  - `🎒 학군프리미엄` 카드에 학군 상세(`_render_school_detail`, 라이브 API) 통합, AI 인사이트의 `📚 학군 분석` 제거
  - 실거래가 차트(line_chart)는 코드상 정상 — 8501 컨테이너는 master 마운트라 worktree 미커밋 변경 미반영(재기동으로도 해결 불가)
  - E2E 시나리오 5건(SCN-21~25) 추가, 회귀 10 failed/887 passed/1 error (기존 baseline과 동일, 신규 실패 없음)
  - `docs/guidelines/sop.md` Phase 2 step 6에 "재기동 필요 시 진단만 하지 말고 직접 재기동" + worktree 마운트 예외 조항 명문화
  - 미해결 관찰: `🎒 학군프리미엄` evidence("학교: 8개")와 `_render_school_detail` 라이브 API("반경 1km 학교 수: 0개") 값 불일치 (별도 이슈, 범위 외)
  - **다음 단계:** worktree → master 머지/커밋 필요 (사용자 명시 요청 시 진행)

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
