# Location Scoring Redesign — 실거주/투자 이중 점수 체계

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 기존 단일 종합점수(ScoringEngine 5차원)를 실거주 점수 + 투자 점수 이중 체계로 전면 재설계. 항목 추가가 용이한 유연한 아키텍처 적용.

**Architecture:** `BaseDimension` 추상 클래스 기반 차원 구현체 + config.yaml 가중치 정의. `LocationScorer`가 두 점수를 계산하고 항목별 breakdown을 반환. 기존 `ScoringEngine` deprecate.

**Tech Stack:** Python dataclass, SQLite (poi_cache 확장), Kakao Local API, Streamlit, YAML config

---

## 배경 및 결정 사항

### 왜 이중 점수 체계인가

단일 종합점수는 실거주자(생활 편의 중시)와 투자자(가격 상승 잠재력 중시)의 니즈를 동시에 반영하지 못한다. 동일 단지에 대해 두 관점의 점수를 병렬로 제공해 사용자가 전략적 판단을 내릴 수 있게 한다.

### 아키텍처 선택: 하이브리드 (Option C)

- Dimension 구현체는 타입 있는 Python 클래스 → 테스트 가능, 타입 안전
- 가중치와 차원-점수 매핑은 config.yaml → 코드 변경 없이 조정 가능
- 향후 멀티유저 지원 시: config 읽기를 DB 읽기로 교체하면 인터페이스 불변

### 기존 ScoringEngine 흡수

현재 5개 차원(commute, liquidity, school, living_convenience, price_potential)을 9개 Dimension으로 재편하여 실거주/투자 두 점수 아래 배치. 기존 ScoringEngine은 제거.

---

## 차원 구성

### 실거주 점수 (Residential Score)

| Dimension ID | 클래스 | 데이터 소스 | 기본 가중치 |
|---|---|---|---|
| `transportation` | `TransportationDimension` | poi_stations + commute_minutes | 0.25 |
| `education` | `EducationDimension` | school_scores (전입률 기반) | 0.20 |
| `living_infra` | `LivingInfraDimension` | poi: 편의점+약국+마트 | 0.20 |
| `medical` | `MedicalDimension` | poi: 병원/의원 반경 1km | 0.15 |
| `nature` | `NatureDimension` | poi: 공원 최근접 거리(m) | 0.20 |

### 투자 점수 (Investment Score)

| Dimension ID | 클래스 | 데이터 소스 | 기본 가중치 |
|---|---|---|---|
| `price_potential` | `PricePotentialDimension` | 재건축 가능성 + GTX | 0.30 |
| `commercial` | `CommercialDimension` | poi: 음식점+카페 반경 500m | 0.25 |
| `liquidity` | `LiquidityDimension` | 세대수 기반 회전율 | 0.20 |
| `school_premium` | `SchoolPremiumDimension` | school_scores (투자 관점 재활용) | 0.25 |

> 학군은 실거주(교육환경)와 투자(매도 용이성) 양쪽에 반영. 가중치는 독립적으로 적용.

---

## 파일 구조

```
src/modules/real_estate/
  location/
    __init__.py
    dimensions/
      __init__.py
      base.py               # BaseDimension 추상 클래스
      transportation.py     # TransportationDimension
      education.py          # EducationDimension
      living_infra.py       # LivingInfraDimension (신규)
      medical.py            # MedicalDimension (신규)
      nature.py             # NatureDimension (신규)
      commercial.py         # CommercialDimension (신규)
      price_potential.py    # PricePotentialDimension
      liquidity.py          # LiquidityDimension
      school_premium.py     # SchoolPremiumDimension
    location_scorer.py      # LocationScorer + LocationScore
  poi_collector.py          # 신규 POI 카테고리 확장
  scoring.py                # ScoringEngine → deprecated (제거)
  config.yaml               # scoring 섹션 전면 재작성

tests/modules/real_estate/
  location/
    test_dimensions.py      # 각 Dimension 단위 테스트
    test_location_scorer.py # LocationScorer 통합 테스트
```

---

## 핵심 인터페이스

### BaseDimension

```python
from abc import ABC, abstractmethod

class BaseDimension(ABC):
    def __init__(self, config: dict):
        self._config = config

    @abstractmethod
    def score(self, candidate: dict) -> int:
        """Return 0-100. Return data_absent_neutral (default 50) when data unavailable."""

    @property
    @abstractmethod
    def dimension_id(self) -> str:
        """Unique identifier matching config.yaml dimension id."""
```

### LocationScore

```python
@dataclass
class LocationScore:
    complex_code: str
    residential_total: int                    # 0-100
    residential_breakdown: dict[str, int]     # {dimension_id: score}
    investment_total: int                     # 0-100
    investment_breakdown: dict[str, int]      # {dimension_id: score}
    scored_at: str
```

### LocationScorer

```python
class LocationScorer:
    def __init__(self, config: dict):
        # config에서 residential_dimensions / investment_dimensions 읽음
        # 각 dimension_id를 해당 Dimension 구현체에 매핑

    def score(self, candidate: dict) -> LocationScore:
        # 실거주: Σ(dimension.score() × weight)
        # 투자:   Σ(dimension.score() × weight)
```

### config.yaml 신규 섹션

