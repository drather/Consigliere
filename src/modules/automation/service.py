import httpx
import json
from typing import Dict, Any, List, Optional

class AutomationService:
    """
    Service to interact with the n8n REST API.
    Handles deploying, listing, and activating workflows.
    """
    def __init__(self, n8n_url: str = "http://consigliere_n8n:5678", api_key: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIzZThlMGEwMC1kOTdhLTQ5MGYtOGE2Ni0wMTA4ZGViMWRkNWMiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzcxNzY0NTk0fQ.Ou0CRuP8RrH_cwEk_7vJBrr_dlXYdefjJmKF6rcqclk"):
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
