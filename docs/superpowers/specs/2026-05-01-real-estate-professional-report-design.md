# 부동산 전문 컨설턴트 리포트 시스템 설계

**Date:** 2026-05-01  
**Status:** Approved  
**Phase:** 1 (카카오 POI + 리포트 아카이브) → 2 (외부 API 확장 + 실시간 조회)

---

## 1. 배경 및 목표

### 문제
현재 Job4가 생성하는 리포트는 5기준 점수 + LLM 서술 1회로 구성된 단순 파이프라인이다.
실제 부동산 의사결정에 필요한 입지 분석, 학군 분석, 상권 분석, 예산 시뮬레이션이 빠져 있어
"진짜로 실행 가능한 전략"을 제공하지 못한다.

### 목표
- 부동산 컨설턴트 수준의 단지별 상세 분석 리포트 자동 생성 (매일 07:00)
- 실거래가 추세 + 카카오 로컬 POI + 건축물대장 + 거시경제를 모두 반영
- 생성된 리포트를 아카이브에 저장하고 대시보드에서 열람 가능
- Slack으로 Executive Summary 발송 (기존 유지)
- 페르소나(예산/직장/선호) 대시보드 UI에서 편집 가능

---

## 2. 전체 아키텍처

```
Job4 (n8n 스케줄, 매일 07:00 KST)
  └─ ReportOrchestrator
       ├─ [Python] FinancialCalculator   → DSR 기반 구매 가능 예산 계산
       ├─ [Python] CandidateFilter       → 예산/선호 필터링 (기존 재활용)
       ├─ [Python] TrendAnalyzer         → 실거래가 6개월 추세 (SQLite 집계 쿼리)
       ├─ [Python] PoiCollector          → 카카오 로컬 API 반경 POI 수집 + 캐시
       ├─ [Python] ScoringEngine (강화)   → 용적률/POI 반영 5기준 점수 재계산
       ├─ [LLM]   LocationAgent          → 입지 분석 서술 (Top 5 배치 1회 호출)
       ├─ [LLM]   SchoolAgent            → 학군/학원가 분석 서술 (Top 5 배치 1회 호출)
       ├─ [LLM]   StrategyAgent          → 투자 전략 + 액션 플랜
       └─ [LLM]   SynthesizerAgent       → 전체 통합 리포트 서술 (기존 강화)
            ├─ ReportRepository          → Markdown + JSON 저장
            └─ SlackSender              → Executive Summary 발송
```

### 설계 원칙
- **Python이 사실(fact)을 계산, LLM이 해석(interpretation)을 담당**: 가격 추세·예산·점수는 Python. LLM은 수치의 의미를 서술
- **LLM 호출 최소화**: 단지별 개별 호출 대신, Top 5를 배치로 묶어 에이전트당 1회 호출
- **기존 코드 재활용**: `InsightOrchestrator`, `ScoringEngine`, `CandidateFilter`, `CommuteService` 구조 유지

---

## 3. 리포트 구성

