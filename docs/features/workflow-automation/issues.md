# Issues Log: Workflow Automation

## 1. n8n API `400 Bad Request` during Deployment
- **Problem**: When deploying workflows via `POST /workflows`, the API returned `400 Bad Request`.
- **Cause**: 
    1. The n8n v1 API requires a specific JSON schema, including a mandatory `settings` object.
    2. The API rejects additional properties not defined in its schema (e.g., `style`, `pinData`).
    3. Missing or invalid `X-N8N-API-KEY`.
- **Fix**: 
    1. Updated workflow JSON files to include `"settings": { "executionOrder": "v1" }`.
    2. Stripped `style` and `pinData` from the JSON templates.
    3. Configured `N8N_API_KEY` in `.env` and updated `AutomationService` to use it.

## 2. Python Package Architecture Mismatch (macOS Apple Silicon)
- **Problem**: Streamlit failed to start with a `dlopen` error for `numpy` and `pandas`.
- **Cause**: The virtual environment (`.venv`) contained x86_64 binaries, while the host system required ARM64.
- **Fix**: Force-reinstalled all dependencies using `arch -arm64 pip install --force-reinstall -r requirements.txt`.

## 3. Container Networking (Connection Refused)
- **Problem**: Dashboard reported "No workflows found" and API logged `Connection refused`.
- **Cause**: The API container was trying to reach n8n at `localhost:5678`, which is only valid outside the container.
- **Fix**: Updated `docker-compose.yml` to set `N8N_WEBHOOK_URL=http://consigliere_n8n:5678` for the `api` service.

## 4. Dashboard Port Conflict
- **Problem**: `docker-compose up` failed for the `dashboard` service because port `8501` was already in use.
- **Cause**: A manual Streamlit process was still running on the host.
- **Fix**: Terminated the manual process using `kill -9` before starting the container.
