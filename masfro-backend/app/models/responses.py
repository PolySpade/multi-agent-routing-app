"""
Pydantic response models for API endpoints.
"""

from pydantic import BaseModel
from typing import List, Tuple, Optional


class RouteResponse(BaseModel):
    """Response model for route results."""
    route_id: str
    status: str
    path: List[Tuple[float, float]]
    distance: Optional[float] = None
    estimated_time: Optional[float] = None
    risk_level: Optional[float] = None
    warnings: List[str] = []
    message: Optional[str] = None
