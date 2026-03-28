# Spec: 커뮤니티 트렌드 조사 모듈

**Branch:** `feature/community-trend-collector`
**Created:** 2026-03-28
**Ref:** `docs/master_plan.md` — 커리어 Daily Report 확장

---

## 1. 목표 (Goals)

채용 공고·기술 트렌드(GitHub/HN/Dev.to)만으로는 알 수 없는 개발자/AI 커뮤니티의 실제 여론과 트렌드를 수집·분석해 커리어 Daily Report에 통합한다.

- Reddit(r/cscareerquestions 등), Twitter(Nitter 스크래핑), 국내 커뮤니티(클리앙, 디씨인사이드)에서 개발/AI 직무 관련 핫 토픽·의견·우려사항 수집
- LLM 분석으로 핵심 의견 요약 → Daily Report에 `🌐 커뮤니티 트렌드` 섹션 추가
- 수집 실패(Nitter 불안정 등) 시 상태를 리포트에 표기해 즉각 인지 가능하도록

---

## 2. 아키텍처 (Architecture)

### 2.1 계층 구조

```
기존 Collector Layer 확장:

RedditCollector  ─┐
NitterCollector  ─┤  CommunityAnalyzer  ─┐
ClienCollector   ─┤  (LLM)               ├─ DailyReporter (커뮤니티 섹션 추가)
DCInsideCollector─┘                       │
                                          └─ CommunityTrendAnalysis (collection_status 포함)
```

### 2.2 파이프라인 흐름

```
Job 추가: fetch_community() → data/career/community/{date}_community.json

generate_report():
  fetch_jobs()       → JobAnalysis
  fetch_trends()     → TrendAnalysis
  fetch_community()  → CommunityTrendAnalysis  ← 신규
  skill_gap_analyzer.analyze()
  daily_reporter.generate(community_trend=...) → Markdown에 커뮤니티 섹션 포함
```

**skip 로직:** 당일 `{date}_community.json` 존재 시 재수집 생략 (기존 패턴 동일)

---

## 3. 수집 소스 및 설정

| 소스 | 방식 | 라이브러리 | 안정성 |
|------|------|-----------|--------|
| Reddit | 공식 API (무료) | asyncpraw | 높음 |
| Twitter/X | Nitter 인스턴스 스크래핑 | aiohttp + BS4 | 낮음 (예외처리 강화) |
| 클리앙 | 웹 스크래핑 | aiohttp + BS4 | 중간 |
| 디씨인사이드 | 웹 스크래핑 | aiohttp + BS4 | 중간 (anti-bot) |

### Reddit 대상 subreddit
- r/cscareerquestions, r/ExperiencedDevs, r/MachineLearning
- r/artificial, r/LocalLLaMA, r/devops, r/programming

### Nitter 인스턴스 (순차 fallback)
- nitter.net, nitter.privacydev.net, nitter.poast.org, nitter.1d4.us

### 국내 커뮤니티
- 클리앙: `https://www.clien.net/service/board/cm_programmers`
- 디씨인사이드: `https://gall.dcinside.com/board/lists/?id=programming`

---

## 4. 새 파일 목록

| 경로 | 내용 |
|------|------|
| `src/modules/career/collectors/reddit.py` | RedditCollector (asyncpraw) |
| `src/modules/career/collectors/nitter.py` | NitterCollector (aiohttp + BS4) |
| `src/modules/career/collectors/clien.py` | ClienCollector (aiohttp + BS4) |
| `src/modules/career/collectors/dcinside.py` | DCInsideCollector (aiohttp + BS4) |
| `src/modules/career/processors/community_analyzer.py` | LLM 커뮤니티 분석기 |
| `src/prompts/career/community_analyst.md` | 프롬프트 템플릿 |

## 5. 수정 파일 목록

| 경로 | 변경 내용 |
|------|-----------|
| `src/modules/career/models.py` | RedditPost, NitterTweet, KoreanPost, CommunityTrendAnalysis 추가 |
| `src/modules/career/config.yaml` | community_sources 섹션 추가 |
| `src/modules/career/config.py` | get_community_config() 추가 |
| `src/modules/career/service.py` | fetch_community(), 초기화, generate_report() 통합 |
| `src/modules/career/reporters/daily_reporter.py` | 커뮤니티 섹션 추가 (optional 파라미터) |
| `requirements.txt` | asyncpraw>=7.7 추가 |
| `tests/test_career.py` | 신규 테스트 클래스 추가 |

---

## 6. 새 Pydantic 모델

```python
class RedditPost(BaseModel):
    id: str; title: str; subreddit: str
    score: int = 0; url: str = ""; num_comments: int = 0; selftext: str = ""

class NitterTweet(BaseModel):
    id: str; text: str; username: str
    date: str = ""; url: str = ""

class KoreanPost(BaseModel):
    id: str; title: str; source: str  # "clien" | "dcinside"
    url: str = ""; views: int = 0; comments: int = 0; date: str = ""

class CommunityTrendAnalysis(BaseModel):
    hot_topics: List[str] = []
    key_opinions: List[str] = []
    emerging_concerns: List[str] = []
    community_summary: str = ""
    collection_status: Dict[str, str] = {}  # "reddit"|"nitter"|"clien"|"dcinside" → "ok"|"failed"|"partial"
```

---

## 7. 환경 변수

```
REDDIT_CLIENT_ID=...       # Reddit API (무료, https://www.reddit.com/prefs/apps)
REDDIT_CLIENT_SECRET=...   # Reddit API secret
```

---

## 8. 에러 처리 원칙

- 모든 Collector: `safe_collect()` 래퍼 → 예외 발생 시 `[]` 반환, 파이프라인 중단 없음
- Nitter: 인스턴스 순차 시도, 전체 실패 시 `[]` 반환
- 수집 상태(`collection_status`)가 `CommunityTrendAnalysis`에 항상 포함
- DailyReporter: failed/partial 소스를 `⚠️` 표기로 즉각 가시화
- DCInside 403 → 정상 처리 (anti-bot, intermittent)

---

## 9. 완료 조건 (Done Criteria)

- [ ] 4개 Collector 구현 완료 (unit test 포함)
- [ ] CommunityAnalyzer 구현 완료 (unit test 포함)
- [ ] DailyReporter 커뮤니티 섹션 추가 (기존 테스트 호환 유지)
- [ ] CareerAgent `fetch_community()` 캐시 로직 구현
- [ ] `generate_report()` 커뮤니티 분석 통합
- [ ] 전체 테스트 green (기존 42개 + 신규 ~25개)
- [ ] 라이브 smoke test 통과 (일부 소스 실패 허용)
