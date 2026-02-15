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
