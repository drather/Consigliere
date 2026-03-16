import os
import yaml
from typing import Dict, Any, Optional

class RealEstateConfig:
    """
    Dynamic configuration provider for Real Estate module.
    Avoids hardcoded constants by providing a centralized 
    access point for parameters.
    """
    def __init__(self, config_path: str = "src/modules/real_estate/config.yaml"):
        self.config_path = config_path
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        return {}

    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    def get_bok_codes(self) -> Dict[str, str]:
        return self.get("bok_codes", {
            "base_rate": "722Y001",
            "m2": "101Y001",
            "loan_rate": "121Y002"
        })

    def get_financial_defaults(self) -> Dict[str, Any]:
        return self.get("financial_defaults", {
            "tax_rate_multiplier": 0.03,
            "interest_rate": 0.045,
            "loan_term_years": 30
        })
