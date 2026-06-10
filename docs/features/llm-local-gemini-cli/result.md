# Result

**완료일:** 2026-06-10

## 변경 내용

- `~/.gemini/GEMINI.md` — Consigliere 전용 글로벌 메모리 제거
- `src/core/llm.py` — `GeminiCliClient` 재작성 (`--model`/`--extensions ""`/`cwd=/tmp`, `GEMINI_CLI_MODEL` env)
- `tests/core/test_llm_cli_clients.py` — `TestGeminiCliClient` 5개 신규 테스트
- `Dockerfile` — Node.js 20 + `@google/gemini-cli@0.24.0` 설치 (apt + npm)
- `docker-compose.yml` — `LLM_PROVIDER=gemini-cli`, `GEMINI_CLI_MODEL=gemini-3-flash-preview`,
  `~/.gemini:/root/.gemini` (rw) 마운트

## 검증

- `TestGeminiCliClient` 10/10 pass
- `docker exec consigliere_api gemini --model gemini-3-flash-preview --extensions "" "ok만 답해"`
  → 9.5초, "ok" 응답 (워크스페이스 스캔 없음)
- `LLMFactory.create()` (`LLM_PROVIDER=gemini-cli`) → `GeminiCliClient`
  → `generate_json("...JSON으로 summary 키...")` → `{'summary': '...5% 상승했습니다.'}` 정상 파싱
- 컨테이너 정상 기동, 로그에 `Initializing GeminiCliClient (local CLI subprocess)` 확인

## 테스트 결과

```
893 tests, 10 failed, 883 passed
```

- 변경 전(stash) 기준 9 failed / 875 passed (884 tests)
- 추가된 9개 신규 테스트 모두 통과, 신규 회귀 없음
- 기존 10개 실패는 `test_career.py`/`test_dashboard_ui.py`/`test_n8n_news.py`/`test_news_insight.py`/
  `test_real_estate_insight.py`/`test_real_estate_tab5.py` 등 기존부터 존재하던 flaky/환경 의존 실패
  (stash 비교로 본 변경과 무관함 확인)

## E2E 검증 면제

- **사유:** 화면단(Streamlit) 변경 없음 — LLM provider 백엔드 교체 + Docker 인프라 변경만 포함
- **변경 범위:** `src/core/llm.py`, `Dockerfile`, `docker-compose.yml`, `~/.gemini/GEMINI.md`
