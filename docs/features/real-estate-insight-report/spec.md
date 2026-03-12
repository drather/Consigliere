# Feature Spec: 부동산 종합 인사이트 리포트 (Comprehensive Real Estate Insight Report)

## 1. Overview
The goal is to provide a high-value daily report that goes beyond simple transaction listings. It categorizes real estate data into:
1. **실거래가 (Actual Transactions):** Recent trends in interest areas.
2. **부동산 정책 (Policy Updates):** New government regulations or tax changes.
3. **지역 개발 (Regional Development):** Infrastructure news (GTX, new cities, etc.).

## 2. Requirements
- **Aggregation:** Fetch data from existing `real_estate` modules.
- **Categorization:** Use LLM (Gemini) to categorize news and data points.
- **Formatting:** Use Slack Block Kit for a premium, readable report.
- **Scheduling:** Automated daily delivery (08:30 KST).

## 3. Data Flow
1. **Trigger:** n8n Cron (08:30 KST).
2. **Fetch:** `RealEstateAgent.generate_insight_report()` is called.
3. **Process:**
   - Fetch latest transactions from DB/API.
   - Fetch news via existing scrapers.
   - LLM: "Identify which are policies, which are development news, and summarize."
4. **Notify:** Send via `/notify/slack`.

## 4. UI Design (Slack)
- Header: 🗓️ [날짜] 부동산 종합 인사이트 리포트
- Section 1: 💰 최근 실거래 수합
- Section 2: ⚖️ 핵심 정책/규제 변화
- Section 3: 🏗️ 주요 지역 개발 소식
- Footer: 🔗 [상세 대시보드 링크]
