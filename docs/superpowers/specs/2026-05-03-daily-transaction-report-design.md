# 데일리 실거래 기반 부동산 전략 리포트 — 설계 문서

**작성일:** 2026-05-03  
**대상:** 기존 professional report 파이프라인 대체  
**핵심 패러다임 전환:** "전체 DB → 필터 → 분석" → "최근 3일 실거래 → 주목 단지 선별 → 풀 분석"

---

## 1. 배경 및 목표

기존 리포트는 `apt_master` 전체 DB에서 persona 조건으로 후보를 추린 뒤 분석하는 방식이었다.
이 방식의 문제는 **"오늘 시장에서 무슨 일이 있었는가"** 라는 가장 중요한 질문에 답하지 못한다는 점이다.

새 리포트는 매일 아침 부동산 전략 컨설턴트가 하는 일을 모방한다:
- 최근 3일 실거래를 열어 "어디서 거래가 활발했나, 가격이 움직였나" 확인
- 주목할 단지를 추려 각각 풀 분석
- "오늘 이 시장에서 나는 무엇을 해야 하는가" 전략 제안

---

## 2. 시스템 구조

### 2.1 신규 파일

```
src/modules/real_estate/
  daily_report/
    __init__.py
    models.py                    ← AggregatedTransaction, DailyReportResult
    transaction_aggregator.py    ← 최근 N일 거래 집계 + composite score
    daily_report_orchestrator.py ← 파이프라인 오케스트레이터

src/modules/real_estate/prompts/
  daily_strategy.md              ← LLM 프롬프트

src/api/routers/real_estate.py
  POST /jobs/daily-report/generate   ← 기존 /jobs/professional-report/generate 대체

src/dashboard/main.py
  "📰 데일리 리포트" 탭             ← 기존 리포트 탭 대체
```

### 2.2 재사용 컴포넌트 (변경 없음)

기존 `report_orchestrator.py`의 아래 순수 함수들을 그대로 import해 사용:
- `_enrich_with_geocode()` — road_address → lat/lng 변환 (POI·commute 전 필수)
- `_enrich_with_poi()` — 역세권·학군·마트 (lat/lng 필요)
- `_enrich_with_building()` — 용적률·건폐율·준공연도 (pnu 필요)
- `_enrich_with_commute()` — persona.workplace_station 기준 출퇴근 시간
- `_enrich_with_trend()` — 중장기 시세 추세

---

## 3. 데이터 모델

### AggregatedTransaction

```python
@dataclass
class AggregatedTransaction:
    apt_master_id: int
    apt_name: str
    district_code: str
    sigungu: str
    complex_code: Optional[str]
    recent_tx_count: int        # 최근 N일 거래 건수
    avg_recent_price: float     # 최근 N일 평균 거래가 (만원)
    price_change_pct: float     # 직전 30일 평균 대비 변동률 (%)
    exclusive_area: float       # 가장 많이 거래된 면적 (㎡)
    composite_score: float      # 최종 선별 점수 (0.0 ~ 1.0)
```

### DailyReportResult

```python
@dataclass
class DailyReportResult:
    date: str                          # YYYY-MM-DD
    analysis_period: str               # "2026-05-01 ~ 2026-05-03"
    total_transactions: int            # 분석 기간 전체 거래 수
    top_candidates: List[Dict]         # enrich 완료 단지 목록
    market_summary: str                # LLM 생성 시장 총평
    candidate_insights: List[Dict]     # 단지별 전략 코멘트
    report_markdown: str               # 최종 렌더링 MD
    generated_at: str                  # 생성 시각
```

---

## 4. Composite Score 계산

```
composite_score =
    tx_score (40%)         ← recent_tx_count / max_tx_count (기간 내 최대 대비 정규화)
  + price_signal (30%)     ← min(|price_change_pct| / 10.0, 1.0) — 방향 무관, 변동폭 주목
  + persona_affinity (30%) ← (budget_fit + area_fit + household_fit) / 3
      budget_fit:    avg_recent_price ≤ max_budget → 1.0, 초과 시 선형 감점
      area_fit:      sigungu ∈ persona.interest_areas → 1.0, 미포함 → 0.5
      household_fit: household_count ≥ min_household_count → 1.0, 미달 → 0.0
```

**설계 의도:**
- `price_signal`은 방향 무관 — 급등·급락 모두 "시장이 움직이는 곳"으로 포착
- `persona_affinity`는 필터가 아닌 가중치 — 관심 지역 외 단지도 점수 높으면 포함
- 모든 가중치는 `config.yaml` `daily_report.scoring` 섹션에서 조정 (Zero Hardcoding)

---

## 5. 파이프라인 흐름

