# Environment Guide

**Last Updated:** 2026-03-31

## 1. Python 실행 (CRITICAL — ARM64)

이 프로젝트는 **macOS Apple Silicon (ARM64)** 환경에서 동작한다.

### ❌ 절대 금지
```bash
python3 script.py
source .venv/bin/activate && pytest ...
pip install <package>
```
> 이유: `.venv` Python은 universal binary지만 pydantic-core 등 C 확장은 arm64 전용 컴파일. `arch` 없이 실행하면 x86_64로 해석되어 `ImportError: incompatible architecture` 발생.

### ✅ 올바른 실행 형식
```bash
# 스크립트 실행
arch -arm64 .venv/bin/python3.12 script.py

# 테스트 실행
arch -arm64 .venv/bin/python3.12 -m pytest tests/ -v
arch -arm64 .venv/bin/python3.12 -m pytest tests/modules/career/ -v

# 패키지 설치
arch -arm64 .venv/bin/pip install <package>
```

---

## 2. Docker 환경 규칙

- 모든 서비스는 Docker Compose로 실행한다. 로컬 직접 실행 금지 (디버깅 스크립트 제외).
- 서비스 상태 확인: `docker-compose ps`
- 서비스 기동: `docker-compose up -d`
- API 재빌드: `docker compose up -d --build api`
- API 재시작: `docker compose restart api`
- x86_64(i386) 바이너리를 Rosetta로 설치하지 않는다 (ChromaDB 등 C 확장 오류 원인).

---

## 3. 환경변수 관리

- 모든 환경변수는 `.env` 파일로 관리한다.
- 새 키 추가 시 반드시 `.env.example`에도 추가한다.
- **LLM 전환:** `.env`의 `LLM_PROVIDER` 값으로 모델 교체 (`claude`, `gemini` 등).
- 현재 기본값: `LLM_PROVIDER=claude` → `claude-sonnet-4-6`
- 코드에 API 키, 토큰 등을 하드코딩하지 않는다.
