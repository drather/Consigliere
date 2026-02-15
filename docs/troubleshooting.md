# 🔧 Troubleshooting Log
This document records technical issues encountered during development and their solutions.
Consult this file before starting new tasks to avoid repeating past mistakes.

## 🏗️ Infrastructure & Docker
### Issue: Docker Image Pull Error (`invalid tar header`)
- **Date:** 2026-02-15
- **Symptom:** `docker-compose up` fails with `archive/tar: invalid tar header` when pulling `n8n:latest`.
- **Root Cause:** Network instability or corrupted layer cache for the `latest` tag.
- **Solution:**
  1. Pin the image version (e.g., `image: docker.n8n.io/n8nio/n8n:1.72.0`).
  2. Run `docker system prune -f` to clear corrupted cache.

## 🐍 Python & Application
### Issue: ModuleNotFoundError (`No module named 'agents'`)
- **Date:** 2026-02-15
- **Symptom:** Running `src/main.py` fails with import errors.
- **Root Cause:** Python does not automatically add the `src/` directory to `sys.path` when running scripts from the root.
- **Solution:**
  1. Use a unified entrypoint script (`run_server.py`) that explicitly appends `src/` to `sys.path`.
  2. Or run via `export PYTHONPATH=src && python -m uvicorn src.main:app`.

### Issue: Gemini API Quota Exceeded (`429 Resource Exhausted`)
- **Date:** 2026-02-15
- **Symptom:** AI features fail with `429 Quota exceeded` error.
- **Root Cause:** The `gemini-3-pro-preview` model has strict quotas or billing requirements on the API key being used.
- **Solution:**
  1. Switch to a more efficient model: `gemini-3-flash-preview`.
  2. Check Google AI Studio billing settings.

## 🔗 n8n Integration
### Issue: 422 Unprocessable Entity
- **Date:** 2026-02-15
- **Symptom:** n8n HTTP Request returns 422 error.
- **Root Cause:** n8n sent data wrapped in an unexpected JSON structure (using `bodyParameters`), failing Pydantic validation.
- **Solution:**
  1. In n8n HTTP Node, set `JSON/Raw Parameters` to `On`.
  2. Manually construct the JSON body: `{"text": "{{ $json.text }}"}`.
