# Result: 커뮤니티 트렌드 조사 모듈

**완료일:** 2026-03-28
**브랜치:** feature/community-trend-collector

## 결과 요약

| 항목 | 내용 |
|------|------|
| 신규 Collector | 4종 (Reddit, Mastodon, Clien, DCInside) |
| 신규 Processor | 1종 (CommunityAnalyzer) |
| 신규 모델 | 4종 (RedditPost, NitterTweet, KoreanPost, CommunityTrendAnalysis) |
| 신규 테스트 | 59개 |
| 전체 테스트 | 101개 (모두 green) |
| SOLID 신규 파일 | 2종 (processors/base.py, collectors/factory.py) |

## 변경 파일

| 파일 | 변경 내용 |
|------|-----------|
| `collectors/reddit.py` | Reddit 공개 JSON API 수집기 (인증 불필요) |
| `collectors/mastodon.py` | Mastodon 해시태그 타임라인 API 수집기 |
| `collectors/clien.py` | 클리앙 개발자 게시판 스크래퍼 (cm_app) |
| `collectors/dcinside.py` | 디씨인사이드 프로그래밍 갤러리 스크래퍼 |
| `collectors/base.py` | `make_connector()` SSL 공통 메서드 추가 |
| `processors/community_analyzer.py` | LLM 커뮤니티 분석기 |
| `prompts/career/community_analyst.md` | 개조식 분석 프롬프트 |
| `prompts/career/trend_analyst.md` | 개조식 출력 스타일 적용 |
| `prompts/career/skill_gap_analyst.md` | 개조식 출력 스타일 적용 |
| `models.py` | 4종 모델 추가 |
| `config.yaml` | community_sources 섹션 추가 |
| `service.py` | fetch_community(), generate_report() 통합 |
| `reporters/daily_reporter.py` | 커뮤니티 섹션 + 가독성 개선 (bullet/백틱) |
| `api/routers/career.py` | `/jobs/career/fetch-community` 엔드포인트 추가 |

## 검증 결과

### 수집 현황 (2026-03-28 실측)
- **Reddit**: 20개 (7개 subreddit, 공개 JSON API)
- **Mastodon**: 68개 (fosstodon.org, hachyderm.io, mastodon.social, 7개 해시태그)
- **클리앙**: 20개 (cm_app 개발한당 게시판)
- **DCInside**: 20개 (프로그래밍 갤러리)
- **collection_status**: 4/4 all ok

### 리포트 품질
- 커뮤니티 의견 개조식 적용: `키워드 — 핵심 논점 한 줄`
- 핫 토픽 bullet + 백틱 적용
- 종합 멀티라인 bullet 렌더링
- 백엔드 시사점 줄바꿈 분리

## 참고 사항

### 시도했으나 실패한 Twitter 대안
| 방법 | 결과 | 이유 |
|------|------|------|
| Nitter (ntscraper) | ❌ | 모든 인스턴스 서비스 종료 |
| Bluesky public API | ❌ | Cloudflare 403 차단 |
| Twitter API v2 | ❌ | Free 티어 검색 불가 (402 CreditsDepleted) |
| Mastodon (mastodon.social) | ❌ | 검색 API 결과 0건 |
| **Mastodon (fosstodon.org 등)** | ✅ | 해시태그 타임라인 API 정상 작동 |

### SSL 이슈 해결
- macOS Python 환경에서 `SSLCertVerificationError` 발생
- `BaseCollector.make_connector()`로 certifi CA 번들 공통 적용
- 전체 10개 Collector에 일관 적용 완료

### SOLID 리팩토링 (추가 세션)
- **BaseAnalyzer** (`processors/base.py`): Processor 4개의 중복 LLM 호출 패턴 공통화
  - `_call_llm(prompt_key, variables, model_class)` 헬퍼로 각 Analyzer 코드량 50% 감소
  - TestBaseAnalyzer 6개 추가
- **CollectorFactory** (`collectors/factory.py`): Collector 생성 책임 `service.py`에서 분리
  - 새 커뮤니티 소스 추가 시 factory.py + `_KOREAN_SOURCES` 상수만 수정
  - `fetch_community()` 제네릭 딕셔너리 루프로 전환 (소스 추가 시 자동 반영)
  - TestCollectorFactory 6개 추가
