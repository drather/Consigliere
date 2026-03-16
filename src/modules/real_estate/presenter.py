from typing import List, Dict, Any
from datetime import date

class RealEstatePresenter:
    """
    Handles formatting of real estate data into UI-specific structures 
    (e.g., Slack Block Kit).
    """
    
    @staticmethod
    def format_daily_summary(target_date: date, dedup_txs: List[tuple]) -> List[Dict[str, Any]]:
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🏢 {target_date.strftime('%Y-%m-%d')} 실거래가 요약",
                    "emoji": True
                }
            },
            {"type": "divider"}
        ]
        
        for tx, count in dedup_txs:
            eok = tx.price // 100000000
            man = (tx.price % 100000000) // 10000
            price_str = f"{eok}억"
            if man > 0:
                price_str += f" {man}만"
            
            count_str = f"외 {count-1}건" if count > 1 else ""
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{tx.apt_name}* ({tx.exclusive_area:g}m² / {tx.floor}층) {count_str}\n💰 *{price_str}*원  |  🏗️ {tx.build_year}년식"
                },
                "accessory": {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "지도 보기",
                        "emoji": True
                    },
                    "url": tx.naver_map_url,
                    "action_id": f"map_btn_{tx.apt_name}"
                }
            })
        return blocks

    @staticmethod
    def inject_validation_warning(report_json: Dict[str, Any], score: int) -> Dict[str, Any]:
        if score < 80:
            report_json.setdefault("blocks", [])
            report_json["blocks"].append({"type": "divider"})
            report_json["blocks"].append({
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": "⚠️ *[AI 검증 알림]* 본 리포트는 내부 검증 점수가 낮습니다. 실제 자금조달 시 전문가 상담을 권장합니다."}]
            })
        return report_json

    @staticmethod
    def beautify_citations(report_json: Dict[str, Any], policy_facts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Replaces raw fact IDs (e.g., fact_20260316_...) with markdown links.
        Format: [뉴스: 짧은제목](URL)
        """
        import re
        
        # Create fact mapping for quick lookup
        fact_map = {}
        for fact in policy_facts:
            f_id = fact.get("id")
            metadata = fact.get("metadata", {})
            title = metadata.get("short_title", "부동산 정책")
            url = metadata.get("url", "#")
            fact_map[f_id] = (title, url)

        # Regex to find fact IDs matching our pattern
        pattern = re.compile(r"fact_\d{8}_-?\d+")

        def replace_match(match):
            f_id = match.group(0)
            if f_id in fact_map:
                title, url = fact_map[f_id]
                return f"<{url}|[뉴스: {title}]>" # Slack specific link format
            return f_id

        # Traverse and replace in all mrkdwn strings
        if "blocks" in report_json:
            for block in report_json["blocks"]:
                if block.get("type") == "section" and "text" in block:
                    text_obj = block["text"]
                    if text_obj.get("type") == "mrkdwn":
                        text_obj["text"] = pattern.sub(replace_match, text_obj["text"])
        
        return report_json
