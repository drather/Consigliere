# 🏗️ Infrastructure & Environment Troubleshooting
Issues related to Docker, Networking, OS, and Environment Variables.

## 📦 Docker
### Issue: Docker Image Pull Error (`invalid tar header`)
- **Date:** 2026-02-15
- **Symptom:** `docker-compose up` fails with `archive/tar: invalid tar header` when pulling `n8n:latest`.
- **Root Cause:** Network instability or corrupted layer cache for the `latest` tag.
- **Solution:**
  1. Pin the image version (e.g., `image: docker.n8n.io/n8nio/n8n:1.72.0`).
  2. Run `docker system prune -f` to clear corrupted cache.
# 🐍 Backend & Application Troubleshooting
Issues related to Python Code, FastAPI Server, Dependencies, and Imports.

## 🐍 Python Runtime
### Issue: ModuleNotFoundError (`No module named 'agents'`)
- **Date:** 2026-02-15
- **Symptom:** Running `src/main.py` fails with import errors.
- **Root Cause:** Python does not automatically add the `src/` directory to `sys.path` when running scripts from the root.
- **Solution:**
  1. Use a unified entrypoint script (`run_server.py`) that explicitly appends `src/` to `sys.path`.
  2. Or run via `export PYTHONPATH=src && python -m uvicorn src.main:app`.
