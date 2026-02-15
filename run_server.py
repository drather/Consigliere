import sys
import os
import uvicorn

def main():
    # 1. Setup Path
    # Get the project root directory (where this script is located)
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Define 'src' directory path
    src_dir = os.path.join(project_root, "src")
    
    # Add 'src' to system path so Python can find 'agents', 'core', etc.
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
        print(f"✅ Added to PYTHONPATH: {src_dir}")

    # 2. Run Server
    # Configuration can be loaded from .env in the future
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    is_dev = os.getenv("ENV", "development") == "development"

    print(f"🚀 Starting Consigliere Server on http://{host}:{port}")
    
    # Start Uvicorn
    # 'src.main:app' works because we added 'src' to path, 
    # but uvicorn needs to know the module path relative to path.
    # Since we run from root, 'src.main:app' is correct.
    uvicorn.run("src.main:app", host=host, port=port, reload=is_dev)

if __name__ == "__main__":
    main()
