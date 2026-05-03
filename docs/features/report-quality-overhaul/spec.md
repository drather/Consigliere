# report-quality-overhaul — Spec

**작성일:** 2026-05-02  
**브랜치:** `feature/report-quality-overhaul`

---

## 목표

부동산 전략 리포트의 품질을 전문 컨설턴트 수준으로 끌어올린다.  
구체적으로: 실거래가 기반 후보 선정 → POI·출퇴근 실측 → LLM 입지/학군 분석 → 점수 차별화 → 예산 적합 추천.

---

## 아키텍처 개요

```
persona (interest_areas, min_household_count, budget)
    ↓
AptMasterRepository.search()  ← apartments LEFT JOIN (lat/lng 포함)
    ↓
ReportOrchestrator.generate()
    ├── _enrich_with_poi()         ← Kakao 역세권/학원/마트 (lat/lng 필수)
    ├── _enrich_with_building()    ← building_master FAR/BCR/build_year
    ├── _enrich_with_commute()     ← TMAP 출퇴근 실측 (TMAP_API_KEY 필수)
    ├── _enrich_with_trend()       ← 실거래가 멀티 면적 탐색
    ├── ScoringEngine.score_all()  ← 5개 기준 가중 점수
    ├── _call_location_agent()     ← LLM 입지 분석 (variables 주입 필수)
    ├── _call_school_agent()       ← LLM 학군 분석 (variables 주입 필수)
    └── _call_strategy_agent()     ← LLM 투자 전략
    ↓
_build_markdown() → ReportRepository.save()
```

---

## 변경 범위 (다음 스프린트)

### P0-A: LLM 분석 variables 주입 수정
- 파일: `src/modules/real_estate/report_orchestrator.py`
- 변경: `load_with_cache_split("location_analyst", variables={"candidates_poi_json": json_str})`
- 동일 수정: `school_analyst`, `strategy_analyst`

### P0-B: lat/lng → apt_master 파이프라인 연결
- 파일: `src/modules/real_estate/apt_master_repository.py`
  - `search()` SELECT에 `a.lat, a.lng` 추가
- 파일: `src/modules/real_estate/models.py`
  - `AptMasterEntry`에 `lat: Optional[float] = None`, `lng: Optional[float] = None` 추가
- 파일: `src/modules/real_estate/apt_master_repository.py`
  - `_row_to_entry()`: lat/lng 키 가드 추가
- 선행 조건: `apartments` 테이블에 `lat`, `lng` 컬럼이 있는지 확인 (`SELECT * FROM apartments LIMIT 1`)

### P1: 출퇴근 수집 실패 원인 진단 및 수정
- API 서버 로그에서 `[Orchestrator] Commute 실패` WARNING 확인
- `apartments.road_address` 채움률 점검: 강남구/서초구 후보 대상
- CommuteService 단위 테스트: `dest=None` 시 config 기본 좌표(삼성역) 폴백 동작 검증
- TMAP_API_KEY는 `.env` + `env_file: - .env` 로 이미 정상 주입됨 — 환경 설정 이슈 없음

### P2: 예산 적합성 기반 후보 정렬
- 파일: `src/modules/real_estate/report_orchestrator.py`
  - `generate()` 내 scored 리스트 정렬 전, budget_available 대비 초과 단지에 total_score 패널티 (-10점)
  - 또는 `ScoringEngine.score_all()` 에 `budget_available` 파라미터 추가하여 예산 적합성 보정

---

## 데이터 모델

`AptMasterEntry` (추가 필드):
```python
lat: Optional[float] = None
lng: Optional[float] = None
```

---

## 테스트 기준

- `test_apt_master_repository.py`: search() 결과에 lat/lng 포함 확인
- `test_report_orchestrator.py`: _call_location_agent() 반환값 비어있지 않음 확인
- E2E 면제 (화면단 변경 없음)
