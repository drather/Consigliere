# Real Estate Transaction Monitor: Specification

## 🎯 Objective
Automatically fetch daily real estate transaction data (Apartment) from the **Ministry of Land, Infrastructure and Transport (MOLIT)** via the Public Data Portal API. This data will be used to track market trends and alert the user of significant price changes.

## 🔑 Key Features
1. **API Integration:** Connect to the MOLIT Real Estate Transaction Price API.
2. **Data Parsing:** Parse XML responses into structured Python objects (`RealEstateTransaction`).
3. **Storage:** Store transaction records in a database (initially ChromaDB as metadata or SQLite for structured query).
4. **Scheduling:** Run the data fetch job daily (e.g., via `APScheduler` or OS Cron).

## 🛠️ Architecture
- **Module Path:** `src/modules/real_estate/monitor/`
- **Components:**
  - `api_client.py`: Handles HTTP requests to the government API.
  - `parser.py`: Converts raw XML to Pydantic models.
  - `scheduler.py`: Triggers the job.
- **Data Source:** [Public Data Portal - Apartment Transaction Price](https://www.data.go.kr/data/15058747/openapi.do)

## 📝 Data Model (Draft)
```python
from pydantic import BaseModel
from datetime import date

class RealEstateTransaction(BaseModel):
    deal_date: date          # 계약일 (YYYY-MM-DD)
    district_code: str       # 법정동코드 (e.g., 11110)
    apt_name: str            # 아파트명
    exclusive_area: float    # 전용면적 (m2)
    floor: int               # 층
    price: int               # 거래금액 (만원 -> 원 변환 필요)
    build_year: int          # 건축년도
```

## ⚠️ Constraints & Considerations
- **API Key:** Requires a valid Service Key from `data.go.kr`.
- **Rate Limit:** The API has a daily call limit (usually 1,000 or 10,000 calls).
- **Data Delay:** Transaction data is often updated with a lag (up to 30 days). The monitor should handle retroactive updates.
