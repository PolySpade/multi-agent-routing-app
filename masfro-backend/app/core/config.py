# filename: masfro-backend/app/core/config.py
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from .env and config YAML files.

    Environment variables (.env) take precedence over YAML configuration.
    """
    # Define the variables you expect to be in your .env file
    GOOGLE_API_KEY: str
    DATABASE_URL: str
    TWITTER_EMAIL: str
    TWITTER_PASSWORD: str

    # Security settings
    ALLOWED_ORIGINS: str = "http://localhost:3000"
    API_KEY: str = "development-key-change-in-production"
    ENVIRONMENT: str = "development"

    # This tells Pydantic to load variables from a file named .env
    model_config = SettingsConfigDict(env_file=".env")

    def __init__(self, **kwargs):
        """Initialize settings and load YAML configuration."""
        super().__init__(**kwargs)
        self._yaml_config = self._load_yaml_config()

    def _load_yaml_config(self) -> Dict[str, Any]:
        """
        Load configuration from YAML file.

        Returns:
            Dictionary containing YAML configuration, or empty dict if not found
        """
        config_path = Path(__file__).parent.parent.parent / "config" / "default.yaml"

        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    return config or {}
            except Exception as e:
                print(f"Warning: Failed to load YAML config: {e}")
                return {}
        else:
            print(f"Warning: Config file not found at {config_path}")
            return {}

    def get(self, path: str, default: Any = None) -> Any:
        """
        Get nested configuration value using dot notation.

        Args:
            path: Dot-separated path (e.g., 'agents.hazard.cache.max_scout')
            default: Default value if path not found

        Returns:
            Configuration value or default

        Example:
            >>> settings.get('agents.hazard.cache.max_scout')
            1000
            >>> settings.get('agents.routing.risk_weight', 0.5)
            0.5
        """
        keys = path.split('.')
        value = self._yaml_config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value


# Create a single, reusable instance of the settings
settings = Settings()