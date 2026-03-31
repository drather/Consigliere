# Application Structure Guide

**Last Updated:** 2026-03-31

> 상세 다이어그램 및 모듈별 설명은 [`docs/system_snapshot/sw_architecture.md`](../system_snapshot/sw_architecture.md) 참조.

## 1. 아키텍처 레이어

```
Presentation  →  FastAPI Routes / Streamlit Dashboard
Business      →  Agent / Service 클래스 (도메인별)
Data Access   →  Repository 인터페이스 (Markdown, ChromaDB)
Infrastructure→  LLMClient, StorageProvider, PromptLoader
```

## 2. `src/` 디렉토리 구조

```
src/
├── core/
│   ├── llm.py              # LLMClient Factory (LLM_PROVIDER 환경변수로 전환)
│   ├── prompt_loader.py    # 프롬프트 파일 로더 (cache_boundary 지원)
│   ├── storage/            # StorageProvider 인터페이스 + 로컬 구현
│   └── notify/slack.py     # Slack Webhook 알림 발송
│
├── modules/
│   ├── real_estate/        # 부동산 모듈
│   │   ├── service.py      # RealEstateAgent (파사드)
│   │   ├── monitor/        # 실거래가 수집 (ChromaDB)
│   │   └── news/           # 뉴스 분석 (Naver API + LLM)
│   │
│   ├── finance/            # 가계부 모듈
│   │   ├── service.py      # FinanceAgent
│   │   ├── repository.py   # LedgerRepository 인터페이스
│   │   └── markdown_ledger.py  # Markdown 기반 구현
│   │
│   ├── career/             # 커리어 모듈 (2026-03-28 추가)
│   │   ├── service.py      # CareerAgent (파사드 오케스트레이터)
│   │   ├── collectors/     # 9종 Collector (GitHub, HackerNews, DevTo, Wanted, Jumpit, Reddit, Mastodon, Clien, DCInside)
│   │   │   ├── base.py     # BaseCollector (SSL 공통화, safe_collect)
│   │   │   └── factory.py  # CollectorFactory (OCP/DIP)
│   │   ├── processors/     # 4종 Analyzer (Job, Trend, SkillGap, Community)
│   │   │   └── base.py     # BaseAnalyzer (_call_llm 공통 헬퍼)
│   │   ├── reporters/      # DailyReporter, WeeklyReporter, MonthlyReporter
│   │   ├── models.py       # Pydantic 모델 12종
│   │   ├── config.yaml     # 수집 소스 설정
│   │   └── persona.yaml    # 사용자 스킬/목표 페르소나
│   │
│   └── automation/
│       └── service.py      # AutomationService (n8n API 연동)
│
├── dashboard/
│   ├── main.py             # Streamlit 라우터 (사이드바 네비게이션)
│   ├── views/              # finance.py, real_estate.py, automation.py
│   └── api_client.py       # FastAPI HTTP 클라이언트
│
└── n8n/templates/          # n8n 워크플로우 JSON 템플릿
```

## 3. 새 모듈 추가 시 규칙

- 도메인 모듈은 반드시 `src/modules/{domain}/` 하위에 위치한다.
- Agent 클래스는 `BaseAgent`를 상속한다 (OCP).
- Collector 클래스는 `BaseCollector`를 상속한다.
- Analyzer 클래스는 `BaseAnalyzer`를 상속한다.
- 새 모듈은 독립적으로 테스트 가능하게 설계한다.