```yaml
scoring:
  data_absent_neutral: 50
  residential_dimensions:
    - id: transportation
      weight: 0.25
    - id: education
      weight: 0.20
    - id: living_infra
      weight: 0.20
    - id: medical
      weight: 0.15
    - id: nature
      weight: 0.20
  investment_dimensions:
    - id: price_potential
      weight: 0.30
    - id: commercial
      weight: 0.25
    - id: liquidity
      weight: 0.20
    - id: school_premium
      weight: 0.25
  thresholds:
    transportation:
      subway_close_min: 5        # ≤5분 도보 → HIGH
      commute_high_min: 20       # ≤20분 → HIGH
      commute_medium_min: 35     # ≤35분 → MEDIUM
    living_infra:
      high_count: 5              # 편의점+약국+마트 합산 ≥5 → HIGH
      medium_count: 2
    medical:
      high_count: 3              # 반경 1km 내 ≥3개 → HIGH
      medium_count: 1
    nature:
      close_m: 300               # ≤300m → HIGH
      medium_m: 800              # ≤800m → MEDIUM
    commercial:
      high_count: 30             # 음식점+카페 합산 ≥30 → HIGH
      medium_count: 10
    liquidity:
      high_households: 500
      medium_households: 300
    school_premium:
      high_transfer_rate: 0.06
      medium_transfer_rate: 0.03
```

---

## POI 수집 확장

### 신규 수집 카테고리

| 필드명 | 쿼리 | 반경 | 방식 |
|---|---|---|---|
| `convenience_count` | "편의점" | 500m | 단일 페이지 |
| `pharmacy_count` | "약국" | 500m | 단일 페이지 |
| `medical_count` | "병원" | 1000m | 단일 페이지 |
| `park_nearest_m` | "공원" | 1000m | 최근접 거리(m) 추출 |
| `restaurant_count` | "음식점" | 500m | 3페이지 페이지네이션 |
| `cafe_count` | "카페" | 500m | 3페이지 페이지네이션 |

### 캐시 전략

- TTL: 30일 (기존 유지)
- 신규 컬럼은 `ALTER TABLE` 자동 마이그레이션 (기존 패턴)
- 기존 93개 단지: 신규 컬럼 없으므로 최초 `collect()` 호출 시 재수집

---

## 데이터 흐름

**수집 트리거는 리포트 생성 한 곳뿐이다.** 대시보드는 캐시에서 읽기만 한다.

```
[리포트 생성 시] ← 유일한 수집 트리거
  후보 단지 선정
  → PoiCollector.collect(complex_code, lat, lng)
       캐시 히트(30일 이내) → poi_cache에서 즉시 반환
       캐시 미스/만료      → Kakao API 수집 후 poi_cache 저장
  → candidate dict 구성:
       poi_cache     → POI 수치 전체
       school_scores → school_score (전입률 기반)
       commute_cache → commute_minutes, transit_minutes
       apt_master    → household_count, reconstruction_potential, gtx_benefit
  → LocationScorer.score(candidate) → LocationScore
  → location_scores 테이블 upsert (complex_code별 최신 점수 보관)
  → LLM 인사이트 주입: residential_total, investment_total + breakdown
  → 리포트 저장

[대시보드 단지 상세 패널] ← 읽기 전용, API 호출 없음
  location_scores 테이블 조회
    값 있음 → 실거주/투자 점수 카드 + breakdown 표시
    값 없음 → "리포트 생성 후 표시됩니다" 안내
```

이 방식의 이점:
- API 호출이 리포트 생성이라는 의도적 액션에만 묶임
- 대시보드는 항상 빠름 (DB 읽기만, 수집 대기 없음)
- 30일 TTL은 리포트 재생성 시 자동 갱신

### ScoringEngine 교체 범위

기존 `ScoringEngine` 호출처 전부를 `LocationScorer`로 교체:
- `src/modules/real_estate/report_service.py` — 리포트 생성 파이프라인 (수집 + scoring)
- `src/modules/real_estate/daily_report_service.py` — 일일 리포트
- `src/dashboard/views/real_estate.py` — 단지 상세 패널 (읽기 전용)
- `src/api/routers/real_estate.py` — scoring 엔드포인트
- `scoring.py` 파일 자체 삭제

---

## 대시보드 UI

단지 상세 패널(`_render_apt_detail_panel`) 내 기존 expander들을 두 점수 카드로 대체.

```
┌─────────────────────────────────────────────────────┐
│  🏠 실거주 점수  78        💰 투자 점수  65          │
│  ━━━━━━━━━━━━━━━━━━━━     ━━━━━━━━━━━━━━━━━━━━      │
│  ▼ 항목별 상세             ▼ 항목별 상세             │
│    교통 접근성   85          가격 상승 잠재력  80    │
│    교육 환경     90          상권 활성도       60    │
│    생활 인프라   70          거래 유동성       55    │
│    의료 접근성   65          학군 프리미엄     90    │
│    자연 환경     60                                  │
└─────────────────────────────────────────────────────┘
```

기존 통근/학군 expander는 제거. 두 점수 카드가 단지 상세 패널 최상단에 위치.

---

## 에러 처리

- POI 미수집 단지: 해당 dimension `score()` → `data_absent_neutral` (50) 반환
- API 수집 실패: `PoiCollector.collect()` 기존 try/except 유지, 빈 PoiData 반환
- config 가중치 합산이 1.0 아닌 경우: `LocationScorer.__init__`에서 normalize 처리

---

## 테스트 전략

- 각 Dimension: `score()` 경계값 테스트 (HIGH=100, MEDIUM=60, LOW=20, 데이터없음=50)
- `LocationScorer`: mock candidate로 가중합산 검증
- `PoiCollector` 신규 카테고리: 기존 mock 패턴 확장
- 기존 `test_scoring.py` → `test_location_scorer.py`로 전환

---

## 향후 확장 경로

- **새 차원 추가:** `BaseDimension` 구현체 1개 + config 1줄
- **가중치 조정:** config.yaml만 수정 (대시보드 가중치 UI와 연동)
- **멀티유저 지원:** `LocationScorer.__init__`의 config 소스를 YAML → DB로 교체 (인터페이스 불변)
- **부(-)요인 추가:** 간선도로/철도 인접 = `NoiseDimension` (실거주 점수 감점 방향)
