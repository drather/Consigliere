# Spec: Scheduled Real Estate News (Slack Delivery)

## Goal
Automate the daily delivery of real estate news insights to Slack at 06:00 KST.

## Architecture
1. **Trigger**: n8n `Schedule Trigger` set to `0 6 * * *`.
2. **Analysis**: Existing Consigliere API endpoint `/agent/real_estate/news/analyze` fetches and summarizes news.
3. **Notification**: Call Consigliere API endpoint `/notify/slack` with the analysis summary.

## Data Model
- **Input**: None (Scheduled).
- **Output**: JSON payload to `/notify/slack`.
  ```json
  {
    "message": "📢 *데일리 부동산 뉴스 리포트*\n\n{analysis_summary}"
  }
  ```

## Proposed Changes
### real_estate_news.json
- [MODIFY] Update Schedule ID `schedule-trigger` to trigger at 06:00.
- [NEW] Add node `slack-notification` (HTTP Request).
- [MODIFY] Link `Trigger News Analysis` -> `slack-notification`.

## Constraints
- Must use the internal Docker network URL: `http://consigliere_api:8000`.
- Must handle Korean characters correctly (UTF-8).
