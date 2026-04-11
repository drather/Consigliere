from streamlit.testing.v1 import AppTest
import os
import sys

# 프로젝트 루트 경로 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def test_real_estate_tab5_rendering():
    """Verify that Tab 5 (단지 검색) and its sub-tabs render correctly."""
    at = AppTest.from_file("src/dashboard/main.py").run()
    
    # 1. 부동산 페이지로 이동
    at.sidebar.radio[0].set_value("🏢 Real Estate").run()
    
    # 2. Tab 5 (단지 검색) 선택
    # tabs = ["📊 Market Monitor", "💡 Insight", "📋 Report Archive", "👤 페르소나", "🏗️ 단지 검색"]
    print(f"Tab methods: {dir(at.tabs[0])}")
    # 보통 AppTest에서는 tabs[i]를 직접적으로 '선택'하는 명시적 메서드가 없거나 버전에 따라 다릅니다.
    # 클릭 효과를 주기 위해 value를 변경해봅니다.
    try:
        at.tabs[4].run() # 탭 내용이 렌더링되도록 실행
    except:
        pass
    
    # 디버깅: 현재 화면의 탭 라벨과 위젯 키들 출력
    print(f"Current Tabs: {[t.label for t in at.tabs]}")
    print(f"All subheaders: {[s.value for s in at.subheader]}")
    for err in at.error:
        print(f"❌ UI Error: {err.value}")
    
    # 3. Tab 5 내용 검증
    # "🏗️ 아파트 마스터 DB 검색" 텍스트가 있는지 확인
    assert any("아파트 마스터 DB 검색" in s.value for s in at.subheader)
    
    # 4. 필터 위젯 존재 확인 (key로 접근)
    # text_input 위젯들 중에서 key가 'master_search_name'인 것 찾기
    inputs = [i for i in at.text_input if i.key == "master_search_name"]
    assert len(inputs) > 0, f"master_search_name not found. Available keys: {[i.key for i in at.text_input]}"
    assert at.selectbox("master_sido") is not None
    assert at.selectbox("master_sigungu") is not None
    
    # 5. 서브탭 존재 확인
    # sub_list, sub_map = st.tabs(["📋 단지 목록", "🗺️ 지도 뷰"])
    # Tab 5 내부에 또 탭이 있으므로 at.tabs를 다시 확인
    # 전체 앱 수준에서 탭 인덱스가 부여되므로 주의
    
    # 서브탭 텍스트 확인
    tab_labels = [t.label for t in at.tabs]
    assert "📋 단지 목록" in tab_labels
    assert "🗺️ 지도 뷰" in tab_labels

    print("✅ Tab 5 UI Components Rendered Successfully")

if __name__ == "__main__":
    test_real_estate_tab5_rendering()
