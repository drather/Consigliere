# Issues: 커뮤니티 트렌드 조사 모듈

## ISS-001: Reddit API Key 발급 방식 변경
- **현상:** Reddit이 API key 발급 정책을 변경해 asyncpraw 인증이 어렵게 됨
- **원인:** Reddit 정책 변경 (2024)
- **해결:** asyncpraw 제거 → `/r/{sub}/top.json?t=day` 공개 JSON API 사용 (User-Agent 헤더만 필요)

## ISS-002: Twitter 데이터 수집 전면 불가 → Mastodon 전환
- **현상:** Twitter 관련 모든 수집 방법 실패
- **시도 경과:**
  - Nitter (ntscraper): 모든 인스턴스 서비스 종료
  - Bluesky public API: Cloudflare 403 차단
  - twscrape: X.com Cloudflare 봇 감지로 로그인 불가
  - Twitter API v2 Free 티어: Bearer Token 발급 성공 → 검색 API 402 CreditsDepleted (Basic $100/월 필요)
- **해결:** Mastodon 해시태그 타임라인 API (`/api/v1/timelines/tag/{hashtag}`) 공개 엔드포인트로 전환. fosstodon.org/hachyderm.io/mastodon.social 인스턴스 사용. 68개/회 수집 확인

## ISS-003: 클리앙 게시판 URL 변경
- **현상:** `cm_programmers` 게시판 HTTP 404 반환
- **원인:** 클리앙 게시판 구조 변경으로 해당 URL 삭제
- **해결:** 사이트 직접 탐색 → `cm_app` (개발한당) 확인 후 config.yaml 업데이트, 20개 수집 정상

## ISS-004: macOS Python SSL 인증서 검증 실패 (SSLCertVerificationError)
- **현상:** 모든 외부 사이트 수집 시 `SSLCertVerificationError` 발생 (reddit, dcinside, github 등)
- **원인:** macOS Python 환경에서 시스템 CA 번들 자동 로드 실패
- **해결:** `BaseCollector.make_connector()` 공통 메서드 추가 — certifi CA 번들 기반 `aiohttp.TCPConnector` 반환. 전체 10개 Collector에 일관 적용 완료

<!-- 이슈 발생 시 아래 형식으로 추가 -->

<!--
## ISS-001: 제목
- **현상:**
- **원인:**
- **해결:**
-->
