"""
Secure credential management for MAS-FRO system.

Uses Pydantic settings to load credentials from environment variables
without storing them in memory unnecessarily.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class TwitterCredentials(BaseSettings):
    """
    Twitter/X API credentials loaded from environment variables.

    Required environment variables:
        - TWITTER_BEARER_TOKEN: OAuth 2.0 Bearer Token for Twitter API v2
        - TWITTER_API_KEY: API Key (Consumer Key)
        - TWITTER_API_SECRET: API Secret (Consumer Secret)

    Optional (for legacy scraping - NOT RECOMMENDED):
        - TWITTER_EMAIL: Email for web scraping (security risk)
        - TWITTER_PASSWORD: Password for web scraping (security risk)
    """
    twitter_bearer_token: Optional[str] = None
    twitter_api_key: Optional[str] = None
    twitter_api_secret: Optional[str] = None

    # Legacy scraping credentials (NOT RECOMMENDED - security risk)
    twitter_email: Optional[str] = None
    twitter_password: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


class PAGASACredentials(BaseSettings):
    """
    PAGASA API credentials loaded from environment variables.

    Required environment variables:
        - PAGASA_API_KEY: API key for PAGASA services (if required)
    """
    pagasa_api_key: Optional[str] = None
    pagasa_api_url: str = "https://www.pagasa.dost.gov.ph"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


class OpenWeatherMapCredentials(BaseSettings):
    """
    OpenWeatherMap API credentials loaded from environment variables.

    Required environment variables:
        - OPENWEATHER_API_KEY: API key for OpenWeatherMap
    """
    openweather_api_key: Optional[str] = None
    openweather_api_url: str = "https://api.openweathermap.org/data/2.5"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


class DatabaseCredentials(BaseSettings):
    """
    Database connection credentials loaded from environment variables.

    Required environment variables:
        - DATABASE_URL: Full PostgreSQL connection string
    """
    database_url: str = "postgresql://postgres:password@localhost:5432/masfro_db"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


def get_twitter_credentials() -> TwitterCredentials:
    """Get Twitter credentials from environment."""
    return TwitterCredentials()


def get_pagasa_credentials() -> PAGASACredentials:
    """Get PAGASA credentials from environment."""
    return PAGASACredentials()


def get_openweather_credentials() -> OpenWeatherMapCredentials:
    """Get OpenWeatherMap credentials from environment."""
    return OpenWeatherMapCredentials()


def get_database_credentials() -> DatabaseCredentials:
    """Get database credentials from environment."""
    return DatabaseCredentials()
