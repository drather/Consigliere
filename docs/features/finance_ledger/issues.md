# Finance Ledger: Troubleshooting Log
This file tracks specific issues encountered during the development of Finance Ledger.

## 🔗 Related Issues
For general system-wide issues, refer to:
- [Backend Troubleshooting](../../troubleshooting/backend.md)
- [Workflow Troubleshooting](../../troubleshooting/workflows.md)

## 🐍 Python & Application
### Issue: ModuleNotFoundError (`No module named 'agents'`)
- **Date:** 2026-02-15
- **Symptom:** Running `src/main.py` fails with import errors.
- **Root Cause:** Python path configuration.
- **Solution:** Use `run_server.py`.

## ⚙️ n8n Integration
### Issue: 422 Unprocessable Entity
- **Date:** 2026-02-15
- **Symptom:** n8n HTTP Request returns 422 error.
- **Root Cause:** n8n JSON payload format mismatch.
- **Solution:** Manually construct JSON body: `{"text": "{{ $json.text }}"}`.
