# report-quality-overhaul — Issues & 품질 저하 원인 분석

**작성일:** 2026-05-02  
**브랜치:** `feature/report-quality-overhaul`  
**분석 대상 리포트:** `data/real_estate_reports/2026-05-02.md`

---

## 발견된 품질 저하 항목 및 근본 원인

### ISSUE-01: 입지 분석·학군 분석 섹션 완전 공백

**증상:** 리포트 3번 섹션 "입지 분석", "학군 분석"이 빈 칸.  
**근본 원인 (코드 버그):**

`_call_location_agent()` / `_call_school_agent()` 내부에서 아래 패턴 사용:

```python
_, system, user_tmpl = prompt_loader.load_with_cache_split("location_analyst")
user = user_tmpl.replace("{{candidates_poi_json}}", json.dumps(poi_input, ...))
```

`load_with_cache_split()` 는 내부적으로 `PromptLoader.load(variables=None)` 을 호출하고,
Jinja2 Template이 `{{candidates_poi_json}}` 를 **빈 문자열로 치환** (변수 미전달).  
이후 `user_tmpl = ""` (cache_boundary 없음) → Python `.replace()` 호출해도 결과 `""`.  
LLM은 빈 user 메시지를 받아 빈 `analyses` 반환.

**조치 계획:**  
`load_with_cache_split()` 호출 시 `variables={"candidates_poi_json": json_str}` 전달.
또는 프롬프트에 `cache_boundary` 마커를 추가해 정적 system / 동적 user로 분리.

---

### ISSUE-02: POI 수집 전체 실패 → 역세권·학군 점수 neutral(50)

**증상:** `_poi` 데이터 없음 → 입지 섹션에 역세권 정보 불출력, `_score_living_convenience` / `_score_school` 전부 50점.  
**근본 원인 (데이터 구조 누락):**

`apt_master` 테이블에 `lat`, `lng` 컬럼 없음.  
`AptMasterRepository.search()` 의 LEFT JOIN SELECT:
```sql
SELECT am.*, a.household_count, a.road_address, a.approved_date
FROM apt_master am LEFT JOIN apartments a ON am.complex_code = a.complex_code
```
`apartments.lat / apartments.lng` 미포함 → `c.get("lat") = None` → PoiCollector 스킵.

**조치 계획:**  
LEFT JOIN SELECT에 `a.lat, a.lng` 추가.  
`AptMasterEntry` 모델에 `lat: Optional[float]`, `lng: Optional[float]` 필드 추가.  
`_row_to_entry()` 에 lat/lng 키 가드 추가.

---

### ISSUE-03: 출퇴근 시간 전부 미수집 (표시: "?분")

**증상:** 모든 단지 `commute_transit_minutes = None`, `_score_commute = neutral(50)`.  
**근본 원인 (환경 설정 누락):**

`TMAP_API_KEY` 가 `.env` 및 `docker-compose.yaml` 에 미등록.  
`TmapClient(api_key="")` → API 호출 실패 → CommuteService 예외 후 건너뜀.

**조치 계획:**  
`.env.example` 에 `TMAP_API_KEY=` 항목 추가 (가이드).  
실제 키 발급 후 `.env` 및 Docker 환경변수에 등록.

---

### ISSUE-04: 전체 후보 동점 65점 — 점수 무차별화

**증상:** Top 5가 모두 65.0점 → 우선순위 판단 불가.  
**근본 원인 (복합):**

ISSUE-01~03 의 연쇄 효과 + 필터 설계 문제.

| 기준 | 점수 | 원인 |
|------|------|------|
| commute | 50 (neutral) | TMAP 키 없음 (ISSUE-03) |
| liquidity | 100 (HIGH) | min_household_count=500 → 모두 500세대 이상 |
| school | 50 (neutral) | POI 없음 (ISSUE-02) |
| living_convenience | 50 (neutral) | POI 없음 (ISSUE-02) |
| price_potential | 60 (MEDIUM) | 2014-2015년 준공 (11-12년), FAR 150-177% |

가중합: (50×25 + 100×25 + 50×8 + 50×17 + 60×25) / 100 = **65점** — 전 단지 동일.

`min_household_count=500` 으로 liquidity 기준이 사전에 고정되어, 이 점수로는 차별화 효과 없음.

**조치 계획:**  
ISSUE-02, 03 해소 시 자연스럽게 차별화 회복.  
`liquidity` 점수를 '세대수 절대값'이 아닌 **상대 순위 기반 분포** 로 재설계 검토.

---

### ISSUE-05: 예산(13.5억) 대비 현실 부적합 후보 출력

**증상:** 추천 Top 5 전원 17.5억~23.8억 → 모두 "예산 초과".  
**근본 원인 (페르소나 설계 불일치):**

`persona.interest_areas` = [강남구, 서초구, 분당구, 송파구, 성동구].  
강남구/서초구 84㎡ 평균가 ≥ 20억 → 13.5억 예산으로 구매 불가.  
리포트 파이프라인에 예산 초과 후보를 필터하거나 페널티 주는 로직 없음.  
`budget_band_ratio(10%)` 설정은 있으나 `generate_professional_report` 에서 미사용.

**조치 계획:**

단기 — `score_all()` 에서 예산 초과 단지에 price_potential 패널티 부여.  
중기 — `persona.interest_areas` 에 예산 내 지역(마포구, 광진구, 성남시 수정구 등) 추가.  
중기 — 예산 ±20% 범위 내 후보를 우선 정렬, 초과 후보는 하단 배치.

---

### ISSUE-06: _build_markdown의 실거래가 면적 라벨 잔존 하드코딩

**증상:** 일부 코드 경로에서 `(84㎡ 기준)` 고정 출력 (Task 6에서 수정 완료 — 확인 필요).  
**현재 상태:** `trend.avg_price_eok()` + `_trend_area_sqm` 동적 처리로 수정됨.  
**잔존 위험:** `trend.avg_price_eok()` 내부가 외부 면적 정보 없이 고정 반환하는지 확인 미완.

---

## 결론 및 다음 스프린트 우선순위

| 우선순위 | 이슈 | 효과 | 공수 |
|---------|------|------|------|
| P0 | ISSUE-01 (LLM 분석 빈칸) | 입지/학군/전략 섹션 복원 | 小 |
| P0 | ISSUE-02 (lat/lng 누락) | POI 수집 → 역세권/학군 점수 실질화 | 中 |
| P1 | ISSUE-03 (TMAP 키 미등록) | 출퇴근 시간 실측 → commute 점수 실질화 | 小 (환경 설정) |
| P1 | ISSUE-04 (동점) | P0+P1 해소 후 자동 개선 | — |
| P2 | ISSUE-05 (예산 부적합) | 현실적 추천 후보 출력 | 中 |
