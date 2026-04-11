# Result: apt_master_map_integration

**완료일:** 2026-04-11
**브랜치:** `feature/apt_master_map_integration`

---

## 구현 요약

Tab5(🏗️ 아파트 마스터 검색)에 지도 뷰를 통합하여, 기존 필터 검색 결과를 지도 마커로 시각화하고 각 마커 팝업에 해당 단지의 실거래가 이력을 표시하는 기능을 완성했다.

---

## 변경 파일

| 파일 | 변경 내용 |
|------|----------|
| `src/dashboard/components/map_view.py` | `_build_master_popup_html()`, `render_master_map_view()` 함수 2개 추가 |
| `src/dashboard/api_client.py` | `get_transactions_by_district_codes()` 메서드 추가 |
| `src/dashboard/views/real_estate.py` | import 추가, Tab5 블록 서브탭 구조로 재편 |
| `tests/test_map_view.py` | render_master_map_view, _build_master_popup_html 테스트 12개 추가 |
| `tests/test_apt_master_map.py` | get_transactions_by_district_codes 테스트 7개 (신규) |

---

## 테스트 결과

```
tests/test_map_view.py         16 passed
tests/test_apt_master_map.py    7 passed
합계: 23 passed
```

---

## 기능 설명

### Tab5 레이아웃 변경

**Before:** 필터 → 검색 → 테이블 → 단지 상세 expander

**After:** 필터 → 검색 → 서브탭 [📋 단지 목록 | 🗺️ 지도 뷰]
- 📋 단지 목록: 기존 테이블 + expander 그대로 유지
- 🗺️ 지도 뷰: 지도 로드 버튼 → 마커 지도 표시

### 마커 색상 규칙
- 파란 마커: 저장된 실거래가 이력이 있는 단지
- 회색 마커: 거래 이력 없는 단지

### 팝업 구성
```
[단지명]
[도로명 주소]
──────────────
세대수: N세대 | 준공: YYYY년 | 건설사: XXX
──────────────
실거래가 이력 (최신순, 최대 10건)
YYYY-MM-DD | 84.5㎡ | 15억 2,000만원
...
```

### 캐시 전략
- 검색 결과 단지 키 집합 hash → 변경 시 자동 재렌더링
- 초기화 버튼으로 강제 캐시 초기화 가능

### API 호출 최적화
- district_code 단위 광역 조회 (보통 1~5회)
- Python 레벨 apt_name 필터링으로 단지별 N번 호출 방지

---

## SOLID 검증

| 원칙 | 적용 |
|------|------|
| SRP | 렌더링(map_view.py) / 페칭(api_client.py) / 뷰(real_estate.py) 역할 분리 |
| OCP | 기존 render_map_view() 미수정, 신규 함수 추가로 확장 |
| DIP | geocoder 의존성 주입 (GeocoderProtocol 인터페이스 사용) |
| Zero Hardcoding | limit_per_district=500 파라미터로 노출 |
