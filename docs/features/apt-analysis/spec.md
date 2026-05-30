# 개별 아파트 심층 분석 기능

**작성일:** 2026-05-30
**브랜치:** master

## 목표

단지 코드를 입력받아 DB에 축적된 모든 데이터를 통합하고,
로컬 LLM CLI(Claude Code / Gemini CLI)로 자연어 종합 인사이트를 생성한다.
결과는 DB에 저장되어 이후에도 조회 가능하며, Slack 알림과 대시보드 Tab1에서 확인 가능하다.

## 변경 파일

- `src/core/llm.py` — ClaudeCodeClient, GeminiCliClient 추가
- `src/modules/real_estate/apt_analysis/` — 신규 패키지 (models, repository, orchestrator, formatter)
- `src/api/routers/real_estate.py` — POST /jobs/apt/analyze, GET /dashboard/apt/analysis 엔드포인트
- `src/dashboard/views/real_estate.py` — Tab1 심층 분석 버튼 추가
- `docker-compose.yml` — claude CLI 볼륨 마운트
