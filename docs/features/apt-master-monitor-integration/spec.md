# Spec: 아파트 마스터 × Market Monitor 통합 탐색 허브

**Feature:** `apt-master-monitor-integration`
**작성일:** 2026-04-12
**작성자:** Orchestrator (Plan Phase)

---

## 1. 목표

현재 분리된 두 화면(Tab1 Market Monitor, Tab5 단지 검색)을 통합하여
**"아파트 필터 → 목록 → 클릭 → 상세 + 실거래가 + 지도"** 라는
단일하고 일관된 탐색 흐름을 제공한다.

---

## 2. 현황 분석 (AS-IS)

### Tab1 — Market Monitor
- **역할:** 실거래가 수집(trigger) + raw 거래 목록 조회
- **필터:** district_code, apt_name, 날짜, 금액 범위
- **출력:** 거래 테이블 + 지도 뷰
- **문제:** 아파트 마스터 정보(세대수, 건설사, 준공연도 등)가 없음

### Tab5 — 단지 검색
- **역할:** 마스터 DB 필터링 검색
- **필터:** 시도/시군구(cascading), 아파트명, 세대수, 건설사, 준공연도
- **출력:** 단지 목록 테이블 + 단지 상세 expander + 지도 뷰
- **문제:**
  - 단지 클릭 시 상세 정보(마스터)만 표시 → **실거래가 데이터 없음**
  - DB를 Streamlit에서 직접 접근 (`ApartmentMasterRepository` import)
  - Tab1의 실거래가 수집 기능과 연결 고리 없음

### 핵심 GAP
| GAP | 현재 | 목표 |
|-----|------|------|
| 단지 클릭 → 실거래가 | ❌ 없음 | ✅ 최근 실거래가 테이블 표시 |
| 마스터 필터 + 실거래가 연계 | ❌ 분리 | ✅ 단일 흐름 |
| 실거래가 수집 진입점 | Tab1만 | Tab5에서도 특정 단지 수집 가능 |

---

## 3. 목표 UX 흐름 (TO-BE)

```
Tab5: 🔍 아파트 탐색 허브
│
├── [1] 🔍 필터 섹션 (expander, 기본 펼침)
│     ├── 시도 selectbox
│     ├── 시군구 selectbox (시도 연동 cascading)
│     ├── 아파트명 text_input (부분검색)
│     ├── 세대수 범위 slider
│     ├── 건설사 selectbox
│     ├── 준공연도 범위 slider
│     └── [🔍 검색] 버튼
│
├── [2] 📋 검색 결과 목록 (N건, 클릭 가능 dataframe)
│     └── 컬럼: 아파트명 | 시군구 | 세대수 | 건설사 | 준공연도 | 최고층
│
├── [3] 선택 단지 → 서브탭 분기
│     ├── 📋 단지 상세 + 실거래가
│     │     ├── 기본정보 metric 카드 (세대수·동수·준공·최고층·건설사·난방·승강기)
│     │     ├── 면적별 세대수 (60/85/135/136+)
│     │     ├── 주소 (도로명 or 지번)
│     │     └── 최근 실거래가 테이블 (최대 50건, 날짜/면적/가격/층)
│     │           └── [📥 실거래가 수집] 버튼 (해당 단지 district 기준)
│     └── 🗺️ 지도 뷰 (검색 결과 전체, 마커 클릭 시 실거래가 팝업)
│
└── (Tab1은 현행 유지 — 실거래가 수집 + raw 조회 전용)
```

---

## 4. 아키텍처 결정

### 4.1 DB 직접 접근 유지 (현행 패턴)
- `ApartmentMasterRepository`를 Tab5에서 직접 import하는 현행 패턴 유지
- 이유: Dashboard 컨테이너가 src/ 모듈을 공유하는 현재 구조에서 API 경유는 over-engineering
- Tab1의 실거래가 조회는 기존처럼 `DashboardClient`(FastAPI) 경유

### 4.2 실거래가 조회 방식
- 특정 단지 실거래가: `DashboardClient.get_real_estate_transactions(district_code, apt_name, limit=50)`
- 이미 존재하는 메서드 재사용 (신규 추가 불필요)

