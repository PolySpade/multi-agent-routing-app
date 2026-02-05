"""
General API endpoints (health checks, statistics, scheduler).
"""

import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends

from app.core.dependencies import (
    get_environment,
    get_flood_agent,
    get_hazard_agent,
    get_routing_agent,
    get_evacuation_manager
)
from app.services.flood_data_scheduler import get_scheduler

logger = logging.getLogger(__name__)

router = APIRouter(tags=["General"])


@router.get("/")
async def read_root():
    """Health check endpoint."""
    return {
        "message": "Welcome to MAS-FRO Backend API",
        "version": "1.0.0",
        "status": "operational"
    }


@router.get("/health")
async def health_check(
    environment=Depends(get_environment),
    flood_agent=Depends(get_flood_agent),
    hazard_agent=Depends(get_hazard_agent),
    routing_agent=Depends(get_routing_agent),
    evacuation_manager=Depends(get_evacuation_manager)
):
    """System health check."""
    graph_status = "loaded" if environment.graph else "not_loaded"

    return {
        "status": "healthy",
        "graph_status": graph_status,
        "agents": {
            "flood_agent": "active" if flood_agent else "inactive",
            "hazard_agent": "active" if hazard_agent else "inactive",
            "routing_agent": "active" if routing_agent else "inactive",
            "evacuation_manager": "active" if evacuation_manager else "inactive"
        }
    }


@router.get("/statistics")
async def get_statistics(
    environment=Depends(get_environment),
    evacuation_manager=Depends(get_evacuation_manager)
):
    """Get system statistics."""
    try:
        stats = evacuation_manager.get_route_statistics()

        graph_stats = {}
        if environment.graph:
            graph_stats = {
                "total_nodes": environment.graph.number_of_nodes(),
                "total_edges": environment.graph.number_of_edges()
            }

        return {
            "route_statistics": stats,
            "graph_statistics": graph_stats,
            "system_status": "operational"
        }

    except Exception as e:
        logger.error(f"Statistics error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving statistics: {str(e)}"
        )


@router.get("/scheduler/status", tags=["Scheduler"])
async def get_scheduler_status():
    """
    Get scheduler health status.

    Returns current scheduler status including:
    - Running state
    - Interval configuration
    - Uptime
    - Basic statistics
    """
    try:
        scheduler = get_scheduler()
        if not scheduler:
            raise HTTPException(
                status_code=503,
                detail="Scheduler not initialized"
            )

        status = scheduler.get_status()
        return {
            "status": "healthy" if status["is_running"] else "stopped",
            **status
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Scheduler status error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving scheduler status: {str(e)}"
        )


@router.get("/scheduler/stats", tags=["Scheduler"])
async def get_scheduler_statistics():
    """
    Get detailed scheduler statistics.

    Returns comprehensive statistics including:
    - Total runs
    - Success/failure rates
    - Data collection metrics
    - Last run information
    - Error history
    """
    try:
        scheduler = get_scheduler()
        if not scheduler:
            raise HTTPException(
                status_code=503,
                detail="Scheduler not initialized"
            )

        status = scheduler.get_status()
        return {
            "scheduler_status": "running" if status["is_running"] else "stopped",
            "configuration": {
                "interval_seconds": status["interval_seconds"],
                "interval_minutes": status["interval_minutes"]
            },
            "runtime": {
                "uptime_seconds": status["uptime_seconds"],
                "started_at": status["statistics"]["last_run_time"]
            },
            "statistics": status["statistics"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Scheduler statistics error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving scheduler statistics: {str(e)}"
        )


@router.post("/scheduler/trigger", tags=["Scheduler"])
async def trigger_scheduler_manual_collection():
    """
    Manually trigger flood data collection (outside of schedule).

    This endpoint forces an immediate data collection run without waiting
    for the next scheduled interval. Useful for testing and on-demand updates.

    Returns:
        Collection results including status, data points, and duration
    """
    try:
        scheduler = get_scheduler()
        if not scheduler:
            raise HTTPException(
                status_code=503,
                detail="Scheduler not initialized"
            )

        logger.info("Manual scheduler trigger requested via API")
        result = await scheduler.trigger_manual_collection()

        if result["status"] == "success":
            return {
                "status": "success",
                "message": "Manual data collection completed successfully",
                **result
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Manual collection failed: {result.get('error')}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Manual trigger error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error triggering manual collection: {str(e)}"
        )