```
📊 Consigliere 부동산 전략 리포트 — YYYY-MM-DD

━━━━━━━━━━━━━━━━━━━━━━━━━━━
 1. Executive Summary (오늘의 요약)
━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 현재 구매 가능 예산: XX억 (자산 + 대출 한도)
- 시장 상황 한 줄 요약 (기준금리/주담대 기반)
- 추천 단지 Top 3 (단지명 + 총점 + 한 줄 이유)
- 지금 당장 해야 할 액션 1가지

━━━━━━━━━━━━━━━━━━━━━━━━━━━
 2. 거시경제 컨텍스트
━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 기준금리 / 주담대 금리 현황
- DSR 계산 결과 → 실질 구매 가능 예산
- 시장 방향성 (LLM 해석)

━━━━━━━━━━━━━━━━━━━━━━━━━━━
 3. 추천 단지 상세 분석 (Top 5)
━━━━━━━━━━━━━━━━━━━━━━━━━━━
각 단지마다:

  [단지명] 총점 87/100

  📍 입지 분석
    - 역세권: 2호선 강남역 도보 7분, 9호선 신논현역 도보 4분
    - 생활편의: 반경 500m 대형마트 2개, 병원 8개
    - 입지 평가: (LocationAgent LLM 서술 2-3문장)

  🏫 학군 분석
    - 반경 1km 내 초등학교 2개, 중학교 1개, 학원 43개
    - 학군 평가: (SchoolAgent LLM 서술 2-3문장)

  📈 실거래가 추세
    - 6개월 평균가: 12.3억 (84㎡ 기준)
    - 3개월 전 대비: +2.1% / 월 평균 거래량 8건
    - 추세 해석: (LLM 서술 1-2문장)

  🏗️ 재건축/투자 잠재력
    - 건축연도: 1994년 (32년), 용적률: 198%, 건폐율: 18%
    - 재건축 가능성 평가: (LLM 서술)

  🚌 출퇴근 (삼성역 기준, 캐시 활용)
    - 대중교통 23분 / 자가용 18분

  💰 예산 적합성
    - 최근 3개월 실거래 최고가 (호가 proxy) vs 구매 가능 예산 비교
    - 실행 가능 여부 + 자금 조달 방법 제안

━━━━━━━━━━━━━━━━━━━━━━━━━━━
 4. 투자 전략 및 액션 플랜
━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 지금 당장 실행 가능한 전략 (청약/매수/관망)
- 단기(3개월) / 중기(1년) 액션 플랜
- 리스크 요인 및 주의사항
```

**Slack 발송:** Executive Summary 섹션 요약본  
**아카이브 저장:** 전체 리포트 (Markdown + JSON)  
**대시보드:** 날짜별 전체 리포트 열람

---

## 4. 신규 컴포넌트 상세

### 4-1. PoiCollector

카카오 로컬 API "반경 키워드 검색" 활용. `GeocoderService`가 이미 카카오 API key를 사용 중이므로 key 추가 불필요.

```python
class PoiCollector:
    def collect(self, road_address: str, complex_code: str) -> PoiData:
        ...
```

수집 항목:
- 반경 500m: 지하철역 (역명, 도보 분)
- 반경 1km: 초/중학교 (개수), 학원 (개수), 대형마트/백화점 (개수)

캐시: `real_estate.db`의 `poi_cache` 테이블, `collected_at` 기준 30일 TTL

```sql
CREATE TABLE poi_cache (
    complex_code TEXT PRIMARY KEY,
    road_address TEXT,
    subway_stations TEXT,   -- JSON
    schools_count   INTEGER,
    academies_count INTEGER,
    marts_count     INTEGER,
    collected_at    TEXT
);
```

### 4-2. TrendAnalyzer

`TransactionRepository`에 집계 쿼리 추가. 신규 클래스로 분리.

```python
class TrendAnalyzer:
    def get_trend(self, apt_master_id: int, area_sqm: float, months: int = 6) -> TrendData:
        # avg_price, price_change_pct (3개월 전 대비), monthly_volume, price_range
```

### 4-3. ReportOrchestrator

현재 `InsightOrchestrator`의 상위 레이어. `InsightOrchestrator`를 내부적으로 호출하되,
PoiCollector / TrendAnalyzer / 신규 LLM 에이전트를 조합한다.

```python
class ReportOrchestrator:
    def generate(self, target_date: date) -> ReportResult:
        ...
```

### 4-4. LLM 에이전트 (3개 신규)

| 에이전트 | 입력 | 출력 |
|---------|------|------|
| `LocationAgent` | Top 5 단지 POI 데이터 배치 | 단지별 입지 분석 텍스트 |
| `SchoolAgent` | Top 5 단지 학교/학원 수 배치 | 단지별 학군 분석 텍스트 |
| `StrategyAgent` | 전체 분석 결과 + 거시경제 | 투자 전략 + 액션 플랜 |

