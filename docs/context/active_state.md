# Project Consigliere: Active State
**Last Updated:** 2026-03-21
**Current Active Feature:** 부동산 모듈 종합 버그픽스 & 성능 개선

## 📍 Current Focus
- **Branch:** `fix/real-estate-comprehensive-review`
- **Feature Doc:** `docs/features/real-estate-comprehensive-bugfix/`
- **Status:** 🔧 진행 중 — Phase 2.5 (SOLID Review) 단계

## 💡 Recent Context
- **completed:** 부동산 파이프라인 종합 버그픽스 7건 (BUG-001 ~ BUG-007)
- **completed:** gemini-2.5-flash 전환, API 호출 최적화 (6→2회)
- **completed:** api_client.py 429 재시도 로직 추가 (exponential backoff)
- **blocked:** Job1 병렬화 — OOM(max_workers=8), 429(max_workers=3) 이슈로 불안정
  - ThreadPoolExecutor 방식 한계 확인 → aiohttp + asyncio 전환 설계 완료
- **blocked:** 국토부 API 일일 호출 횟수 초과 → 내일 자정 이후 해소

## 🔜 다음 작업 로드맵

### 1순위 — 내일 (2026-03-22): Job1 aiohttp 전환 (브랜치 계속)
- **브랜치:** `fix/real-estate-comprehensive-review`
- **설계 문서:** `docs/features/real-estate-comprehensive-bugfix/` + `/Users/kks/.claude/plans/zazzy-doodling-kahan.md`
- **수정 파일 5개:** `requirements.txt`, `monitor/service.py`, `models.py`, `repository.py`, `service.py`
- **핵심 변경:**
  - aiohttp + asyncio.Semaphore(2) → OOM/429 근본 해결
  - 3일치만 저장 (deal_date 필터)
  - 1년 이상 ChromaDB 데이터 자동 삭제
- **완료 조건:** OOM·429 없이 71개 구 완주, 3~5분 이내

### 2순위 — Job4 부동산 전략 리포트 고도화
- 현재 리포트 품질 개선 (점수 안정화, 예산 준수, 단지 추천 정확도)
- 페르소나 기반 개인화 강화 (interest_areas 매핑 고도화)
- 거시경제 + 뉴스 + 실거래 데이터 통합 인사이트 품질 향상

### 3순위 — 커리어 Daily Report (신규 모듈)
- 개인화된 커리어 관련 일일 리포트 기능
- 구직 동향, 기술 트렌드, 채용 공고 요약 등 포함 예정
- 설계 필요 (spec 없음)

## ✅ Completed Tasks (Recent)
- [x] **Feature: 데이터 파이프라인 분리 및 대시보드 고도화** <!-- id: 34 -->
    - 4개 독립 Job API 분리 및 `/jobs/real-estate/` 네임스페이스 신설
    - 수도권 전체(71개 지구) 실거래가 자동 수집
    - Market Monitor: 시/구 selectbox, 금액 슬라이더↔숫자 입력 동기화, 페이지네이션
    - Insight 탭: 거시경제 시계열 차트, 뉴스 리포트, 정책 팩트
    - Report Archive: 저장 리포트 목록·상세 뷰어
    - n8n 4개 스케줄 워크플로우 등록 (05:00 실거래가·뉴스, 월1회 거시경제, 06:00 리포트+Slack)
    - ChromaDB 볼륨 경로 버그 수정 (데이터 영속성 확보)
- [x] **Maintenance: Update Real Estate Insight Report Schedule** <!-- id: 31 -->
    - Changed cron expression from `30 8 * * *` to `0 7 * * *` (07:00 KST).
    - Redeployed workflow and restarted Docker containers.
- [x] **BugFix: Resolved n8n Workflow Deployment Duplication & Inactivation** <!-- id: 32 -->
    - Fixed `AutomationService` to support workflow updates (PUT) instead of always creating new ones.
    - Added automatic activation logic to the deployment pipeline.
    - Cleaned up duplicate/inactive workflows from n8n environment.
    - Fixed `Header NoneType` bug in `AutomationService`.
- [x] **Maintenance: Gemini Model Update** <!-- id: 33 -->
    - Updated default Gemini model to `gemini-3.1-flash-lite-preview`.
    - Refactored `GeminiClient` to support `GEMINI_MODEL` environment variable.
    - Updated `.env` and `.env.example` with the new model configuration.
- [x] **Feature: Funding Plan Logic Correction & Logic Guard** <!-- id: 29 -->
    - Implemented LTV-back-calculation constraint to prevent simple budget summation.
    - Added 100-iteration self-reflection loop with scoring and feedback.
    - Integrated `duckduckgo-search` for real-time LTV/DSR policy context.
- [x] **Feature: Spousal Income & First-time Buyer Logic** <!-- id: 30 -->
    - Added `is_first_time_buyer` and `spouse_income` handling in `persona.yaml`.
    - Enforced conservative budget selection between LTV and DSR limits.
    - Corrected date logic for 2026 context.
    - Expanded data collection to 9+ metropolitan districts (10+ txs).
    - Integrated 2026 Financial Policy (Stress DSR Phase 3) check.
    - Resolved Slack Block Kit formatting issues (`invalid_blocks_format`).
