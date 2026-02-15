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
