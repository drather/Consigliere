# 거시경제 지표 수집 시스템 설계

**Date:** 2026-04-18  
**Status:** Approved  
**Domain:** 부동산 전략 / 금융 (공유 인프라)

---

## 1. 목적

부동산 매수/매도 타이밍, 지역 선택, 레버리지 전략 수립에 필요한 거시경제 지표를 체계적으로 수집·저장·조회하는 시스템을 구축한다. 현재 `real_estate/macro/`에 고정 필드 3개로 구현된 BOK 수집 로직을 확장성 있는 공유 인프라로 재설계한다.

---

## 2. 설계 원칙

- **도메인 중립 공유 모듈** — 부동산/금융 어디서든 재사용 가능
- **Zero Hardcoding** — 지표 목록은 DB에서 관리, 코드 변경 없이 지표 추가 가능
- **Per-indicator 수집 주기** — 지표별 발표 주기에 맞게 `collect_every_days` 설정
- **Revision 이력 보존** — 동일 기간 데이터라도 수집일 단위로 누적 저장

---

## 3. 모듈 구조

### 3.1 신규 공유 모듈

```
src/modules/macro/
  __init__.py
  models.py          # MacroIndicatorDef, MacroRecord (dataclass)
  repository.py      # DB CRUD (indicator_definitions + records)
  bok_client.py      # BOK ECOS API 클라이언트 (real_estate/macro/bok_service.py 이전)
  service.py         # MacroCollectionService (수집 오케스트레이션)
```

### 3.2 기존 모듈 처리

```
src/modules/real_estate/macro/
  bok_service.py     # 삭제 (macro/bok_client.py로 통합)
  models.py          # 삭제 (macro/models.py로 통합)
  service.py         # 유지 — real_estate 도메인 전용 쿼리만 담당
                     #   (MacroCollectionService 위임 패턴)
```

---

## 4. DB 스키마

**DB 파일:** `data/macro.db` (기존 `real_estate.db`와 분리)  
**Config 등록:** `config.yaml`의 `macro_db_path: "data/macro.db"` 추가 (Zero Hardcoding)

### 4.1 `macro_indicator_definitions` — 지표 메타데이터

```sql
CREATE TABLE macro_indicator_definitions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    code                TEXT NOT NULL,          -- BOK stat_code (예: "722Y001")
    item_code           TEXT NOT NULL,          -- BOK item_code (예: "0101000")
    name                TEXT NOT NULL,          -- "한국은행 기준금리"
    unit                TEXT NOT NULL,          -- "%", "십억원", "지수"
    frequency           TEXT NOT NULL,          -- "M"월별, "Q"분기, "A"연간, "D"일별
    collect_every_days  INTEGER NOT NULL,       -- 수집 간격 (일): 30, 90, 365
    domain              TEXT NOT NULL,          -- "real_estate", "finance", "common"
    category            TEXT NOT NULL,          -- "금리", "주택시장", "물가", "유동성", "경기"
    is_active           INTEGER DEFAULT 1,      -- 0: 비활성화
    last_collected_at   TEXT,                   -- ISO datetime, NULL이면 미수집
    created_at          TEXT NOT NULL
);
```

### 4.2 `macro_records` — 수집된 시계열 레코드

```sql
CREATE TABLE macro_records (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    indicator_id    INTEGER NOT NULL REFERENCES macro_indicator_definitions(id),
    period          TEXT NOT NULL,              -- "202503" (BOK 발표 기준 기간)
    value           REAL NOT NULL,
    collected_at    TEXT NOT NULL,              -- 실제 수집 일시 (ISO datetime)
    UNIQUE(indicator_id, period, collected_at)  -- 수집일 단위 중복 방지
);
```

**UNIQUE 설계 의도:**
- `(indicator_id, period)` 단독이 아닌 `collected_at` 포함 → 동일 기간 데이터의 revision 이력 보존
- BOK 소급 수정 감지 가능 (같은 period, 다른 collected_at에서 값 변화 추적)

---

## 5. 초기 시딩 지표 목록

`scripts/seed_macro_indicators.py`로 DB에 insert.

| 이름 | code | item_code | domain | category | frequency | collect_every_days |
|------|------|-----------|--------|----------|-----------|--------------------|
| 한국은행 기준금리 | 722Y001 | 0101000 | common | 금리 | M | 30 |
| 예금은행 주택담보대출 금리 | 121Y002 | BEABAA2 | real_estate | 금리 | M | 30 |
| COFIX 신규취급액 기준금리 | 121Y013 | 신규확인필요 | real_estate | 금리 | M | 30 |
| M2 통화량(기말, 계절조정) | 101Y001 | BBGS00 | common | 유동성 | M | 30 |
| 가계신용 총량 | 600Y001 | 신규확인필요 | common | 유동성 | Q | 90 |
| 주택매매가격지수(전국) | 901Y062 | 신규확인필요 | real_estate | 주택시장 | M | 30 |
| 전세가격지수(전국) | 901Y063 | 신규확인필요 | real_estate | 주택시장 | M | 30 |
| 소비자물가지수(CPI) | 902Y009 | 신규확인필요 | common | 물가 | M | 30 |
| GDP 성장률(실질) | 200Y001 | 신규확인필요 | common | 경기 | Q | 90 |

