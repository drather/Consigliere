"""
tests/api/conftest — API 테스트용 sys.path 및 외부 의존성 스텁 설정.
google.genai 패키지가 없는 환경에서도 FastAPI 앱을 임포트할 수 있도록
MagicMock 스텁을 등록한다.
"""
import os
import sys
import types
from unittest.mock import MagicMock

# Ensure src/ is on path (complements the root conftest.py)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_src = os.path.join(_project_root, "src")
for _p in [_src, _project_root]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Stub google.genai — the installed package is google-generativeai 0.8.x which
# exposes google.generativeai, not google.genai.  The app code imports the newer
# google.genai namespace, so we stub it here to allow test-time import.
if "google.genai" not in sys.modules:
    _google_pkg = sys.modules.get("google") or types.ModuleType("google")
    _genai_stub = types.ModuleType("google.genai")
    _genai_stub.Client = MagicMock()
    _genai_stub.types = MagicMock()
    sys.modules["google"] = _google_pkg
    sys.modules["google.genai"] = _genai_stub
    sys.modules["google.genai.types"] = MagicMock()
