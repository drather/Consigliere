# System Architecture & Infrastructure

## 1. Overview
Project Consigliere operates on a **Docker Compose** infrastructure, ensuring isolation and consistency across environments. All backend services must be managed via Docker.

## 2. Service Layout (docker-compose.yml)

| Service Name | Container Name | Port (Host:Container) | Description | Dependencies |
| :--- | :--- | :--- | :--- | :--- |
| **api** | `consigliere_api` | `8000:8000` | FastAPI Backend (Python 3.12). Core logic & Agents. | `chromadb` |
| **n8n** | `consigliere_n8n` | `5678:5678` | Workflow Automation. Triggers API via HTTP. | `api` |
| **chromadb** | `consigliere_chromadb` | `8001:8000` | Vector Database for RAG & Memory. | - |

## 3. Data Persistence (Volumes)
- **Codebase:** `./src` -> `/app/src` (Hot-reloading enabled for API)
- **Data:** `./data` -> `/app/data` (Shared storage for Ledgers, Reports)
- **ChromaDB:** `./data/chroma_data` -> `/chroma/chroma` (Vector indexes)
- **n8n:** `./data/n8n_data` -> `/home/node/.n8n` (Workflow data)

## 4. Network
- **Network Name:** `consigliere_net` (Bridge)
- **Internal Communication:**
    - API -> ChromaDB: `http://consigliere_chromadb:8000`
    - n8n -> API: `http://consigliere_api:8000` (Use internal DNS)

## 5. Development Guidelines
- **Always** use `docker-compose up -d` to start the backend.
- **Do not** run `run_server.py` locally unless debugging a specific script in isolation (and ensure port 8000 is free).
- **Streamlit:** Currently runs locally via `.venv` (Port 8502) but consumes APIs from the Dockerized Backend (`localhost:8000`).
