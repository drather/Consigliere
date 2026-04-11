# Feature Spec: 아파트 마스터 + 실거래가 지도 통합

**작성일:** 2026-04-11
**Feature Branch:** `feature/apt_master_map_integration`

---

## 1. 배경 및 목표

현재 Tab5(🏗️ 단지 검색)는 마스터 DB 필터 + 테이블 목록 + expander 상세 보기만 있고 지도가 없다.
Tab1(📊 Market Monitor)은 지도가 있으나 실거래가 중심이라 단지 맥락이 없다.

| 문제 | 현황 | 목표 |
|------|------|------|
| 마스터 검색 결과가 텍스트 목록뿐 | 지도로 위치 파악 불가 | 검색된 단지들이 지도 마커로 표시 |
| 단지와 실거래가가 분리된 탭 | 단지 → 거래 흐름이 단절 | 마커 팝업에 해당 단지 실거래가 이력 표시 |

---

## 2. 작업 범위

### Tab5 레이아웃 재편
- 검색 결과를 **서브탭(📋 단지 목록 / 🗺️ 지도 뷰)** 으로 분리
- 📋 단지 목록: 기존 테이블 + expander 상세 보기 그대로 유지
- 🗺️ 지도 뷰: 신규 추가

### 🗺️ 지도 뷰 동작
1. "지도 로드" 버튼 클릭 → lazy loading (검색마다 자동 로드하지 않음)
2. 검색된 단지들의 실거래가를 district_code별 광역 조회 후 Python 필터링
3. 각 단지 지오코딩(Kakao API + SQLite 캐시) → 마커 생성
4. 마커 팝업: 단지 기본정보 + 실거래가 이력(최신 10건)
5. 마커 색상: 파란색(거래있음) / 회색(거래없음)
6. 검색 조건 변경 시 캐시 자동 무효화

### Tab1 변경 없음
- 광역 실거래가 조회 기능 유지

---

## 3. 아키텍처 설계

### 데이터 흐름

```
사용자 필터 입력
        ↓
ApartmentMasterRepository.search()
        ↓ List[ApartmentMaster]
st.session_state.master_results
        │
        ├─ sub_tab 📋: 기존 테이블 그대로
        │
        └─ sub_tab 🗺️: [지도 로드] 버튼
                            ↓
           DashboardClient.get_transactions_by_district_codes(
               district_codes=[dc1, dc2, ...],  ← master에서 추출
               apt_names={name1, name2, ...}    ← master에서 추출
           )
                            ↓ pd.DataFrame
           GeocoderService.batch_geocode(apt_keys)
                            ↓ {cache_key: (lat, lng)}
           render_master_map_view(masters, tx_df, geocoder)
                            ↓ folium.Map
           st_folium(fmap)
```

### 트랜잭션 페칭 전략 (Option B)
- N개 단지마다 개별 API 호출 대신, district_code 종류 수만큼(보통 1~5회) 호출
- 반환된 데이터를 apt_name 집합으로 Python 필터링
- 이유: N개 호출은 결과가 수백 건일 때 성능 문제. apt_name 부분검색은 마스터 명칭과 불일치 가능

---

## 4. 신규 함수/메서드

### `src/dashboard/components/map_view.py`

**`_build_master_popup_html(master, transactions: pd.DataFrame) -> str`**
- 기존 `_format_price()` 재사용
- 팝업 구조: 단지명 + 주소 + 기본정보 + 실거래가 이력

**`render_master_map_view(masters, transactions_df, geocoder) -> folium.Map`**
- Tab5 전용. 기존 `render_map_view()`는 건드리지 않음
- `masters: List[ApartmentMaster]` + `transactions_df: pd.DataFrame` (빈 DataFrame 허용)
- 마커 색상: 거래있음=blue, 거래없음=gray

### `src/dashboard/api_client.py`

**`get_transactions_by_district_codes(district_codes, apt_names, limit_per_district) -> pd.DataFrame`**
- district_code별 광역 조회 후 apt_names 집합으로 Python 필터링

---

## 5. 테스트 계획

| 테스트 파일 | 케이스 |
|------------|--------|
| `tests/test_map_view.py` | `render_master_map_view`: 빈 masters, 거래있음/없음 마커, 팝업 HTML 내용 |
| `tests/test_map_view.py` | `_build_master_popup_html`: 거래있음/없음, 주소없음, 최대 10건 제한 |
| `tests/test_apt_master_map.py` (신규) | `get_transactions_by_district_codes`: 단일/복수 코드, apt_names 필터, 빈결과 |

---

## 6. 세션 스테이트 관리

| 키 | 타입 | 용도 |
|---|------|------|
| `master_results` | `List[ApartmentMaster]` | 검색 결과 (기존) |
| `master_tx_df` | `pd.DataFrame` | 실거래가 (신규) |
| `master_cached_fmap` | `folium.Map` | 렌더링된 지도 (신규) |
| `master_map_cache_key` | `str` | 재렌더링 감지용 해시 (신규) |

---

## 7. 참조
- `src/dashboard/components/map_view.py` — 기존 `render_map_view()` 패턴
- `src/modules/real_estate/geocoder.py` — `GeocoderService.batch_geocode()`
- `src/dashboard/api_client.py` — `get_real_estate_transactions()` 재사용
- `tests/test_map_view.py` — MockGeocoder 패턴 재사용
