import sys
import os
import json
import httpx
from pathlib import Path

# Add src to python path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from modules.automation.service import AutomationService

def main():
    service = AutomationService(n8n_url="http://localhost:5678")
    
    workflows_to_deploy = [
        "workflows/finance/finance_mvp.json",
        "workflows/real_estate/real_estate_monitor.json",
        "workflows/real_estate/real_estate_news.json"
    ]
    
    base_dir = Path(__file__).parent.parent
    
    for relative_path in workflows_to_deploy:
        file_path = base_dir / relative_path
        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            continue
            
        print(f"Deploying {file_path.name}...")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                workflow_json = json.load(f)
                
            with httpx.Client() as client:
                response = client.post(
                    f"{service.base_url}/workflows",
                    headers=service.headers,
                    json=workflow_json
                )
                if response.status_code >= 400:
                    print(f"❌ Failed to deploy {file_path.name}: {response.text}")
                else:
                    workflow_id = response.json().get("id")
                    print(f"✅ Successfully deployed {file_path.name} with ID: {workflow_id}")
                
        except Exception as e:
            print(f"❌ Error processing {file_path.name}: {e}")

if __name__ == "__main__":
    main()
