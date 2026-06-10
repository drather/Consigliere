# UI Structure Snapshot

**Status:** Active
**Last Updated:** 2026-06-11

## 1. Dashboard Structure (Navigation)

사이드바가 "도메인"과 "시스템 운영" 두 그룹으로 분리된다.

### 1.1 Sitemap

```
사이드바
├─ 도메인
│   ├─ 🏠 Home          — 이번달 지출 / 최근 브리핑 / 오늘 Job 실행 현황
│   ├─ 🚀 Career        — 리포트(일별/주간/월간) / 스킬갭 / 페르소나 / 파이프라인
│   ├─ 💰 Finance       — 가계부 CRUD (월별)
│   └─ 🏢 Real Estate   — 6탭 (아래 참조)
└─ 시스템 운영
    └─ ⚙️ Automation    — 워크플로우 목록 / 실행 내역
```

## 2. Real Estate 탭 구조 (6탭)

| 탭 | 내용 |
|----|------|
| 🔍 아파트 탐색 | 3단: 목록 + 카드 상세(KPI+확장 섹션) + 지도 |
| 📈 거시경제 | BOK 지표 카테고리별 최신값 + 추이 차트 |
| 📰 뉴스 리포트 | 일별 뉴스 분석 리포트 뷰어 |
| 📌 정책 팩트 | ChromaDB 정책 팩트 검색 |
| 📋 데일리 브리핑 | 실거래가+거시경제+LLM 인사이트 통합 브리핑 |
| 👤 페르소나 | 자산/소득/출퇴근/가중치/관심지역 설정 |

## 3. 아파트 탐색 탭 — 3단 레이아웃

```
[검색바: 아파트명 | 시도 ▾ | 시군구 ▾ | 검색]

┌──────────────┬───────────────────────┬──────────────────────┐
│  단지 목록   │    카드 상세 패널      │       지도           │
│  (260px)     │    (340px)            │    (나머지)          │
│              │                       │                      │
│ ▶ 래미안원베일│ ### 래미안원베일리    │  [📍 위치] [🏙 POI] │
│  반포자이    │ [89.5억][82점][38분]  │                      │
│  잠실주공5   │ ──────────────────    │  🏢 단지 핀          │
│  ...         │ 📍 입지점수 ▲         │  🏢 직장 핀          │
│              │   [교통27] [편의22]   │  ---- 출퇴근 경로    │
│              │   [학군19] [공원14]   │   🚇 38분 배지       │
│              │ 📈 실거래가 ▼         │                      │
│              │ 🚇 출퇴근 ▼           │                      │
│              │ 🤖 AI 인사이트 ▼      │                      │
└──────────────┴───────────────────────┴──────────────────────┘
```

## 4. Automation 탭 (Jobs 통합)

| 탭 | 내용 |
|----|------|
| 📋 워크플로우 | n8n 워크플로우 목록 + n8n 에디터 링크 |
| 🕐 실행 내역 | 기간별 실행 타임라인 + 성공/실패 요약 |

## 5. 구현 파일 현황

| 파일 | 역할 |
|------|------|
| `src/dashboard/main.py` | 사이드바 2그룹, 라우팅, Home 위젯 |
| `src/dashboard/views/real_estate.py` | Real Estate 6탭 전체 |
| `src/dashboard/views/career.py` | Career 4탭 |
| `src/dashboard/views/finance.py` | Finance 단일 화면 |
| `src/dashboard/views/automation.py` | Automation 2탭 (Jobs 통합) |
| `src/dashboard/components/map_view.py` | render_master_map_view(), render_detail_map() |
| `src/dashboard/api_client.py` | DashboardClient — 모든 API 호출 |
| `src/dashboard/services.py` | DB 직접 접근 서비스 진입점 |
