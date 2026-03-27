# Spec: 커리어 Daily Report

**Branch:** `feature/career-daily-report`
**Created:** 2026-03-25
**Ref:** `docs/master_plan.md` — 개인화된 LLM 기반 비서 플랫폼, 커리어 도메인 확장

---

## 1. 목표 (Goals)

백엔드 엔지니어로서 매일 아침 기술 트렌드, 채용 시장, 스킬 갭을 한눈에 파악하고 장기적인 성장 방향을 트래킹한다.

- **일별 리포트:** 오늘의 채용공고 요약 + 기술 트렌드 + 연봉 인사이트 + 스킬 갭 & 학습 추천
- **주간 리포트:** 이번 주 핵심 트렌드 종합 (매주 금요일 자동 생성)
- **월간 리포트:** 이달의 성장 요약 + 스킬 진척 + 다음 달 목표 추천 (매월 말일 자동 생성)
- **히스토리 트래킹:** 스킬 갭 점수 및 주별 기술 트렌드 누적 저장 → 성장 흐름 가시화

---

## 2. 아키텍처 (Architecture)

### 2.1 계층 구조

```
Collector Layer       →  Processor Layer  →  Reporter Layer  →  Notifier
(데이터 수집)              (LLM 분석)           (리포트 생성)         (Slack 전송)

GithubTrendingCollector ─┐
HackerNewsCollector     ─┤  TrendAnalyzer   ─┐
DevToCollector          ─┘                    │
                                              ├─ DailyReporter → Markdown .md
WantedCollector  ─┐                           │   WeeklyReporter
JumpitCollector  ─┘  JobAnalyzer ─────────────┤   MonthlyReporter
                                              │
                     SkillGapAnalyzer ────────┘
                     (+ History Context)          Presenter → Slack Block Kit
```

### 2.2 파이프라인 흐름

```
Job 1: fetch_jobs()    → data/career/jobs/{date}_jobs.json
Job 2: fetch_trends()  → data/career/trends/{date}_trends.json
Job 3: generate_report() → LLM 3회 호출 → data/career/reports/daily/{date}_CareerReport.md

(매주 금) generate_weekly_report()  → data/career/reports/weekly/{YYYY-WW}_WeeklyReport.md
(매월 말) generate_monthly_report() → data/career/reports/monthly/{YYYY-MM}_MonthlyReport.md
```

**skip 로직:** Job1/Job2는 당일 파일 존재 시 재수집 생략 (real_estate 패턴 동일)

---

## 3. 모듈 구조

```
src/modules/career/
├── service.py                  # CareerAgent (파사드 — 모든 Job 오케스트레이션)
├── config.py                   # CareerConfig (config.yaml 로드)
├── config.yaml                 # 소스 엔드포인트, 언어 필터, 스코어 임계값
├── persona.yaml                # 사용자 커리어 프로필
├── models.py                   # Pydantic 모델
├── presenter.py                # Markdown → Slack Block Kit 변환
│
├── collectors/                 # 수집 계층
│   ├── base.py                 # BaseCollector (공통 인터페이스)
│   ├── github_trending.py      # BeautifulSoup 스크래핑
│   ├── hacker_news.py          # Firebase REST API (aiohttp)
│   ├── devto.py                # dev.to 공개 REST API
│   ├── wanted.py               # XHR API (fallback: BeautifulSoup)
│   └── jumpit.py               # 점핏 내부 API
│
├── processors/                 # 처리 계층 (LLM 분석)
│   ├── job_analyzer.py         # JD → 스킬 빈도 + 연봉 통계
│   ├── trend_analyzer.py       # GitHub + HN + Dev.to → 기술 트렌드
│   └── skill_gap_analyzer.py   # 갭 분석 + 학습 추천
│
├── reporters/                  # 리포트 계층
│   ├── daily_reporter.py       # 3개 분석 결과 → 일별 Markdown
│   ├── weekly_reporter.py      # 7일치 일별 MD → 주간 Markdown (LLM)
│   └── monthly_reporter.py     # 주간 MD → 월간 Markdown (LLM)
│
├── history/
│   └── tracker.py              # 스킬 갭 스냅샷 저장/로드, 주간 트렌드 집계
│
└── prompts/
    ├── job_analyst.md
    ├── trend_analyst.md
    ├── skill_gap_analyst.md
    ├── weekly_synthesizer.md
    └── monthly_synthesizer.md
```

