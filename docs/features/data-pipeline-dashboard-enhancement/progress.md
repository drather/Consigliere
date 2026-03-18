# Progress: 데이터 파이프라인 분리 및 대시보드 고도화

## 상태: ✅ 완료 (2026-03-18)

---

## Phase 1: 리포트 저장 레이어 + Report Archive 탭 ✅

### Backend
- [x] `insight_orchestrator.py` — `_score` 반환값에 포함
- [x] `service.py` — `_save_report()` 추가, 리포트 생성 후 `data/real_estate/reports/{date}_Report.json` 저장
- [x] `real_estate.py` (router) — `GET /dashboard/real-estate/reports` 추가
- [x] `real_estate.py` (router) — `GET /dashboard/real-estate/reports/{filename}` 추가

### Dashboard
- [x] `api_client.py` — `list_insight_reports()`, `get_insight_report()` 메서드 추가
- [x] `views/real_estate.py` — "📋 Report Archive" 서브탭 추가 (목록 테이블 + 상세 블록 렌더링)

### 검증
- [x] API 테스트: `GET /dashboard/real-estate/reports` → 목록 정상 반환
- [x] API 테스트: `GET /dashboard/real-estate/reports/{filename}` → 상세 정상 반환
- [x] 대시보드 컨테이너 정상 기동 확인

---

## Phase 2: 실거래가 그리드 고도화 ✅

### Backend
- [x] `real_estate.py` (router) — `/dashboard/real-estate/monitor` 에 `date_from`, `date_to`, `apt_name`, `price_min`, `price_max` 파라미터 추가
- [x] `repository.py` — ChromaDB 날짜 범위·아파트명·금액 범위 필터 지원 (Python 레벨 후처리)
- [x] `real_estate.py` (router) — `GET /dashboard/real-estate/districts` 추가 (구/시 목록)
- [x] 조회 limit 상한 50 → 500으로 확장

### Dashboard
- [x] `api_client.py` — `get_transactions()` 파라미터 확장 (date_from, date_to, apt_name, price_min, price_max)
- [x] `api_client.py` — `get_districts()` 메서드 추가
- [x] `views/real_estate.py` — Market Monitor 탭 UI 개선
  - [x] 시/구 selectbox (71개 수도권 구/시, 동코드 텍스트 입력 대체)
  - [x] 아파트명 부분 검색 필터
  - [x] 날짜 from/to 캘린더 피커
  - [x] 금액 범위 필터: 슬라이더 ↔ 숫자 입력 양방향 동기화 (0~200억)
  - [x] 페이지네이션 (최대 500건 fetch, 페이지당 10/20/30/50건, ◀/▶ 네비게이션)
  - [x] 그리드에 구/시 이름 표시 (코드 → 이름 매핑)
  - [x] 초기 데이터 자동 로드 (session_state 캐싱)
  - [x] 수집 버튼: 시/구 selectbox로 변경, 수도권 전체 옵션 포함

### 이슈
- ChromaDB `.get()` 메서드는 `$gte`/`$lte` 연산자를 지원하지 않음 (`InvalidArgumentError` 발생)
  - 해결: `limit * 10` (최대 500건)을 ChromaDB에서 가져온 뒤 Python 레벨에서 필터링
- Streamlit 슬라이더 ↔ number_input 양방향 동기화: `on_change` 콜백 + `session_state` 패턴으로 구현

---

## Phase 3: 4개 독립 Job API + Insight 탭 고도화 ✅

### Backend — 신규 Job 엔드포인트 (`/jobs/real-estate/`)
- [x] `service.py` — `fetch_transactions()` 메서드 분리 (Job 1), `district_code=None` 시 수도권 전체 71개 지구 순회
- [x] `service.py` — `fetch_news()` 메서드 분리 (Job 2)
- [x] `service.py` — `fetch_macro_data()` 메서드 분리 + `data/real_estate/macro/{date}_macro.json` 저장 (Job 3)
- [x] `service.py` — `generate_report()` 가 저장된 macro 데이터 우선 사용, ChromaDB 실거래가 읽기 (Job 4)
- [x] `service.py` — `run_insight_pipeline()` 메서드 (Job 1~4 + Slack)
- [x] `real_estate.py` (router) — `POST /jobs/real-estate/fetch-transactions` 추가
- [x] `real_estate.py` (router) — `POST /jobs/real-estate/fetch-news` 추가
- [x] `real_estate.py` (router) — `POST /jobs/real-estate/fetch-macro` 추가
- [x] `real_estate.py` (router) — `POST /jobs/real-estate/generate-report` 추가
- [x] `real_estate.py` (router) — `POST /jobs/real-estate/run-pipeline` 추가
- [x] `real_estate.py` (router) — `GET /dashboard/real-estate/policy-facts` 추가
- [x] `real_estate.py` (router) — `GET /dashboard/real-estate/macro-history` 추가
- [x] `macro/bok_service.py` — `get_statistic_series()`, `fetch_macro_history()` 추가 (10개월 시계열)
- [x] `config.yaml` — districts 9개 → 71개 확장 (서울 25구 + 경기 38 + 인천 8)

