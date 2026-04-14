"""
pytest conftest — 모든 테스트에서 src/ 경로가 sys.path에 있도록 보장.
Streamlit AppTest가 모듈을 찾지 못하는 문제를 방지한다.
"""
import os
import sys

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_src = os.path.join(_project_root, "src")

for _p in [_src, _project_root]:
    if _p not in sys.path:
        sys.path.insert(0, _p)