### 4.3 실거래가 수집 트리거
- 단지 상세 패널 내 "📥 실거래가 수집" 버튼 → `DashboardClient.trigger_fetch_transactions(district_code)`
- 이미 존재하는 메서드 재사용

### 4.4 Tab 구조 변경
- Tab5의 탭명 변경: `🏗️ 단지 검색` → `🔍 아파트 탐색`
- Tab1(Market Monitor)은 구조 변경 없음

---

## 5. 변경 파일 목록

| 파일 | 변경 내용 | 크기 |
|------|-----------|------|
| `src/dashboard/views/real_estate.py` | Tab5 섹션 전면 재작성 | 중 |
| `src/dashboard/main.py` | Tab5 탭명 변경 (show_real_estate 내부라 불필요) | - |

**신규 추가 파일:** 없음 (기존 컴포넌트 재사용)
**DashboardClient 변경:** 없음 (기존 메서드 재사용)

---

## 6. 데이터 흐름

```
[마스터 필터 입력]
    ↓
ApartmentMasterRepository.search() — SQLite 직접
    ↓
[결과 목록 테이블] → 행 선택 (st.dataframe on_select)
    ↓
선택된 ApartmentMaster 객체
    ↓
┌── 상세 패널 ──────────────────────────────────────────────┐
│  마스터 정보 (메모리에 있음, API 불필요)                   │
│  실거래가 조회: DashboardClient.get_real_estate_transactions│
│     → /dashboard/real-estate/monitor (FastAPI)            │
│     → RealEstateRepository.get_transactions()             │
└────────────────────────────────────────────────────────────┘
    ↓
[지도 뷰] — render_master_map_view() (기존 컴포넌트 재사용)
```

---

## 7. UI 상세 설계

### 7.1 결과 목록 테이블 (현행과 동일)
```python
selection = st.dataframe(
    df_master[display_cols],
    on_select="rerun",
    selection_mode="single-row",
    key="master_table",
)
```

### 7.2 단지 상세 + 실거래가 패널 (신규)
- 선택된 단지가 있을 때만 표시 (`if selected_rows:`)
- 기본정보 metric 카드 (기존 expander 내용 → expander 제거, 직접 표시)
- 실거래가 테이블:
  ```python
  tx_df = DashboardClient.get_real_estate_transactions(
      district_code=m.district_code,
      apt_name=m.apt_name,
      limit=50,
  )
  ```
- 수집 버튼: `DashboardClient.trigger_fetch_transactions(district_code=m.district_code)`

### 7.3 지도 뷰 (현행 유지, session state 캐시)
- 검색 결과 전체 기준 지도
- `render_master_map_view(results[:100], tx_df, geocoder)` 재사용

---

## 8. 세션 스테이트 키 정의

| 키 | 용도 |
|----|------|
| `master_results` | 마스터 검색 결과 (`List[ApartmentMaster]`) |
| `master_selected_idx` | 현재 선택된 단지 인덱스 |
| `master_tx_df_{cache_key}` | 선택 단지 실거래가 DataFrame 캐시 |
| `master_cached_fmap` | 지도 folium 객체 캐시 |
| `master_map_cache_key` | 지도 캐시 무효화 키 |

---

## 9. 제약 조건

- 실거래가 테이블은 기본 미로드 (API 호출 비용) → 선택 후 자동 로드 (50건)
- 지도 뷰는 명시적 "지도 로드" 버튼 클릭 시 로드 (지오코딩 시간)
- 지도 단지 상위 100개 제한 (기존 성능 제한 유지)
- Tab1은 변경하지 않음 (실거래가 raw 조회 도구 역할 유지)

---

## 10. 테스트 계획

| 테스트 대상 | 방법 |
|-------------|------|
| `_build_apt_detail_section()` 헬퍼 분리 시 | pytest mock |
| 실거래가 로드 흐름 (단지 선택 → API 호출) | E2E 브라우저 확인 |
| 지도 렌더링 (캐시 히트/미스) | 브라우저 확인 |
| 필터 cascading (시도 → 시군구) | 브라우저 확인 |
