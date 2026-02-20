# filename: app/api/evacuation_routes.py

"""
API routes for evacuation center management.

Provides endpoints for retrieving evacuation center information,
capacity status, and updating occupancy during simulations.

Author: MAS-FRO Development Team
Date: November 2025
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from pydantic import BaseModel, Field
import logging

from app.services.evacuation_service import get_evacuation_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agents/evacuation", tags=["evacuation"])


# Request/Response Models
class OccupancyUpdate(BaseModel):
    """Model for updating center occupancy."""
    center_name: str = Field(..., description="Name of the evacuation center")
    occupancy: int = Field(..., ge=0, description="New occupancy count (>= 0)")


class AddEvacueesRequest(BaseModel):
    """Model for adding evacuees to a center."""
    center_name: str = Field(..., description="Name of the evacuation center")
    count: int = Field(..., gt=0, description="Number of evacuees to add (> 0)")


@router.get("/centers", response_model=Dict[str, Any])
async def get_evacuation_centers():
    """
    Get all evacuation centers with capacity status.

    Returns:
        Dict containing status and list of evacuation centers with:
        - name, coordinates, capacity, current_occupancy
        - available_slots, occupancy_percentage
        - status (available/limited/full)
        - contact info, facilities
    """
    try:
        service = get_evacuation_service()
        centers = service.get_all_centers()

        return {
            "status": "success",
            "centers": centers,
            "count": len(centers),
            "statistics": service.get_statistics()
        }

    except Exception as e:
        logger.error(f"Failed to get evacuation centers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/centers/available", response_model=Dict[str, Any])
async def get_available_centers():
    """
    Get only available evacuation centers (not full).

    Returns:
        Dict containing centers with status 'available' or 'limited'
    """
    try:
        service = get_evacuation_service()
        centers = service.get_available_centers()

        return {
            "status": "success",
            "centers": centers,
            "count": len(centers)
        }

    except Exception as e:
        logger.error(f"Failed to get available centers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/centers/{center_name}", response_model=Dict[str, Any])
async def get_center_by_name(center_name: str):
    """
    Get specific evacuation center by name.

    Args:
        center_name: Name of the evacuation center

    Returns:
        Dict containing center information
    """
    try:
        service = get_evacuation_service()
        center = service.get_center_by_name(center_name)

        if not center:
            raise HTTPException(
                status_code=404,
                detail=f"Evacuation center '{center_name}' not found"
            )

        return {
            "status": "success",
            "center": center
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get center '{center_name}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/centers/occupancy", response_model=Dict[str, Any])
async def update_center_occupancy(update: OccupancyUpdate):
    """
    Update occupancy for a specific evacuation center.

    Args:
        update: OccupancyUpdate model with center_name and new occupancy

    Returns:
        Dict with success status and updated center info
    """
    try:
        service = get_evacuation_service()
        success = service.update_occupancy(update.center_name, update.occupancy)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Center '{update.center_name}' not found"
            )

        updated_center = service.get_center_by_name(update.center_name)

        return {
            "status": "success",
            "message": f"Updated occupancy for {update.center_name}",
            "center": updated_center
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update occupancy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/centers/add-evacuees", response_model=Dict[str, Any])
async def add_evacuees_to_center(request: AddEvacueesRequest):
    """
    Add evacuees to a center (for simulation).

    Args:
        request: AddEvacueesRequest with center_name and count

    Returns:
        Dict with success status and updated center info
    """
    try:
        service = get_evacuation_service()
        result = service.add_evacuees(request.center_name, request.count)

        if not result['success']:
            raise HTTPException(
                status_code=400,
                detail=result['message']
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add evacuees: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/centers/reset", response_model=Dict[str, Any])
async def reset_all_occupancy():
    """
    Reset occupancy to 0 for all centers (for simulation reset).

    Returns:
        Dict with success status
    """
    try:
        service = get_evacuation_service()
        service.reset_all_occupancy()

        return {
            "status": "success",
            "message": "All evacuation center occupancy reset to 0",
            "statistics": service.get_statistics()
        }

    except Exception as e:
        logger.error(f"Failed to reset occupancy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics", response_model=Dict[str, Any])
async def get_evacuation_statistics():
    """
    Get overall statistics about evacuation centers.

    Returns:
        Dict with statistics including:
        - total_centers, total_capacity, total_occupancy
        - total_available_slots, overall_occupancy_percentage
        - status_counts (available/limited/full)
    """
    try:
        service = get_evacuation_service()
        stats = service.get_statistics()

        return {
            "status": "success",
            "statistics": stats
        }

    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
