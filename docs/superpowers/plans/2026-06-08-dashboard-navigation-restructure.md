# Dashboard 메뉴/구조 재정비 — 작업계획서 (검토용 초안)

**작성일:** 2026-06-08
**상태:** 🟡 사용자 검토 대기 (브레인스토밍 미완료 — 기상 후 방향 확정 필요)

> 이 문서는 사용자가 "지금 바로 작업계획서를 제출하고 자러 갈 것"을 요청해 작성된 **분석 + 제안 + 실행계획 초안**입니다.
> 평소 절차(superpowers:brainstorming → 합의 → spec → plan)를 생략하고 먼저 진단과 옵션을 제시했으니,
> 기상 후 "어느 방향으로 갈지"만 결정해 주시면 그 시점에 정식 spec/plan으로 전환해 구현을 시작하겠습니다.

---

## 1. 현황 진단 (코드 기준 실측)

`src/dashboard/main.py` + 5개 view 파일(`real_estate.py`, `career.py`, `finance.py`, `automation.py`, `jobs.py`)을 직접 읽고 도출한 문제점입니다. (`docs/system_snapshot/ui_structure.md`는 2026-02-18 기준으로 이미 stale — Career/Jobs 누락)

### 1.1 최상위 메뉴 — 도메인과 시스템 기능이 같은 레벨에 혼재

```
🏠 Home | 🚀 Career | 💰 Finance | 🏢 Real Estate | ⚙️ Automation | 🕐 Jobs
```

- **Automation**과 **Jobs**는 둘 다 "n8n 워크플로우" 관련 화면인데 별개의 최상위 메뉴로 분리됨
  (Automation = 워크플로우 목록/n8n 에디터 진입, Jobs = 실행 내역 타임라인)
- **Home**은 실제로는 정적 placeholder 텍스트("- 최근 지출 내역 요약 보이기", "- 최근 거래 알림/뉴스 요약 보이기")만 있고 데이터 연동이 안 된 빈 껍데기 (`main.py:48, 51`)
- 도메인(Career/Finance/Real Estate)과 운영 도구(Automation/Jobs)가 구분 없이 나열되어 "이게 내 자산 관리용인지 시스템 모니터링용인지" 한눈에 안 들어옴

### 1.2 화면별 깊이/구조가 제각각 — 일관성 없음

| 화면 | 구조 | 비고 |
|---|---|---|
| Real Estate | 탭 4개, 그 중 Tab1·Tab2는 **서브탭**까지 중첩 (3단계: 탭→서브탭→동적 카테고리탭) | 가장 복잡. Insight 탭 하나에 거시경제/뉴스/정책 3개 기능이 다시 묶여있음 |
| Career | 탭 4개, 단층 | 리포트/스킬갭/페르소나/파이프라인 |
| Finance | 탭 없음, 단일 화면 | |
| Jobs | 탭 없음, 단일 화면 (radio + metric + table) | |
| Automation | 탭 없음, expander 카드 리스트 | |
| Home | 정적 텍스트 2단 컬럼 | 사실상 미구현 |

→ 같은 "탭"이라는 패턴을 화면마다 다른 깊이·다른 목적으로 써서, 사용자가 "여기서는 또 어떻게 찾아야 하지" 매번 새로 학습해야 함.
→ Real Estate Tab2(Insight) 안의 "💡 Insight"라는 이름도 모호함 — 실제로는 거시경제 지표 + 뉴스 리포트 + 정책 팩트 검색이라는 **서로 다른 3개 기능**이 들어있음 (`real_estate.py:783`).

### 1.3 같은 기능이 화면마다 따로 구현됨 (페르소나 편집 중복)

- `real_estate.py` Tab4 "👤 페르소나" (`:929`)
- `career.py` Tab3 "👤 페르소나 편집" (`:90`)

