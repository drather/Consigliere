# Issues: 커뮤니티 트렌드 조사 모듈

## ISS-001: Reddit API Key 발급 방식 변경
- **현상:** Reddit이 API key 발급 정책을 변경해 asyncpraw 인증이 어렵게 됨
- **원인:** Reddit 정책 변경 (2024)
- **해결:** asyncpraw 제거 → `/r/{sub}/top.json?t=day` 공개 JSON API 사용 (User-Agent 헤더만 필요)

## ISS-002: Nitter 전체 서비스 종료
- **현상:** 테스트한 모든 Nitter 인스턴스 응답 실패 (503/연결 오류)
- **원인:** Nitter 인프라 전반 종료 (Twitter API 정책 변경 이후 운영 불가)
- **해결:** ntscraper로 확인 → 0개 인스턴스 동작. Bluesky(403), Mastodon(0 results) 대안도 불가. 현재는 `collection_status["nitter"] = "failed"` 처리 후 리포트에 ⚠️ 표기로 처리

## ISS-003: 클리앙 HTTP 404
- **현상:** Docker 환경에서 클리앙 board URL 404 반환
- **원인:** URL 변경 가능성 또는 Docker IP 차단
- **해결:** 미해결 — `safe_collect()` 패턴으로 빈 배열 반환 처리, `collection_status["clien"] = "failed"` 표기

<!-- 이슈 발생 시 아래 형식으로 추가 -->

<!--
## ISS-001: 제목
- **현상:**
- **원인:**
- **해결:**
-->
