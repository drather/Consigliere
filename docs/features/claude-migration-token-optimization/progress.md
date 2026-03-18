# Progress: Claude LLM 전환 및 토큰 최적화

## 작업 로그

- [x] `LLMFactory` 기본값 `"gemini"` → `"claude"` 변경
- [x] `.env.example` Claude 설정 항목 추가
- [x] Docker 기동 및 인사이트 리포트 실행 테스트
- [x] 버그 1 발견 및 수정: `max_tokens=4096` truncation → 8192으로 상향
- [x] 버그 2 발견 및 수정: JSON 앞뒤 텍스트로 인한 파싱 실패 → 경계 추출 로직 추가
- [x] 인사이트 리포트 E2E 테스트 성공 (Score 82, HTTP 200)
- [x] Slack 전송 확인 (`POST /notify/slack` → `ok: true`)
- [x] 토큰 최적화 적용 (MAX_ITERATIONS, Validator max_tokens, 데이터 상한)
- [x] API 재시작 및 정상 동작 확인
