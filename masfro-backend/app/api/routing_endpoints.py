"""
Routing API endpoints for route calculation and evacuation centers.
"""

import logging
import uuid
from typing import Tuple
from fastapi import APIRouter, HTTPException, Depends

from app.models.requests import RouteRequest, FeedbackRequest
from app.models.responses import RouteResponse
from app.core.dependencies import (
    get_environment,
    get_routing_agent,
    get_evacuation_manager
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Routing"])


@router.post("/route", response_model=RouteResponse)
async def get_route(
    request: RouteRequest,
    environment=Depends(get_environment),
    routing_agent=Depends(get_routing_agent)
):
    """
    Calculate optimal flood-safe route between two points.

    Uses RoutingAgent with risk-aware A* algorithm to find the safest path
    considering current flood conditions.
    """
    logger.info(f"Route request: {request.start_location} -> {request.end_location}")

    try:
        # Check if graph is loaded
        if not environment.graph:
            raise HTTPException(
                status_code=503,
                detail="Road network not loaded. Please contact administrator."
            )

        # Use RoutingAgent to calculate route
        route_result = routing_agent.calculate_route(
            start=request.start_location,
            end=request.end_location,
            preferences=request.preferences
        )

        if not route_result.get("path"):
            raise HTTPException(
                status_code=404,
                detail="No safe route found between these locations."
            )

        # Generate route ID
        route_id = str(uuid.uuid4())

        return RouteResponse(
            route_id=route_id,
            status="success",
            path=route_result["path"],
            distance=route_result.get("distance"),
            estimated_time=route_result.get("estimated_time"),
            risk_level=route_result.get("risk_level"),
            warnings=route_result.get("warnings", [])
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Route calculation validation error: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Route calculation error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error during route calculation: {str(e)}"
        )


@router.post("/feedback")
async def submit_feedback(
    feedback: FeedbackRequest,
    evacuation_manager=Depends(get_evacuation_manager)
):
    """
    Submit user feedback about road conditions.

    Users can report:
    - Road clear (passable)
    - Road blocked (impassable)
    - Flooding detected
    - Traffic conditions
    """
    logger.info(f"Feedback received: {feedback.feedback_type} for route {feedback.route_id}")

    try:
        # Process feedback through evacuation manager
        success = evacuation_manager.collect_user_feedback(
            route_id=feedback.route_id,
            feedback_type=feedback.feedback_type,
            location=feedback.location,
            data={
                "severity": feedback.severity or 0.5,
                "description": feedback.description
            }
        )

        if success:
            return {
                "status": "success",
                "message": "Feedback received and processed. Thank you!"
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid feedback data"
            )

    except Exception as e:
        logger.error(f"Feedback processing error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing feedback: {str(e)}"
        )


@router.post("/evacuation-center")
async def get_nearest_evacuation_center(
    location: Tuple[float, float],
    environment=Depends(get_environment),
    routing_agent=Depends(get_routing_agent)
):
    """
    Find nearest evacuation center and calculate route.

    Returns the closest safe evacuation center with route information.
    """
    logger.info(f"Evacuation center request from {location}")

    try:
        if not environment.graph:
            raise HTTPException(
                status_code=503,
                detail="Road network not loaded."
            )

        result = routing_agent.find_nearest_evacuation_center(location)

        if not result:
            raise HTTPException(
                status_code=404,
                detail="No evacuation centers found or accessible."
            )

        return {
            "status": "success",
            "evacuation_center": result["center"],
            "route": {
                "path": result["path"],
                "distance": result["metrics"]["total_distance"],
                "estimated_time": result["metrics"]["estimated_time"],
                "risk_level": result["metrics"]["average_risk"]
            },
            "alternatives": result.get("alternatives", [])
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Evacuation center lookup error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error finding evacuation center: {str(e)}"
        )
