# Career SOLID 장기 개선 — Spec

**Feature:** `career-solid-refactor`
**Created:** 2026-04-05
**Status:** Planning (구현 대기)

---

## 1. 목표

현재 `CareerAgent`는 데이터 수집·분석·리포트 생성·경로 관리를 모두 직접 담당하는 **God Class**다.
또한 Processor들은 구체 클래스에 직접 의존하며, 공식 Protocol이 없어 ISP/DIP가 약하다.
이번 작업의 목표는 **SRP·OCP·DIP**를 충족하도록 구조를 개선하는 것이다.

---

## 2. 현황 분석 및 문제점

### 2-1. God Class — CareerAgent (`service.py`)

| 책임 | 현재 위치 |
|------|----------|
| 데이터 수집 (jobs/trends/community) | `CareerAgent.fetch_*()` |
| 분석 오케스트레이션 | `CareerAgent.generate_report()` |
| 파일 경로 관리 | `CareerAgent._*_path()` 헬퍼 7개 |
| 슬랙 블록 생성 | `CareerAgent.run_pipeline()` |
| 리포트 파일 목록 조회 | `CareerAgent.list_*()` 메서드 |

→ SRP 위반. 클래스가 변경되는 이유가 5가지 이상이다.

### 2-2. DIP 미충족 — Processor 구체 클래스 직접 주입

```python
# service.py __init__
self.job_analyzer = JobAnalyzer(self.llm, self.prompt_loader)   # 구체 클래스
self.trend_analyzer = TrendAnalyzer(self.llm, self.prompt_loader)
```

→ Protocol(인터페이스) 없이 구체 클래스에 의존. 테스트 시 Mock 주입이 불편하고, 구현 교체가 어렵다.

### 2-3. ISP 미충족 — BaseAnalyzer 단일 추상 클래스

- `BaseAnalyzer`가 `_call_llm()` 헬퍼를 제공하지만, 각 Analyzer의 `analyze()` 시그니처가 모두 다르다.
- 공식 `Protocol`이 없어 타입 체커가 계약을 검증할 수 없다.

### 2-4. generate_report / run_pipeline 중복

- `generate_report()`와 `run_pipeline()` 내부에서 `fetch_jobs`, `fetch_trends`, LLM 분석 3종이 **중복 실행**된다.
- 동일 날짜에 `run_pipeline()` 호출 시 분석이 2회 수행되는 문제가 잠재한다.

---

## 3. 개선 설계

### 3-1. Processor Protocol 정의 (ISP/DIP)

`src/modules/career/processors/protocols.py` 신규 파일 생성.

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class JobAnalyzerProtocol(Protocol):
    def analyze(self, postings, persona) -> JobAnalysis: ...

@runtime_checkable
class TrendAnalyzerProtocol(Protocol):
    def analyze(self, repos, stories, articles, languages) -> TrendAnalysis: ...

@runtime_checkable
class SkillGapAnalyzerProtocol(Protocol):
    def analyze(self, job_analysis, trend_analysis, persona, history) -> SkillGapAnalysis: ...

@runtime_checkable
class CommunityAnalyzerProtocol(Protocol):
    def analyze(self, reddit_posts, mastodon_posts, korean_posts, status) -> CommunityTrendAnalysis: ...
```

- `CareerAgent.__init__`에서 Protocol 타입으로 주입받도록 타입 힌트 변경.
- 테스트에서 Mock/Stub을 자유롭게 주입 가능.

### 3-2. SRP 분리 — CareerPathResolver

`src/modules/career/path_resolver.py` 신규 파일.

```
CareerPathResolver
  ├── jobs_path(d) → str
  ├── trends_path(d) → str
  ├── community_path(d) → str
  ├── daily_report_path(d) → str
  ├── weekly_report_path(iso_week) → str
  └── monthly_report_path(ym) → str
```

- `CareerAgent`에서 경로 헬퍼 7개를 제거하고 `CareerPathResolver`에 위임.
- `CareerConfig`에서 `data_dir`을 받아 생성.

### 3-3. SRP 분리 — CareerDataStore (캐시 Read/Write 책임)

`src/modules/career/data_store.py` 신규 파일.

- `fetch_jobs()` / `fetch_trends()` / `fetch_community()` 내부의 **파일 캐시 read/write 로직**을 분리.
- `CareerAgent`는 "캐시가 없으면 수집 → 저장" 흐름만 오케스트레이션.

```python
class CareerDataStore:
    def load_jobs(self, d: date) -> list | None: ...
    def save_jobs(self, d: date, data: list) -> None: ...
    # trends / community 동일 패턴
```

### 3-4. run_pipeline 중복 제거

- `run_pipeline()`이 `generate_report()` 결과를 재사용하도록 수정.
- 분석 결과(job_analysis, trend_analysis, skill_gap)를 `generate_report()` 반환값으로 포함하거나,
  내부 `_analyze()` 헬퍼로 추출하여 두 메서드가 공유.

### 3-5. CareerAgent 의존성 주입 개선

```python
class CareerAgent:
    def __init__(
        self,
        llm: BaseLLMClient | None = None,
        job_analyzer: JobAnalyzerProtocol | None = None,
        trend_analyzer: TrendAnalyzerProtocol | None = None,
        skill_gap_analyzer: SkillGapAnalyzerProtocol | None = None,
        community_analyzer: CommunityAnalyzerProtocol | None = None,
        path_resolver: CareerPathResolver | None = None,
        data_store: CareerDataStore | None = None,
    ):
        ...
```

- 모든 의존성에 기본값(None → 내부 생성)을 제공하여 **하위 호환성 유지**.
- 테스트에서 원하는 의존성만 주입 가능.

---

## 4. 파일 변경 목록

| 파일 | 변경 유형 | 내용 |
|------|----------|------|
| `src/modules/career/processors/protocols.py` | 신규 | 4종 Protocol 정의 |
| `src/modules/career/path_resolver.py` | 신규 | 경로 헬퍼 분리 |
| `src/modules/career/data_store.py` | 신규 | 파일 캐시 Read/Write |
| `src/modules/career/service.py` | 수정 | DI 패턴 적용, 경로/캐시 위임, run_pipeline 중복 제거 |
| `tests/modules/career/test_protocols.py` | 신규 | Protocol 적합성 테스트 |
| `tests/modules/career/test_path_resolver.py` | 신규 | CareerPathResolver 단위 테스트 |
| `tests/modules/career/test_data_store.py` | 신규 | CareerDataStore 단위 테스트 |
| `tests/modules/career/test_career_agent_di.py` | 신규 | Mock 주입 통합 테스트 |

---

## 5. 비기능 요건

- 기존 195개 테스트 전부 Green 유지 (회귀 없음)
- `CareerAgent()` 인수 없이 생성 시 기존과 동일하게 동작 (하위 호환)
- 신규 테스트 20개 이상 추가 목표

---

## 6. 참조

- `docs/guidelines/coding_guide.md` — SOLID 원칙, TDD
- `docs/guidelines/sop.md` — 4단계 SOP
- `docs/master_plan.md` — 전체 방향
