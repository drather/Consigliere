# 설계 문서: 부동산 리포트 품질 업그레이드

**작성일:** 2026-05-25  
**범위:** Job4 리포트 생성 파이프라인 전환 + 비교 분석·수익 구조·공급 리스크 3개 신규 모듈  
**브랜치 제안:** `feature/report-quality-upgrade`

---

## 1. 배경 및 목표

### 현재 문제
- Job4가 구형 `InsightOrchestrator`를 사용 중 — 데이터 없으면 전 항목 50점(중립) 반환
- 비교 기준 없음: 단지가 비싼지 저렴한지 판단 불가
- 전세/공급 데이터 미수집: 투자 수익 구조 및 공급 리스크 분석 불가
- 뉴스와 단지 분석이 분리되어 호재/악재가 리포트에 미반영

### 목표
전문 부동산 전략가 수준의 단지별 분석 리포트 생성:
1. **구 평균 + 유사 단지 ㎡당 가격 비교** — 상대 가치 위치 파악
2. **전세가율 + 갭투자 비용 + 월 보유비용** — 투자 수익 구조 계산
3. **청약홈 입주 예정 물량 + 뉴스 호재/악재 태깅** — 공급·이벤트 리스크

---

## 2. 아키텍처 결정: Option 2 — 완전 전환 + 3개 모듈 동시 추가

### 이유
- `DailyReportOrchestrator`는 이미 구현 완료(649 tests PASS) — 교체 적기
- 새 `report_formatter`가 SVG 차트·입지 현황·LLM verdict 등 훨씬 풍부한 출력 지원
- 3개 모듈을 enrich pipeline 마지막에 추가하는 구조라 기존 코드 변경 최소화
- LLM 프롬프트(daily_strategy.md)를 새 데이터와 함께 한 번만 수정

### 버리는 것
- `InsightOrchestrator` — Job4 연결 해제 (코드 삭제 아님, 레거시 유지)
- `ScoringEngine` — 이미 삭제 완료 (location-scoring-redesign에서)

---

## 3. 파이프라인 변경

### Before (현재 Job4)
```
거래 집계 → horea_validator(LLM) → ScoringEngine(중립 50점) → report_synthesizer(LLM) → Slack Blocks JSON
```

### After (신규 Job4)
```
TransactionAggregator
  → Enrich: Geocode → POI → Building → Commute → School → Trend
  → Enrich NEW: ComparativeAnalyzer → YieldCalculator → SupplyRiskAnalyzer
  → LocationScorer (실거주/투자 이중 점수)
  → LLM: daily_strategy (신규 데이터 포함)
  → report_formatter → Markdown + Slack
```

### DailyReportOrchestrator 연결 추가 (3줄)
```python
# Step 3. Enrich pipeline 마지막에 추가
candidates = _enrich_with_comparative(candidates, self._comp_analyzer)
candidates = _enrich_with_yield(candidates, self._yield_calc)
candidates = _enrich_with_supply(candidates, self._supply_analyzer)
```

---

## 4. 신규 데이터 수집

### 4-A. Job: 전세 거래 수집
- **API:** 국토부 실거래가 전월세 API (`getRTMSDataSvcAptRent`)
- **스케줄:** n8n, 월 1회 (매매 Job과 동일 패턴)
- **엔드포인트:** `POST /jobs/jeonse/collect`
- **저장:** `real_estate.db` → `jeonse_transactions` 테이블

#### 테이블 스키마: `jeonse_transactions`
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER PK | auto |
| complex_code | TEXT | apt_master FK (nullable) |
| apt_name | TEXT | 아파트명 |
| district_code | TEXT | 법정동 코드 |
| deal_date | TEXT | 계약일 (YYYY-MM-DD) |
| exclusive_area | REAL | 전용면적(㎡) |
| deposit | INTEGER | 보증금(만원) |
| monthly_rent | INTEGER | 월세(만원), 전세=0 |
| contract_type | TEXT | 'jeonse' \| 'monthly' |
| floor | INTEGER | 층 |
| collected_at | TEXT | 수집 일시 |

### 4-B. Job: 청약 공급 수집
- **API:** 청약홈 분양 정보 API (`getAPTLttotPblancDetail`)
- **스케줄:** n8n, 월 1회
- **엔드포인트:** `POST /jobs/supply/collect`
- **저장:** `real_estate.db` → `supply_schedule` 테이블

#### 테이블 스키마: `supply_schedule`
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER PK | auto |
| project_name | TEXT | 단지/분양 프로젝트명 |
| sigungu_code | TEXT | 시군구 코드 |
| lat | REAL | 위도 (반경 계산용) |
| lng | REAL | 경도 |
| household_count | INTEGER | 공급 세대수 |
| expected_date | TEXT | 입주 예정 (YYYY-MM) |
| supply_type | TEXT | 'sale' \| 'move_in' |
| collected_at | TEXT | 수집 일시 |

