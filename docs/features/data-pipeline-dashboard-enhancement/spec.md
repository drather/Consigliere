# Spec: 데이터 파이프라인 분리 및 대시보드 고도화

## 개요
- **작업 일자:** 2026-03-18 ~
- **브랜치:** `feature/data-pipeline-dashboard-enhancement`
- **참조:** `docs/master_plan.md`

---

## 핵심 설계 원칙

현재 `generate_insight_report()` 는 아래 4가지를 하나의 함수 안에서 순차 실행한다:

```
실거래가 수집 → 뉴스/정책 수집 → 금융/거시경제 수집 → LLM 리포트 생성 → Slack 전송
```

이를 **4개의 독립 Job** + **1개의 파이프라인 Job**으로 분리한다.

```
┌─────────────────────────────────────────────────────────┐
│                    독립 Job (각각 단독 실행 가능)           │
│                                                         │
│  Job 1: fetch_transactions()                            │
│    MOLIT API → 파싱 → ChromaDB (real_estate_transactions)│
│                                                         │
│  Job 2: fetch_news()                                    │
│    Naver API + AdvancedScraper                          │
│    → 마크다운 파일 (data/real_estate/news/)              │
│    → ChromaDB (policy_knowledge)                        │
│                                                         │
│  Job 3: fetch_macro_data()                              │
│    한국은행 API + DuckDuckGo 정책 검색                    │
│    → JSON 파일 (data/real_estate/macro/)                 │
│                                                         │
│  Job 4: generate_report()                               │
│    저장된 데이터(Job1~3 결과)를 읽어서 LLM 리포트 생성     │
│    → JSON 파일 (data/real_estate/reports/)               │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                    파이프라인 Job                         │
│                                                         │
│  run_insight_pipeline()                                 │
│    = Job1 → Job2 → Job3 → Job4 → POST /notify/slack     │
│    (= 현재의 부동산 인사이트 리포트 기능)                   │
└─────────────────────────────────────────────────────────┘
```

---

## 배경

### 현재 문제점
1. 4가지 수집 작업이 결합되어 있어, 하나라도 실패하면 전체 실패
2. 이미 수집된 데이터가 있어도 매번 재수집 (비효율, 토큰 낭비)
3. 수집 결과를 대시보드에서 독립적으로 조회 불가
4. 각 Job을 개별 스케줄링 불가 (예: 실거래가는 1일 1회, 뉴스는 2회)
5. 생성된 리포트가 Slack 전송 후 영속적으로 저장되지 않음

### 기대 효과
- 각 Job을 n8n에서 개별 스케줄 등록 가능
- Job 4 (리포트 생성)는 이미 저장된 데이터를 읽어 빠르게 실행 (LLM 비용 절감)
- 대시보드에서 각 데이터를 독립 조회 가능
- 실패 격리: 뉴스 수집 실패가 리포트 생성에 영향 없음 (저장 데이터 fallback)

---

## 구현 상세

### Job 1: fetch_transactions (실거래가 수집)

**API 엔드포인트 (신규):**
```
POST /jobs/real-estate/fetch-transactions
  Body: { "district_codes": ["11680", "41135"], "year_month": "202603" }
  Response: { "status": "ok", "saved_count": 42 }
```

**내부 로직:**
- `TransactionMonitorService.get_daily_transactions()` 호출 (기존 유지)
- ChromaDB `real_estate_transactions` 컬렉션에 upsert
- 저장 메타데이터에 `fetched_at` 타임스탬프 추가

---

### Job 2: fetch_news (뉴스/정책 수집)

**API 엔드포인트 (신규):**
```
POST /jobs/real-estate/fetch-news
  Body: {} (옵션: keywords)
  Response: { "status": "ok", "news_saved": "2026-03-18_News.md", "facts_indexed": 12 }
```

**내부 로직:**
- 기존 `NewsService.generate_daily_report()` 실행 → 마크다운 저장
- 기존 `AdvancedScraper.run_daily_scraping()` 실행 → ChromaDB 저장
- 두 작업을 하나의 Job으로 통합

---

### Job 3: fetch_macro_data (금융/거시경제 수집)

**API 엔드포인트 (신규):**
```
POST /jobs/real-estate/fetch-macro
  Body: {}
  Response: { "status": "ok", "saved_at": "data/real_estate/macro/2026-03-18_Macro.json" }
```

**내부 로직:**
- 기존 `MacroService.fetch_latest_macro_data()` 실행
- 기존 `fetch_latest_financial_policies()` 실행 (DuckDuckGo 정책 검색)
- 결과를 `data/real_estate/macro/{YYYY-MM-DD}_Macro.json` 으로 저장
- `MacroDataRepository` 신규 생성 (저장/로딩 담당)

---

### Job 4: generate_report (리포트 생성)

