# Issues: System Dashboard

## 🔴 Known Issues

### 1. NumPy Import Error (C-extensions failed)
- **Status:** Open
- **Date:** 2026-02-18
- **Description:** 
  Streamlit fails to run due to a `numpy` dependency issue. The system is unable to import the NumPy C-extensions.
- **Error Message:**
  ```
  ImportError: Unable to import required dependencies: numpy:
  IMPORTANT: PLEASE READ THIS FOR ADVICE ON HOW TO SOLVE THIS ISSUE!
  Importing the numpy C-extensions failed. This error can happen for many reasons, often due to issues with your setup or how NumPy was installed.
  The Python version is: Python 3.12 from "/Users/kks/Desktop/Laboratory/Consigliere/.venv/bin/python"
  The NumPy version is: "2.4.2"
  ```
- **Potential Causes:**
  - **Architecture Mismatch (High Probability):** On macOS (Apple Silicon), libraries might have been installed for the wrong architecture (e.g., x86/Windows instead of ARM64). This matches previous experiences where binary compatibility caused C-extension failures.
  - Python 3.12 compatibility with NumPy 2.x on macOS (darwin).
  - Virtual environment corruption.
- **To-Do:**
  - Reinstall numpy within the virtual environment.
  - Consider pinning numpy to a stable 1.x version if 2.x causes issues with streamlit components.
  - Verify environment architecture.