---

## 5. 신규 모듈 설계

### 5-A. ComparativeAnalyzer
**위치:** `src/modules/real_estate/comparative/`  
**의존성:** `TransactionRepository` (기존) — 신규 API 없음

**인터페이스:**
```python
def analyze(self, complex_code: str, sigungu: str,
            exclusive_area: float, build_year: int,
            avg_sale_price: int) -> ComparativeResult
```

**ComparativeResult 필드:**
- `district_avg_per_sqm: float` — 구 평균 ㎡당 가격 (원)
- `pct_vs_avg: float` — (단지 ㎡당가 - 평균) / 평균 × 100
- `similar_units: List[SimilarUnit]` — 유사 단지 최대 3개 `{name, price_per_sqm}`

**로직:**
- 조건: 동일 sigungu + 면적 ±10㎡ + 연식 ±5년 + 최근 90일 거래
- 구 평균: `avg(price / exclusive_area)` from tx_repo
- 유사 단지: 위 조건에서 distinct apt_name, 거래 건수 내림차순 상위 3개

**enrich 함수:** `_enrich_with_comparative(candidates, analyzer)` — `report_orchestrator.py`에 추가

**candidate dict 필드:**
```
_comp_district_avg_per_sqm: float
_comp_pct_vs_avg: float
_comp_similar_units: List[dict]
```

---

### 5-B. YieldCalculator
**위치:** `src/modules/real_estate/yield_analysis/`  
**의존성:** `JeonseRepository` (신규, jeonse_transactions 조회)

**인터페이스:**
```python
def calculate(self, complex_code: str, apt_name: str,
              district_code: str, exclusive_area: float,
              avg_sale_price: int) -> Optional[YieldResult]
```
→ 전세 표본 0건이면 `None` 반환

**조회 전략 (fallback):**
1. `complex_code` 있으면 → `jeonse_transactions.complex_code` 일치 + 면적 ±5㎡ 조회
2. `complex_code` 없거나 결과 0건이면 → `apt_name` + `district_code` + 면적 ±5㎡ fallback 조회

**YieldResult 필드:**
- `jeonse_rate: float` — 전세가율 (0~1)
- `jeonse_avg: int` — 평균 전세가(만원)
- `gap_cost: int` — 갭투자 비용 (매매가 - 전세가, 만원)
- `monthly_cost: int` — 월 보유비용 (원리금 + 관리비 추정 15만원, 만원)
- `jeonse_sample: int` — 표본 건수

**월 보유비용 계산식:**
```
원리금 = 매매가 × LTV(0.7) × (mortgage_rate/12) / (1-(1+r)^-360)
월 보유비용 = 원리금 + 15만원(관리비)
```
- `mortgage_rate`: `config.yaml` 거시경제 값 주입 (현재 2.83%)

**enrich 함수:** `_enrich_with_yield(candidates, calculator)` — `report_orchestrator.py`에 추가

**candidate dict 필드:**
```
_yield_jeonse_rate: Optional[float]
_yield_jeonse_avg: Optional[int]
_yield_gap_cost: Optional[int]
_yield_monthly_cost: Optional[int]
_yield_jeonse_sample: int
```

---

### 5-C. SupplyRiskAnalyzer
**위치:** `src/modules/real_estate/supply/`  
**의존성:** `SupplyRepository` (신규) + `NewsService` (기존)

**인터페이스:**
```python
def analyze(self, lat: float, lng: float,
            apt_name: str, sigungu: str,
            radius_km: float = 2.0,
            months_ahead: int = 12) -> SupplyRiskResult
```

**SupplyRiskResult 필드:**
- `nearby_units: int` — 반경 내 향후 N개월 입주 예정 세대수
- `supply_period: str` — 입주 예정 기간 요약 (예: "2026H2")
- `news_catalysts: List[Newscatalyst]` — `{type: 'positive'|'negative', title, date}`

**로직 (공급):**
- Haversine 공식으로 supply_schedule 내 반경 필터
- `months_ahead` 이내 `expected_date` 필터
- 세대수 합산

**로직 (뉴스):**
- `NewsService.get_categorized_news(query=f"{apt_name} {sigungu}")` 호출
- 결과 기사를 LLM 단일 호출 (`news_catalyst_classifier` 프롬프트 신규 작성)로 positive/negative 분류
- 기사 없으면 빈 리스트 반환

**enrich 함수:** `_enrich_with_supply(candidates, analyzer)` — `report_orchestrator.py`에 추가

**candidate dict 필드:**
```
_supply_nearby_units: int
_supply_period: str
_news_catalysts: List[dict]
```

---

## 6. LLM 프롬프트 수정: `daily_strategy.md`

### 추가할 변수
```
{{comp_text}}     # "구 평균 대비 -7.8% (유사: 잠실엘스 1,231만, ...)"
{{yield_text}}    # "전세가율 62.4%, 갭 3.5억, 월 187만원"
{{supply_text}}   # "반경 2km 2,340세대 입주예정(2026H2), 호재: GTX-A"
```

