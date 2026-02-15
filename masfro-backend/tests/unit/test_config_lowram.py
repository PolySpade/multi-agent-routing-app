"""
Tests for low-RAM configuration flags in app.core.config.Settings.

Each test creates a fresh Settings() instance to avoid cross-contamination
from the module-level singleton.
"""

import os
from unittest.mock import patch

import pytest

from app.core.config import Settings


class TestSettingsDefaults:
    """Verify default values when no env vars are set."""

    def test_low_ram_default_false(self):
        with patch.dict(os.environ, {}, clear=False):
            # Remove the key if it exists so we get the default
            os.environ.pop("MASFRO_LOW_RAM", None)
            s = Settings(_env_file=None)
            assert s.MASFRO_LOW_RAM is False

    def test_disable_selenium_default_false(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MASFRO_DISABLE_SELENIUM", None)
            s = Settings(_env_file=None)
            assert s.MASFRO_DISABLE_SELENIUM is False

    def test_disable_scheduler_default_false(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MASFRO_DISABLE_SCHEDULER", None)
            s = Settings(_env_file=None)
            assert s.MASFRO_DISABLE_SCHEDULER is False

    def test_scheduler_interval_default_5(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MASFRO_SCHEDULER_INTERVAL", None)
            s = Settings(_env_file=None)
            assert s.MASFRO_SCHEDULER_INTERVAL == 5


class TestSettingsOverrides:
    """Verify env var overrides change behavior."""

    def test_low_ram_true_from_env(self):
        with patch.dict(os.environ, {"MASFRO_LOW_RAM": "true"}):
            s = Settings(_env_file=None)
            assert s.MASFRO_LOW_RAM is True
            assert s.is_low_ram() is True

    def test_disable_selenium_true_from_env(self):
        with patch.dict(os.environ, {"MASFRO_DISABLE_SELENIUM": "true"}):
            s = Settings(_env_file=None)
            assert s.MASFRO_DISABLE_SELENIUM is True
            assert s.is_selenium_enabled() is False

    def test_disable_scheduler_true_from_env(self):
        with patch.dict(os.environ, {"MASFRO_DISABLE_SCHEDULER": "true"}):
            s = Settings(_env_file=None)
            assert s.MASFRO_DISABLE_SCHEDULER is True
            assert s.is_scheduler_enabled() is False

    def test_scheduler_interval_override(self):
        with patch.dict(os.environ, {"MASFRO_SCHEDULER_INTERVAL": "15"}):
            s = Settings(_env_file=None)
            assert s.MASFRO_SCHEDULER_INTERVAL == 15


class TestSettingsHelpers:
    """Verify helper method logic."""

    def test_is_low_ram_false_by_default(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MASFRO_LOW_RAM", None)
            s = Settings(_env_file=None)
            assert s.is_low_ram() is False

    def test_is_selenium_enabled_true_by_default(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MASFRO_DISABLE_SELENIUM", None)
            s = Settings(_env_file=None)
            assert s.is_selenium_enabled() is True

    def test_is_scheduler_enabled_true_by_default(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MASFRO_DISABLE_SCHEDULER", None)
            s = Settings(_env_file=None)
            assert s.is_scheduler_enabled() is True

    def test_is_llm_enabled_default_true(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("LLM_ENABLED", None)
            s = Settings(_env_file=None)
            assert s.is_llm_enabled() is True
