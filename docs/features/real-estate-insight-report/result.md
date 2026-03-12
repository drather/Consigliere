# Result: 부동산 종합 인사이트 리포트 구축

## 개요
부동산 실거래가와 최신 뉴스를 결합하여, 매일 아침 사용자에게 가독성 높은 종합 인사이트 리포트를 제공하는 기능을 성공적으로 구축했습니다.

## 주요 성과
- **데이터 통합:** MOLIT 실거래가 API와 Naver 뉴스 API를 단일 리포트로 통합.
- **LLM 기반 요약:** 다량의 데이터를 그룹화하고, 신고가 및 주요 정책 소식을 자동으로 추출.
- **수혜 단지 매핑:** 개발 소식과 관련된 주변 수혜 아파트 단지명을 자동으로 식별하여 리포트에 포함.
- **자동화 배포:** n8n 워크플로우를 통해 매일 08:30 KST에 Slack으로 자동 전송.

## 결과물 리스트
- **API:** `/agent/real_estate/insight_report`
- **워크플로우:** `workflows/real_estate/insight_report_workflow.json`
- **프롬프트:** `src/modules/real_estate/prompts/insight_parser.md`

## 검증 스크린샷/로그
(실제 Slack 메시지 및 테스트 로그 내용은 Walkthrough 참조)