### 데이터 디렉토리

```
data/career/
├── jobs/{date}_jobs.json
├── trends/{date}_trends.json
├── reports/
│   ├── daily/{date}_CareerReport.md
│   ├── weekly/{YYYY-WW}_WeeklyReport.md
│   └── monthly/{YYYY-MM}_MonthlyReport.md
└── history/
    ├── skill_gap/{date}_skill_gap.json
    └── weekly/{YYYY-WW}_weekly_trend.json
```

---

## 4. 데이터 모델 (Pydantic)

```python
class JobPosting(BaseModel):
    id: str
    company: str
    position: str
    skills: List[str]
    salary_min: Optional[int]
    salary_max: Optional[int]
    experience_min: Optional[int]
    url: str
    source: str  # "wanted" | "jumpit"

class TrendingRepo(BaseModel):
    name: str
    description: str
    language: str
    stars_today: int
    url: str

class HNStory(BaseModel):
    id: int
    title: str
    url: Optional[str]
    score: int

class DevToArticle(BaseModel):
    id: int
    title: str
    url: str
    tags: List[str]
    reactions: int

class JobAnalysis(BaseModel):
    top_skills: List[str]
    skill_frequency: Dict[str, int]
    salary_range: Dict[str, Optional[int]]  # median, p75, p90
    hiring_signal: str
    notable_postings: List[Dict]

class TrendAnalysis(BaseModel):
    hot_topics: List[str]
    github_top: List[Dict]
    hn_highlight: str
    devto_picks: List[Dict]
    backend_relevance_comment: str

class SkillGapAnalysis(BaseModel):
    gap_score: int  # 0-100
    missing_skills: List[Dict]  # skill, urgency, frequency_in_jd
    study_recommendations: List[Dict]  # topic, why, resource
    gap_trend: str

class SkillGapSnapshot(BaseModel):
    date: str
    gap_score: int
    missing_skills: List[str]
    study_recommendations: List[Dict]
```

---

## 5. persona.yaml 구조

```yaml
user:
  name: kks
  domain: 백엔드 엔지니어
  experience_years: 3
  current_company_type: 스타트업
  target_company_types:
    - 중견 테크 스타트업
    - B2B SaaS
  career_goal: 시니어 백엔드 → 아키텍트

skills:
  current:
    - Python
    - FastAPI
    - PostgreSQL
    - Redis
    - Docker
    - Git
  learning:
    - Kubernetes
    - Go
  target:
    - Kubernetes
    - Go
    - Terraform
    - AWS

job_search:
  active: false
  preferred_location: [서울, 판교]
  min_salary: 60000000
  preferred_employment_type: 정규직
  remote_preference: 하이브리드

learning:
  weekly_hours: 10
  preferred_format: [유튜브 강의, 공식 문서, 사이드 프로젝트]
  current_focus: Kubernetes CKA

trend_sources:
  github_languages: [python, go, typescript, java, rust]
  hn_min_score: 50
  devto_tags: [backend, python, go, devops, career, system-design]
```

---

## 6. LLM 처리 설계

**총 3회 호출** (일별 리포트 기준)

| Call | Processor | Prompt | Input | Output |
|------|-----------|--------|-------|--------|
| 1 | JobAnalyzer | `job_analyst.md` | Wanted + 점핏 원본 JSON | top_skills, salary_range, notable_postings |
| 2 | TrendAnalyzer | `trend_analyst.md` | GitHub + HN + Dev.to JSON | hot_topics, github_top, hn_highlight, backend_relevance_comment |
| 3 | SkillGapAnalyzer | `skill_gap_analyst.md` | Call1 + Call2 결과 + persona 스킬 + 4주 갭 히스토리 | gap_score, missing_skills, study_recommendations |

**주간/월간 추가 호출:**
- 주간: `weekly_synthesizer.md` — 7일치 일별 MD 텍스트 → 주간 종합
- 월간: `monthly_synthesizer.md` — 해당 월 주간 MD 텍스트 → 월간 종합

**Block Kit 조립은 코드 기반** (`presenter.py`) — LLM hallucination 방지

---

## 7. 리포트 포맷 (일별 Markdown 구조)

