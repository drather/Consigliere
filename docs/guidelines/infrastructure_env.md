# Infrastructure & Environment Guidelines

## 1. Environment Agnostic
- The application is containerized using Docker and `docker-compose.yml`.
- The backend API, n8n, and Vector DB (ChromaDB) run as Docker containers.
- **DO NOT** run `run_server.py` locally for production unless debugging an isolated script.
- Verify service status with `docker-compose ps`.

## 2. Hardware Architecture (CRITICAL)
- **Target environment is macOS Apple Silicon (ARM64).**
- ALWAYS prefix shell commands with `arch -arm64` if they involve python, pip, or library execution to ensure ARM architecture.
- Verify architecture with `python3 -c "import platform; print(platform.machine())"` if in doubt.
- Avoid installing x86_64 (i386) binaries via Rosetta to prevent deep C-extension failures (e.g., ChromaDB).

## 3. Configuration & Secrets
- All environment variables are loaded via `.env` files.
- Refer to `.env.example` when adding new keys.
- **Swappable LLM Backend**: Use `LLM_PROVIDER` in `.env` to define whether to use `gemini`, `claude`, etc.
