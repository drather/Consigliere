# Feature: 부동산 실거래가 지도 시각화

**작성일:** 2026-03-31
**브랜치:** feature/real-estate-map-view
**상태:** Confirmed

---

## 1. 목표

현재 테이블로만 표시되는 실거래가 데이터를 지도 위에 시각화한다.
실거래가가 있는 아파트 위치에 마커를 표시하고, 마커 클릭 시 해당 아파트의 거래 이력을 최신순으로 보여준다.

---

## 2. 핵심 동작

- **마커:** 실거래가 데이터가 존재하는 아파트 단위로 1개 마커 (거래 건별 마커 아님)
- **팝업 내용:** 아파트명 + 거래 이력 최신순 리스트 (거래일 | 전용면적 | 거래금액)
- **필터 공유:** 기존 tab1의 시/구, 아파트명, 날짜 범위, 금액 범위 필터와 동일하게 적용

---

## 3. UI 구조

```
tab1: 📊 Market Monitor
  ├── sub-tab A: 📋 거래 목록  (기존 테이블, 변경 없음)
  └── sub-tab B: 🗺️ 지도 뷰  (신규)
        - 필터: 기존과 동일
        - 지도: folium (OpenStreetMap 배경)
        - 마커: 아파트별 1개, 클릭 시 팝업
        - 팝업:
            아파트명: 래미안 퍼스티지
            ──────────────────────
            2026-03-15 | 84.97m² | 25억 5,000만원
            2026-02-20 | 59.91m² | 18억 2,000만원
            2026-01-08 | 84.97m² | 24억 9,000만원
```

---

## 4. 기술 스택

| 항목 | 결정 |
|------|------|
| 지오코딩 | 카카오 Local API (keyword 검색) |
| 지오코딩 캐시 | SQLite (`data/geocode_cache.db`) |
| 지도 라이브러리 | `folium` + `streamlit-folium` |

---

## 5. 데이터 처리 흐름

```
1. 현재 필터 조건으로 transactions 조회
2. apt_name + district_code 기준으로 그룹핑
3. 각 아파트 그룹에 대해 GeocoderService.geocode() 호출
   - 캐시 히트 → 즉시 반환
   - 캐시 미스 → 카카오 API 호출 → 캐시 저장
4. 좌표 획득 성공한 아파트만 마커 생성
5. 각 마커 팝업에 해당 아파트 거래 이력 최신순 렌더링
```

---

## 6. 구현 범위

### 신규 파일

| 파일 | 역할 |
|------|------|
| `src/modules/real_estate/geocoder.py` | `GeocoderService` — 카카오 API 호출, SQLite 캐시 |
| `src/dashboard/components/map_view.py` | `render_map_view(df)` — folium 지도 렌더링 |
| `tests/modules/real_estate/test_geocoder.py` | GeocoderService 단위 테스트 |
| `tests/test_map_view.py` | 지도 컴포넌트 단위 테스트 |

### 수정 파일

| 파일 | 변경 내용 |
|------|----------|
| `src/dashboard/views/real_estate.py` | tab1에 서브탭 추가, `render_map_view` 호출 |
| `requirements.txt` | `folium`, `streamlit-folium` 추가 |

### 변경 없음

| 파일 | 이유 |
|------|------|
| `src/modules/real_estate/models.py` | lat/lng는 런타임 지오코딩으로 처리, 모델 변경 불필요 |
| `src/modules/real_estate/repository.py` | 기존 조회 그대로 사용 |

---

## 7. GeocoderService 인터페이스

```python
class GeocoderService:
    def __init__(self, api_key: str, cache_path: str = "data/geocode_cache.db")

    def geocode(self, apt_name: str, district_code: str) -> Optional[tuple[float, float]]
    # 반환: (lat, lng) 또는 None

    def batch_geocode(self, apt_keys: list[dict]) -> dict[str, tuple[float, float]]
    # apt_keys: [{"apt_name": str, "district_code": str}, ...]
    # 반환: {"apt_name__district_code": (lat, lng), ...}
```

**SQLite 캐시 스키마:**
```sql
CREATE TABLE geocode_cache (
    cache_key TEXT PRIMARY KEY,  -- "{district_code}__{apt_name}"
    lat REAL,
    lng REAL,
    created_at TEXT
)
```

---

## 8. 테스트 계획

### `test_geocoder.py` (6개)
- `test_geocode_cache_hit` — 캐시 히트 시 API 미호출
- `test_geocode_cache_miss_calls_api` — 캐시 미스 시 카카오 API mock 호출
- `test_geocode_returns_none_on_api_failure` — API 실패 시 None 반환
- `test_batch_geocode_returns_dict` — 배치 결과 dict 구조 확인
- `test_batch_geocode_skips_failed` — 실패 항목 결과에서 제외
- `test_cache_persistence` — SQLite 저장/재로드 확인

### `test_map_view.py` (4개)
- `test_render_map_returns_folium_map` — folium.Map 반환 확인
- `test_render_map_empty_df` — 빈 df 입력 시 에러 없이 빈 지도 반환
- `test_marker_count_matches_apts` — 아파트 수만큼 마커 생성
- `test_popup_contains_apt_name` — 팝업 HTML에 아파트명 포함

---

## 9. 완료 기준

- [ ] GeocoderService 구현 및 테스트 10개 통과
- [ ] `data/geocode_cache.db` SQLite 캐시 정상 동작
- [ ] folium 지도에 아파트별 마커 렌더링
- [ ] 마커 팝업에 거래 이력 최신순 표시
- [ ] tab1에 서브탭(거래 목록 / 지도 뷰) 정상 동작
- [ ] `arch -arm64 .venv/bin/python3.12 -m pytest tests/ -v` 전체 통과