모두 `generate_json()` 호출, `TaskType` 라우팅 적용. 프롬프트 파일: `src/modules/real_estate/prompts/` 하위에 추가.

### 4-5. ReportRepository

```python
class ReportRepository:
    def save(self, date: date, report: ReportResult) -> None:
        # data/real_estate_reports/YYYY-MM-DD.md
        # data/real_estate_reports/YYYY-MM-DD.json
    
    def list_dates(self) -> List[date]: ...
    def load(self, date: date) -> ReportResult: ...
```

---

## 5. ScoringEngine 강화

재건축 잠재력 점수에 용적률/건축연도 정량화 반영:

| 조건 | 점수 |
|------|------|
| 용적률 ≤ 200% AND 건축연도 ≥ 30년 | HIGH (100) |
| 용적률 ≤ 250% OR 건축연도 ≥ 20년 | MEDIUM (60) |
| 그 외 | LOW (20) |

생활편의 점수에 POI 반영:
- 도보 5분 내 역 2개 이상 → HIGH
- 학원 20개 이상 → 학군 점수 MEDIUM → HIGH 승격

---

## 6. 대시보드 변경

### 탭 구조 변경
```
현재: 🔍 아파트 탐색 | 📊 Insight | 📈 거시경제 | ⚙️ 자동화
변경: 🔍 아파트 탐색 | 📋 리포트 아카이브 | 📊 Insight | 📈 거시경제 | ⚙️ 자동화
```

### 신규: 📋 리포트 아카이브 탭
- 날짜 selectbox → 해당 날짜 리포트 로드
- Executive Summary 상단 고정 표시
- 단지별 상세 분석은 expander로 펼침
- 투자 전략 섹션 하단 표시

### 기존 변경: ⚙️ 자동화 탭 → "👤 내 설정" 서브탭 추가
- 예산 (자산/소득) 수정
- 직장 주소 수정
- 선호 지역 멀티셀렉트
- 우선순위 가중치 슬라이더 (출퇴근/학군/유동성/생활편의/가격잠재력)
- 저장 → `PersonaManager.update()` 호출

---

## 7. 에러 처리

| 장애 | 처리 방식 |
|------|---------|
| 카카오 POI API 실패 | 해당 단지 POI `None`, 리포트에 "정보 미수집" 표시, 파이프라인 계속 |
| LLM 에이전트 실패 | 해당 섹션 fallback 텍스트, 나머지 섹션 계속 생성 |
| 실거래가 없는 단지 | 추세 분석 skip, 점수 neutral(50) |
| 리포트 저장 실패 | Slack 발송은 계속 진행 |

---

## 8. 테스트 계획

| 대상 | 방식 |
|------|------|
| `TrendAnalyzer` 집계 정확성 | SQLite in-memory 단위 테스트 |
| `PoiCollector` 파싱 + TTL 캐시 | 카카오 API mock |
| `ScoringEngine` 용적률 반영 | 단위 테스트 |
| `ReportOrchestrator` 전체 흐름 | 서비스 mock 통합 테스트 |
| `ReportRepository` 저장/조회 | 임시 디렉토리 |
| 대시보드 아카이브 탭 | Playwright E2E |

---

## 9. Phase 구분

### Phase 1 (현재 구현 범위)
- `PoiCollector` (카카오 로컬 API + poi_cache)
- `TrendAnalyzer` (SQLite 집계)
- `ReportOrchestrator` (신규 상위 레이어)
- LLM 3개 신규 에이전트 + SynthesizerAgent 강화
- `ReportRepository` (Markdown + JSON)
- 대시보드 리포트 아카이브 탭 신설
- 페르소나 편집 UI

### Phase 2 (이후)
- 학교알리미 API (학업성취도, 진학 현황)
- 소상공인 상권분석 API (상권 밀도)
- 대시보드 실시간 what-if 조회 (조건 변경 → 즉시 재추천)
