from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

from api.dependencies import get_automation_service
from modules.automation.service import AutomationService
from core.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["Automation"])

class WorkflowDeployRequest(BaseModel):
    workflow_json: Dict[str, Any] = Field(..., description="The n8n workflow JSON definition")

class WorkflowActivateRequest(BaseModel):
    workflow_id: str
    active: bool = True

@router.get("/agent/automation/workflows")
def list_workflows(automation_service: AutomationService = Depends(get_automation_service)):
    try:
        workflows = automation_service.list_workflows()
        return {"status": "success", "workflows": workflows}
    except Exception as e:
        logger.error(f"Automation List Workflows Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/agent/automation/workflow/deploy")
def deploy_workflow(request: WorkflowDeployRequest, automation_service: AutomationService = Depends(get_automation_service)):
    try:
        result = automation_service.deploy_workflow(request.workflow_json)
        if "error" in result:
             raise HTTPException(status_code=500, detail=result["error"])
        return {"status": "success", "workflow": result}
    except Exception as e:
        logger.error(f"Automation Deploy Workflow Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/agent/automation/workflow/activate")
def activate_workflow(request: WorkflowActivateRequest, automation_service: AutomationService = Depends(get_automation_service)):
    try:
        result = automation_service.activate_workflow(request.workflow_id, request.active)
        if "error" in result:
             raise HTTPException(status_code=500, detail=result["error"])
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"Automation Activate Workflow Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/agent/automation/workflow/{workflow_id}/run")
def run_workflow(workflow_id: str, payload: Optional[Dict[str, Any]] = None, automation_service: AutomationService = Depends(get_automation_service)):
    try:
        result = automation_service.run_workflow(workflow_id, payload)
        if "error" in result:
             raise HTTPException(status_code=500, detail=result["error"])
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"Automation Run Workflow Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
