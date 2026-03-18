# Spec: 데이터 파이프라인 분리 및 대시보드 고도화

## 개요
- **작업 일자:** 2026-03-18 ~
- **브랜치:** `feature/data-pipeline-dashboard-enhancement`
- **참조:** `docs/master_plan.md`

---

## 배경 및 목표

### 현재 문제점
현재 인사이트 리포트는 단일 API 호출 한 번에 아래를 모두 수행한다:
```
실거래가 수집 → 뉴스/정책 수집 → LLM 분석 → 리포트 생성 → Slack 전송
```
이로 인해:
- 각 데이터를 독립적으로 조회·저장·재사용할 수 없음
- 리포트 결과가 Slack 전송 후 사라짐 (영속적 저장 없음)
- 대시보드의 Market Monitor는 단순 테이블로 필터링·정렬 기능 부족
- News Insights 탭은 마크다운 파일 목록만 표시하는 수준

### 목표
각 데이터 파이프라인을 독립적으로 분리하여 **수집 → 저장 → 조회**가 각각 가능하도록 하고, 대시보드에서 통합적으로 확인할 수 있는 구조로 고도화한다.

```
[수집 단계] (독립 스케줄링 가능)
  실거래가 수집 (MOLIT API) ─────→ ChromaDB (real_estate_transactions)
  뉴스/정책 수집 (Naver API) ────→ 파일시스템 + ChromaDB (policy_knowledge)
  리포트 생성 (LLM) ─────────────→ 파일시스템 (data/real_estate/reports/)

[조회 단계] (대시보드)
  Market Monitor  ← ChromaDB 조회 (50건, 날짜·동코드 필터)
  News Insight    ← 파일 + ChromaDB 정책 팩트 조회
  Report Archive  ← 저장된 리포트 목록·상세 조회
```

---

## 아키텍처 변경 계획

### Phase 1: 인사이트 리포트 저장 레이어 추가
생성된 리포트를 `data/real_estate/reports/` 에 JSON으로 저장하고, 대시보드에서 목록·상세 조회 가능하게 한다.

**변경 파일:**
- `src/modules/real_estate/service.py` — 리포트 생성 후 파일 저장 로직 추가
- `src/api/routers/real_estate.py` — 리포트 조회 엔드포인트 2개 추가
- `src/dashboard/views/real_estate.py` — "📋 Report Archive" 서브탭 추가

**신규 엔드포인트:**
```
GET /dashboard/real-estate/reports
  → 저장된 리포트 목록 (날짜, 파일명)

GET /dashboard/real-estate/reports/{filename}
  → 리포트 상세 내용 (blocks JSON)
```

---

### Phase 2: 실거래가 대시보드 그리드 고도화
Market Monitor를 최대 50건, 날짜·동코드 필터 지원 그리드로 개선한다.

**변경 파일:**
- `src/api/routers/real_estate.py` — `/dashboard/real-estate/monitor` 파라미터 확장
- `src/dashboard/views/real_estate.py` — Market Monitor 탭 UI 개선

**API 파라미터 확장:**
```
GET /dashboard/real-estate/monitor
  기존: district_code (str), limit (int)
  추가: date_from (str, YYYY-MM-DD), date_to (str, YYYY-MM-DD)
  limit 상한: 10 → 50
```

**대시보드 UI 변경:**
- 필터 영역: 동코드, 날짜 범위(from/to), 최대 건수(10·20·30·50)
- 그리드 컬럼: 거래일자, 아파트명, 전용면적(㎡), 층, 거래가(억), 건축연도, 동코드
- 컬럼 정렬 가능 (Streamlit `st.dataframe` sort 활용)
- 총 조회 건수 표시

---

### Phase 3: News Insight 탭 고도화
실거래가 수집, 뉴스 수집을 각각 별도 트리거로 실행 가능하게 하고, 수집된 정책 팩트(ChromaDB)도 함께 표시한다.

**변경 파일:**
- `src/api/routers/real_estate.py` — 정책 팩트 목록 조회 엔드포인트 추가
- `src/dashboard/views/real_estate.py` — News Insight 탭 UI 고도화

**신규 엔드포인트:**
```
GET /dashboard/real-estate/policy-facts
  params: query (str), limit (int, max 20)
  → ChromaDB policy_knowledge 검색 결과

POST /dashboard/real-estate/trigger/fetch-transactions
  params: district_codes (List[str]), year_month (str)
  → 실거래가 수집 실행 (비동기)

POST /dashboard/real-estate/trigger/scrape-news
  → 뉴스/정책 스크래핑 실행 (비동기)
```

**대시보드 UI 변경:**
- 서브탭 구성:
  - `📰 뉴스 리포트` — 기존 마크다운 리포트 목록·상세 (개선)
  - `📌 정책 팩트` — ChromaDB policy_knowledge 조회 및 검색
  - `🔄 데이터 수집` — 실거래가/뉴스 수동 트리거 버튼

---

### Phase 4: 인사이트 리포트 파이프라인 분리
`generate_insight_report()` 가 이미 저장된 데이터를 기반으로 동작하도록 리팩토링한다.

**변경 파일:**
- `src/modules/real_estate/service.py`

**변경 내용:**
- 현재: 리포트 생성 시 실시간으로 MOLIT API, 뉴스 API 직접 호출
- 변경: ChromaDB에 저장된 당일 실거래 데이터를 우선 사용, 없으면 실시간 수집 (fallback)
- 리포트 생성 후 `data/real_estate/reports/{YYYY-MM-DD}_Report.json` 으로 저장

---

## 데이터 모델

### ReportSummary (신규)
```python
class ReportSummary(BaseModel):
    date: str           # "YYYY-MM-DD"
    filename: str       # "2026-03-18_Report.json"
    score: int          # Validator 승인 점수
    tx_count: int       # 사용된 실거래 건수
    created_at: str     # 생성 시각
```

### TransactionFilter (신규)
```python
class TransactionFilter(BaseModel):
    district_code: Optional[str] = None
    date_from: Optional[str] = None  # "YYYY-MM-DD"
    date_to: Optional[str] = None    # "YYYY-MM-DD"
    limit: int = 20                  # max 50
```

---

## 구현 순서 (수행 계획)

| Phase | 내용 | 예상 범위 |
|---|---|---|
| Phase 1 | 리포트 저장 레이어 + 대시보드 Report Archive 탭 | 소 |
| Phase 2 | 실거래가 그리드 고도화 (필터, 50건, 정렬) | 소~중 |
| Phase 3 | News Insight 탭 고도화 (정책팩트, 트리거) | 중 |
| Phase 4 | 인사이트 리포트 파이프라인 분리 (저장 데이터 우선 사용) | 중 |

---

## SOLID 원칙 준수 계획

- **SRP:** 각 데이터 타입(거래, 뉴스, 리포트)별로 Repository 메서드를 독립적으로 유지
- **OCP:** 신규 엔드포인트는 기존 라우터 수정 없이 추가
- **DIP:** 대시보드는 API Client(`DashboardClient`)를 통해서만 백엔드에 의존

---

## Zero Hardcoding 점검

- 리포트 저장 경로: `config.yaml` 또는 `.env`의 `LOCAL_STORAGE_PATH` 활용
- 필터 기본값(limit=20, max=50): `config.yaml`에서 관리