**API 엔드포인트 (신규):**
```
POST /jobs/real-estate/generate-report
  Body: { "target_date": "2026-03-18" }  (생략 시 오늘)
  Response: { "status": "ok", "report_file": "2026-03-18_Report.json", "score": 82 }
```

**내부 로직:**
- ChromaDB에서 `target_date`의 실거래 데이터 로딩 (Job 1 결과)
- 파일에서 당일 뉴스 리포트 로딩 (Job 2 결과)
- 파일에서 당일 거시경제 데이터 로딩 (Job 3 결과)
- 없으면 실시간 수집으로 fallback (기존 로직)
- `InsightOrchestrator.generate_strategy()` 실행
- 결과를 `data/real_estate/reports/{YYYY-MM-DD}_Report.json` 으로 저장

---

### 파이프라인 Job: run_insight_pipeline

**API 엔드포인트 (신규):**
```
POST /jobs/real-estate/run-pipeline
  Body: { "target_date": "2026-03-18" }
  Response: { "status": "ok", "report_file": "...", "slack_sent": true }
```

**내부 로직 (순서):**
```python
1. fetch_transactions(district_codes, year_month)
2. fetch_news()
3. fetch_macro_data()
4. generate_report(target_date)
5. POST /notify/slack  (생성된 리포트 blocks 전송)
```

**기존 `GET /agent/real_estate/insight_report`는 이 파이프라인으로 위임:**
- n8n 기존 워크플로우 호환 유지를 위해 기존 엔드포인트는 내부적으로 `run_insight_pipeline()` 호출

---

## 대시보드 변경

### Real Estate 탭 서브탭 구성 (변경 후)

```
🏢 Real Estate
  ├─ 📊 Market Monitor     (실거래가 그리드 - Phase 2)
  ├─ 📰 News Insight        (뉴스/정책 - Phase 3)
  └─ 📋 Report Archive      (생성된 리포트 목록/상세 - Phase 1)
```

### Market Monitor 개선 (Phase 2)
- 필터: 동코드, 날짜 범위(from/to), 건수(최대 50)
- 그리드 컬럼: 거래일자 | 아파트명 | 전용면적㎡ | 층 | 거래가(억) | 건축연도 | 동코드
- 컬럼 정렬 가능

### News Insight 개선 (Phase 3)
서브탭 3개로 분리:
- `📰 뉴스 리포트` — 저장된 마크다운 리포트 목록 및 상세
- `📌 정책 팩트` — ChromaDB `policy_knowledge` 검색 및 목록
- `🔄 데이터 수집` — Job 1~3 수동 트리거 버튼 및 실행 상태

### Report Archive (Phase 1, 신규)
- 저장된 리포트 목록 (날짜, score, 실거래 건수)
- 선택한 리포트 상세 내용 (Slack Block Kit → 마크다운 렌더링)

---

## 신규 API 라우터 설계

기존 `/agent/real_estate/` 와 `/dashboard/real-estate/` 외에 `/jobs/real-estate/` 네임스페이스 신규 추가.

| Method | Endpoint | 역할 |
|---|---|---|
| POST | `/jobs/real-estate/fetch-transactions` | Job 1 |
| POST | `/jobs/real-estate/fetch-news` | Job 2 |
| POST | `/jobs/real-estate/fetch-macro` | Job 3 |
| POST | `/jobs/real-estate/generate-report` | Job 4 |
| POST | `/jobs/real-estate/run-pipeline` | 파이프라인 (Job 1~4 + Slack) |
| GET | `/dashboard/real-estate/reports` | 저장된 리포트 목록 |
| GET | `/dashboard/real-estate/reports/{filename}` | 리포트 상세 |
| GET | `/dashboard/real-estate/policy-facts` | ChromaDB 정책 팩트 조회 |

---

## 관련 파일 변경 목록

| 파일 | 변경 유형 | 내용 |
|---|---|---|
| `src/api/routers/real_estate.py` | 수정 | 신규 엔드포인트 추가 |
| `src/modules/real_estate/service.py` | 수정 | 4개 Job 메서드 분리 |
| `src/modules/real_estate/macro/bok_service.py` | 수정 | 수집 결과 파일 저장 추가 |
| `src/core/policy_fetcher.py` | 수정 | 수집 결과 파일 저장 추가 |
| `src/dashboard/api_client.py` | 수정 | 신규 API 메서드 추가 |
| `src/dashboard/views/real_estate.py` | 수정 | 탭 구조 개편 및 UI 개선 |

---

## Zero Hardcoding 점검

- 저장 경로: `LOCAL_STORAGE_PATH` 환경변수 활용
- district_codes 기본값: `config.yaml`의 `districts` 설정 사용
- Job 실행 시 날짜 기본값: 실행 당일 (`date.today()`)
