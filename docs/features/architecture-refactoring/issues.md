# Issues & Fixes: Architecture Refactoring

## 1. Local Test Environment Architecture Mismatch
- **Status:** Open
- **Discovery Date:** 2026-03-17
- **Description:** `.venv` 환경의 아키텍처 불일치(arm64 vs x86_64)로 인해 `pytest` 실행 시 `_cffi_backend` 등 바이너리 모듈에서 `ImportError`가 발생함.
- **Impact:** 로컬에서의 자동화된 테스트(`pytest`) 실행이 불가능함.
- **Suggested Fix:** 로컬 환경에 맞는 아키텍처(arm64)로 가상환경을 재구축하거나, Docker 컨테이너 내부에서 테스트를 실행하도록 설정 필요.
- **Note:** 코드 정합성(Claude integration, SOLID refactoring)은 논리적으로 확인되었으나 런타임 검증이 필요함.
