# Real Estate 아키텍처 리팩토링 + 가이드라인 재편 설계

**Goal:** real_estate 모듈에 Layered Architecture + DI 패턴을 도입하여 한 계층 변경이 다른 계층을 연쇄 수정하지 않도록 구조를 개선하고, AI가 다음 작업에서도 동일 원칙을 지키도록 가이드라인을 재편한다.

**Architecture:** FastAPI와 Streamlit이 동일한 Service 계층을 호출하는 구조. 의존성은 중앙 `dependencies.py`에서 `Depends()` factory 함수로 조립. 대시보드는 DB/Repository에 직접 접근하지 않고 Service 계층만 호출.

**Tech Stack:** Python 3.12, FastAPI `Depends()`, `functools.lru_cache`, SQLite, Streamlit

---

## 1. 계층 구조

```
┌──────────────────────────────────────────────────────┐
│  실행계층  FastAPI Router / Streamlit View            │
│  (얇은 Controller — 비즈니스 로직 없음, 10~15줄)      │
└───────────────────────┬──────────────────────────────┘
                        │ Depends() / direct factory call
┌───────────────────────▼──────────────────────────────┐
│  Service 계층  (단일 진실 공급원)                      │
│  LocationService / AptAnalysisService /               │
│  DailyReportService / MacroService                    │
│                                                       │
│  ① 분석/수집/저장 계층에서 raw data 조회               │
│  ② 출력계층(Formatter)으로 포맷팅                     │
│  ③ formatted result를 실행계층에 반환                  │
└──────┬──────────────────────────┬─────────────────────┘
       │ query / analyze          │ format(raw_data)
┌──────▼──────────────┐  ┌────────▼────────────────────┐
│  분석/수집/저장 계층  │  │  출력계층 (Formatter)        │
│                      │  │  (순수 함수)                 │
│  - Orchestrator      │  │  - Slack 메시지 포맷          │
│  - Analyzer          │  │  - Markdown 문서 포맷         │
│  - API Clients       │  │  - Dashboard 렌더링 dict      │
│    (MOLIT, Kakao…)   │  │                              │
│  - LLMClient         │  │  규칙: DB·외부 API 접근 금지  │
│  - Repository        │  │  입력 dict → 출력 str/dict   │
└─────────────────────┘  └────────────────────────────┘
```

**데이터 흐름:**
```
실행계층 → Service → 분석/수집/저장 (raw data 조회)
                  ↓
           출력계층 (raw data → formatted output)
                  ↓
실행계층 → 사용자 (화면 / Slack / Markdown)
```

**계층 규칙:**
- 실행계층(FastAPI/Streamlit)은 Service 계층만 호출한다
- Service 계층은 분석/수집/저장 계층과 출력계층 양쪽을 호출한다
- 분석/수집/저장 계층은 HTTP requests·Formatter 호출 금지
- 출력계층은 순수 함수 — DB·외부 API 접근 금지
- 계층 건너뛰기 금지 (실행계층이 Repository 직접 호출 등)

---

## 2. DI 패턴

모든 의존성은 `src/api/dependencies.py` 한 곳에서 factory 함수로 정의한다.

```python
# src/api/dependencies.py
from functools import lru_cache

@lru_cache
def get_settings() -> RealEstateSettings:
    return RealEstateSettings()  # .env + config.yaml 통합

def get_location_service() -> LocationService:
    s = get_settings()
    return LocationService(
        loc_repo=LocationRepository(s.db_path),
        poi_collector=PoiCollector(s.kakao_key, s.db_path),
        scorer=LocationScorer(s.scoring_config),
    )

def get_apt_analysis_service() -> AptAnalysisService:
    s = get_settings()
    return AptAnalysisService(
        orchestrator=_build_apt_orchestrator(s),
        loc_service=get_location_service(),
    )
```

**FastAPI 라우터 사용:**
```python
@router.post("/jobs/apt/analyze")
def apt_analyze(
    req: AptAnalyzeRequest,
    svc: AptAnalysisService = Depends(get_apt_analysis_service),
):
    report = svc.analyze(req.complex_code)
    return {"report": dataclasses.asdict(report)}
```

**Streamlit 사용 (동일 factory 직접 호출):**
```python
# src/dashboard/services.py
from api.dependencies import get_location_service, get_apt_analysis_service

def analyze_apt(complex_code: str):
    return get_apt_analysis_service().analyze(complex_code)

def get_location(complex_code: str):
    return get_location_service().get_score(complex_code)
```

---

## 3. 신규 파일

### 3-1. `src/api/dependencies.py`
모든 서비스 factory 함수의 중앙 집결지.
- `get_settings()` — `@lru_cache` 싱글톤, `.env` + `config.yaml` 통합
- `get_location_service()` → `LocationService`
- `get_apt_analysis_service()` → `AptAnalysisService`
- `get_daily_report_service()` → `DailyReportService`
- `get_macro_service()` → `MacroService`
- private `_build_*` 헬퍼들 (Orchestrator 조립 전용)

### 3-2. `src/modules/real_estate/location/location_service.py`
POI 수집 + 입지점수 계산 + 저장을 하나의 서비스로 통합.

```python
class LocationService:
    def __init__(self, loc_repo, poi_collector, scorer): ...

    def get_score(self, complex_code: str) -> Optional[LocationScore]:
        """저장된 점수 반환. 없으면 None."""

    def get_poi(self, complex_code: str, lat: float, lng: float) -> PoiData:
        """POI 수집 (캐시 우선)."""

    def enrich_and_save(self, complex_code: str, candidate: dict) -> LocationScore:
        """POI 수집 → 스코어링 → 저장 → 반환 (원스톱)."""
```

