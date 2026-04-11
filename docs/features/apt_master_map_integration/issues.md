# Issues & Decisions: apt_master_map_integration

## DECISION-01: 트랜잭션 조회 전략 — Option B (district_code 광역 조회)

**결정:** 단지별 N번 API 호출 대신 district_code 단위로 호출 후 Python 필터링.

**배경:** 검색 결과가 수십~수백 개 단지일 경우, 단지당 API 1회씩 호출하면 수백 번의 HTTP 요청 발생. district_code 종류는 보통 1~5개로 훨씬 적음.

**트레이드오프:**
- 장점: HTTP 요청 수 대폭 감소, 응답 속도 향상
- 단점: district_code 당 limit=500건 이내로 조회되므로 거래 빈도 높은 지구에서 일부 누락 가능

**결론:** 대시보드 탐색 목적에는 500건이 충분. 정밀 분석용도면 추후 limit 파라미터 노출로 해결.

---

## DECISION-02: folium Icon 색상 키 — `marker_color` (snake_case)

**문제:** `icon.options["color"]` → KeyError. `icon.options["markerColor"]` → KeyError.

**원인:** folium 내부에서 Icon 옵션이 `marker_color`(snake_case)로 저장됨.

**해결:** 테스트 assertion을 `icon.options.get("marker_color")`로 수정.

---

## DECISION-03: 지도 렌더링 방식 — 지연 로드(Lazy Load)

**결정:** Tab5 진입 시 자동 렌더링 대신 "지도 로드" 버튼 클릭 시 렌더링.

**이유:**
- 검색 결과마다 즉시 geocoding + API 호출하면 탭 전환 자체가 느려짐
- 사용자가 목록 먼저 확인 후 필요할 때만 지도 로드하는 UX가 더 자연스러움

---

## DECISION-04: 캐시 무효화 — 해시 기반

**결정:** 검색 결과 단지 키 집합의 hash를 `master_map_cache_key`로 사용.

**이유:** 검색 조건이 바뀌면 결과 단지가 달라지고 hash가 달라져 자동으로 캐시 무효화됨. 별도 버전 관리 불필요.

---

---

## BUG-01: `name 'districts' is not defined` — Tab5 로컬 스코프 문제

**발생:** Tab5 `try:` 블록 내부에서 `districts`를 로컬 변수로 참조.  
**원인:** 다른 탭은 `st.session_state.get("districts", [])` 패턴을 쓰는데, Tab5 구현 시 미적용.  
**수정:** `districts` → `st.session_state.get("districts", [])` (real_estate.py line 892)  
**상태:** ✅ 수정 완료

---

## BUG-02: `GeocoderService.__init__() got an unexpected keyword argument 'kakao_api_key'`

**발생:** Tab5 지도 로드 시 GeocoderService 초기화 오류.  
**원인:** `GeocoderService.__init__`의 파라미터명은 `api_key`인데 `kakao_api_key`로 호출.  
**수정:** `GeocoderService(kakao_api_key=_kakao_key)` → `GeocoderService(api_key=_kakao_key)`  
**상태:** ✅ 수정 완료

---

## BUG-03: 지도 깜빡임 / 미표시 (브라우저 테스트)

**발생:** Streamlit 리렌더링 시 st_folium 컴포넌트가 깜빡이거나 지도가 표시되지 않음.  
**원인 분석:**
  1. `st_folium()` 호출 시 `key` 파라미터 미지정 → Streamlit이 동일 컴포넌트를 구분 못해 매 렌더링마다 재생성
  2. 마커 수가 많을 때 브라우저 렌더링 부하 (단지 수백 개)

**수정:**
  - Tab1: `st_folium(..., key="monitor_map")` 추가
  - Tab5: `st_folium(..., key="master_map")` 추가
  - Tab5: 지도 표시 상위 100개 단지로 제한 (`results[:100]`)
  - `render_map_view` / `render_master_map_view` 모두 `MarkerCluster` 적용 (브라우저 부하 감소)
  - 테스트: `_collect_markers()` 헬퍼 추가 (MarkerCluster 내부까지 탐색)

**상태:** ✅ 1차 수정 완료. 단, 근본 해결은 미완 (아래 ISSUE-01 참조)

---

## ISSUE-01: 지도 깜빡임 근본 해결 미완 (다음 세션 이어받기)

**현상:** `key` 파라미터 + MarkerCluster 적용으로 개선됐으나, Streamlit 세션 상태 변경이 많을 때 여전히 리렌더링이 발생할 수 있음.

**근본 원인 후보:**
  1. Tab5 내부 위젯(검색 필터, 슬라이더 등)이 변경되면 전체 페이지가 rerun → `st_folium` 재마운트
  2. `st.session_state.master_map_cache_key` 비교 로직이 매 rerun마다 재실행됨
  3. `results[:100]` 슬라이싱은 임시 방편 — 올바른 해결은 `st.cache_data` 또는 캐시 더 앞단 이동

**다음 세션 TODO:**
  - [ ] `st_folium`에 `returned_objects=[]` 옵션 추가로 불필요한 상태 반환 차단
  - [ ] 지도 렌더링 로직을 `@st.cache_data` 또는 `@st.fragment`로 분리 검토
  - [ ] 마커 수 100개 제한 → 사용자 설정 가능하도록 슬라이더 추가 검토

---

## DECISION-05: 기존 Tab1 render_map_view 미변경

**결정:** `render_map_view()`는 건드리지 않고 `render_master_map_view()`를 별도 신규 추가.

**이유:** Tab1은 광역 거래 데이터 중심, Tab5는 단지 마스터 중심으로 진입점과 데이터 구조가 다름. OCP 준수.
