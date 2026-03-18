# Result: 데이터 파이프라인 분리 및 대시보드 고도화

**완료일:** 2026-03-18
**브랜치:** `master` (직접 커밋)
**커밋:** `feat(pipeline): Expand collection coverage to full metro area (수도권 전체)` 외 다수

---

## 달성 목표 요약

기존에 단일 함수에 묶여 있던 실거래가·뉴스·거시경제·리포트 생성 파이프라인을 **4개의 독립 Job**으로 분리하고, 각 Job을 n8n에서 개별 스케줄링 가능하도록 구현했다. 동시에 Streamlit 대시보드를 전면 개편해 데이터 수집·조회·리포트 확인을 하나의 UI에서 처리할 수 있게 했다.

---

## 최종 아키텍처

### API 엔드포인트 (신규 추가)

| Method | Endpoint | 역할 |
|--------|----------|------|
| POST | `/jobs/real-estate/fetch-transactions` | Job 1: 실거래가 수집 (수도권 71개 지구) |
| POST | `/jobs/real-estate/fetch-news` | Job 2: 뉴스 수집·분석 |
| POST | `/jobs/real-estate/fetch-macro` | Job 3: 한국은행 거시경제 수집 |
| POST | `/jobs/real-estate/generate-report` | Job 4: 인사이트 리포트 생성 |
| POST | `/jobs/real-estate/run-pipeline` | 전체 파이프라인 (Job1~4 + Slack) |
| GET  | `/dashboard/real-estate/reports` | 저장된 리포트 목록 |
| GET  | `/dashboard/real-estate/reports/{filename}` | 리포트 상세 |
| GET  | `/dashboard/real-estate/policy-facts` | ChromaDB 정책 팩트 검색 |
| GET  | `/dashboard/real-estate/macro-history` | 거시경제 10개월 시계열 |
| GET  | `/dashboard/real-estate/districts` | 수도권 71개 구/시 목록 |

### n8n 스케줄 워크플로우

| 워크플로우 | Cron | 비고 |
|-----------|------|------|
| `[Consigliere] Job1 실거래가 수집 (수도권 전체)` | `0 5 * * *` | 매일 05:00 |
| `[Consigliere] Job2 뉴스 수집` | `0 5 * * *` | 매일 05:00 |
| `[Consigliere] Job3 거시경제 수집` | `0 5 1 * *` | 매월 1일 05:00 |
| `[Consigliere] Job4 인사이트 리포트 생성` | `0 6 * * *` | 매일 06:00, Slack 전송 포함 |

### 데이터 수집 범위 확장

| 항목 | Before | After |
|------|--------|-------|
| 수집 지구 수 | 9개 (일부 수도권) | 71개 (서울 25구 + 경기 38 + 인천 8) |
| 실거래가 저장 | ChromaDB upsert | ChromaDB upsert (동일, 범위 확장) |

---

## 대시보드 구조

```
🏢 Real Estate Insights
 ├─ 📊 Market Monitor
 │    ├─ 📥 실거래가 수집 expander
 │    │    └─ 시/구 selectbox (71개) + 년월 + 수집 버튼
 │    ├─ 🔍 조회 필터 expander
 │    │    ├─ 시/구 selectbox
 │    │    ├─ 아파트명 부분 검색
 │    │    ├─ 날짜 범위 (from/to)
 │    │    ├─ 금액 범위 슬라이더 ↔ 숫자 입력 동기화 (0~200억)
 │    │    └─ 페이지당 건수 (10/20/30/50)
 │    └─ 결과 그리드 (최대 500건, 페이지네이션)
 │
 ├─ 💡 Insight
 │    ├─ 📈 거시경제
 │    │    ├─ 기준금리·주담대금리 최신값 카드 (delta 표시)
 │    │    └─ 10개월 시계열 선 그래프
 │    ├─ 📰 뉴스 리포트
 │    │    ├─ 📥 뉴스 수집 expander
 │    │    └─ 날짜별 마크다운 리포트 목록 + 상세
 │    └─ 📌 정책 팩트
 │         ├─ 📥 정책 팩트 수집 expander
 │         └─ 키워드 검색 + [날짜][카테고리] 아코디언
 │
 └─ 📋 Report Archive
      ├─ ⚙️ 리포트 생성 expander (거시경제·리포트·파이프라인)
      └─ 리포트 목록 테이블 + 상세 블록 뷰어 (mrkdwn → Markdown 변환)
```