> **주의:** `신규확인필요`로 표시된 item_code는 구현 Phase에서 BOK ECOS 실제 조회로 확인 후 확정.

---

## 6. 데이터 모델 (Python)

```python
# macro/models.py

@dataclass
class MacroIndicatorDef:
    id: Optional[int]
    code: str
    item_code: str
    name: str
    unit: str
    frequency: str          # "M", "Q", "A", "D"
    collect_every_days: int
    domain: str             # "real_estate", "finance", "common"
    category: str
    is_active: bool
    last_collected_at: Optional[str]
    created_at: str

@dataclass
class MacroRecord:
    id: Optional[int]
    indicator_id: int
    period: str             # "202503"
    value: float
    collected_at: str       # ISO datetime
```

---

## 7. 서비스 인터페이스

### 7.1 MacroCollectionService (`macro/service.py`)

```python
class MacroCollectionService:
    def collect_due_indicators(self, domain: Optional[str] = None) -> dict:
        """
        is_active=True인 지표 중 collect_every_days 기준으로 수집 기한이 된 것만 수집.
        domain="real_estate" / "finance" / "common" / None(전체)
        반환: {"collected": [...], "skipped": [...], "errors": [...]}
        """

    def collect_all(self, domain: Optional[str] = None) -> dict:
        """기한 무관하게 전체 강제 수집. 초기 시딩 및 수동 트리거용."""

    def get_latest(self, domain: Optional[str] = None) -> List[dict]:
        """지표별 최신값 (period별 최근 collected_at 기준)."""

    def get_history(self, indicator_id: int, months: int = 24) -> List[MacroRecord]:
        """단일 지표 시계열 (최근 N개월, 최신 수집분 기준)."""
```

### 7.2 기존 `real_estate/macro/service.py` — RealEstateMacroView

```python
class RealEstateMacroView:
    """real_estate 도메인 전용 쿼리 레이어. MacroCollectionService에 위임."""
    
    def get_real_estate_latest(self) -> MacroData:
        """기존 MacroData 형식 호환 유지 (대시보드 하위 호환)."""
    
    def get_chart_series(self, months: int = 24) -> dict:
        """금리/주택시장 시계열 차트 데이터."""
```

---

## 8. API 엔드포인트

### 8.1 신규

| Method | Path | 설명 |
|--------|------|------|
| `POST` | `/jobs/macro/collect` | 수집 Job 실행 (`domain` query param 선택) |
| `GET` | `/dashboard/macro/latest` | 지표별 최신값 (`domain` 필터) |
| `GET` | `/dashboard/macro/history/{indicator_id}` | 단일 지표 시계열 |

### 8.2 기존 엔드포인트 처리

| 기존 경로 | 처리 방식 |
|-----------|-----------|
| `GET /dashboard/real-estate/macro-history` | 내부적으로 신규 서비스 위임, 응답 형식 호환 유지 |
| `POST /jobs/real-estate/fetch-macro` | Deprecated 표시, `/jobs/macro/collect?domain=real_estate`로 안내 |

---

## 9. 대시보드 표시 구조

거시경제 지표 탭을 카테고리 서브탭으로 재편:

```
거시경제 지표
├── 금리        기준금리 / 주담대금리 / COFIX
├── 주택시장    매매가격지수 / 전세가격지수
├── 물가/경기   CPI / GDP 성장률
└── 유동성      M2 통화량 / 가계신용
```

각 지표 카드: **최신값** + **전기 대비 변화(▲/▼)** + **시계열 차트**

---

## 10. 수집 이력 조회 예시

```sql
-- 기준금리 최신값 (period별 최근 수집)
SELECT period, value, collected_at
FROM macro_records
WHERE indicator_id = 1
GROUP BY period
HAVING collected_at = MAX(collected_at)
ORDER BY period DESC;

-- 기준금리 revision 이력 (2025-03 발표값이 수집될 때마다 어떻게 바뀌었나)
SELECT period, value, collected_at
FROM macro_records
WHERE indicator_id = 1 AND period = '202503'
ORDER BY collected_at;
```

---

## 11. 마이그레이션 전략

1. `data/macro.db` 신규 생성 및 테이블 DDL 적용
2. `scripts/seed_macro_indicators.py` 실행 → 지표 정의 insert
3. `macro/service.py collect_all()` 실행 → 최근 24개월 초기 수집
4. 기존 `real_estate/macro/bok_service.py`, `models.py` 삭제
5. 기존 API 엔드포인트 내부 구현 교체 (응답 형식 동일 유지)
