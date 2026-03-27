import os
import yaml
from typing import Dict, Any
from core.logger import get_logger

logger = get_logger(__name__)


class PersonaManager:
    """
    SRP: persona.yaml 로드/저장 전담.
    CareerAgent에서 persona I/O 책임을 분리한다.
    """

    def __init__(self, persona_path: str = "src/modules/career/persona.yaml"):
        self.persona_path = persona_path
        self._persona = self._load()

    def _load(self) -> Dict[str, Any]:
        if not os.path.exists(self.persona_path):
            logger.warning(f"persona.yaml 없음: {self.persona_path}")
            return {}
        try:
            with open(self.persona_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            logger.error(f"persona.yaml 파싱 실패: {e}")
            return {}

    def get(self) -> Dict[str, Any]:
        return self._persona

    def update(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        self._persona.update(updates)
        try:
            with open(self.persona_path, "w", encoding="utf-8") as f:
                yaml.dump(self._persona, f, allow_unicode=True, default_flow_style=False)
        except OSError as e:
            logger.error(f"persona.yaml 저장 실패: {e}")
        return self._persona
