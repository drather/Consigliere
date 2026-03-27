import os
import logging
import yaml
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class CareerConfig:
    """
    Dynamic configuration provider for Career module.
    """
    def __init__(self, config_path: str = "src/modules/career/config.yaml"):
        self.config_path = config_path
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        if not os.path.exists(self.config_path):
            return {}
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            logger.warning(f"config.yaml 파싱 실패, 기본값 사용: {e}")
            return {}

    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    def get_github_languages(self) -> List[str]:
        return self.get("trend_sources", {}).get("github_languages", ["python", "go", "typescript"])

    def get_hn_min_score(self) -> int:
        return self.get("trend_sources", {}).get("hn_min_score", 50)

    def get_devto_tags(self) -> List[str]:
        return self.get("trend_sources", {}).get("devto_tags", ["backend", "python", "go"])

    def get_wanted_params(self) -> Dict[str, Any]:
        return self.get("job_sources", {}).get("wanted", {})

    def get_jumpit_params(self) -> Dict[str, Any]:
        return self.get("job_sources", {}).get("jumpit", {})

    def get_data_dir(self) -> str:
        return self.get("data_dir", "data/career")

    def get_llm_provider(self) -> str:
        return self.get("llm_provider", "claude")
