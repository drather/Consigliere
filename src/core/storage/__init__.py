# src/core/storage/__init__.py
from .base import StorageProvider
from .local import LocalStorage

def get_storage_provider(storage_mode: str, **kwargs) -> StorageProvider:
    """Factory function to instantiate the correct storage provider."""
    if storage_mode == "local":
        root_path = kwargs.get("root_path", "./data")
        return LocalStorage(root_path)
    
    # elif storage_mode == "gdrive":
    #     return GoogleDriveStorage(**kwargs)
    
    else:
        raise ValueError(f"Unknown storage mode: {storage_mode}")
