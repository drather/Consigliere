import os
from datetime import datetime
from core.storage import get_storage_provider
from core.prompt_loader import PromptLoader

def test_consigliere_integration():
    print("🚀 Starting Consigliere Integration Test...")

    # 1. Setup Storage (Local Mode)
    # For prompts, we point to the project root so it can find 'src/prompts'
    storage_mode = "local"
    project_root = "." 
    
    storage = get_storage_provider(storage_mode, root_path=project_root)
    print(f"✅ Storage Provider initialized: {type(storage).__name__}")

    # 2. Setup Prompt Loader
    # PromptLoader uses the storage provider to read files
    prompt_loader = PromptLoader(storage, base_dir="src/prompts")
    print("✅ Prompt Loader initialized.")

    # 3. Load and Render Prompt
    # We will pass variables to the Jinja2 template
    variables = {
        "user_name": "KKS",
        "today": datetime.now().strftime("%Y-%m-%d"),
        "storage_mode": storage_mode
    }
    
    try:
        metadata, rendered_prompt = prompt_loader.load("system/consigliere", variables)
        
        print("\n--- [Test Results] ---")
        print(f"Metadata: {metadata}")
        print("-" * 30)
        print("Rendered Prompt Content:")
        print(rendered_prompt)
        print("-" * 30)
        
        # 4. Verification
        assert metadata["model"] == "gemini-2.5-flash"
        assert "KKS" in rendered_prompt
        assert variables["today"] in rendered_prompt
        print("\n✨ Integration Test Passed Successfully!")

    except Exception as e:
        print(f"\n❌ Test Failed: {str(e)}")

if __name__ == "__main__":
    test_consigliere_integration()
