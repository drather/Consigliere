# Progress: 데이터 파이프라인 분리 및 대시보드 고도화

## 상태: 🟡 기획 완료, 구현 대기

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
- [x] `real_estate.py` (router) — `/dashboard/real-estate/monitor` 에 `date_from`, `date_to` 파라미터 추가
- [x] `repository.py` — ChromaDB 날짜 범위 필터 지원 (Python 레벨 후처리, ChromaDB `.get()` `$gte`/`$lte` 미지원으로 인해)
- [x] limit 상한 50건으로 확장

### Dashboard
- [x] `api_client.py` — `get_transactions()` 파라미터 확장 (date_from, date_to, limit)
- [x] `views/real_estate.py` — Market Monitor 탭 UI 개선
  - [x] 필터 영역 (동코드, 날짜 from/to, 건수 10·20·30·50)
  - [x] 그리드 컬럼 (거래일자, 아파트명, 전용면적, 층, 거래가(억), 건축연도, 동코드)
  - [x] 총 조회 건수 표시

### 검증
- [x] API 테스트: `GET /dashboard/real-estate/monitor?date_from=2026-01-01&date_to=2026-03-18&limit=10` → 정상 반환
- [x] API 테스트: `GET /dashboard/real-estate/monitor?district_code=11680&limit=5` → 5건 정상 반환
- [x] 대시보드 컨테이너 정상 기동 확인

### 이슈
- ChromaDB `.get()` 메서드는 `$gte`/`$lte` 연산자를 지원하지 않음 (`InvalidArgumentError` 발생)
- 해결: `limit * 10` (최대 500건)을 ChromaDB에서 가져온 뒤 Python 레벨에서 날짜 문자열 비교로 필터링
- `"YYYY-MM-DD"` 포맷이 사전식 정렬과 일치하므로 올바른 날짜 범위 필터링 가능

---

## Phase 3: 4개 독립 Job API + News Insight 탭 고도화 ✅

### Backend — 신규 Job 엔드포인트 (`/jobs/real-estate/`)
- [x] `service.py` — `fetch_transactions()` 메서드 분리 (Job 1)
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

### Dashboard
- [x] `api_client.py` — Job 트리거 메서드 6개 추가 (fetch-transactions/news/macro, generate-report, run-pipeline, search_policy_facts)
- [x] `views/real_estate.py` — News Insight 탭 서브탭 3개로 분리
  - [x] 📰 뉴스 리포트 (마크다운 리포트 목록 + 상세)
  - [x] 📌 정책 팩트 (ChromaDB 검색 + 아코디언 목록)
  - [x] 🔄 데이터 수집 (Job 1~4 개별 버튼 + 전체 파이프라인 트리거)

### 검증
- [x] `GET /dashboard/real-estate/policy-facts?query=부동산` → 3건 정상 반환
- [x] `POST /jobs/real-estate/fetch-macro` → 기준금리 2.5% 수집 + JSON 저장
- [x] `POST /jobs/real-estate/fetch-transactions` → 18건 수집, 18건 저장

---

## Phase 4: 최종 검증

- [ ] SOLID 체크리스트 통과
- [ ] 각 Job 독립 실행 테스트 (API 직접 호출)
- [ ] 파이프라인 Job 통합 테스트 (E2E → Slack)
- [ ] 대시보드 각 탭 동작 확인
- [ ] Docker 재기동 후 E2E 확인
