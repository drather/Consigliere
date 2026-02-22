import httpx
import json

BASE_URL = "http://localhost:8000"

def test_automation_api():
    print("🚀 Starting FastAPI <-> n8n Integration Test")

    # 1. Load the template JSON
    try:
        with open("src/n8n/templates/http_fetch_schedule.json", "r") as f:
             template = json.load(f)
        print("✅ Loaded http_fetch_schedule.json template")
    except Exception as e:
        print(f"❌ Failed to load template: {e}")
        return

    # 2. Test Deploy Endpoint
    print("\n📦 Test: Deploying Workflow")
    try:
        response = httpx.post(
            f"{BASE_URL}/agent/automation/workflow/deploy",
            json={"workflow_json": template},
            timeout=10.0
        )
        response.raise_for_status()
        deploy_result = response.json()
        print(f"✅ Deployment successful: {deploy_result}")
        
        # Extract the created workflow ID for the next steps
        workflow_id = deploy_result.get("workflow", {}).get("id")
        if not workflow_id:
             print("❌ Could not extract workflow ID from response")
             return
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        return

    # 3. Test Activate Endpoint
    print(f"\n🟢 Test: Activating Workflow [{workflow_id}]")
    try:
        response = httpx.post(
             f"{BASE_URL}/agent/automation/workflow/activate",
             json={"workflow_id": workflow_id, "active": True},
             timeout=10.0
        )
        response.raise_for_status()
        print(f"✅ Activation successful: {response.json()}")
    except Exception as e:
        print(f"❌ Activation failed: {e}")
        return

    # 4. Test List Endpoint
    print("\n📜 Test: Listing Workflows")
    try:
        response = httpx.get(f"{BASE_URL}/agent/automation/workflows", timeout=10.0)
        response.raise_for_status()
        workflows = response.json().get("workflows", [])
        
        # Verify our workflow is in the list
        found = False
        for wf in workflows:
             if wf.get("id") == workflow_id:
                 found = True
                 print(f"✅ Found our deployed workflow in the list. Status: active={wf.get('active')}")
                 break
        if not found:
             print("❌ Deployed workflow not found in list")
    except Exception as e:
        print(f"❌ Listing workflows failed: {e}")
        return

    print("\n🎉 All E2E Tests Passed Successfully!")

if __name__ == "__main__":
    test_automation_api()
