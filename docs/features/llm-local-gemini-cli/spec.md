# LLM 호출 전면 로컬화 (Gemini CLI)

**작성일:** 2026-06-10
**브랜치:** master (직접 작업, 별도 feature 브랜치 없음)

## 목표

유료 LLM API 호출을 전면 금지하고, 로컬에 설치된 `gemini` CLI(`gemini-3-flash-preview`)를
서브프로세스로 호출하는 방식으로 전체 LLM 파이프라인을 교체한다.

## 배경

- 사용자 지시: "이제부터 LLM을 API로 호출하는 것은 절대 없을 것 — 로컬 gemini CLI로 전면 교체"
- 모델: `gemini-3-flash-preview` (요약/종합 용도로 충분, 사용자 직접 검증)

## 변경 범위

1. **`~/.gemini/GEMINI.md` 글로벌 메모리 정리**
   - Consigliere 전용 지시("`.gemini_instructions.md`/`active_state.md` 항상 읽기") 제거
   - 원인: 모든 gemini CLI 실행 시 `gemini-superpowers` 익스텐션 로드 + 프로젝트 워크스페이스 스캔 → 81초 소요

2. **`src/core/llm.py` — `GeminiCliClient` 재작성**
   - `subprocess.run(["gemini", "--model", model, "--extensions", "", prompt], cwd="/tmp", timeout=120)`
   - `GEMINI_CLI_MODEL` 환경변수로 모델 지정 (기본값 `gemini-3-flash-preview`)
   - `cwd=/tmp` + `--extensions ""` → 워크스페이스 스캔 방지 (81s → ~10s)

3. **Docker 통합**
   - `Dockerfile`: Node.js 20 + `@google/gemini-cli@0.24.0`을 apt/npm으로 직접 설치 (Linux 네이티브)
   - `docker-compose.yml`:
     - `LLM_PROVIDER=gemini-cli`, `GEMINI_CLI_MODEL=gemini-3-flash-preview` 환경변수 추가
     - `~/.gemini:/root/.gemini` (read-write) 마운트 — OAuth 자격증명 공유

## 아키텍처

```
LLMFactory.create()  (LLM_PROVIDER=gemini-cli)
  └── GeminiCliClient
        └── subprocess: gemini --model gemini-3-flash-preview --extensions "" <prompt>  (cwd=/tmp)
              └── ~/.gemini (OAuth 자격증명, host ↔ container 공유)
```

`LLMFactory`/`BaseLLMClient` 인터페이스는 변경 없음 — provider 라우팅만 교체 (OCP 준수).
