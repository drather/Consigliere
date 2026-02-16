# Infrastructure Upgrade Specification: Dockerize API

## 🎯 Objective
Integrate the Python FastAPI backend into the Docker Compose ecosystem to ensure consistent environment and seamless communication with n8n and ChromaDB.

## 🛠️ Architecture
- **Service Name:** `consigliere_api`
- **Base Image:** `python:3.12-slim`
- **Network:** `consigliere_net` (Shared with n8n, chromadb)
- **Ports:** `8000:8000` (Host access)
- **Volumes:**
  - `./src:/app/src` (Hot reload for development)
  - `./data:/app/data` (Persistence)

## 🔄 Integration
- **n8n:** Connects via `http://consigliere_api:8000`.
- **ChromaDB:** Connects via `http://consigliere_chromadb:8000`.

## 📝 Dockerfile
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONPATH=/app/src
CMD ["python", "src/main.py"]
```