```markdown
# 커리어 Daily Report — {date}

## 💼 채용공고 요약
- **분석 건수:** Wanted {n}건 + 점핏 {n}건
- **핵심 요구 스킬:** Python (18), Kubernetes (12), Go (8), ...
- **연봉:** 중앙값 6,500만 / 75%ile 8,000만 / 90%ile 1억
- **시장 시그널:** {hiring_signal}
- **주목할 포지션:** ...

## 🔥 기술 트렌드
- **핫 토픽:** Rust + WASM, LLM 인프라, eBPF 옵저버빌리티
- **GitHub 주목 레포:** ...
- **HN 하이라이트:** ...
- **Dev.to 추천:** ...
- **백엔드 시사점:** ...

## 💰 연봉 인사이트
- 시장 중앙값 / 75%ile / 90%ile
- 경력 {n}년차 포지셔닝 분석

## 🎯 스킬 갭 & 학습 추천
- **갭 점수:** 72/100 (지난주 대비 +3)
- **핵심 부족 스킬:** Kubernetes (HIGH), Go (MEDIUM)
- **오늘의 학습 추천:**
  1. Kubernetes CKA 준비 — ...
  2. Go 언어 기초 — ...
- **갭 트렌드:** 2주 연속 Kubernetes 격차 유지
```

---

## 8. API 엔드포인트

**파일:** `src/api/routers/career.py`

```
# 파이프라인 실행
POST /jobs/career/fetch-jobs
POST /jobs/career/fetch-trends
POST /jobs/career/generate-report
POST /jobs/career/generate-weekly-report
POST /jobs/career/generate-monthly-report
POST /jobs/career/run-pipeline

# 대시보드 조회
GET  /dashboard/career/reports/daily
GET  /dashboard/career/reports/daily/{date}
GET  /dashboard/career/reports/weekly
GET  /dashboard/career/reports/monthly
GET  /dashboard/career/skill-gap/history?weeks=4
GET  /dashboard/career/persona
PATCH /dashboard/career/persona
```

---

## 9. Streamlit 대시보드

**파일:** `src/dashboard/pages/career.py`

- **페르소나 편집 탭:** 현재 스킬, 목표 스킬, 직군, 연봉 기대치 등 폼으로 편집 → API PATCH
- **리포트 뷰어 탭:** 일별/주간/월간 탭 분리, MD 원문 렌더링
- **스킬 갭 히스토리 탭:** gap_score 시계열 차트 (Altair/Plotly)

---

## 10. n8n 워크플로우

| 파일 | 스케줄 | 역할 |
|------|--------|------|
| `career_daily_report.json` | `0 9 * * 1-5` (평일 09:00) | Job1 → Job2 → Job3 → Slack |
| `career_weekly_report.json` | `0 18 * * 5` (금요일 18:00) | 주간 리포트 생성 → Slack |
| `career_monthly_report.json` | `0 20 28-31 * *` (28~31일 20:00, 서버에서 말일 체크) | 월간 리포트 생성 → Slack |

---

## 11. SOLID 원칙 준수 계획

- **SRP:** 각 Collector, Processor, Reporter가 단일 책임. 파사드(`service.py`)만 오케스트레이션.
- **OCP:** 새 수집기 추가 시 `BaseCollector` 상속만 하면 됨. 파사드 수정 불필요.
- **DIP:** 모든 Processor는 `LLMClient`(추상) 주입받음. 구체 모델(Gemini/Claude) 교체 가능.
- **Zero Hardcoding:** URL, 임계값, 언어 목록 모두 `config.yaml`에 관리.
- **에러 격리:** 각 Collector 실패 시 빈 리스트 반환, 파이프라인 중단 없음.

---

## 12. 검증 방법

1. 각 Collector 직접 실행 → 데이터 반환 확인
2. `POST /jobs/career/run-pipeline` → `data/career/reports/daily/` MD 파일 생성 확인
3. `POST /jobs/career/generate-weekly-report` → weekly MD 파일 생성 확인
4. Slack Block Kit 4섹션 정상 렌더링 확인
5. 3일 연속 실행 후 `GET /dashboard/career/skill-gap/history` 응답 확인
6. Streamlit Career 페이지 페르소나 편집 → 저장 → API 반영 확인
7. n8n 3개 워크플로우 수동 트리거 실행
