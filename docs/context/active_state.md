# Project Consigliere: Active State
**Last Updated:** 2026-04-30
**Current Active Feature:** 없음 (대기 중)

## 현재 포커스
- **Branch:** `master`
- **Status:** ✅ feature/apt-ratios 롤백 + 컨텍스트 업데이트 완료 (2026-04-30)

## 선행 브랜치 (미머지)
- **Branch:** `feature/real-estate-sqlite-redesign`
- **Status:** ✅ 구현 완료 — 본 브랜치 완료 후 함께 머지 예정
- **완료 내용:**
  - ChromaDB → SQLite 마이그레이션
  - 데이터 클렌징 (`cleanse_apartment_names.py`) — complex_code 매핑 75.6% → 79.8%
  - `ApartmentRepository`, `TransactionRepository` normalize-on-save 적용
  - E2E Playwright 테스트 28개

## 최근 완료 작업
- **completed:** 주소 기반 2차 매핑 구현 (2026-04-27)
  - `map_by_address()`: complex_code → apartments.road_address → building_master 주소 매칭
  - `_normalize_addr()`: 괄호 제거 + 마지막 2토큰("도로명 번지") 추출
  - `get_apt_addresses_by_complex()`: apartments 테이블 bulk 로드
  - 2차 매핑 207건 추가 → 누적 2,908건 / 6,037건 (48.2%)
  - CLI `--map-address` 플래그 추가
  - 8/8 단위 테스트 통과
- **completed:** PNU 기반 Building Master DB 구축 (2026-04-25)
  - 건축HUB 총괄표제부 API(`getBrRecapTitleInfo`) → `building_master` 테이블 구축
  - `apt_master` 이름 유사도 매핑(SequenceMatcher ≥ 0.8) — pnu/mapping_score 컬럼 추가
  - CLI: `scripts/build_building_master.py` (`--collect/--map/--rebuild`)
  - FastAPI: `POST /jobs/building-master/collect` (rebuild 파라미터 포함)
  - bjdong 코드 자동 탐색(`discover_bjdong_codes`): API가 sigunguCd만으론 빈 결과 반환
  - 실데이터 검증: 서초/강남/송파/분당 4개 구 361건 수집, 최신 아파트 단지명 score 1.0 매핑 확인
  - 26/26 단위 테스트 통과
- **completed:** 출퇴근 경로 상세 정보 추가 — legs + route_summary (2026-04-22)
  - `CommuteResult`에 `legs: List[dict]`, `route_summary: str` 필드 추가
  - `TmapClient.route_with_legs()` — transit legs 파싱, car/walking 도로명 파싱, _build_summary()
  - `CommuteRepository` — route_json/route_summary 컬럼 + ALTER TABLE 자동 마이그레이션
  - `CommuteService` — route_with_legs() 호출로 교체 (기존 route() 유지, 비파괴적 확장)
  - FastAPI `GET /dashboard/real-estate/commute` — transit_legs/car_legs/walking_legs/summary 추가
  - `_enrich_transactions()` — transit_summary/car_summary/walking_summary 거래 데이터에 추가
  - 대시보드 — 3단 카드(대중교통/자가용/도보) expander 추가
  - LLM 프롬프트 — insight_parser.md, context_analyst.md에 route_summary 필드 추가
  - 490+ tests PASS, 기존 18개 테스트 변경 없음
- **completed:** 리포트 생성 전면 점검 + LLM 할루시네이션 수정 (2026-04-19~20)
  - ChromaDB → tx_repo SQLite 전환, dedup normalize, apt_master enrich
  - 거시경제 주담대금리(2.83%) 예산 산출 반영
  - LLM 2회→1회 통합 (horea_analyst 제거), horea_validator 단계 추가
  - 가격 ±10% 필터, data_absent_neutral=50
  - `_format_candidates_for_llm()` — LLM 점수 재계산/가격 오변환/phantom 후보 방지
  - 178 tests PASS, Job4 실행 검증 완료
- **completed:** 거시경제 지표 수집 시스템 구축 (2026-04-18)
  - `src/modules/macro/` 신규 패키지 (models, repo, bok_client, service)
  - API 3개 (`/jobs/macro/collect`, `/dashboard/macro/latest`, `/dashboard/macro/history/{id}`)
  - 대시보드 Insight 탭 거시경제 서브탭 확장
  - BOKClient 분기 날짜 포맷 버그 수정 (`%Y%m` → `{Y}Q{n}`)
  - 8개 지표 실데이터 수집 완료 (기준금리, 주담대, M2, 가계신용, 주택매매, 전세, CPI, GDP)
- **completed:** Transaction-First 아파트 마스터 재설계 (2026-04-15)
  - `apt_master` 테이블 신설 (실거래가 파생 마스터 권위 소스)
  - `AptMasterRepository` + 마이그레이션 스크립트 TDD 구현 (117 tests PASS)
  - API: `GET /dashboard/real-estate/apt-master`, monitor에 `apt_master_id` 파라미터
  - 대시보드 Tab1 `AptMasterRepository` 기반으로 완전 교체
  - 미매핑 거래 ~20.2% → 0% 해결 (apt_master_id 항상 존재)
