# Dashboard 전체 재설계 — Design Spec

**작성일:** 2026-06-09
**상태:** ✅ 사용자 승인 완료 (브레인스토밍 세션)
**범위:** 사이드바 메뉴 재편 + Real Estate 탭 구조 개선 + 아파트 탐색 탭 UI 현대화 + Automation/Jobs 통합 + Home 실데이터화

---

## 1. 핵심 목표

- **중구난방 해소:** 도메인 화면과 시스템 운영 도구가 같은 레벨에 나열된 문제 해결
- **가독성 개선:** Real Estate 탭의 과도한 중첩 (3단계) 및 "뉴스 리포트"/"데일리 리포트" 이름 충돌 제거
- **아파트 탐색 현대화:** 목록 버튼 나열 → Master-Detail + 카드 그리드 + 지도 3단 레이아웃

---

## 2. 사이드바 메뉴 재편 (`main.py`)

### 현재 (6개 플랫 나열)
```
🏠 Home | 🚀 Career | 💰 Finance | 🏢 Real Estate | ⚙️ Automation | 🕐 Jobs
```

### 변경 후 (5개 + 그룹 캡션)
```
── 도메인 ──
🏠 Home
🚀 Career
💰 Finance
🏢 Real Estate

── 시스템 운영 ──
⚙️ Automation   ← Jobs 흡수
```

**변경 사항:**
- `st.radio` 하나를 두 개 그룹으로 분리 (`st.caption("도메인")` / `st.caption("시스템 운영")`)
- `🕐 Jobs` 메뉴 제거 — `Automation` 탭 내부로 흡수
- `main.py`에서 Jobs import·라우팅 제거

---

## 3. Real Estate 탭 재편 (`views/real_estate.py`)

### 현재 (4탭 + 중첩 서브탭)
```
🔍 아파트 탐색 | 💡 Insight [서브탭 3개] | 📰 데일리 리포트 | 👤 페르소나
                   └ 거시경제 / 뉴스 리포트 / 정책 팩트
```

### 변경 후 (6탭 플랫)
```
🔍 아파트 탐색 | 📈 거시경제 | 📰 뉴스 리포트 | 📌 정책 팩트 | 📋 데일리 브리핑 | 👤 페르소나
```

**변경 사항:**
- `Insight` 탭 제거, 내부 서브탭 3개를 최상위 탭으로 승격
- `📰 데일리 리포트` → `📋 데일리 브리핑` 으로 개명 (뉴스 리포트와 혼동 방지)
- 탭 깊이 최대 1단계로 통일

---

## 4. 아파트 탐색 탭 — UI 현대화 (핵심 변경)

### 4.1 전체 레이아웃 (3단 분할)

```
┌─────────────────────────────────────────────────────────────┐
│  🔍 아파트명, 지역 검색...    [서울 ▾] [서초구 ▾] [검색]    │
├──────────────┬───────────────────────┬──────────────────────┤
│  단지 목록   │     카드 상세 패널     │       지도           │
│  (260px)     │     (340px)           │     (나머지 공간)    │
│              │                       │                      │
│ 래미안원베일리│ [89.5억][82점][38분]  │  🏢 래미안원베일리  │
│ 반포자이     │ ──────────────────    │   (아파트 핀)        │
│ 잠실주공5단지│ 📍 입지점수 ▲         │  🏢 직장 (여의도)   │
│ ...          │   [교통27][편의22]    │   (직장 핀)          │
│              │   [학군19][공원14]    │  ----출퇴근경로----  │
│              │ 📈 실거래가 ▼         │   🚇 38분           │
│              │ 🚇 출퇴근 ▼           │                      │
│              │ 🤖 AI 인사이트 ▼      │  [위치][POI][위성]   │
└──────────────┴───────────────────────┴──────────────────────┘
```

Streamlit 구현: `st.columns([1.2, 1.6, 1.8])` + 각 컬럼 내 스크롤

### 4.2 단지 목록 컬럼 (좌)

- 검색바: `st.text_input` + `st.selectbox` × 2 (시도/시군구)
- 결과: `st.button` 대신 `st.container` + `on_click` 패턴으로 카드형 행 렌더링
- 선택된 행: `st.session_state.selected_apt_idx`로 하이라이트

### 4.3 카드 상세 패널 (중)

**KPI 행 (항상 표시):**
```python
col1, col2, col3, col4 = st.columns(4)
col1.metric("최근거래", "89.5억")
col2.metric("입지점수", "82점")
col3.metric("출퇴근", "38분")
col4.metric("전세가율", "58%")
```

**확장 섹션 (클릭 시 근거 표시):**

각 섹션은 `st.expander`로 구현. 확장 시 내부 콘텐츠는 **2열 카드 그리드** 패턴 사용.

| 섹션 | 기본 표시 | 확장 시 |
|------|----------|---------|
| 📍 입지점수 | 실거주 82점 / 투자 74점 | 교통·편의·학군·공원 2열 카드 (점수 + 근거 텍스트 + 바) |
| 📈 실거래가 | 최근 89.5억 · 84㎡ · 12층 | 거래 이력 2열 카드 (날짜 + 가격 + 면적·층) |
| 🚇 출퇴근 | 38분 (지하철) | 지하철/버스 카드 2장 (경로 상세) |
| 🤖 AI 인사이트 | 1줄 요약 | 전체 LLM 리포트 텍스트 |

