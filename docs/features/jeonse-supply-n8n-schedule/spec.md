# 전세/공급 데이터 n8n 자동 수집 등록

**작성일:** 2026-05-27  
**브랜치:** master

## 목표

매주 일요일 05:00 KST에 전세 수집 → 공급 수집을 순차 실행하고,
실패 시 Slack 알림을 발송한다.

## 배경

`JeonseClient`(`POST /jobs/jeonse/collect`)와 `SupplyClient`(`POST /jobs/supply/collect`)는
2026-05-25에 구현 완료됐으나 수동 트리거만 가능한 상태.
n8n 스케줄에 주 1회 자동 수집 Job으로 등록해 데이터를 항상 최신 상태로 유지한다.

## 변경 내용

- 신규: `workflows/real_estate/jeonse_supply_collect.json` — n8n 워크플로우 (7 nodes)
- 수정: `scripts/deploy_workflows.py` — workflows_to_deploy 리스트에 1줄 추가
- 수정: `docs/workflows_registry.md` — WR-007 항목 추가

## 아키텍처

```
[n8n] Weekly Schedule (cron: 0 5 * * 0)
  → POST /jobs/jeonse/collect
    ├── 200 OK → POST /jobs/supply/collect
    │               ├── 200 OK → 완료
    │               └── 오류 → POST /notify/slack "[전세/공급수집] 공급 수집 실패"
    └── 오류 → POST /notify/slack "[전세/공급수집] 전세 수집 실패"
```
