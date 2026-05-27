# Jeonse & Supply n8n Weekly Schedule Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** n8n에 매주 일요일 05:00 KST 전세/공급 자동 수집 워크플로우를 등록하고, 실패 시 Slack 알림을 발송한다.

**Architecture:** 단일 n8n 워크플로우 (`jeonse_supply_collect.json`) — scheduleTrigger → Collect Jeonse → IF OK? → Collect Supply → IF OK? / Slack Error. 기존 `real_estate_monitor.json` 패턴 그대로 따름.

**Tech Stack:** n8n JSON, `scripts/deploy_workflows.py` (AutomationService), `docs/workflows_registry.md`

---

### Task 1: SOP 문서 생성 (spec.md + progress.md)

**Files:**
- Create: `docs/features/jeonse-supply-n8n-schedule/spec.md`
- Create: `docs/features/jeonse-supply-n8n-schedule/progress.md`

- [ ] **Step 1: spec.md 작성**

`docs/features/jeonse-supply-n8n-schedule/spec.md` 생성:

```markdown
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
```

- [ ] **Step 2: progress.md 작성**

`docs/features/jeonse-supply-n8n-schedule/progress.md` 생성:

```markdown
# Progress

- [ ] Task 1: SOP 문서 생성
- [ ] Task 2: n8n 워크플로우 JSON 작성
- [ ] Task 3: deploy_workflows.py 수정
- [ ] Task 4: workflows_registry.md WR-007 추가
- [ ] Task 5: 배포 검증 + result.md + context 업데이트
```

- [ ] **Step 3: progress.md Task 1 체크 후 커밋**

progress.md에서 Task 1 체크 후:
```bash
git add docs/features/jeonse-supply-n8n-schedule/spec.md \
        docs/features/jeonse-supply-n8n-schedule/progress.md
git commit -m "docs(sop): jeonse-supply-n8n-schedule spec + progress 생성"
```

---

### Task 2: n8n 워크플로우 JSON 파일 작성

**Files:**
- Create: `workflows/real_estate/jeonse_supply_collect.json`

- [ ] **Step 1: 워크플로우 JSON 파일 생성**

`workflows/real_estate/jeonse_supply_collect.json` 생성:

