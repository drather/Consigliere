import httpx
import json
from typing import Dict, Any, List, Optional
from core.logger import get_logger

logger = get_logger(__name__)


class AutomationService:
    """
    Service to interact with the n8n REST API.
    Handles deploying, listing, and activating workflows.
    """
    def __init__(self, n8n_url: Optional[str] = None, api_key: Optional[str] = None):
        import os
        n8n_url = n8n_url or os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678").rstrip('/')
        api_key = api_key or os.getenv("N8N_API_KEY")
        
        self.base_url = f"{n8n_url}/api/v1"
        self.headers = {
             "accept": "application/json", 
             "Content-Type": "application/json"
        }
        if api_key:
            self.headers["X-N8N-API-KEY"] = api_key

    def list_workflows(self) -> List[Dict[str, Any]]:
        """Fetch all workflows from n8n."""
        try:
            with httpx.Client() as client:
                response = client.get(f"{self.base_url}/workflows", headers=self.headers)
                response.raise_for_status()
                data = response.json()
                return data.get("data", [])
        except Exception as e:
            logger.error(f"❌ Error fetching workflows: {e}")
            return []

    def deploy_workflow(self, workflow_json: Dict[str, Any], activate: bool = True) -> Dict[str, Any]:
        """
        Deploy or update a workflow. If 'id' is in workflow_json, it updates.
        Otherwise it creates a new one.
        """
        workflow_id = workflow_json.get("id")
        try:
            with httpx.Client() as client:
                if workflow_id:
                    # Update existing
                    url = f"{self.base_url}/workflows/{workflow_id}"
                    response = client.put(url, headers=self.headers, json=workflow_json)
                else:
                    # Create new
                    url = f"{self.base_url}/workflows"
                    response = client.post(url, headers=self.headers, json=workflow_json)
                
                if response.status_code >= 400:
                    logger.error(f"❌ n8n API Error ({response.status_code}): {response.text}")
                    return {"error": response.text, "status_code": response.status_code}
                
                result = response.json()
                
                # Activate if requested
                if activate and result.get("id"):
                    self.activate_workflow(result["id"], True)
                    result["active"] = True
                
                return result
        except Exception as e:
            logger.error(f"❌ Error deploying workflow: {e}")
            return {"error": str(e)}

    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow by ID."""
        try:
            with httpx.Client() as client:
                response = client.delete(f"{self.base_url}/workflows/{workflow_id}", headers=self.headers)
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"❌ Error deleting workflow {workflow_id}: {e}")
            return False

    def get_workflow_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find a workflow by its name."""
        workflows = self.list_workflows()
        for wf in workflows:
            if wf.get("name") == name:
                return wf
        return None

    def activate_workflow(self, workflow_id: str, active: bool = True) -> Dict[str, Any]:
        """Activate or deactivate a workflow by ID."""
        try:
            with httpx.Client() as client:
                response = client.post(
                    f"{self.base_url}/workflows/{workflow_id}/activate" if active else f"{self.base_url}/workflows/{workflow_id}/deactivate",
                    headers=self.headers
                )
                response.raise_for_status()
                return {"status": "success", "id": workflow_id, "active": active}
        except Exception as e:
            logger.error(f"❌ Error activating workflow {workflow_id}: {e}")
            return {"error": str(e)}

    def run_workflow(self, workflow_id: str, payload: Dict[str, Any] = None) -> Dict[str, Any]:
         """Run a workflow manually (if it has a manual trigger)."""
         try:
             with httpx.Client() as client:
                 url = f"{self.base_url}/workflows/{workflow_id}/run"
                 response = client.post(url, headers=self.headers, json=payload or {})
                 response.raise_for_status()
                 return response.json()
         except Exception as e:
             logger.error(f"❌ Error running workflow {workflow_id}: {e}")
             return {"error": str(e)}