---

## 주요 기술 이슈 및 해결

### 1. ChromaDB 볼륨 경로 불일치 (데이터 휘발)
- **증상:** `docker compose down && up` 후 수집 데이터 전부 소실
- **원인:** `docker-compose.yml`이 `/chroma/chroma`에 마운트했으나 ChromaDB 실제 저장 경로는 `/data`
- **해결:** `./data/chroma_data:/data`로 수정, `chroma.sqlite3` 로컬 영속 저장 확인

### 2. LLM JSON 배열 파싱 실패 (정책 팩트 수집 0건)
- **증상:** 정책 팩트 수집 트리거 후 항상 0건 반환
- **원인:** `ClaudeClient.generate_json()`의 경계 추출이 `{...}` 만 처리, `[...]` 배열 응답 누락
- **해결:** `find('[')` vs `find('{')` 중 먼저 등장하는 타입으로 분기 처리

### 3. ChromaDB `.get()` 범위 필터 미지원
- **증상:** `date_from`/`date_to` where 절에 `$gte`/`$lte` 사용 시 `InvalidArgumentError`
- **원인:** ChromaDB `.get()` API는 `$eq`/`$ne`만 지원
- **해결:** `limit * 10` (최대 500건) fetch 후 Python 레벨 문자열 비교 필터링 (`"YYYY-MM-DD"` 포맷은 사전식 정렬과 일치)

### 4. 리포트 Slack mrkdwn 포맷 가독성
- **증상:** 리포트 뷰어에서 `*굵은글씨*`, `•` 불릿이 그대로 출력됨
- **해결:** `_mrkdwn_to_md()` 변환 함수 추가 (정규식 `*...*` → `**...**`, `•` → `-`)

### 5. n8n 워크플로우 활성화 방법
- **원인:** 생성 시 `active: true` payload 및 `PATCH` 요청 모두 무시됨 (read-only 필드)
- **해결:** `POST /api/v1/workflows/{id}/activate` 별도 호출 필요

---

## 검증 결과

| 테스트 항목 | 결과 |
|------------|------|
| `POST /jobs/real-estate/fetch-transactions` | ✅ 강남구 18건 수집·저장 |
| `POST /jobs/real-estate/fetch-macro` | ✅ 기준금리 2.5% 수집, JSON 저장 |
| `GET /dashboard/real-estate/policy-facts` | ✅ ChromaDB 정책 팩트 3건 반환 |
| `GET /dashboard/real-estate/macro-history` | ✅ 기준금리 10개월 시계열 반환 |
| `GET /dashboard/real-estate/reports` | ✅ 저장된 리포트 목록 반환 |
| `GET /dashboard/real-estate/districts` | ✅ 71개 구/시 목록 반환 |
| Market Monitor 금액 필터 | ✅ 0~200억 슬라이더·숫자 입력 동기화 |
| Market Monitor 페이지네이션 | ✅ 500건 fetch, 페이지 네비게이션 정상 |
| 시/구 selectbox | ✅ 71개 항목 로딩, 코드 변환 정상 |
| Docker 재기동 후 데이터 영속성 | ✅ ChromaDB 볼륨 수정 후 데이터 유지 |
| Report Archive 렌더링 | ✅ mrkdwn → Markdown 변환 정상 |

---

## 변경 파일 목록

| 파일 | 변경 내용 |
|------|----------|
| `src/modules/real_estate/service.py` | Job 메서드 4개 분리, 수도권 전체 수집 지원 |
| `src/modules/real_estate/repository.py` | apt_name·price_min·price_max 필터 추가, limit 500 |
| `src/modules/real_estate/config.yaml` | districts 9→71개 확장 |
| `src/modules/real_estate/macro/bok_service.py` | 시계열 조회 `get_statistic_series()`, `fetch_macro_history()` 추가 |
| `src/api/routers/real_estate.py` | Job/Dashboard/Districts 엔드포인트 추가, limit 500 |
| `src/dashboard/api_client.py` | Job 트리거·거시경제·구목록 메서드 추가 |
| `src/dashboard/views/real_estate.py` | 탭 전면 개편, 슬라이더 동기화, 페이지네이션 |
| `src/core/llm.py` | `generate_json()` 배열/객체 분기 파싱 수정 |
| `docker-compose.yml` | ChromaDB 볼륨 경로 수정 |
