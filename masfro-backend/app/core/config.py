# filename: masfro-backend-v2/app/core/config.py

"""
Configuration module for MAS-FRO Backend v2.

Handles loading of environment variables and YAML configuration files.
v2 adds LLM configuration settings for Qwen 3 integration.

Author: MAS-FRO Development Team
Date: February 2026
"""

import yaml
import os
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from .env and config YAML files.

    Environment variables (.env) take precedence over YAML configuration.

    v2 Additions:
    - LLM configuration (Ollama/Qwen 3)
    - LLM service enable/disable flag
    """
    # Define the variables you expect to be in your .env file
    GOOGLE_API_KEY: str = ""
    DATABASE_URL: str = ""
    TWITTER_EMAIL: str = ""
    TWITTER_PASSWORD: str = ""
    OPENWEATHERMAP_API_KEY: str = ""

    # Security settings
    ALLOWED_ORIGINS: str = "http://localhost:3000"
    API_KEY: str = "development-key-change-in-production"
    ENVIRONMENT: str = "development"

    # ========== LLM CONFIGURATION (v2) ==========
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_TEXT_MODEL: str = ""
    LLM_VISION_MODEL: str = ""
    LLM_TIMEOUT_SECONDS: int = 30
    LLM_ENABLED: bool = True

    # ========== MOCK DATA SOURCES ==========
    USE_MOCK_SOURCES: bool = False
    MOCK_SERVER_URL: str = "http://localhost:8081"

    # ========== LOW-RAM MODE ==========
    MASFRO_LOW_RAM: bool = False
    MASFRO_DISABLE_SELENIUM: bool = False
    MASFRO_DISABLE_LLM: bool = False
    MASFRO_DISABLE_SCHEDULER: bool = False
    MASFRO_SCHEDULER_INTERVAL: int = 5  # minutes

    # ========== STARTUP CONFIGURATION ==========
    LOAD_INITIAL_FLOOD_DATA: bool = False  # Load rr01_step_01.tif at startup?

    # This tells Pydantic to load variables from a file named .env
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"  # Ignore extra env vars
    )

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

    def get_llm_config(self) -> Dict[str, Any]:
        """
        Get LLM configuration as a dictionary.

        Returns:
            Dict with LLM configuration:
            {
                "base_url": str,
                "text_model": str,
                "vision_model": str,
                "timeout_seconds": int,
                "enabled": bool
            }
        """
        return {
            "base_url": self.OLLAMA_BASE_URL,
            "text_model": self.LLM_TEXT_MODEL,
            "vision_model": self.LLM_VISION_MODEL,
            "timeout_seconds": self.LLM_TIMEOUT_SECONDS,
            "enabled": self.LLM_ENABLED
        }

    def is_llm_enabled(self) -> bool:
        """Check if LLM integration is enabled."""
        return self.LLM_ENABLED

    def is_low_ram(self) -> bool:
        """Check if running in low-RAM mode."""
        return self.MASFRO_LOW_RAM

    def is_selenium_enabled(self) -> bool:
        """Check if Selenium scraping is enabled."""
        return not self.MASFRO_DISABLE_SELENIUM

    def is_scheduler_enabled(self) -> bool:
        """Check if the flood data scheduler is enabled."""
        return not self.MASFRO_DISABLE_SCHEDULER


# Create a single, reusable instance of the settings
settings = Settings()
