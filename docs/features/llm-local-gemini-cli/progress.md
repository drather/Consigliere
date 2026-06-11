# Progress

- [x] `~/.gemini/GEMINI.md` Consigliere 전용 지시 제거
- [x] `GeminiCliClient` TDD (5개 신규 테스트, `--model`/`--extensions`/`cwd=/tmp`/모델 기본값/env override)
- [x] `GeminiCliClient.generate()` / `generate_json()` 재작성
- [x] `Dockerfile` — Node.js 20 + `@google/gemini-cli@0.24.0` 설치
- [x] `docker-compose.yml` — `LLM_PROVIDER`/`GEMINI_CLI_MODEL` env + `~/.gemini` 마운트
- [x] 이미지 재빌드 + 컨테이너 재시작
- [x] 컨테이너 내 `gemini` CLI 단독 호출 검증 (9.5초, 정상 응답)
- [x] `LLMFactory.create()` → `GeminiCliClient` → `generate_json()` E2E 검증
- [x] 전체 테스트 회귀 확인 (893 tests, 신규 9개 포함, 기존 flaky 9개 외 신규 실패 없음)
- [x] `docs/context/active_state.md` 업데이트
