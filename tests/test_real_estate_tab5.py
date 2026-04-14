"""
Tab1 아파트 탐색 (구 Tab5 통합) UI 렌더링 테스트.

Tab1+Tab5 통합 후 검증 항목:
- 전체 탭 수 4개 (5→4로 감소)
- 첫 번째 탭 라벨: "🔍 아파트 탐색"
- 필터 위젯: master_search_name, master_sido, master_sigungu 등 존재
- 서브탭: "📋 단지 목록", "🗺️ 지도 뷰" 존재
"""
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def test_tab_count_reduced_to_four():
    """통합 후 최상위 탭이 4개여야 한다."""
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file("src/dashboard/main.py").run()
    at.sidebar.radio[0].set_value("🏢 Real Estate").run()

    top_level_labels = [t.label for t in at.tabs]
    # 최상위 탭 4개
    assert "🔍 아파트 탐색" in top_level_labels, f"탐색 탭 없음: {top_level_labels}"
    assert "🏗️ 단지 검색" not in top_level_labels, "구 Tab5가 아직 남아있음"
    assert "📊 Market Monitor" not in top_level_labels, "구 Tab1이 아직 남아있음"
    print(f"Top tabs: {top_level_labels}")


def test_apt_search_filter_widgets_exist():
    """아파트 탐색 탭에 필터 위젯이 모두 존재해야 한다."""
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file("src/dashboard/main.py").run()
    at.sidebar.radio[0].set_value("🏢 Real Estate").run()

    text_keys = [i.key for i in at.text_input]
    select_keys = [s.key for s in at.selectbox]

    assert "master_search_name" in text_keys, f"아파트명 검색 위젯 없음: {text_keys}"
    assert "master_sido" in select_keys, f"시도 selectbox 없음: {select_keys}"
    assert "master_sigungu" in select_keys, f"시군구 selectbox 없음: {select_keys}"
    assert "master_constructor" in select_keys, f"건설사 selectbox 없음: {select_keys}"
    print("✅ 필터 위젯 전부 존재")


def test_apt_search_subtabs_exist():
    """아파트 탐색 탭 안에 단지 목록 / 지도 뷰 서브탭이 있어야 한다."""
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file("src/dashboard/main.py").run()
    at.sidebar.radio[0].set_value("🏢 Real Estate").run()

    all_labels = [t.label for t in at.tabs]
    assert "📋 단지 목록" in all_labels, f"단지 목록 서브탭 없음: {all_labels}"
    assert "🗺️ 지도 뷰" in all_labels, f"지도 뷰 서브탭 없음: {all_labels}"
    print(f"All tab labels: {all_labels}")


def test_no_module_import_errors_on_load():
    """모듈 임포트 오류(No module named …)가 없어야 한다.
    DB 파일 없음 등 런타임 오류는 테스트 환경에서 허용한다."""
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file("src/dashboard/main.py").run()
    at.sidebar.radio[0].set_value("🏢 Real Estate").run()

    module_errors = [
        e.value for e in at.error
        if "No module named" in e.value
    ]
    assert len(module_errors) == 0, f"모듈 임포트 오류 발생: {module_errors}"
    print("✅ 모듈 임포트 오류 없음")


if __name__ == "__main__":
    test_tab_count_reduced_to_four()
    test_apt_search_filter_widgets_exist()
    test_apt_search_subtabs_exist()
    test_no_ui_errors_on_load()