```json
{
  "name": "Jeonse & Supply Weekly Collect",
  "nodes": [
    {
      "parameters": {
        "rule": {
          "interval": [
            {
              "field": "cronExpression",
              "expression": "0 5 * * 0"
            }
          ]
        }
      },
      "type": "n8n-nodes-base.scheduleTrigger",
      "typeVersion": 1.2,
      "position": [0, 0],
      "id": "schedule-trigger",
      "name": "Weekly Schedule (Sunday 05:00)"
    },
    {
      "parameters": {
        "method": "POST",
        "url": "http://consigliere_api:8000/jobs/jeonse/collect",
        "sendBody": true,
        "bodyParameters": {"parameters": []},
        "options": {}
      },
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [240, 0],
      "id": "collect-jeonse",
      "name": "Collect Jeonse"
    },
    {
      "parameters": {
        "conditions": {
          "options": {"caseSensitive": true, "leftValue": "", "typeValidation": "strict"},
          "conditions": [
            {
              "leftValue": "={{ $response.statusCode }}",
              "rightValue": 200,
              "operator": {"type": "number", "operation": "equals"}
            }
          ],
          "combinator": "and"
        }
      },
      "type": "n8n-nodes-base.if",
      "typeVersion": 2,
      "position": [480, 0],
      "id": "if-jeonse-ok",
      "name": "Jeonse OK?"
    },
    {
      "parameters": {
        "method": "POST",
        "url": "http://consigliere_api:8000/jobs/supply/collect",
        "sendBody": true,
        "bodyParameters": {"parameters": []},
        "options": {}
      },
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [720, -80],
      "id": "collect-supply",
      "name": "Collect Supply"
    },
    {
      "parameters": {
        "method": "POST",
        "url": "http://consigliere_api:8000/notify/slack",
        "sendBody": true,
        "bodyParameters": {
          "parameters": [
            {
              "name": "message",
              "value": "=⚠️ *[전세/공급수집]* 전세 수집 실패 ({{ $now.format('YYYY-MM-DD HH:mm') }})"
            }
          ]
        },
        "options": {}
      },
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [720, 80],
      "id": "slack-jeonse-error",
      "name": "Slack Jeonse Error"
    },
    {
      "parameters": {
        "conditions": {
          "options": {"caseSensitive": true, "leftValue": "", "typeValidation": "strict"},
          "conditions": [
            {
              "leftValue": "={{ $response.statusCode }}",
              "rightValue": 200,
              "operator": {"type": "number", "operation": "equals"}
            }
          ],
          "combinator": "and"
        }
      },
      "type": "n8n-nodes-base.if",
      "typeVersion": 2,
      "position": [960, -80],
      "id": "if-supply-ok",
      "name": "Supply OK?"
    },
    {
      "parameters": {
        "method": "POST",
        "url": "http://consigliere_api:8000/notify/slack",
        "sendBody": true,
        "bodyParameters": {
          "parameters": [
            {
              "name": "message",
              "value": "=⚠️ *[전세/공급수집]* 공급 수집 실패 ({{ $now.format('YYYY-MM-DD HH:mm') }})"
            }
          ]
        },
        "options": {}
      },
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [1200, -160],
      "id": "slack-supply-error",
      "name": "Slack Supply Error"
    }
  ],
  "connections": {
    "Weekly Schedule (Sunday 05:00)": {
      "main": [
        [{"node": "Collect Jeonse", "type": "main", "index": 0}]
      ]
    },
    "Collect Jeonse": {
      "main": [
        [{"node": "Jeonse OK?", "type": "main", "index": 0}]
      ]
    },
    "Jeonse OK?": {
      "main": [
        [{"node": "Collect Supply", "type": "main", "index": 0}],
        [{"node": "Slack Jeonse Error", "type": "main", "index": 0}]
      ]
    },
    "Collect Supply": {
      "main": [
        [{"node": "Supply OK?", "type": "main", "index": 0}]
      ]
    },
    "Supply OK?": {
      "main": [
        [],
        [{"node": "Slack Supply Error", "type": "main", "index": 0}]
      ]
    }
  },
  "settings": {
    "executionOrder": "v1"
  }
}
```

- [ ] **Step 2: progress.md Task 2 체크 후 커밋**

progress.md에서 Task 2 체크 후:
```bash
git add workflows/real_estate/jeonse_supply_collect.json \
        docs/features/jeonse-supply-n8n-schedule/progress.md
git commit -m "feat(n8n): Jeonse & Supply Weekly Collect 워크플로우 JSON 추가"
```

---

### Task 3: deploy_workflows.py 수정

**Files:**
- Modify: `scripts/deploy_workflows.py:23-28`

- [ ] **Step 1: workflows_to_deploy 리스트에 경로 추가**

`scripts/deploy_workflows.py` 의 `workflows_to_deploy` 리스트:

```python
    workflows_to_deploy = [
        "workflows/finance/finance_mvp.json",
        "workflows/real_estate/real_estate_monitor.json",
        "workflows/real_estate/real_estate_news.json",
        "workflows/real_estate/insight_report_workflow.json",
        "workflows/real_estate/jeonse_supply_collect.json",
    ]
```

- [ ] **Step 2: progress.md Task 3 체크 후 커밋**

progress.md에서 Task 3 체크 후:
```bash
git add scripts/deploy_workflows.py \
        docs/features/jeonse-supply-n8n-schedule/progress.md
git commit -m "feat(deploy): jeonse_supply_collect.json 배포 스크립트에 추가"
```

---

### Task 4: workflows_registry.md WR-007 추가

**Files:**
- Modify: `docs/workflows_registry.md`

- [ ] **Step 1: Active Routines 테이블에 WR-007 행 추가**

`docs/workflows_registry.md` Active Routines 테이블 마지막에 추가:

```markdown
| `WR-007`   | Real Estate | Jeonse & Supply Weekly Collect  | 매주 일요일 05:00 KST | 전세/공급 데이터 주 1회 자동 수집 (실패 시 Slack) | Active | - |
```

- [ ] **Step 2: Last Updated 날짜 업데이트**

