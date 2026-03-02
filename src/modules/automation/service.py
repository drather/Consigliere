import httpx
import json
from typing import Dict, Any, List, Optional

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
             "Content-Type": "application/json",
             "X-N8N-API-KEY": api_key
        }

    def list_workflows(self) -> List[Dict[str, Any]]:
        """Fetch all workflows from n8n."""
        try:
            with httpx.Client() as client:
                response = client.get(f"{self.base_url}/workflows", headers=self.headers)
                response.raise_for_status()
                data = response.json()
                return data.get("data", [])
        except Exception as e:
            print(f"❌ Error fetching workflows: {e}")
            return []

    def deploy_workflow(self, workflow_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deploy a new workflow using the provided JSON representation.
        """
        try:
            with httpx.Client() as client:
                response = client.post(
                    f"{self.base_url}/workflows",
                    headers=self.headers,
                    json=workflow_json
                )
                if response.status_code >= 400:
                    print(f"❌ n8n API Error ({response.status_code}): {response.text}")
                    return {"error": response.text, "status_code": response.status_code}
                
                response.raise_for_status()
                return response.json()
        except Exception as e:
            print(f"❌ Error deploying workflow: {e}")
            return {"error": str(e)}

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
            print(f"❌ Error activating workflow {workflow_id}: {e}")
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
             print(f"❌ Error running workflow {workflow_id}: {e}")
             return {"error": str(e)}