→ "페르소나"라는 같은 개념의 설정 화면이 도메인마다 따로 박혀있어, 사용자 입장에서는 "내 정보/설정"을 어디서 관리하는지 헷갈림. 통합 설정 영역이 없음.

### 1.4 톤/네이밍 불일치

- 한글/영문 혼용: "🚀 커리어 Daily Report" vs "Operations: Automation Workflows" vs "🕐 Jobs: 실행 내역"
- 이모지 사용 규칙 없음 (Automation 카드의 상태 아이콘은 🟢/⚫, Jobs는 ✅/❌/⏳/⚠️ — 같은 "상태 표시"인데 다른 기호 체계)

---

## 2. 개선 방향 — 3가지 옵션

### 옵션 A. 메뉴 그룹핑만 재정렬 (최소 변경) — 추천 ⭐

**무엇을 하나:** 코드/탭 구조는 그대로 두고, **사이드바 메뉴를 "도메인"과 "운영(System Ops)"으로 시각적으로 분리**하고, Automation+Jobs를 하나의 "⚙️ Automation" 메뉴 아래 탭(워크플로우 / 실행내역)으로 합친다. Home은 실제 위젯(최근 지출 합계, 최근 부동산 알림 N건, 오늘 실행된 Job 수)으로 채운다.

- 장점: 리스크 최소, 기존 view 함수·라우팅 구조 거의 그대로 재사용, 1~2일 내 완료 가능
- 단점: Real Estate 내부의 깊은 중첩(3단계 탭) 문제는 그대로 남음

### 옵션 B. 화면 내부 구조까지 표준화 (중간 규모)

옵션 A에 더해 **모든 view에 공통 레이아웃 규칙**을 도입:
- 탭은 최대 2단계까지만 허용 (Real Estate Insight의 "거시경제/뉴스/정책"을 별도 탭으로 승격, "Insight"라는 모호한 이름 제거)
- 상태 아이콘·타이틀 포맷·한글 표기 규칙을 `dashboard/components/`에 공통 헬퍼로 추출

- 장점: 중첩 깊이 문제 해결, 화면 간 일관성 확보 → "가독성" 문제의 근본 해결
- 단점: Real Estate view(`real_estate.py`, 1200+ 줄)의 탭 구조 변경 필요 — 회귀 테스트 범위 커짐

### 옵션 C. 페르소나/설정 통합 + 전체 IA 재설계 (대규모)

옵션 B에 더해 "👤 페르소나"를 도메인에서 분리해 **"⚙️ 설정" 같은 통합 공간**으로 이동, 전체 사이트맵을 역할 기반(자산관리 / 정보수집 / 시스템운영)으로 재설계.

- 장점: 가장 깔끔한 최종 구조
- 단점: 영향 범위가 가장 큼 (라우팅 변경 + 여러 view의 session_state 키 재배치 등) — 일정/리스크 부담 가장 큼, 단기간에 끝내기 어려움

### 추천

**옵션 A를 먼저 하고, 만족스러우면 옵션 B의 "탭 깊이 표준화"를 별도 작업으로 이어가는 것**을 추천합니다. "중구난방"이라고 느끼시는 핵심 원인은 ①Automation/Jobs 분리 ②Home 미구현 ③Real Estate의 과도한 중첩인데, A만으로도 ①②는 즉시 해소되고 체감 개선이 큽니다. C(페르소나 통합)는 영향 범위에 비해 "가독성" 개선 효과가 상대적으로 적어 우선순위를 낮추는 게 합리적입니다.

---

## 3. (옵션 A 기준) 제안 구조

```
사이드바
├─ 📂 도메인
│   ├─ 🏠 Home              (실데이터 위젯으로 교체)
│   ├─ 🚀 Career
│   ├─ 💰 Finance
│   └─ 🏢 Real Estate
└─ 🛠 시스템 운영
    └─ ⚙️ Automation         ← 탭: [워크플로우 목록] [🕐 실행 내역]  (기존 Jobs 통합)
```

