# filename: masfro-backend/app/core/auth.py
"""
API Authentication Module

Provides API key authentication for protecting sensitive endpoints.
"""

from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Define the API key header scheme
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(API_KEY_HEADER)) -> str:
    """
    Verify API key for protected endpoints.

    Args:
        api_key: API key from X-API-Key header

    Returns:
        The validated API key

    Raises:
        HTTPException: 401 if API key is missing or invalid
    """
    if not api_key:
        logger.warning("API request without API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Include X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if api_key != settings.API_KEY:
        logger.warning(f"Invalid API key attempt: {api_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return api_key