```
Step 1. TransactionAggregator.aggregate(days=3, top_k=10)
         → List[AggregatedTransaction] (composite_score 정렬)

Step 2. apt_master_repo.get_by_id()로 각 단지 메타데이터 보완
         (household_count, road_address, pnu 등)

Step 3. 기존 enrich 함수 순서대로 적용
         _enrich_with_geocode()    ← road_address → lat/lng (POI·commute 전 필수)
         _enrich_with_poi()        ← 역세권·학군·마트 (lat/lng 필요)
         _enrich_with_building()   ← 용적률·건폐율·준공연도 (pnu 필요)
         _enrich_with_commute()    ← persona.workplace_station 기준 출퇴근
         _enrich_with_trend()      ← 중장기 시세 추세

Step 4. MacroService에서 최신 거시경제 요약 조회

Step 5. LLM: daily_strategy.md 프롬프트
         입력: 날짜 범위 + 단지별 enrich 결과 + persona 요약 + macro 요약
         출력: 시장 총평 + 단지별 전략 코멘트

Step 6. Markdown 렌더링 → data/daily_reports/daily_YYYY-MM-DD.md 저장

Step 7. SlackSender로 전체 MD 내용 전송
```

---

## 6. LLM 프롬프트 구조 (`daily_strategy.md`)

```markdown
역할: 매일 아침 브리핑을 준비하는 부동산 전략 컨설턴트.
실거래 데이터를 기반으로 오늘의 시장 신호를 읽고, 페르소나 맞춤 전략을 제안한다.

[분석 기간]
{date_range} 실거래 데이터 기준

[페르소나 요약]
예산: {max_budget}억, 직장: {workplace_station}, 선호 면적: {preferred_area}㎡

[거시경제 요약]
{macro_summary}

[주목 단지 {N}개 — composite score 상위]
{candidates_text}
(각 단지: 거래가·변동률·출퇴근·POI·시세추세·건축연도·용적률·세대수)

출력 형식 (반드시 아래 구조 준수):
## 오늘의 시장 신호
(3~5줄, 오늘 시장에서 주목할 패턴 서술)

## 주목 단지 분석
### {순위}. {apt_name} — {score}점
- **거래 동향**: ...
- **단지 특징**: ...
- **전략 제안**: ...
```

---

## 7. API 엔드포인트

### `POST /jobs/daily-report/generate`

기존 `/jobs/professional-report/generate` 대체.

**Request:**
```json
{
  "target_date": "2026-05-03",   // 기본값: 오늘
  "days": 3,                     // 분석 기간 (기본 3일)
  "top_k": 5,                    // 상위 단지 수 (기본 5, 최대 10)
  "force": false                 // 이미 오늘 리포트 있어도 재생성
}
```

**Response:**
```json
{
  "status": "success",
  "date": "2026-05-03",
  "top_k": 5,
  "total_transactions_analyzed": 142,
  "report_path": "data/daily_reports/daily_2026-05-03.md",
  "slack_sent": true
}
```

---

## 8. Streamlit 탭

기존 professional report 탭을 "📰 데일리 리포트" 탭으로 교체.

```
[날짜 선택 드롭다운]  ←  data/daily_reports/ 파일 목록에서 자동 생성
[리포트 본문]         ←  st.markdown()으로 MD 렌더링
[메타 정보]           ←  분석 기간·주목 단지 수·생성 시각
```

---

## 9. n8n 자동화

기존 부동산 뉴스 수집 워크플로우와 동일 패턴으로 추가:

```
Cron: 매일 07:30 KST (실거래 수집 완료 후)
  → POST /jobs/daily-report/generate
  → 응답의 slack_sent 확인
```

---

## 10. 테스트 전략

| 테스트 대상 | 검증 항목 |
|------------|---------|
| `TransactionAggregator` | 최근 N일 필터링, composite score 계산, top_k 반환 |
| `DailyReportOrchestrator` | enrich 함수 호출 순서, LLM 입력 포맷, MD 저장 |
| FastAPI 엔드포인트 | 정상 응답, force 재생성, top_k 범위 검증 |

---

## 11. 대체 범위 (기존 코드 처리)

| 기존 | 처리 |
|------|------|
| `POST /jobs/professional-report/generate` | deprecated 처리 후 새 엔드포인트로 리다이렉트 |
| `report_orchestrator.py` | enrich 순수 함수만 재사용, orchestrator 클래스는 사용 안 함 |
| `data/real_estate_reports/` | 기존 파일 유지, 신규는 `data/daily_reports/`에 저장 |
| Streamlit 기존 리포트 탭 | 새 "📰 데일리 리포트" 탭으로 교체 |
