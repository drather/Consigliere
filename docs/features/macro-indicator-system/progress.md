# Progress: 거시경제 지표 수집 시스템

**작성일:** 2026-04-18

---

## Task 체크리스트

- [x] **Task 1:** MacroIndicatorDef, MacroRecord 데이터 모델 정의
- [x] **Task 2:** MacroRepository SQLite CRUD (TDD 12 tests)
- [x] **Task 3:** BOKClient 공유 모듈 이전 및 frequency/item_code 파라미터 추가
- [x] **Task 4:** MacroCollectionService 수집 오케스트레이션 (TDD 8 tests)
- [x] **Task 5:** BOK item_code 검증 및 시딩 스크립트
- [x] **Task 6:** API Router 추가 (`/jobs/macro/collect`, `/dashboard/macro/latest`, `/dashboard/macro/history/{id}`)
- [x] **Task 7:** real_estate 매크로 어댑터 교체 + 구 파일 삭제
- [x] **Task 8:** 초기 데이터 수집 실행 (8개 지표)
- [x] **Task 9:** 대시보드 거시경제 탭 카테고리 서브탭 확장
- [x] **Task 10:** 최종 검증 및 정리

## 버그픽스 (머지 후)

- [x] BOK_API_KEY Docker 컨테이너 미주입 → `--force-recreate`로 해결
- [x] BOKClient Q frequency 날짜 포맷 버그 (`%Y%m` → `{Y}Q{n}`)
- [x] 5개 지표 stat_code 오류 수정 (M2, 가계신용, CPI, GDP, COFIX 비활성화)
- [x] 대시보드 십억원 단위 → 조원 표시 수정 (/ 1000)
- [x] st.stop() 전역 종료 버그 → _render_apt_search_tab() 분리 + return 교체
