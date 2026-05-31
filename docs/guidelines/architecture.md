# Architecture Guide

**Last Updated:** 2026-05-31

> **AI 필독 — 모든 코드 작업 전 이 문서를 반드시 읽는다.**

## 1. 계층 구조

```
┌──────────────────────────────────────────────────────┐
│  실행계층  FastAPI Router / Streamlit View            │
│  (얇은 Controller — 비즈니스 로직 없음, ~15줄)        │
└───────────────────────┬──────────────────────────────┘
                        │ Depends() / direct factory call
┌───────────────────────▼──────────────────────────────┐
│  Service 계층  (단일 진실 공급원)                      │
│  LocationService / AptAnalysisService /               │
│  DailyReportService / MacroService                    │
│                                                       │
│  ① 분석/수집/저장 계층에서 raw data 조회               │
│  ② 출력계층(Formatter)으로 포맷팅                      │
│  ③ formatted result를 실행계층에 반환                  │
└──────┬──────────────────────────┬─────────────────────┘
       │ query / analyze          │ format(raw_data)
┌──────▼──────────────┐  ┌────────▼────────────────────┐
│  분석/수집/저장 계층  │  │  출력계층 (Formatter)        │
│  - Orchestrator      │  │  (순수 함수)                 │
│  - Analyzer          │  │  - Slack / Markdown / dict  │
│  - API Clients       │  │  - DB·외부 API 접근 금지     │
│  - LLMClient         │  │  - 입력 dict → 출력 str/dict │
│  - Repository        │  └─────────────────────────────┘
└─────────────────────┘
```

**데이터 흐름:**
```
실행계층 → Service → 분석/수집/저장 (raw data 조회)
                  ↓
           출력계층 (raw data → formatted output)
                  ↓
실행계층 → 사용자 (화면 / Slack / Markdown)
```

## 2. 계층 규칙

| 계층 | 호출 가능 | 금지 |
|------|----------|------|
| 실행계층 (FastAPI/Streamlit) | Service 계층만 | Repository, sqlite3, requests 직접 |
| Service 계층 | 분석/수집/저장 계층, 출력계층 | requests HTTP 직접, st.metric() |
| 분석/수집/저장 계층 | Repository (내부), 외부 API | Formatter 호출, 계층 건너뛰기 |
| 출력계층 (Formatter) | 없음 (순수 함수) | DB 접근, 외부 API 호출 |

**절대 금지:**
- 실행계층에서 Repository/sqlite3 직접 접근
- 두 계층 이상 건너뛰기 (예: 실행계층 → Repository 직접 호출)
- 출력계층에서 DB/API 호출

## 3. DI 패턴

> **현재 적용 중 (이 리팩토링으로 구현):** 아래 패턴은 이 작업에서 점진적으로 적용된다.

모든 의존성은 `src/api/dependencies.py`에서 module-level 싱글톤으로 정의한다.

```python
# src/api/dependencies.py
_cfg = RealEstateConfig()
_db = _cfg.get("real_estate_db_path", "data/real_estate.db")

_location_service = LocationService(
    loc_repo=LocationRepository(db_path=_db),
    poi_collector=PoiCollector(api_key=os.getenv("KAKAO_API_KEY", ""), db_path=_db),
    scorer=LocationScorer(config=_load_scoring_config()),
)

def get_location_service() -> LocationService:
    return _location_service
```

**FastAPI 라우터:**
```python
@router.post("/jobs/apt/analyze")
def apt_analyze(
    req: AptAnalyzeRequest,
    orchestrator: AptAnalysisOrchestrator = Depends(get_apt_orchestrator),
    repo: AptAnalysisRepository = Depends(get_apt_analysis_repo),
):
    report = orchestrator.analyze(req.complex_code)
    repo.save(report)
    return {"status": "success", "report": dataclasses.asdict(report)}
```

**Streamlit (동일 factory 직접 호출):**
```python
# src/dashboard/services.py — 대시보드 유일한 진입점 (이 리팩토링에서 신규 생성)
from api.dependencies import get_location_service

def get_location_score(complex_code: str):
    return get_location_service().get_score(complex_code)
```

## 4. 새 기능 추가 체크리스트

- [ ] 새 코드가 올바른 계층에 위치하는가?
- [ ] 의존성은 `src/api/dependencies.py` 싱글톤 또는 Depends()로 주입되는가?
- [ ] 실행계층(FastAPI/Streamlit)이 Repository/DB에 직접 접근하지 않는가?
- [ ] 출력계층(Formatter)이 DB나 외부 API를 호출하지 않는가?
- [ ] 새 Service는 생성자 주입으로 모든 의존성을 받는가?

## 5. 새 모듈 추가 시 규칙

- 도메인 모듈은 반드시 `src/modules/{domain}/` 하위에 위치한다.
- Agent 클래스는 `BaseAgent`를 상속한다 (OCP).
- Collector 클래스는 `BaseCollector`를 상속한다.
- Analyzer 클래스는 `BaseAnalyzer`를 상속한다.
- 새 모듈은 독립적으로 테스트 가능하게 설계한다.
- 새 Service는 `src/api/dependencies.py`에 factory 함수를 반드시 등록한다.