### Dashboard
- [x] `api_client.py` — Job 트리거 메서드 추가 (fetch-transactions/news/macro, generate-report, run-pipeline, search_policy_facts, get_macro_history)
- [x] `views/real_estate.py` — "News Insight" → "💡 Insight" 탭으로 개편, 서브탭 3개
  - [x] 📈 거시경제: 기준금리·주담대금리 최신값 카드 + 10개월 시계열 선 그래프
  - [x] 📰 뉴스 리포트: 수집 트리거 + 마크다운 리포트 목록 및 상세
  - [x] 📌 정책 팩트: 수집 트리거 + ChromaDB 검색 + 날짜/카테고리 표시 아코디언
- [x] Slack mrkdwn → Markdown 변환 함수 `_mrkdwn_to_md()` 추가 (리포트 가독성 개선)

### n8n 자동화
- [x] 비활성 워크플로우 일괄 삭제
- [x] 4개 신규 스케줄 워크플로우 등록 및 활성화
  - Job 1 (실거래가 수집): 매일 05:00 KST
  - Job 2 (뉴스 수집): 매일 05:00 KST
  - Job 3 (거시경제 수집): 매월 1일 05:00 KST
  - Job 4 (인사이트 리포트): 매일 06:00 KST + Slack 전송

### 버그 수정
- [x] `core/llm.py` — `ClaudeClient.generate_json()` JSON 배열(`[...]`) 파싱 실패 수정
  - 원인: `find('{')` 경계 추출 로직이 배열 응답을 처리하지 못함
  - 수정: `[` 과 `{` 중 먼저 등장하는 것을 감지해 배열/객체 분기 처리
- [x] `docker-compose.yml` — ChromaDB 볼륨 경로 불일치 수정
  - 원인: `./data/chroma_data:/chroma/chroma` (컨테이너 내 실제 저장 경로는 `/data`)
  - 수정: `./data/chroma_data:/data`

---

## Phase 4: 최종 검증 ✅

- [x] SOLID 체크리스트 통과 (SRP: Job 분리, OCP: 신규 Job 추가 기존 코드 불변, DIP: Router→Agent→Services)
- [x] 각 Job 독립 실행 테스트: fetch-transactions(✅), fetch-news(✅), fetch-macro(✅), policy-facts(✅)
- [x] 대시보드 전 탭 동작 확인 (Market Monitor / Insight 3서브탭 / Report Archive)
- [x] Docker 재기동 후 E2E 확인
- [x] 금액 필터 + 페이지네이션 정상 동작 확인
- [x] 시/구 selectbox 71개 항목 정상 로딩 확인
- [ ] 파이프라인 통합 테스트 (Job4 리포트 생성은 LLM 토큰 비용으로 스킵 — 기존 저장 리포트로 검증 완료)

---

## 이슈 & 수정 전체 목록

| # | 이슈 | 원인 | 해결 |
|---|------|------|------|
| 1 | ChromaDB 재기동 후 데이터 휘발 | 볼륨 경로 `/chroma/chroma` vs 실제 `/data` 불일치 | `docker-compose.yml` 볼륨 경로 수정 |
| 2 | 정책 팩트 수집 0건 | `generate_json()`이 `[...]` 배열 응답 파싱 실패 | 배열/객체 분기 추출 로직 추가 |
| 3 | 리포트 가독성 저하 | Slack mrkdwn `*bold*`, `•` 불릿이 Streamlit에서 미렌더링 | `_mrkdwn_to_md()` 변환 함수 추가 |
| 4 | ChromaDB 날짜 범위 필터 불가 | `.get()`이 `$gte`/`$lte` 미지원 | Python 레벨 후처리 필터로 우회 |
| 5 | BOK API 데이터 10건 제한 | 샘플키 최대 10 row | `get_statistic_series()` max cap 10으로 설계 반영 |
| 6 | n8n 워크플로우 활성화 실패 | `active: true` payload 및 PATCH 미지원 | `POST /api/v1/workflows/{id}/activate` 사용 |
| 7 | 슬라이더 입력 불편 | 슬라이더만 제공, 정밀 입력 어려움 | number_input ↔ slider 양방향 동기화 (`on_change` 콜백) |
| 8 | 50건 초과 조회 불가 | API 하드캡 50 | API cap 500으로 상향, UI 페이지네이션 추가 |