**카드 그리드 구현 패턴 (Streamlit):**
```python
with st.expander("📍 입지점수 — 실거주 82점 / 투자 74점", expanded=True):
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**🚇 교통 · 27점**")
        st.progress(27/30)
        st.caption("9호선 신반포역 150m · 7호선 반포역 350m")
    with c2:
        st.markdown("**🛍 생활편의 · 22점**")
        st.progress(22/25)
        st.caption("마트 2개 · 편의점 8개 · 병원 12개")
    # ... 학군, 공원
```

### 4.4 지도 컬럼 (우)

- `streamlit-folium` 기반 (`st_folium` 이미 코드에 존재)
- 표시 요소:
  - 아파트 위치 마커 (파란 핀 + 단지명 툴팁)
  - 직장 위치 마커 (초록 핀 + "직장" 툴팁) — `persona.commute.workplace_coords` 또는 주소 geocoding
  - 출퇴근 경로 점선 (아파트 → 직장)
  - 출퇴근 시간 배지 (`DivIcon`)
- 탭 버튼 (위치 / POI / 위성): `st.radio(horizontal=True)` → 지도 레이어 전환
  - POI 모드: 지하철역(파란)/학교(초록)/마트(주황)/공원(연두) 핀 추가
- 신규 `render_detail_map(apt, persona)` 함수를 `components/map_view.py`에 추가. 기존 `render_master_map_view()`(목록 전체 지도용)는 유지 — 용도가 다름 (단지 목록 지도 vs 단일 단지 상세 지도)

---

## 5. Automation 탭 통합 (`views/automation.py`)

### 현재
- `⚙️ Automation`: 워크플로우 목록 카드
- `🕐 Jobs`: 실행 내역 타임라인 (별도 메뉴)

### 변경 후
```python
tab1, tab2 = st.tabs(["📋 워크플로우", "🕐 실행 내역"])
with tab1:
    # 기존 show_automation() 본문
with tab2:
    # 기존 show_jobs() 본문 (jobs.py에서 이식)
```

- `jobs.py` 파일: `show_jobs()` 본문을 `automation.py`의 tab2로 직접 이식 후 `jobs.py` 삭제
- `main.py`: Jobs import·메뉴 항목·라우팅 3곳 모두 제거

---

## 6. Home 페이지 실데이터화 (`main.py::show_home()`)

### 변경 후 위젯 구성

```python
col1, col2, col3 = st.columns(3)

# 이번달 지출
with col1:
    df = DashboardClient.get_finance_ledger(year, month)
    total = df["amount"].sum() if not df.empty else 0
    st.metric("💰 이번달 지출", f"{total:,.0f}원")

# 부동산 데일리 리포트
with col2:
    dates = DashboardClient.list_daily_reports()
    latest = dates[0] if dates else None
    st.metric("🏢 데일리 브리핑", latest or "없음", help="최근 생성일")

# 오늘 Job 실행 현황
with col3:
    result = DashboardClient.get_executions(days=1)
    summary = result.get("summary", {})
    st.metric("⚙️ 오늘 실행", f"{summary.get('total',0)}건",
              delta=f"실패 {summary.get('error',0)}건" if summary.get('error') else "정상")
```

---

## 7. 명명 규칙 통일

| 변경 전 | 변경 후 |
|---------|---------|
| `⚙️ Operations: Automation Workflows` | `⚙️ Automation` |
| `🕐 Jobs: 실행 내역` | (Automation 탭 내 `🕐 실행 내역`) |
| `💡 Insight` (모호) | 제거 — 하위 3개 탭으로 분리 |
| `📰 데일리 리포트` | `📋 데일리 브리핑` |
| `🚀 커리어 Daily Report` | `🚀 Career` (제목은 내부 뷰에서 별도 표시) |

---

## 8. 변경 범위 요약

| 파일 | 변경 유형 |
|------|----------|
| `src/dashboard/main.py` | 사이드바 그룹 분리, Jobs 제거 |
| `src/dashboard/views/real_estate.py` | 탭 6개 재편, Tab1 3단 레이아웃 전면 교체 |
| `src/dashboard/views/automation.py` | 탭 2개 추가, Jobs 본문 이식 |
| `src/dashboard/views/jobs.py` | 독립 메뉴 제거, 함수만 잔류 (또는 automation.py로 통합) |
| `src/dashboard/components/map_view.py` | `render_detail_map()` 신규 추가 |
| `docs/system_snapshot/ui_structure.md` | 최신 구조로 전면 갱신 |

**영향 없는 파일:** `services.py`, `api_client.py`, `career.py`, `finance.py`, 백엔드 전체

---

## 9. 테스트 전략

- **회귀:** 기존 E2E 시나리오 (Tab1 AptMasterRepository 기반) → 새 3단 레이아웃 기준으로 업데이트
- **신규:** `render_detail_map()` 단위 테스트 (마커 생성, 경로 렌더링)
- **수동 확인:** 단지 선택 → 상세 카드 → 지도 동기화 골든패스

---

## 10. 미결 사항 (구현 전 확인 필요)

- `persona.commute`에 직장 좌표/주소 필드 존재 여부 → 없으면 페르소나에 `workplace_address` 필드 추가 필요
- `st.columns` 비율이 Streamlit wide layout에서 실제로 3단을 지원하는지 확인 (모니터 해상도에 따라 좌우 패널 collapse 처리 필요할 수 있음)
