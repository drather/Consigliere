# Issues & 의사결정

## 1. 모델 선택: `gemini-3-flash-preview`
- `gemini-3.5-flash`, `gemini-2.5-flash-preview-05-20` → 404 (모델 없음)
- `gemini-3-flash-preview` → 정상 동작, 사용자 직접 검증 후 채택

## 2. Gemini CLI 워크스페이스 스캔 (81초 → ~10초)
- **증상:** `gemini --model ... <prompt>` 실행 시 81초 소요 + 무관한 프로젝트(문정시영 등) 언급
- **원인:** `~/.gemini/GEMINI.md` 글로벌 메모리에 "Consigliere 프로젝트는 항상 active_state.md를 읽어라" 지시가 박혀 있어,
  cwd와 무관하게 `gemini-superpowers` 익스텐션 로드 + 워크스페이스 스캔 발생
- **해결:** 해당 지시 제거 + `cwd=/tmp` + `--extensions ""` → ~10초로 단축

## 3. (당초 계획 폐기) 호스트 바이너리 바인드 마운트
- **당초 계획:** 호스트 `/usr/local/bin/node`, `/usr/local/bin/gemini`, `node_modules/@google`를 컨테이너에 바인드 마운트
- **실패 원인 1:** 호스트 `node`/`gemini`는 macOS Mach-O 바이너리 → Linux 컨테이너에서 `exec format error`
- **실패 원인 2:** `/usr/local`은 Docker Desktop 기본 파일 공유 경로(`/Users`, `/tmp` 등)에 포함되지 않아 `mount ... not a directory` 에러
- **최종 결정:** Dockerfile에서 Node.js 20 + `@google/gemini-cli@0.24.0`을 apt/npm으로 직접 설치 (Linux 네이티브 바이너리)

## 4. `~/.gemini` 마운트: read-only → read-write
- **증상:** `:ro`로 마운트 시 `EROFS: read-only file system, open '/root/.gemini/oauth_creds.json'`
  + `mkdir '/root/.gemini/tmp/.../chats'` ENOENT
- **원인:** gemini CLI가 OAuth 토큰 갱신(`cacheCredentials`) 및 세션 임시파일(`chats/`)을 `~/.gemini`에 씀
- **해결:** `~/.gemini:/root/.gemini` (read-write)로 변경 — 호스트와 컨테이너가 동일 자격증명 디렉토리 공유

## 5. Docker BuildKit 캐시 손상
- **증상:** `docker compose build api` 반복 실패 — `failed to solve: python:3.12-slim: ... lease does not exist: not found`
- **해결:** `docker buildx prune -a -f` (8GB 캐시 정리) 후 정상 빌드
- **참고:** 이번 작업의 Dockerfile 변경과 무관한 BuildKit 자체 이슈
