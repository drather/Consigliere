# report-quality-overhaul — Result

**브랜치:** `feature/report-quality-overhaul`  
**완료일:** 2026-05-02  
**작업자:** kks

---

## 구현 결과 요약

### 이전 (2026-05-01 리포트)

| 항목 | 상태 |
|------|------|
| 추천 단지 | 소형 오피스텔·소단지 (500세대 미만) |
| 실거래가 | 0.0억 (데이터 매핑 실패) |
| 건축연도/용적률 | 미표시 |
| 입지/학군 분석 | LLM 호출 성공 (데이터 있을 때) |
| 출퇴근 | 미수집 |
| 총점 | 59점 (전 단지 동점) |

### 이후 (2026-05-02 리포트)

| 항목 | 상태 |
|------|------|
| 추천 단지 | 500세대 이상 대단지 정상 필터링 |
| 실거래가 | 84㎡/99㎡ 멀티 면적 탐색, 실제 가격 표시 (17.5억~23.8억) |
| 건축연도/용적률/건폐율 | building_master JOIN으로 정상 표시 |
| 입지/학군 분석 | **빈 칸** (ISSUE-01 미해결) |
| 출퇴근 | 미수집 (ISSUE-03 미해결) |
| 총점 | 65점 (전 단지 동점 — ISSUE-02 미해결) |

---

## 구현된 변경 사항

### 1. AptMasterRepository.search() — 세대수 필터 + LEFT JOIN
- `min_household_count` 파라미터 추가
- `apartments` 테이블 LEFT JOIN → `household_count`, `road_address`, `approved_date` 조인

### 2. AptMasterEntry 모델 필드 추가
- `household_count: Optional[int]`
- `road_address: Optional[str]`
- `approved_date: Optional[str]`

### 3. ReportOrchestrator — building_master 조인
- `_enrich_with_building()`: pnu → building_master → FAR/BCR/build_year 채움
- `approved_date` 파생 build_year fallback 추가

### 4. ReportOrchestrator — commute 파이프라인 연결
- `_resolve_workplace_coords()`: persona.commute.workplace_station → lat/lng
- `_enrich_with_commute()`: CommuteService.get() dest_override 지원

### 5. ReportOrchestrator — 멀티 면적 실거래가 탐색
- `_enrich_with_trend()`: preferred_areas 순차 탐색 (84㎡ 없으면 99㎡ fallback)

### 6. _build_markdown — 동적 면적 라벨
- `(84㎡ 기준)` 하드코딩 → `c.get('_trend_area_sqm', 84)` 동적 적용

### 7. PoiCollector — 학교 쿼리 분리
- `"초등학교 중학교"` 단일 → `"초등학교"` + `"중학교"` 분리 + id/place_name dedup

### 8. generate_professional_report 엔드포인트
- min_household_count 파라미터 persona 연동
- CommuteService, GeocoderService orchestrator 주입
- candidates limit 50 → 100 확장

---

## 미해결 이슈 (다음 스프린트로 이관)

`docs/features/report-quality-overhaul/issues.md` 참조.

- **ISSUE-01** (P0): LLM 입지/학군 분석 빈칸 — Jinja2/load_with_cache_split 불일치
- **ISSUE-02** (P0): lat/lng 누락 → POI 전체 실패 → 점수 무차별화
- **ISSUE-03** (P1): TMAP_API_KEY 미등록 → 출퇴근 미수집
- **ISSUE-05** (P2): 예산 대비 후보 부적합 (interest_areas 확장 필요)

---

## E2E 검증 면제

- **사유:** 화면단(Streamlit) 변경 없음 — 백엔드 리포트 생성 파이프라인만 수정
- **변경 범위:** `src/modules/real_estate/report_orchestrator.py`, `apt_master_repository.py`, `poi_collector.py`, `commute/commute_service.py`, `models.py`, `src/api/routers/real_estate.py`
