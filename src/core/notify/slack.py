import os
import requests
from typing import Dict, Any
from .sender import Sender

class SlackSender(Sender):
    """
    Implementation of Sender for Slack using either Webhook URL or Bot Token + chat.postMessage.
    
    Prioritizes Bot Token if both are provided, as it allows for more complex interactions later.
    """
    
    def __init__(self):
        self.bot_token = os.getenv("SLACK_BOT_TOKEN")
        self.channel_id = os.getenv("SLACK_CHANNEL_ID")
        self.webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        
        if not (self.bot_token and self.channel_id) and not self.webhook_url:
            print("⚠️ WARNING: Slack credentials missing in environment variables.")

    def send(self, message: str, **kwargs) -> Dict[str, Any]:
        """
        Sends a message to Slack.
        If blocks are provided in kwargs, text acts as fallback.
        """
        if self.bot_token and self.channel_id:
            return self._send_via_api(message, **kwargs)
        elif self.webhook_url:
            return self._send_via_webhook(message, **kwargs)
        else:
            return {
                "status": "error", 
                "error": "Missing Slack configuration (Token+Channel or Webhook URL)"
            }

    def _send_via_api(self, message: str, **kwargs) -> Dict[str, Any]:
        url = "https://slack.com/api/chat.postMessage"
        headers = {
            "Authorization": f"Bearer {self.bot_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "channel": self.channel_id,
            "text": message
        }
        
        # Add rich blocks if provided
        if "blocks" in kwargs:
            payload["blocks"] = kwargs["blocks"]

        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            
            if not data.get("ok"):
                print(f"❌ Slack API Error: {data.get('error')}")
                return {"status": "error", "error": data.get("error")}
                
            return {"status": "success", "data": data}
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Slack Network Error: {e}")
            return {"status": "error", "error": str(e)}

    def _send_via_webhook(self, message: str, **kwargs) -> Dict[str, Any]:
        payload = {"text": message}
        if "blocks" in kwargs:
            payload["blocks"] = kwargs["blocks"]

        try:
            response = requests.post(self.webhook_url, json=payload)
            response.raise_for_status()
            return {"status": "success", "data": response.text}
        except requests.exceptions.RequestException as e:
            print(f"❌ Slack Webhook Error: {e}")
            return {"status": "error", "error": str(e)}
