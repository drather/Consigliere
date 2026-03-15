from duckduckgo_search import DDGS
from typing import Dict, Any
from datetime import datetime
from core.llm import LLMClient
from core.logger import get_logger

logger = get_logger(__name__)

def fetch_latest_financial_policies() -> Dict[str, Any]:
    """
    Fetches the latest real estate financial policies (LTV, DSR) from the web
    and uses an LLM to summarize them into a structured context dictionary.
    """
    logger.info("🔍 [PolicyFetcher] Fetching latest financial policies via DuckDuckGo Search...")
    current_year_month = datetime.now().strftime("%Y년 %m월")
    # Use a broader query to avoid getting only calendar-related results for future dates
    query = "현행 주택담보대출 LTV DSR 규제 정책 가이드"
    
    try:
        # Try a more specific query first, then fall back if needed
        results = DDGS().text(query, max_results=8)
        raw_text = "\n".join([f"[{r['title']}] {r['body']}" for r in results])
        
        if len(raw_text) < 200: # If results are too thin
            logger.info("⚠️ [PolicyFetcher] Initial search results too thin, trying alternative query...")
            alt_query = "2024 2025 주택담보대출 규제 LTV DSR 현황"
            alt_results = DDGS().text(alt_query, max_results=5)
            raw_text += "\n" + "\n".join([f"[{r['title']}] {r['body']}" for r in alt_results])

        if not raw_text.strip():
            logger.warning("⚠️ [PolicyFetcher] Web search returned empty results, using fallback.")
            return _get_fallback_policy()

        # Load and Render Prompt
        from core.storage import get_storage_provider
        from core.prompt_loader import PromptLoader
        
        root_storage = get_storage_provider("local", root_path=".")
        loader = PromptLoader(root_storage, base_dir="src/core/prompts")
        
        _, prompt_str = loader.load(
            "policy_analyzer",
            variables={
                "current_year_month": current_year_month,
                "raw_text": raw_text
            }
        )
        
        # LLM Summary
        llm = LLMClient()
        policy_context = llm.generate_json(prompt_str)
        if "error" in policy_context:
            logger.error(f"❌ [PolicyFetcher] LLM summary failed: {policy_context.get('error')}")
            return _get_fallback_policy()
            
        logger.info(f"✅ [PolicyFetcher] Successfully generated real-time policy context.")
        return policy_context
        
    except Exception as e:
        logger.error(f"❌ [PolicyFetcher] Web search encountered an error: {e}")
        return _get_fallback_policy()


def _get_fallback_policy() -> Dict[str, Any]:
    return {
        "standard_year": datetime.now().strftime("%Y년 %m월"),
        "ltv": {
            "first_time_buyer": "최대 80%",
            "non_regulated_area": "최대 70%",
            "regulated_area": "최대 50%"
        },
        "dsr": {
            "limit": "40%",
            "stress_dsr": "스트레스 DSR 적용 중 (3단계 여부 불확실, 은행에 확인 필요)"
        },
        "news_summary": "(웹 검색 실패로 인한 기본 보수적 지표 적용 중)"
    }