`docs/workflows_registry.md` 헤더의 `**Last Updated:** 2026-02-20` → `**Last Updated:** 2026-05-27`

- [ ] **Step 3: progress.md Task 4 체크 후 커밋**

progress.md에서 Task 4 체크 후:
```bash
git add docs/workflows_registry.md \
        docs/features/jeonse-supply-n8n-schedule/progress.md
git commit -m "docs(registry): WR-007 Jeonse & Supply Weekly Collect 등록"
```

---

### Task 5: 배포 + 검증 + result.md + context 업데이트

**Files:**
- Create: `docs/features/jeonse-supply-n8n-schedule/result.md`
- Modify: `docs/context/active_state.md`
- Modify: `docs/context/history.md`

- [ ] **Step 1: deploy_workflows.py 실행**

```bash
arch -arm64 .venv/bin/python3.12 scripts/deploy_workflows.py
```

예상 출력 (신규 워크플로우):
```
Processing Jeonse & Supply Weekly Collect (jeonse_supply_collect.json)...
  ✅ Successfully deployed and activated jeonse_supply_collect.json with ID: <n8n-id>
```

n8n이 반환한 워크플로우 ID를 기록해둔다 (다음 스텝에서 사용).

- [ ] **Step 2: n8n UI에서 수동 실행 검증**

n8n UI (`http://localhost:5678`) 접속 → "Jeonse & Supply Weekly Collect" 워크플로우 → "Execute Workflow" 버튼 클릭 → 실행 결과 확인:
- Collect Jeonse 노드: HTTP 200 응답
- Collect Supply 노드: HTTP 200 응답
- Slack Error 노드: 실행되지 않음 (정상)

- [ ] **Step 3: workflows_registry.md WR-007 n8n ID 업데이트**

Step 1에서 얻은 n8n ID를 `docs/workflows_registry.md` WR-007 행의 `N8N ID` 컬럼에 기입:
```markdown
| `WR-007`   | Real Estate | Jeonse & Supply Weekly Collect  | 매주 일요일 05:00 KST | 전세/공급 데이터 주 1회 자동 수집 (실패 시 Slack) | Active | `<실제-n8n-id>` |
```

- [ ] **Step 4: result.md 작성**

`docs/features/jeonse-supply-n8n-schedule/result.md` 생성:

```markdown
# Result

**완료일:** 2026-05-27

## 변경 내용

- 신규: `workflows/real_estate/jeonse_supply_collect.json` — 7-node n8n 워크플로우
- 수정: `scripts/deploy_workflows.py` — jeonse_supply_collect.json 추가
- 수정: `docs/workflows_registry.md` — WR-007 등록

## 검증 결과

- n8n 수동 실행: Collect Jeonse ✅ → Collect Supply ✅
- WR-007 n8n ID: `<실제-n8n-id>`

## E2E 검증 면제

- **사유:** 화면단 변경 없음. n8n 워크플로우 수동 실행으로 검증.
```

(실제 n8n ID 및 검증 결과로 내용 채우기)

- [ ] **Step 5: active_state.md 업데이트**

`docs/context/active_state.md` 에서 현재 포커스를 jeonse-supply-n8n-schedule 완료로 업데이트.

- [ ] **Step 6: history.md 업데이트**

`docs/context/history.md` 맨 위에 2026-05-27 항목 추가:

```markdown
## 2026-05-27 — 전세/공급 n8n 스케줄 등록

- `workflows/real_estate/jeonse_supply_collect.json` 신규: 매주 일요일 05:00 KST 전세/공급 수집 (실패 시 Slack)
- `scripts/deploy_workflows.py` + `docs/workflows_registry.md` WR-007 등록
```

- [ ] **Step 7: progress.md Task 5 체크 후 최종 커밋**

progress.md 모든 항목 체크 후:
```bash
git add docs/features/jeonse-supply-n8n-schedule/result.md \
        docs/features/jeonse-supply-n8n-schedule/progress.md \
        docs/workflows_registry.md \
        docs/context/active_state.md \
        docs/context/history.md
git commit -m "docs(sop): jeonse-supply-n8n-schedule result.md + context 업데이트"
```
