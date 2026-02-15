from abc import ABC, abstractmethod
from typing import List, Optional

class StorageProvider(ABC):
    """
    Abstract base class for storage providers (Local, Google Drive, etc.).
    This ensures that the application logic remains decoupled from the physical storage location.
    """

    @abstractmethod
    def read_file(self, path: str) -> str:
        """Reads the content of a file."""
        pass

    @abstractmethod
    def write_file(self, path: str, content: str) -> None:
        """Writes content to a file."""
        pass

    @abstractmethod
    def list_files(self, path: str) -> List[str]:
        """Lists files in a directory."""
        pass

    @abstractmethod
    def exists(self, path: str) -> bool:
        """Checks if a file or directory exists."""
        pass
