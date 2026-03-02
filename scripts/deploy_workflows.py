import sys
import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Add src to python path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

try:
    from modules.automation.service import AutomationService
except ImportError as e:
    print(f"❌ Failed to import AutomationService: {e}")
    sys.exit(1)

def main():
    # Load environment variables from .env
    base_dir = Path(__file__).parent.parent
    load_dotenv(base_dir / ".env")
    
    service = AutomationService()
    
    workflows_to_deploy = [
        "workflows/finance/finance_mvp.json",
        "workflows/real_estate/real_estate_monitor.json",
        "workflows/real_estate/real_estate_news.json"
    ]
    
    for relative_path in workflows_to_deploy:
        file_path = base_dir / relative_path
        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            continue
            
        print(f"Deploying {file_path.name}...")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                workflow_json = json.load(f)
                
            # Remove 'id' if present, as n8n API expects new workflows to not have an ID
            if 'id' in workflow_json:
                del workflow_json['id']
            
            # Use AutomationService for deployment
            result = service.deploy_workflow(workflow_json)
            
            if "error" in result:
                print(f"❌ Failed to deploy {file_path.name}: {result['error']}")
            else:
                workflow_id = result.get("id")
                print(f"✅ Successfully deployed {file_path.name} with ID: {workflow_id}")
                
        except Exception as e:
            print(f"❌ Error processing {file_path.name}: {e}")

if __name__ == "__main__":
    main()
