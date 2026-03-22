# 부동산 모듈 종합 버그픽스 & 성능 개선: Progress
**Branch:** `fix/real-estate-comprehensive-review`
**Status:** 진행 중
**Started:** 2026-03-21

---

## Phase 1: Planning
- [x] spec.md 작성 (버그 목록 7개 정의)
- [x] progress.md 초기화

## Phase 2: Implementation

### BugFix
- [x] **T-01** MOLIT resultCode 체크 로직 수정 (`monitor/api_client.py`)
- [x] **T-02** `send_blocks` → `send(..., blocks=)` 수정 (`service.py`)
- [x] **T-03** Synthesizer 프롬프트 예산 하드 제약 강화 (`prompts/insight_parser.md`)
- [x] **T-04** `persona.yaml` interest_areas 추가
- [x] **T-05** GeminiClient generate_json 파싱 강화 (`core/llm.py`)
- [x] **T-06** `insight_validator.md` 삭제 (미사용 파일 정리)
- [x] `calculator.py` DSR/LTV rate 파싱 버그 수정 (stress rate 혼용 문제)
- [x] Calculator 단위 오류 수정, approval threshold 90점으로 상향
- [x] Gemini → `gemini-2.5-flash` 전환, 대시보드 mrkdwn 렌더링 개선
- [x] Gemini API 호출 횟수 6회 → 2회 축소 (per pipeline run)

### Performance — Job1 병렬화 (진행 중, 문제 발생)

- [x] 1차: ThreadPoolExecutor(max_workers=8) 적용 → **OOM** (ChromaDB 병렬 save 시 메모리 폭발)
  - docker events 확인: `container oom` → exitCode=137
- [x] 2차: fetch/save 분리 (병렬 fetch + 직렬 save), max_workers=3 → **429 Rate Limit**
  - MOLIT API 동시 3개 요청 시 Too Many Requests
- [x] 3차: api_client.py 429 재시도 로직 추가 (exponential backoff 1s/2s/4s)
- [ ] **4차 (내일): aiohttp + asyncio.Semaphore 전환** ← 다음 작업
  - OOM 없음 (스레드 없음), rate limit 제어 (Semaphore=2)
  - 3일치만 저장 (deal_date 필터)
  - 1년 이상 ChromaDB 데이터 자동 삭제

### 추가 발견 이슈
- [x] MOLIT API 응답에 `totalCount` 있으나 페이지네이션 미구현 (100건 초과 구 데이터 누락)
  - 3일 필터 도입 시 실질적으로 100건 미만이므로 우선순위 낮음
- [ ] 국토부 API 일일 호출 횟수 초과 → 2026-03-21 저녁 기준 수집 불가 상태
  - 내일 새벽 리셋 후 재시도 필요

## Phase 2.5: SOLID Review
- [ ] SOLID 체크리스트 검토
- [ ] 회귀 테스트 (`pytest`)
- [ ] Docker 재기동 후 E2E 확인 (Job1 aiohttp 전환 후)

## Phase 3: Documentation
- [x] issues.md 작성
- [ ] result.md 작성 (Job1 안정화 완료 후)
- [ ] system_snapshot 업데이트 (필요 시)
- [ ] history.md 업데이트

---

## 📅 Log
- **2026-03-21:** 브랜치 생성, 종합 버그픽스 7건 적용 (T-01 ~ T-06 + 추가 버그)
- **2026-03-21:** gemini-2.5-flash 전환, API 호출 최적화 (6→2회)
- **2026-03-21:** Job1 병렬화 1차 시도 — ThreadPoolExecutor(max_workers=8) → OOM 확인
- **2026-03-21:** Job1 병렬화 2차 — fetch/save 분리, max_workers=3 → 429 확인
- **2026-03-21:** api_client.py 429 재시도 로직 추가
- **2026-03-21:** SOP 누락 문서 일괄 작성 (progress.md, issues.md)
- **2026-03-21:** Job1 aiohttp 전환 + 3일 필터 + 1년 삭제 설계 완료 → 내일 구현 예정
- **2026-03-21:** 국토부 API 일일 호출 횟수 초과로 작업 중단, 커밋 후 내일 재개
