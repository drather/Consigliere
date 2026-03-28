import os
import yaml
from datetime import datetime
from typing import Dict, Any, List

from core.logger import get_logger

logger = get_logger(__name__)

_PERSONA_PATH = os.path.join(os.path.dirname(__file__), "persona.yaml")
_PREFERENCE_RULES_PATH = os.path.join(os.path.dirname(__file__), "preference_rules.yaml")


class PersonaManager:
    """Handles loading and updating of persona.yaml. SRP: only persona I/O."""

    def load(self) -> Dict[str, Any]:
        try:
            with open(_PERSONA_PATH, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"⚠️ Failed to load persona: {e}")
            return {"user": {}}

    def update(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Deep-merges *updates* into current persona, backs up previous version, and persists."""
        current = self.load()

        history_dir = os.path.join(os.getenv("LOCAL_STORAGE_PATH", "./data"), "real_estate", "persona_history")
        os.makedirs(history_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(history_dir, f"{ts}_persona.yaml")
        with open(backup_path, "w", encoding="utf-8") as f:
            yaml.dump(current, f, allow_unicode=True, default_flow_style=False)

        merged = self._deep_merge(current, updates)
        with open(_PERSONA_PATH, "w", encoding="utf-8") as f:
            yaml.dump(merged, f, allow_unicode=True, default_flow_style=False)

        logger.info(f"[Persona] Updated and backed up to {backup_path}")
        return merged

    @staticmethod
    def _deep_merge(base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
        result = dict(base)
        for k, v in updates.items():
            if isinstance(v, dict) and isinstance(result.get(k), dict):
                result[k] = PersonaManager._deep_merge(result[k], v)
            else:
                result[k] = v
        return result


class PreferenceRulesManager:
    """Handles loading and updating of preference_rules.yaml. SRP: only rules I/O."""

    def get(self) -> List[Dict[str, Any]]:
        try:
            with open(_PREFERENCE_RULES_PATH, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return data.get("rules", [])
        except Exception as e:
            logger.error(f"⚠️ Failed to load preference_rules: {e}")
            return []

    def update(self, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        try:
            with open(_PREFERENCE_RULES_PATH, "w", encoding="utf-8") as f:
                yaml.dump({"rules": rules}, f, allow_unicode=True, default_flow_style=False)
            logger.info(f"[PreferenceRules] Saved {len(rules)} rules.")
            return rules
        except Exception as e:
            logger.error(f"⚠️ Failed to update preference_rules: {e}")
            raise
