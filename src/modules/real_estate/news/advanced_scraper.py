import json
import yaml
from datetime import datetime
from typing import List, Dict, Any
from core.logger import get_logger
from core.llm import LLMClient
from .client import NaverNewsClient
from ..repository import ChromaRealEstateRepository

logger = get_logger(__name__)

class AdvancedScraper:
    """
    Scraper that focuses on high-fidelity policy and development news
    and indexes them into ChromaDB for RAG.
    """
    def __init__(self):
        self.news_client = NaverNewsClient()
        self.llm = LLMClient()
        self.repo = ChromaRealEstateRepository()

    def _generate_dynamic_queries(self) -> List[str]:
        """
        Generates dynamic search queries based on the user's persona and interest areas.
        """
        try:
            # Load persona to get interest areas
            from core.storage import get_storage_provider
            storage = get_storage_provider("local", root_path=".")
            persona_yaml = storage.read_file("src/modules/real_estate/persona.yaml")
            persona_data = yaml.safe_load(persona_yaml)
            interest_areas = persona_data.get("interest_areas", ["수도권"])
            
            prompt = f"""
            사용자의 관심 지역({interest_areas})과 부동산 투자 성향을 바탕으로, 
            가장 최신의 '정책 사실(Hard Facts)'과 '개발 호재'를 수집하기 위한 네이버 뉴스 검색어 5개를 생성하십시오.
            
            검색어는 구체적이어야 하며, 국토교통부 보도자료, 지자체 고시, 구체적인 프로젝트명을 포함해야 합니다.
            
            출력 형식 (JSON List):
            ["검색어1", "검색어2", "검색어3", "검색어4", "검색어5"]
            """
            queries = self.llm.generate_json(prompt)
            if isinstance(queries, list) and len(queries) > 0:
                logger.info(f"🔮 [AdvancedScraper] Generated dynamic queries: {queries}")
                return queries
        except Exception as e:
            logger.warning(f"⚠️ [AdvancedScraper] Failed to generate dynamic queries, using fallback: {e}")
            
        return [
            "국토교통부 보도자료 부동산",
            "3기 신도시 입주 분양 일정",
            "GTX 착공 완공 일자",
            "재건축 재개발 고시",
            "부동산 대출 규제 변경"
        ]

    def run_daily_scraping(self):
        logger.info("🚀 [AdvancedScraper] Starting daily high-fidelity scraping...")
        
        target_queries = self._generate_dynamic_queries()
        all_facts = []
        for query in target_queries:
            items = self.news_client.search_news(query, display=10)
            if not items:
                continue
            
            # Extract Facts via LLM
            logger.info(f"🧠 [AdvancedScraper] Extracting facts from query: {query}")
            facts = self._extract_facts(items)
            all_facts.extend(facts)
            
        # Index into ChromaDB
        for fact in all_facts:
            policy_id = f"fact_{datetime.now().strftime('%Y%m%d')}_{hash(fact['content'])}"
            metadata = {
                "source": fact.get("source", "NaverNews"),
                "date": datetime.now().strftime("%Y-%m-%d"),
                "category": fact.get("category", "General"),
                "relevance": "high"
            }
            self.repo.save_policy(policy_id, fact['content'], metadata)
            
        logger.info(f"✅ [AdvancedScraper] Indexed {len(all_facts)} facts into policy_knowledge.")
        return len(all_facts)

    def _extract_facts(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Uses LLM to filter out noise and extract only 'Hard Facts' 
        (dates, numbers, supply volumes, specific project names).
        """
        news_input = ""
        for item in items:
            news_input += f"Title: {item['title']}\nDesc: {item['description']}\nLink: {item['link']}\n---\n"
            
        prompt = f"""
        당심은 상급 부동산 데이터 과학자입니다. 제공된 뉴스 목록에서 '단순 홍보'나 '추측성 기사'를 제외하고,
        '확정된 사실(Hard Facts)'만 추출하십시오.
        
        추출 기준:
        1. 날짜가 구체적으로 명시된 공급/착공/완공 일정.
        2. 수치(공급 가구 수, 분양가, 금리 수치)가 포함된 자료.
        3. 국토부나 지자체가 공식 발표한 정책 변화.
        
        입력:
        {news_input}
        
        결과 형식 (JSON List):
        [
          {{"content": "내용 요약 (구체적 수치/날짜 포함)", "category": "공급/개발/정책/기타", "source": "뉴스원천"}}
        ]
        """
        
        try:
            extracted = self.llm.generate_json(prompt)
            if isinstance(extracted, list):
                return extracted
            return []
        except Exception as e:
            logger.error(f"❌ [AdvancedScraper] Fact extraction failed: {e}")
            return []