- `st.radio`에 시각적 구분을 위해 `st.sidebar`에 섹션 캡션(`st.caption("도메인")` / `st.caption("시스템 운영")`) 추가하거나, 두 개의 `st.radio` 그룹으로 분리
- `automation.py`에 탭 2개 추가, `jobs.py`의 `show_jobs()` 본문을 두 번째 탭 콘텐츠로 이식 → `jobs.py`는 내부 함수로 격하 (또는 automation 모듈로 흡수)
- `main.py`의 메뉴 리스트에서 "🕐 Jobs" 제거, 라우팅 단순화

---

## 4. 실행 계획 (옵션 A 기준, 단계별)

> ⚠️ 아래는 **옵션 A를 선택했을 때**의 단계입니다. 옵션 B/C를 선택하시면 기상 후 별도로 다시 계획을 짭니다.

### Step 0 — 합의 (기상 후 5분)
- 옵션 A/B/C 중 방향 확정
- Home에 어떤 실데이터 위젯을 넣을지 확정 (예: 이번달 지출 합계 / 최근 7일 부동산 알림 수 / 오늘 실행된 워크플로우 수 — `DashboardClient`에 이미 있는 API로 가능한지부터 확인)

### Step 1 — Automation + Jobs 통합
- `automation.py::show_automation()`에 `st.tabs(["📋 워크플로우", "🕐 실행 내역"])` 추가
- `jobs.py::show_jobs()`의 본문을 두 번째 탭으로 이식, `jobs.py` 파일 자체는 제거하거나 내부 헬퍼로 축소
- `main.py`에서 Jobs 메뉴 항목·import·라우팅 제거
- (TDD) 기존 jobs/automation 관련 테스트가 있다면 새 구조에 맞게 업데이트

### Step 2 — 사이드바 메뉴 그룹 시각화
- `main.py`의 `st.radio` 메뉴를 "도메인" / "시스템 운영" 두 그룹으로 분리 표시 (caption 또는 두 개의 radio + 상태 동기화)

### Step 3 — Home 실데이터화
- `show_home()`의 placeholder 텍스트를 `DashboardClient` API 호출 기반 위젯으로 교체
- (TDD) 위젯 렌더링용 헬퍼 함수에 대한 단위 테스트 작성

### Step 4 — 문서 갱신 (SOP 4단계)
- `docs/system_snapshot/ui_structure.md` 갱신 (현재 stale — Career/Jobs 반영 안됨)
- `docs/context/active_state.md` 작업 결과 기록
- spec/progress/issues/result.md 작성 (SOP 준수)

### 예상 영향 범위
- 수정: `main.py`, `automation.py`, `jobs.py`(제거 또는 축소), `ui_structure.md`
- 신규 테스트는 옵션 A 범위에서는 최소 (라우팅/통합 위주라 회귀 리스크 낮음)

---

## 5. 기상 후 확인이 필요한 사항

1. **옵션 A / B / C 중 어느 방향으로 갈지** — 위 추천(A 우선, 이후 B)에 동의하시는지
2. **Home 위젯에 넣을 실데이터 종류** — Finance 합계 / Real Estate 알림 / Job 실행 현황 중 우선순위
3. **"👤 페르소나" 중복을 지금 통합할지, 나중(옵션 C)으로 미룰지** — 옵션 A/B 범위에서는 손대지 않을 예정이라 미리 확인
4. Jobs를 Automation에 흡수하는 것에 이견이 없는지 (혹시 Jobs를 독립 메뉴로 유지하고 싶은 이유가 있다면)

---

**다음 단계:** 위 질문에 대한 답을 주시면, `superpowers:brainstorming` 절차에 따라 정식 design spec(`docs/superpowers/specs/`)을 작성하고, 이어서 `superpowers:writing-plans`로 구현 계획을 확정한 뒤 작업을 시작하겠습니다.
