from typing import List
from pathlib import Path
import os
from .base import StorageProvider

class LocalStorage(StorageProvider):
    """
    Local filesystem implementation of StorageProvider.
    Uses a 'root_path' as the base directory for all operations.
    """

    def __init__(self, root_path: str):
        self.root = Path(root_path).resolve()
        if not self.root.exists():
            os.makedirs(self.root)
            print(f"[LocalStorage] Created root directory: {self.root}")

    def _get_abs_path(self, path: str) -> Path:
        """Resolves the path relative to the root, preventing path traversal."""
        full_path = (self.root / path).resolve()
        if not str(full_path).startswith(str(self.root)):
             raise ValueError(f"Path traversal attempt: {path}")
        return full_path

    def read_file(self, path: str) -> str:
        target_path = self._get_abs_path(path)
        with open(target_path, 'r', encoding='utf-8') as f:
            return f.read()

    def write_file(self, path: str, content: str) -> None:
        target_path = self._get_abs_path(path)
        # Ensure parent directories exist
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def list_files(self, path: str) -> List[str]:
        target_path = self._get_abs_path(path)
        if not target_path.exists():
            return []
        # Return relative paths as strings
        return [str(p.relative_to(self.root)) for p in target_path.glob("**/*") if p.is_file()]

    def exists(self, path: str) -> bool:
        return self._get_abs_path(path).exists()
