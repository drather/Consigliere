# Location Scoring Redesign — Progress

**브랜치:** `feature/location-scoring-redesign`
**시작일:** 2026-05-09

---

## Phase 1: Planning

- [x] spec.md 작성
- [x] progress.md 생성
- [x] 구현 계획서 작성 (`docs/superpowers/plans/2026-05-09-location-scoring-redesign.md`)

---

## Phase 2: Implementation

### Task 1: POI Collector 확장 — 6개 신규 카테고리
- [ ] PoiData 필드 6개 추가 (convenience, pharmacy, medical, park, restaurant, cafe)
- [ ] DB DDL 신규 컬럼 추가 + `_migrate()` 메서드
- [ ] `_fetch_and_cache` 수집 로직 추가
- [ ] `_save_cache` / `_load_cache` 업데이트
- [ ] 테스트 통과

### Task 2: location 패키지 스캐폴드
- [ ] `BaseDimension` 추상 클래스
- [ ] `LocationScore` dataclass
- [ ] `LocationRepository` SQLite
- [ ] 테스트 통과

### Task 3: 실거주 Dimension 5개
- [ ] TransportationDimension
- [ ] EducationDimension
- [ ] LivingInfraDimension
- [ ] MedicalDimension
- [ ] NatureDimension
- [ ] 테스트 통과 (16개)

### Task 4: 투자 Dimension 4개
- [ ] CommercialDimension
- [ ] PricePotentialDimension
- [ ] LiquidityDimension
- [ ] SchoolPremiumDimension
- [ ] 테스트 통과 (27개)

### Task 5: LocationScorer + config.yaml
- [ ] LocationScorer 완성 (registry + 가중치 normalize)
- [ ] config.yaml scoring 섹션 재작성
- [ ] 통합 테스트 통과 (35개)

### Task 6: 오케스트레이터 교체
- [ ] report_orchestrator.py — POI 필드 매핑 + LocationScorer 교체
- [ ] insight_orchestrator.py — LocationScorer 교체
- [ ] 전체 테스트 PASS

### Task 7: ScoringEngine 제거 + 데일리 POI Job
- [ ] scoring.py 삭제
- [ ] test_scoring.py 삭제
- [ ] POST /jobs/poi/collect 엔드포인트 추가
- [ ] 전체 테스트 PASS

### Task 8: 대시보드 UI
- [ ] 실거주/투자 2-score 카드 추가
- [ ] 항목별 breakdown expander
- [ ] 전체 테스트 PASS

---

## Phase 2.5: SOLID Review

- [ ] SRP: 각 Dimension 클래스 단일 책임
- [ ] OCP: 새 Dimension 추가 시 기존 코드 불변
- [ ] DIP: LocationScorer → BaseDimension 인터페이스 의존
- [ ] Zero Hardcoding: 모든 임계값 config.yaml
- [ ] 에러 처리: POI 미수집 시 data_absent_neutral 반환

---

## Phase 3: Documentation

- [ ] issues.md 작성
- [ ] result.md 작성 (walkthrough + 검증 증거)
- [ ] history.md 업데이트
