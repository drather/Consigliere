# Progress: Job1 aiohttp 비동기 전환

## 체크리스트

- [x] spec.md 작성
- [x] `requirements.txt` — aiohttp>=3.9.0 추가
- [x] `monitor/service.py` — `_parse_item_to_transaction` 모듈 레벨 함수 추출
- [x] `models.py` — `deal_date_int` 필드 추가
- [x] `repository.py` — `delete_old_transactions()` 메서드 추가
- [x] `service.py` — `fetch_transactions` async 재구현 + 헬퍼 3개
- [ ] Docker 재빌드 후 검증 (OOM/429 없이 완주)
