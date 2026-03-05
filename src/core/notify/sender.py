from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class Sender(ABC):
    """
    Abstract Base Class for all outbound notification channels.
    """
    
    @abstractmethod
    def send(self, message: str, **kwargs) -> Dict[str, Any]:
        """
        Sends a message to the target platform.
        
        Args:
            message (str): The main text content to send.
            **kwargs: Additional platform-specific parameters (e.g., attachments, blocks).
            
        Returns:
            Dict[str, Any]: A response dictionary containing status and any relevant data/errors.
        """
        pass