### `_format_candidate_for_llm()` 수정 (daily_report_orchestrator.py)
기존 함수에 아래 3개 포맷 블록 추가:
```python
# 비교 분석
comp_pct = c.get("_comp_pct_vs_avg")
if comp_pct is not None:
    similar = ", ".join(f"{u['name']} {u['price_per_sqm']/10000:.0f}만" for u in c.get("_comp_similar_units", []))
    lines.append(f"- 가격 위치: 구 평균 대비 {comp_pct:+.1f}% ({similar})")

# 수익 구조
jeonse_rate = c.get("_yield_jeonse_rate")
if jeonse_rate is not None:
    lines.append(f"- 전세가율 {jeonse_rate*100:.1f}%, 갭 {c['_yield_gap_cost']/10000:.1f}억, 월 보유비용 {c['_yield_monthly_cost']}만원")

# 공급 리스크
supply = c.get("_supply_nearby_units", 0)
catalysts = c.get("_news_catalysts", [])
if supply > 0 or catalysts:
    pos = [x['title'] for x in catalysts if x['type'] == 'positive'][:1]
    neg = [x['title'] for x in catalysts if x['type'] == 'negative'][:1]
    parts = [f"반경 공급 {supply}세대({c.get('_supply_period','')})"]
    if pos: parts.append(f"호재: {pos[0][:20]}")
    if neg: parts.append(f"악재: {neg[0][:20]}")
    lines.append(f"- 공급/호재: {', '.join(parts)}")
```

### 변경할 verdict 지시
```
"verdict": "수치 기반 매수/관망/회피 판단 — 타깃 가격 또는 조건 포함 (50자 이내)"
예: "8.8억 이하 매수 검토, 현재 9.3억은 관망 — 인근 공급 단기 압력"
```

### 신규 프롬프트: `news_catalyst_classifier.md`
- 입력: 뉴스 기사 목록 (title + description)
- 출력: `[{type, title, date}]` JSON
- 역할: SupplyRiskAnalyzer 내부 전용

---

## 7. report_formatter 수정

`build_candidate_card()` 에 3개 블록 추가:

```python
render_price_comparison(comp)   # 신규 — 구 평균 대비 %, 유사 단지
render_yield_analysis(yield_r)  # 신규 — 전세가율, 갭, 월 보유비용
render_supply_risk(supply)      # 신규 — 입주 물량, 호재/악재 태깅
```

각 렌더 함수는 데이터 없으면 빈 문자열 반환 (기존 패턴 동일).

---

## 8. 테스트 전략

| 모듈 | 테스트 방향 |
|------|------------|
| ComparativeAnalyzer | tx_repo fixture로 구 평균 계산 검증, 데이터 없는 경우 처리 |
| YieldCalculator | jeonse_transactions fixture로 전세가율 계산, None 반환 케이스 |
| SupplyRiskAnalyzer | Haversine 반경 필터 정확도, 뉴스 LLM mock |
| JeonseRepository | CRUD + normalize-on-save (기존 tx_repo 패턴 동일) |
| SupplyRepository | CRUD + 반경 쿼리 |
| report_formatter | 신규 render 함수 단위 테스트 |
| DailyReportOrchestrator | 통합 테스트 — 3개 모듈 주입된 enrich 흐름 |

TDD 원칙 적용: 각 모듈 테스트 먼저 작성 후 구현.

---

## 9. 구현 범위 요약

| 항목 | 유형 | 비고 |
|------|------|------|
| `jeonse_transactions` 테이블 + JeonseClient + JeonseRepository | 신규 | Job 포함 |
| `supply_schedule` 테이블 + SupplyClient(청약홈) + SupplyRepository | 신규 | Job 포함 |
| `ComparativeAnalyzer` | 신규 모듈 | tx_repo 재사용 |
| `YieldCalculator` | 신규 모듈 | JeonseRepository 의존 |
| `SupplyRiskAnalyzer` | 신규 모듈 | SupplyRepository + NewsService |
| `_enrich_with_*` 3개 함수 | 신규 (report_orchestrator.py) | |
| `DailyReportOrchestrator` 주입 + Job4 연결 | 수정 | service.py 연결 |
| `daily_strategy.md` 프롬프트 수정 | 수정 | 새 변수 3개 추가 |
| `_format_candidate_for_llm()` 수정 | 수정 (daily_report_orchestrator.py) | comp/yield/supply 텍스트 포맷 추가 |
| `news_catalyst_classifier.md` 프롬프트 | 신규 | |
| `render_price_comparison` / `render_yield_analysis` / `render_supply_risk` | 신규 (report_formatter.py) | |
| `report_types.py` TypedDict 3개 추가 | 수정 | |

**삭제/비활성화:**
- Job4 → `InsightOrchestrator` 연결 해제 (코드 삭제 아님)
