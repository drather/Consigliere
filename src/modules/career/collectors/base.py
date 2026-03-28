import ssl
from abc import ABC, abstractmethod
from typing import List, Any

import aiohttp
import certifi
from core.logger import get_logger


class BaseCollector(ABC):
    """
    공통 수집기 인터페이스.
    각 Collector는 단일 소스에서 데이터를 수집하고 모델 리스트를 반환한다.
    실패 시 빈 리스트를 반환하여 파이프라인 중단을 방지한다.
    """
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    @staticmethod
    def make_connector() -> aiohttp.TCPConnector:
        """certifi CA 번들을 사용하는 SSL connector를 반환한다."""
        ssl_ctx = ssl.create_default_context(cafile=certifi.where())
        return aiohttp.TCPConnector(ssl=ssl_ctx)

    @abstractmethod
    async def collect(self) -> List[Any]:
        """수집 실행. 실패 시 빈 리스트 반환."""
        pass

    async def safe_collect(self) -> List[Any]:
        try:
            return await self.collect()
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] 수집 실패: {e}")
            return []
