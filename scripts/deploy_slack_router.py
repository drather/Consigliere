import os
import sys
from dotenv import load_dotenv

# Ensure src is in PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from modules.automation.service import AutomationService

def setup_slack_workflow():
    load_dotenv()
    service = AutomationService()
    
    workflow_path = "workflows/slack_router.json"
    if not os.path.exists(workflow_path):
        print(f"❌ Workflow file not found: {workflow_path}")
        return

    with open(workflow_path, 'r') as f:
        workflow_json = f.read()
    
    import json
    workflow_data = json.loads(workflow_json)
    
    print("🚀 Deploying Slack Router workflow...")
    result = service.deploy_workflow(workflow_data)
    
    if "id" in result:
        workflow_id = result["id"]
        print(f"✅ Workflow deployed with ID: {workflow_id}")
        
        print(f"⚡ Activating workflow {workflow_id}...")
        activation_result = service.activate_workflow(workflow_id, True)
        
        if activation_result.get("status") == "success":
            print("🎉 Workflow activated successfully!")
        else:
            print(f"❌ Activation failed: {activation_result}")
    else:
        print(f"❌ Deployment failed: {result}")

if __name__ == "__main__":
    setup_slack_workflow()
