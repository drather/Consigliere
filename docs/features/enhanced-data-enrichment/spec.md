# Feature Spec: Enhanced Data Enrichment & RAG (Phase 2)

## 1. Goal
단순 실거래가와 키워드 중심 뉴스 분석에서 벗어나, 거시 경제 데이터(금리 등), 심층 뉴스(공급/개발 일정), 물건 스펙(준공연도)을 결합하여 프로 수준의 부동산 통찰력을 제공하는 **다차원 데이터 엔진**을 구축합니다.

## 2. architecture & Modules

### A. Macro Data Hub (BOK Integration)
- **Module**: `src/modules/real_estate/macro/bok_service.py`
- **Data**: 한국은행 Open API 연동
    - 기준금리 (Base Rate)
    - 예금/대출 금리 (주택담보대출 금리 추이)
    - M2 통화량 증감률
- **Goal**: 현재 매수 시점이 거시경제적으로 유리한지 판단하는 지표 제공.

### B. High-Fidelity News & Development Scraper
- **Module**: `src/modules/real_estate/news/advanced_scraper.py`
- **Source Expansion**:
    - 국토교통부 보도자료 (MOLIT)
    - 서울시/경기도 지자체 고시 (재건축/재개발 진행 상황)
    - 심층 기획 기사 (공급 지연, 지하철 연장 팩트 체크)
- **RAG Enhancement**: 수집된 데이터를 벡터 DB에 저장하여, 특정 아파트나 지역 분석 시 관련 개발 호재와 정책 맥락을 정교하게 결합.

### C. Property Depth Analysis (Building Age)
- **Update**: 실거래가 수집 모듈 (`monitor/service.py`) 고도화.
- **Data**: 개별 아파트의 **준공연도(Build Year)** 데이터 분석.
- **Goal**: 건축 연한 30년 근접 여부를 파악하여 재건축 기대감(Time Value)을 인사이트 리포트에 자동 포함.

## 3. Data Flow
1. **Collector**: BOK, MOLIT, Naver News 등에서 다차원 데이터 수집.
2. **Synthesizer**: 수집된 정량(금리, 물량) + 정성(뉴스, 정책) 데이터를 LLM Context로 통합.
3. **Agent Integration**: `Phase 3`의 Multi-Agent 체계가 사용할 풍부한 Knowledge Base 제공.

## 4. Acceptance Criteria
- [ ] 한국은행 금리 데이터를 성공적으로 가져와 리포트에 반영.
- [ ] 리포트에 "단순 GTX 호재"가 아닌 "실질 착공 현황 및 일차별 공급 가능성" 등 구체적 정보 포함.
- [ ] 아파트 분석 시 재건축 가능성(준공 후 30년 경과 여부) 언급.
