"""
Pydantic request models for API endpoints.
"""

from pydantic import BaseModel
from typing import Tuple, Optional, Dict, Any


class RouteRequest(BaseModel):
    """Request model for route calculation."""
    start_location: Tuple[float, float]  # (latitude, longitude)
    end_location: Tuple[float, float]
    preferences: Optional[Dict[str, Any]] = None


class FeedbackRequest(BaseModel):
    """Request model for user feedback."""
    route_id: str
    feedback_type: str  # "clear", "blocked", "flooded", "traffic"
    location: Optional[Tuple[float, float]] = None
    severity: Optional[float] = None
    description: Optional[str] = None
