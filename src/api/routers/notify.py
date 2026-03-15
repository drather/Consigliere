from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Any

from api.dependencies import get_slack_sender
from core.notify.slack import SlackSender
from core.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["Notify"])

class NotificationRequest(BaseModel):
    message: str
    blocks: Optional[Any] = None

@router.post("/notify/slack")
def send_slack_notification(request: NotificationRequest, sender: SlackSender = Depends(get_slack_sender)):
    """
    Sends a message to Slack using the configured SlackSender.
    """
    try:
        kwargs = {}
        if request.blocks:
            kwargs["blocks"] = request.blocks
            
        result = sender.send(request.message, **kwargs)
        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("error"))
            
        return result
    except Exception as e:
        logger.error(f"Slack Notification Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
