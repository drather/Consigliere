# Project Consigliere: Active State
**Last Updated:** 2026-04-11
**Current Active Feature:** —

## 현재 포커스
- **Branch:** `master`
- **Status:** ✅ apt_master_utilization 완료 — master 머지 완료

## 최근 완료 작업
- **completed:** 아파트 마스터 DB 필드 전면 확장 + 전체 재수집 (2026-04-11)
  - ApartmentMaster 10→26 필드 (API 가용 정보 완전 수집)
  - sido/sigungu/eupmyeondong/ri 필드 추가 (Streamlit cascading 필터)
  - scripts/build_apartment_master.py --rebuild 플래그
  - 수도권 9,275건 완전 재수집 (0 오류)
- **completed:** 아파트 마스터 데이터 활용 고도화 — 1-A + 1-B (2026-04-10)
  - BugFix: `_enrich_transactions()` early return → household_count/constructor 항상 부착
  - `_score_liquidity()` 이제 실제 세대수 기반 동작
  - Streamlit `🏗️ 단지 검색` 탭 (시도/시군구/세대수/건설사/준공연도 필터)
  - 신규 테스트 29개, 전체 81 passed
- **completed:** LLM Filter Chain (2026-04-02)
- **completed:** LLM Harness Engineering (2026-03-30)
- **blocked:** 없음

## 다음 작업 로드맵

### 1순위 — 1-C. 마스터 DB 주기적 갱신
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
