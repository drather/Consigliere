from streamlit.testing.v1 import AppTest
import os
import sys

# 프로젝트 루트 경로 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def test_dashboard_home_render():
    """Verify that the dashboard loads the Home page by default."""
    at = AppTest.from_file("src/dashboard/main.py").run()
    
    # Check if title exists
    if at.exception:
        print(f"❌ App Exception: {at.exception}")
        # Check for st.error messages
        for error_box in at.error:
            print(f"❌ Streamlit Error Box: {error_box.value}")
        raise at.exception[0]
        
    assert "Consigliere" in at.title[0].value
    assert "Welcome to Consigliere" in at.title[1].value

def test_dashboard_navigation():
    """Verify navigation to Finance and Real Estate pages."""
    at = AppTest.from_file("src/dashboard/main.py").run()
    
    # Check for st.error messages
    for error_box in at.error:
        print(f"❌ Streamlit Error Box: {error_box.value}")
    if at.exception:
         print(f"❌ App Exception: {at.exception}")
         raise at.exception[0]

    # 1. Check Sidebar Radio Button
    if not at.sidebar.radio:
        raise AssertionError("Sidebar radio button not found")
    
    # 2. Navigate to Finance
    at.sidebar.radio[0].set_value("💰 Finance").run()
    if at.exception:
        print(f"❌ Finance Page Exception: {at.exception}")
        raise at.exception[0]
    
    # 3. Navigate to Real Estate
    at.sidebar.radio[0].set_value("🏢 Real Estate").run()
    if at.exception:
        print(f"❌ Real Estate Page Exception: {at.exception}")
        raise at.exception[0]

if __name__ == "__main__":
    try:
        test_dashboard_home_render()
        print("✅ Home Page Test Passed")
        test_dashboard_navigation()
        print("✅ Navigation Test Passed")
    except AssertionError as e:
        print(f"❌ Test Failed (Assertion): {e}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ Unexpected Error: {e}")