- **completed:** Playwright E2E 브라우저 테스트 도입 + 지도 로드 버그 수정 (2026-04-13)
  - Playwright MCP 서버 등록 (`~/.claude.json`)
  - `tests/e2e/` 디렉토리 신설: conftest.py + 5개 테스트 파일 (28 tests)
  - `pytest.ini` 추가 — e2e 마커 등록, 기존 단위 테스트와 분리 실행
  - **버그 수정:** `src/dashboard/main.py`에 `load_dotenv()` 추가
    - 원인: `.env`의 `KAKAO_API_KEY`가 os.environ에 반영되지 않아 지도 로드 버튼 클릭해도 경고만 표시
    - 수정: `load_dotenv(dotenv_path=.../.env)` 호출로 환경변수 주입
  - 28/28 PASS (navigation 7 + real_estate 9 + finance 4 + automation 4 + map_load 4(작성))
- **completed:** Real Estate 데이터 저장소 재설계 — ChromaDB → SQLite (2026-04-12)
  - `apartment_repository.py` + `transaction_repository.py` 신규 (real_estate.db 통합)
  - `complex_code` FK로 apt_name 불일치 문제 근본 해결
  - `/monitor` API 엔드포인트 SQLite 기반으로 교체
  - `api_client.py` complex_code 지원, `_render_apt_detail_panel` complex_code 우선 조회
  - `geocoder.py` road_address 기반 Kakao 검색으로 지도 마커 개선
  - `scripts/migrate_to_real_estate_db.py` 마이그레이션 스크립트
  - 24/24 PASS (apt_repo 10 + tx_repo 10 + tab_test 4)
- **completed:** Tab1+Tab5 통합 — "아파트 탐색" 허브 완성 (2026-04-12)
  - Tab5(단지 검색) + Tab1(Market Monitor) → "🔍 아파트 탐색" 단일 탭 (탭 5→4)
  - 마스터 필터 → 단지 목록 클릭 → 상세 + 실거래가 UX
  - `_render_apt_detail_panel()` SRP 분리, config.yaml Zero Hardcoding
  - 11 tests passed
- **completed:** Tab5 아파트 마스터 + 실거래가 지도 통합 + 브라우저 버그 수정 (2026-04-11)
  - render_master_map_view + _build_master_popup_html + get_transactions_by_district_codes
  - Tab5 서브탭 (📋 단지 목록 | 🗺️ 지도 뷰), 지연 로드 + 해시 캐시
  - MarkerCluster 적용, st_folium key 추가, 지도 100개 제한
  - BUG-01(districts 미정의), BUG-02(api_key 오타), BUG-03(깜빡임 1차) 수정
  - 23 tests passed
- **pending:** ISSUE-01 지도 깜빡임 근본 해결 (returned_objects=[], @st.fragment 검토)
- **completed:** 아파트 마스터 DB 필드 전면 확장 + 전체 재수집 (2026-04-11)
  - ApartmentMaster 10→26 필드 (API 가용 정보 완전 수집)
  - sido/sigungu/eupmyeondong/ri 필드 추가 (Streamlit cascading 필터)
  - scripts/build_apartment_master.py --rebuild 플래그
  - 수도권 9,275건 완전 재수집 (0 오류)
- **completed:** 아파트 마스터 데이터 활용 고도화 — 1-A + 1-B (2026-04-10)
- **blocked:** 없음

## 다음 작업 로드맵

### 1순위 — E2E 테스트 코드 업데이트
- **목표:** Transaction-First 전환 이후 변경된 Tab1(아파트 탐색) UX에 맞게 E2E 테스트 정비
- **배경:** `test_e2e_real_estate.py`가 `ApartmentMasterRepository` 기반 UI를 테스트하고 있어 `AptMasterRepository` 전환 후 깨질 가능성 있음
- **작업:**
  - 기존 `tests/e2e/test_e2e_real_estate.py` 검토 및 Tab1 시나리오 업데이트
  - apt_master 기반 단지 탐색 흐름 (필터 → 목록 → 상세 패널) E2E 커버
  - apt_master 미구축 시 마이그레이션 안내 화면 테스트
- **선행 조건:** `scripts/migrate_to_transaction_first.py` 실제 DB에 실행 완료

### 2순위 — 1-C. 마스터 DB 주기적 갱신
- **목표:** 신규 단지 등록 시 자동 보완
- **방식:** `build_apartment_master` Job을 월 1회 n8n 스케줄 등록
- **이어받기:** 기존 `build_initial`의 skipped 로직으로 신규 단지만 추가

### 2순위 — Career SOLID 장기 개선
- Processor Protocol 정의 (ISP/DIP 강화)
- CareerAgent 의존성 주입 패턴 적용
- 상세: `docs/features/career_solid_refactor/spec.md`

### 3순위 — Finance LLM Pipeline 통합 (빠른 개선)
- **문제:** `finance/service.py`가 `LLMClient()` 직접 생성 → SemanticCache, TokenLog 혜택 없음
- **개선:** `build_llm_pipeline()` 교체 (1시간 수정, 다른 모듈과 동일 패턴)

### 4순위 — Career 커뮤니티 소스 분류 config화
- **문제:** `service.py`의 `_REDDIT_SOURCES`, `_KOREAN_SOURCES` 등이 하드코딩
- **개선:** `config.yaml` 소스 정의에 `category` 필드 추가

### 5순위 — n8n 워크플로우 실행 결과 피드백 루프
- n8n `GET /executions` 폴링 또는 Error Workflow → Slack 실패 알림
- AutomationService에 `get_execution_history()` 추가
- 에러 리포트 파일: `logs/n8n_errors/error_{workflow_id}_{timestamp}.json`

### 6순위 — Career 스킬갭 트렌드 예측
- 히스토리(`tracker.py`) gap_score 추이 분석 + 목표 달성 예상 시점

### 7순위 — Streamlit 파이프라인 실행 비동기화
- FastAPI Background Task + 상태 polling 엔드포인트