### 3-3. `src/dashboard/services.py`
대시보드가 호출하는 모든 서비스의 진입점. DB/Repository/requests 직접 사용 금지.

```python
from api.dependencies import (
    get_location_service,
    get_apt_analysis_service,
)
```

### 3-4. `docs/guidelines/architecture.md`
AI 필독 아키텍처 원칙 문서.
- 계층 다이어그램
- 계층별 허용/금지 규칙
- DI 패턴 적용법 (코드 예시 포함)
- 새 기능 추가 체크리스트
- 위반 사례 예시

---

## 4. 수정 파일

### 4-1. `src/api/routers/real_estate.py`
- 엔드포인트 함수 내 직접 의존성 생성 제거
- `Depends(get_*_service)` 패턴으로 교체
- `/jobs/daily-report/generate` 50줄 의존성 조립 → `dependencies.py`로 이동
- 각 엔드포인트 함수는 입력 검증 + 서비스 호출 + 응답 조립만 담당 (10~15줄 목표)

### 4-2. `src/dashboard/views/real_estate.py`
- `_load_poi_from_db()` 삭제 → `dashboard/services.py`의 `get_location_service().get_poi()` 호출
- `_load_location_score_from_db()` 삭제 → `dashboard/services.py`의 `get_location_service().get_score()` 호출
- 함수 내부 `from modules.real_estate... import` 패턴 전면 제거
- `dashboard/services.py` 경유로 통일

### 4-3. `CLAUDE.md`
- 필독 순서에 `docs/guidelines/architecture.md` 추가 (4번째)
- 빠른 참조 테이블에 architecture.md 항목 추가
- `application.md` 항목을 architecture.md로 교체

### 4-4. `docs/guidelines/coding_guide.md`
- SOLID 원칙에 이 프로젝트 적용법 추가
  - DIP → "의존성은 `dependencies.py`에서 factory 함수로 주입"
  - SRP → "Service/Orchestrator/Repository 책임 구분 기준"
- DI 패턴 섹션 신규 추가 (Depends() 예시 포함)

### 4-5. `docs/guidelines/sop.md`
Phase 2.5 SOLID Review 체크리스트에 아키텍처 준수 항목 추가:
- [ ] 새 코드가 올바른 계층에 위치하는가?
- [ ] 의존성은 `dependencies.py` factory를 통해 주입되는가?
- [ ] 실행계층(FastAPI/Streamlit)이 Repository/DB에 직접 접근하지 않는가?
- [ ] 출력계층(Formatter)이 DB나 외부 API를 호출하지 않는가?

### 4-6. `docs/guidelines/environment.md`
- 이미 Docker 재기동 규칙 추가됨 — 현행 유지

---

## 5. 삭제/이동 파일

| 파일 | 조치 | 이유 |
|------|------|------|
| `docs/guidelines/application.md` | `architecture.md`로 내용 통합 후 삭제 | outdated, architecture.md와 중복 |
| `docs/guidelines/feature_list.md` | `docs/context/feature_list.md`로 이동 | 가이드라인이 아닌 프로젝트 상태 정보 |

---

## 6. 구현 순서

의존성 순서에 따라 아래 순서로 구현한다.

**Task 1 — 가이드라인 재편 (AI context 먼저 확립)**
- `docs/guidelines/architecture.md` 신규 작성
- `CLAUDE.md` 필독 순서 + 빠른 참조 업데이트
- `coding_guide.md` DI 패턴 + SOLID 구체화
- `sop.md` Phase 2.5 체크리스트 강화
- `application.md` → 내용 architecture.md 통합 후 삭제
- `feature_list.md` → `docs/context/`로 이동

**Task 2 — `RealEstateSettings` 클래스**
- `src/modules/real_estate/settings.py` 신규
- `.env` + `config.yaml` 통합 접근, `@lru_cache` 싱글톤

**Task 3 — `LocationService`**
- `src/modules/real_estate/location/location_service.py` 신규
- `get_score()`, `get_poi()`, `enrich_and_save()` 구현
- 기존 `_load_poi_from_db()`, `_load_location_score_from_db()` 로직 이동
- 테스트: `tests/modules/real_estate/location/test_location_service.py`

**Task 4 — `dependencies.py`**
- `src/api/dependencies.py` 신규
- 모든 서비스 factory 함수 정의
- 기존 라우터 내 의존성 조립 코드 이동

**Task 5 — `dashboard/services.py`**
- `src/dashboard/services.py` 신규
- `dependencies.py` factory 함수를 import해서 대시보드 진입점 제공

**Task 6 — `routers/real_estate.py` 슬림화**
- 각 엔드포인트에 `Depends()` 적용
- `/jobs/daily-report/generate` 의존성 조립 코드 → `dependencies.py`로 이동
- 엔드포인트 함수 10~15줄 목표

**Task 7 — `dashboard/views/real_estate.py` 정리**
- 직접 DB/Repository 접근 전면 제거
- `dashboard/services.py` 경유로 통일

---

## 7. 검증 기준

- `arch -arm64 .venv/bin/python3.12 -m pytest tests/ -v` 전체 통과
- `grep -rn "sqlite3.connect\|from modules.real_estate" src/dashboard/` → 0건
- `grep -rn "sqlite3.connect\|os.getenv" src/api/routers/real_estate.py` → 0건
- 대시보드에서 헬리오시티 심층분석 버튼 → POI + 입지점수 + 출퇴근 + 학군 표시 확인
