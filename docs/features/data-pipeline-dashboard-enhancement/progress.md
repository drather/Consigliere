# Progress: 데이터 파이프라인 분리 및 대시보드 고도화

## 상태: 🟡 기획 완료, 구현 대기

---

## Phase 1: 인사이트 리포트 저장 레이어

- [ ] `service.py` — 리포트 생성 후 `data/real_estate/reports/{date}_Report.json` 저장
- [ ] `service.py` — `insight_orchestrator`에서 best_score 반환받아 메타데이터 포함 저장
- [ ] `real_estate.py` (router) — `GET /dashboard/real-estate/reports` 엔드포인트 추가
- [ ] `real_estate.py` (router) — `GET /dashboard/real-estate/reports/{filename}` 엔드포인트 추가
- [ ] `api_client.py` (dashboard) — `get_reports()`, `get_report_detail()` 메서드 추가
- [ ] `views/real_estate.py` — "📋 Report Archive" 서브탭 추가 (목록 + 상세 조회)

---

## Phase 2: 실거래가 대시보드 그리드 고도화

- [ ] `real_estate.py` (router) — `/dashboard/real-estate/monitor` 파라미터에 `date_from`, `date_to` 추가
- [ ] `repository.py` — ChromaDB 조회 시 날짜 범위 필터 지원 추가
- [ ] limit 상한 50건으로 확장
- [ ] `api_client.py` (dashboard) — `get_transactions()` 파라미터 확장
- [ ] `views/real_estate.py` — Market Monitor 탭 UI 개선
  - [ ] 필터 영역 (동코드, 날짜 from/to, 건수 선택)
  - [ ] 그리드 컬럼 구성 (거래일자, 아파트명, 전용면적, 층, 거래가, 건축연도)
  - [ ] 거래가 억원 단위 변환 및 포맷팅
  - [ ] 총 조회 건수 표시

---

## Phase 3: News Insight 탭 고도화

- [ ] `real_estate.py` (router) — `GET /dashboard/real-estate/policy-facts` 엔드포인트 추가
- [ ] `real_estate.py` (router) — `POST /dashboard/real-estate/trigger/fetch-transactions` 추가
- [ ] `real_estate.py` (router) — `POST /dashboard/real-estate/trigger/scrape-news` 추가
- [ ] `api_client.py` (dashboard) — 신규 메서드 추가
- [ ] `views/real_estate.py` — News Insight 탭 서브탭 3개로 분리
  - [ ] 📰 뉴스 리포트 (기존 개선)
  - [ ] 📌 정책 팩트 (ChromaDB 조회 + 검색)
  - [ ] 🔄 데이터 수집 (수동 트리거 버튼)

---

## Phase 4: 인사이트 리포트 파이프라인 분리

- [ ] `service.py` — 당일 ChromaDB 저장 데이터 우선 사용, 없으면 실시간 수집 (fallback)
- [ ] `insight_orchestrator.py` — best_score를 반환값에 포함
- [ ] E2E 테스트: 사전 수집 → 리포트 생성 → 저장 → 대시보드 조회

---

## 최종 검증

- [ ] SOLID 체크리스트 통과
- [ ] pytest 전체 실행
- [ ] Docker 재기동 후 E2E 확인
- [ ] 대시보드 각 탭 동작 확인
