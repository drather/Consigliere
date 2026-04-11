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

## DECISION-05: 기존 Tab1 render_map_view 미변경

**결정:** `render_map_view()`는 건드리지 않고 `render_master_map_view()`를 별도 신규 추가.

**이유:** Tab1은 광역 거래 데이터 중심, Tab5는 단지 마스터 중심으로 진입점과 데이터 구조가 다름. OCP 준수.
