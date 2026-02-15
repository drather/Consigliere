# 🔗 Workflow & Integration Troubleshooting
Issues related to n8n, External APIs, and Data Formats.

## ⚙️ n8n Integration
### Issue: 422 Unprocessable Entity
- **Date:** 2026-02-15
- **Symptom:** n8n HTTP Request returns 422 error.
- **Root Cause:** n8n sent data wrapped in an unexpected JSON structure (using `bodyParameters`), failing Pydantic validation.
- **Solution:**
  1. In n8n HTTP Node, set `JSON/Raw Parameters` to `On`.
  2. Manually construct the JSON body: `{"text": "{{ $json.text }}"}`.
