# Progress: apt_master_map_integration

**Feature Branch:** `feature/apt_master_map_integration`
**시작일:** 2026-04-11

---

## Phase 0: Preparation
- [x] 피처 브랜치 생성 (`feature/apt_master_map_integration`)
- [x] docs 디렉토리 생성
- [ ] active_state.md 업데이트

## Phase 1: Planning
- [x] spec.md 작성
- [x] progress.md 생성
- [ ] spec 커밋

## Phase 2: Implementation (TDD)

### Red (테스트 먼저)
- [ ] `tests/test_map_view.py` — `render_master_map_view` 테스트 추가
  - [ ] 빈 masters → 빈 지도 반환
  - [ ] 거래있음 → 파란 마커
  - [ ] 거래없음 → 회색 마커
  - [ ] 팝업 HTML에 단지명 포함 확인
- [ ] `tests/test_map_view.py` — `_build_master_popup_html` 테스트 추가
  - [ ] 거래있음: 이력 표시
  - [ ] 거래없음: "저장된 거래 이력이 없습니다"
  - [ ] 최대 10건 제한
- [ ] `tests/test_apt_master_map.py` (신규) — `get_transactions_by_district_codes` 테스트
  - [ ] 단일 district_code 조회
  - [ ] apt_names 필터 동작
  - [ ] 빈 결과 처리

### Green (최소 로직 구현)
- [ ] `src/dashboard/components/map_view.py`
  - [ ] `_build_master_popup_html()` 추가
  - [ ] `render_master_map_view()` 추가
- [ ] `src/dashboard/api_client.py`
  - [ ] `get_transactions_by_district_codes()` 추가
- [ ] `src/dashboard/views/real_estate.py`
  - [ ] import `render_master_map_view` 추가
  - [ ] Tab5 서브탭 구조 추가 (📋 단지 목록 / 🗺️ 지도 뷰)
  - [ ] 지도 로드 버튼 + 캐시 로직
  - [ ] `get_transactions_by_district_codes()` 호출
  - [ ] `render_master_map_view()` 호출
  - [ ] `st_folium` 렌더링

## Phase 2.5: SOLID Review
- [ ] SRP: render_master_map_view는 렌더링만, get_transactions_by_district_codes는 페칭만
- [ ] Zero Hardcoding: limit_per_district 파라미터로 노출
- [ ] 테스트 가능성: geocoder 의존성 주입 확인

## Phase 3: Documentation
- [ ] issues.md 작성
- [ ] result.md 작성
- [ ] history.md 업데이트
- [ ] active_state.md 업데이트

## Phase 4: Release
- [ ] 전체 테스트 통과 (`arch -arm64 .venv/bin/python3.12 -m pytest tests/ -v`)
- [ ] master 머지 및 push
