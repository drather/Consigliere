# Result: Job1 aiohttp 비동기 전환

**완료일:** 2026-03-22
**브랜치:** `fix/real-estate-comprehensive-review`

## 결과 요약

| 항목 | 이전 | 이후 |
|---|---|---|
| 구현 방식 | ThreadPoolExecutor(max_workers=3) | aiohttp + asyncio.Semaphore(2) |
| OOM | 빈번 (exitCode=137) | 없음 |
| 429 Rate Limit | 빈번 | 없음 |
| 소요 시간 | 완주 불가 (중간 crash) | 약 3분 30초 (71개 구 완주) |
| 수집 범위 | 월 전체 | 최근 7일 이내 |
| 데이터 라이프사이클 | 누적 무한증가 | 1년 이상 자동 삭제 |

## 검증 결과 (2026-03-22 실행)

- **수집:** 71개 지구, 999건 수집 / 992건 저장
- **OOM:** `docker events --filter event=oom` — 없음
- **429:** 로그 없음
- **최신 거래일:** 2026-03-18 (API 신고 지연 특성, 정상)
- **deleted_old_count:** 0 (기존 데이터 1년 미만이므로 정상)

## 변경 파일

| 파일 | 변경 내용 |
|---|---|
| `requirements.txt` | `aiohttp>=3.9.0` 추가 |
| `monitor/service.py` | `_parse_item_to_transaction` 모듈 레벨 함수 추출 |
| `models.py` | `to_chroma_format()`에 `deal_date_int` 필드 추가 |
| `repository.py` | `save_transactions_batch`, `delete_old_transactions` 추가 |
| `service.py` | `fetch_transactions` async 재구현 + `_async_fetch_all`, `_fetch_one_district` 헬퍼 추가 |

## 참고 사항

- 국토부 API 데이터 지연: 계약 후 신고까지 평균 3~5일 → 7일 필터 적용
- ChromaDB upsert 방식 → 중복 없이 update/insert 처리
- Semaphore(2): 429 완전 차단, 필요 시 조정 가능
