# Location Scoring Redesign — Issues & Decisions

**브랜치:** `feature/location-scoring-redesign`

---

## 결정 사항

### D-01: 실거주/투자 이중 점수 (Option C)
- **결정:** 단일 종합점수 대신 실거주 + 투자 두 점수를 병렬 제공
- **근거:** 실거주자(생활 편의)와 투자자(가격 상승 잠재력)의 니즈가 다름. 동일 단지에 두 관점 제공

### D-02: 하이브리드 아키텍처 (Dimension 클래스 + config 가중치)
- **결정:** Dimension 구현체는 Python 클래스, 가중치/임계값은 config.yaml
- **근거:** 타입 안전 + 테스트 가능 + 코드 변경 없이 가중치 조정 가능

### D-03: 수집 트리거 — 리포트 생성 on-demand + 데일리 Job
- **결정:** 대시보드는 cache-only, 리포트 생성 시 on-demand 수집, 데일리 Job으로 선제 워밍
- **근거:** 93개 단지 전체를 대시보드 접근 시마다 수집하면 API 한도 초과

### D-04: LocationRepository 영속 커넥션
- **결정:** sqlite3.connect() per-call 대신 영속 커넥션(self._conn) 사용
- **근거:** `:memory:` DB는 connect() 호출마다 새 DB 생성 → 테스트에서 DDL이 보이지 않는 문제

---

## 버그 / 수정 사항

### B-01: empty distance string → ValueError
- **발견:** 코드 품질 리뷰에서 발견
- **원인:** Kakao API가 `distance` 필드를 빈 문자열로 반환 가능. `int("")` → ValueError
- **수정:** `int(p.get("distance") or 0)` 패턴으로 변경 (2곳: `_parse_stations`, `_fetch_and_cache`)

### B-02: ScoringEngine 호환 테스트 파일 추가 삭제
- **발견:** `test_scoring_liquidity.py`, `test_scoring_neutral_defaults.py`가 계획에 없었으나 ScoringEngine import로 발견됨
- **수정:** 해당 파일 삭제 (ScoringEngine 제거로 더 이상 유효하지 않음)
- **영향:** 해당 로직은 LiquidityDimension, MedicalDimension 등으로 대체됨

### B-03: academies_count 상한 문제 (기존)
- **배경:** 이전 fix(poi) 커밋에서 이미 수정됨 (`_search_paged` 도입)
- **현재:** 최대 45개 수집 가능 (3페이지 × 15)
