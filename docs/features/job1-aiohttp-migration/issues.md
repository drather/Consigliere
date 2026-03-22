# Issues: Job1 aiohttp 비동기 전환

## ISS-001: Docker VM 디스크 공간 부족으로 빌드 실패
- **현상:** `no space left on device` — 빌드 캐시 기록 불가
- **원인:** Docker Desktop VM 가상 디스크 한도 초과 (기존 이미지 4개 = ~7GB)
- **해결:** Docker Desktop → Resources → Virtual disk limit 16GB로 증설

## ISS-002: save_transactions_batch 메서드 누락
- **현상:** `'ChromaRealEstateRepository' object has no attribute 'save_transactions_batch'`
- **원인:** 코드 롤백 시 이전에 추가된 메서드까지 함께 되돌아감
- **해결:** `repository.py`에 메서드 재추가

## ISS-003: 3일 필터가 너무 엄격
- **현상:** 최신 데이터가 조회되지 않음 (3월 17일이 최신으로 표시)
- **원인:** 국토부 API 데이터 지연 특성 (계약 → 신고 → API 게시 3~5일 소요)
- **해결:** cutoff 3일 → 7일로 완화
