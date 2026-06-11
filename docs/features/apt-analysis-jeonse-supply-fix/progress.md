# Progress

- [x] Task 1: 근본 원인 조사 (systematic-debugging Phase 1~2)
- [x] Task 2: `JeonseRepository.get_by_apt_name()` 추가 (TDD)
- [x] Task 3: `_calc_jeonse_ratio` 수정 (조회 방식 + 단위 변환, TDD)
- [x] Task 4: `_get_supply_risk` SupplyRiskAnalyzer DI 수정 (TDD)
- [x] Task 5: `dependencies.py` DI 배선 수정 (Apt Analysis 블록 위치 이동 + geocoder/news_service/prompt_loader 주입)
- [x] Task 6: `JeonseClient._parse()` XML 태그 수정 (한글 → 실제 영문 태그, TDD)
- [x] Task 7: 전체 테스트 실행 (889 passed, pre-existing 7 failed — 무관)
- [x] Task 8: `POST /jobs/jeonse/collect` 실행 (8,180건 저장)
- [x] Task 9: API 컨테이너 재시작 + E2E 검증 (`A10025850` 헬리오시티: jeonse_ratio=37.9, supply_risk_summary 정상 반환)
- [x] Task 10: SOP 문서화 (spec/progress/issues/result + context 갱신)
