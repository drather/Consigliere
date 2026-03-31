# Infrastructure Guide

**Last Updated:** 2026-03-31

> 상세 다이어그램은 [`docs/system_snapshot/infrastructure.md`](../system_snapshot/infrastructure.md) 참조.

## 1. 컨테이너 구성

| 서비스 | 컨테이너명 | 호스트 포트 | 이미지 | 볼륨 |
|--------|-----------|------------|-------|------|
| FastAPI Backend | `consigliere_api` | `8000` | `python:3.12-slim` | `./src:/app/src`, `./data:/app/data` |
| Streamlit Dashboard | `consigliere_dashboard` | `8501` | `python:3.12-slim` | `./src:/app/src`, `./data:/app/data` |
| n8n Automation | `consigliere_n8n` | `5678` | `n8nio/n8n:latest` | `./data/n8n_data:/home/node/.n8n` |
| ChromaDB | `consigliere_chromadb` | `8001` | `chromadb/chroma` | `./data/chroma_data:/chroma/chroma` |

## 2. 네트워크

- **드라이버:** Bridge (`consigliere_net`)
- **컨테이너 간 통신:** 서비스명으로 참조
  - API → ChromaDB: `http://consigliere_chromadb:8000`
  - API → n8n: `http://consigliere_n8n:5678`
- **외부 접근:** `localhost:{호스트 포트}`

## 3. 데이터 볼륨

- 런타임 데이터: `./data/` (컨테이너 외부 마운트, 영속)
- n8n 워크플로우 상태: `./data/n8n_data/`
- ChromaDB 벡터 데이터: `./data/chroma_data/`

## 4. 주요 커맨드

```bash
# 전체 서비스 기동
docker-compose up -d

# 상태 확인
docker-compose ps

# API만 재빌드 (코드 변경 시)
docker compose up -d --build api

# 로그 확인
docker-compose logs -f api
```
