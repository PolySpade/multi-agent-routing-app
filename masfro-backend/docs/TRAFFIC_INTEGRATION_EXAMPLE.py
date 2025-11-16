# filename: docs/TRAFFIC_INTEGRATION_EXAMPLE.py

"""
Example code showing how to integrate TrafficAgent into main.py

This is a reference implementation - copy relevant sections to your main.py
"""

from fastapi import FastAPI, HTTPException
from app.agents.traffic_agent import TrafficAgent
from app.environment.graph_manager import DynamicGraphEnvironment
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# SECTION 1: Add import at the top of main.py
# ============================================================================

# Add this with other agent imports:
from app.agents.traffic_agent import TrafficAgent


# ============================================================================
# SECTION 2: Initialize TrafficAgent in startup event
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize all agents and services."""

    # ... existing code for other agents ...

    # ========== NEW: Initialize TrafficAgent ==========
    try:
        logger.info("Initializing TrafficAgent...")

        traffic_agent = TrafficAgent(
            agent_id="traffic_001",
            environment=graph_env,  # Your DynamicGraphEnvironment instance
            update_interval=14400,   # 4 hours (stays within free tier)
            sample_interval=200      # Sample 60 edges per update
        )

        # Store in app state for access in endpoints
        app.state.traffic_agent = traffic_agent

        logger.info("✅ TrafficAgent initialized successfully")

        # Optionally: Perform initial traffic update
        logger.info("Performing initial traffic data update...")
        stats = traffic_agent.update_traffic_data()
        logger.info(
            f"Initial traffic update complete: "
            f"{stats['edges_updated']} edges, "
            f"avg_traffic={stats['avg_traffic_factor']:.3f}"
        )

    except ValueError as e:
        # API key not configured - traffic integration disabled
        logger.warning(f"⚠️ TrafficAgent not initialized: {e}")
        logger.warning("Traffic integration disabled. Set GOOGLE_MAPS_API_KEY to enable.")
        app.state.traffic_agent = None

    except Exception as e:
        logger.error(f"❌ Failed to initialize TrafficAgent: {e}")
        app.state.traffic_agent = None


# ============================================================================
# SECTION 3: Add traffic update endpoints
# ============================================================================

@app.post("/api/admin/update-traffic", tags=["admin"])
async def update_traffic_data():
    """
    Manually trigger traffic data update.

    This endpoint allows administrators to force a traffic data refresh
    outside of the normal scheduled updates.

    Returns:
        dict: Traffic update statistics

    Example response:
        {
            "success": true,
            "statistics": {
                "edges_updated": 60,
                "edges_skipped": 0,
                "avg_traffic_factor": 0.32,
                "max_traffic_factor": 0.85,
                "elapsed_seconds": 12.4,
                "timestamp": "2025-11-15T14:30:00"
            }
        }
    """
    if not app.state.traffic_agent:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Traffic monitoring not enabled",
                "message": "GOOGLE_MAPS_API_KEY not configured in environment",
                "solution": "Add GOOGLE_MAPS_API_KEY to .env file"
            }
        )

    try:
        logger.info("Manual traffic update requested via API")
        stats = app.state.traffic_agent.update_traffic_data()

        return {
            "success": True,
            "statistics": stats,
            "message": f"Updated {stats['edges_updated']} edges successfully"
        }

    except Exception as e:
        logger.error(f"Traffic update failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Traffic update failed",
                "message": str(e)
            }
        )


@app.get("/api/traffic/status", tags=["traffic"])
async def get_traffic_status():
    """
    Get current traffic monitoring status and statistics.

    Returns current configuration and usage metrics for the traffic
    monitoring system.

    Returns:
        dict: Traffic monitoring status

    Example response:
        {
            "enabled": true,
            "agent_id": "traffic_001",
            "last_update": "2025-11-15T14:30:00",
            "update_interval": 14400,
            "sample_interval": 200,
            "service_stats": {
                "api_requests": 360,
                "cache_entries": 45,
                "cache_duration": 14400
            }
        }
    """
    if not app.state.traffic_agent:
        return {
            "enabled": False,
            "message": "Traffic monitoring not configured",
            "setup_instructions": "Add GOOGLE_MAPS_API_KEY to .env file and restart server"
        }

    stats = app.state.traffic_agent.get_statistics()

    return {
        "enabled": True,
        **stats
    }


@app.get("/api/traffic/segment/{lat1}/{lon1}/{lat2}/{lon2}", tags=["traffic"])
async def get_segment_traffic(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float
):
    """
    Get current traffic factor for a specific road segment.

    Args:
        lat1: Origin latitude
        lon1: Origin longitude
        lat2: Destination latitude
        lon2: Destination longitude

    Returns:
        dict: Traffic information for the segment

    Example:
        GET /api/traffic/segment/14.6507/121.1029/14.6545/121.1089

        Response:
        {
            "origin": [14.6507, 121.1029],
            "destination": [14.6545, 121.1089],
            "traffic_factor": 0.42,
            "interpretation": "Moderate traffic (42% delay)",
            "status": "yellow"
        }
    """
    if not app.state.traffic_agent:
        raise HTTPException(
            status_code=503,
            detail="Traffic monitoring not enabled"
        )

    try:
        origin = (lat1, lon1)
        destination = (lat2, lon2)

        traffic_factor = app.state.traffic_agent.get_current_traffic(
            origin,
            destination
        )

        # Categorize traffic level
        if traffic_factor < 0.2:
            status = "green"
            interpretation = f"Light traffic ({traffic_factor:.0%} delay)"
        elif traffic_factor < 0.5:
            status = "yellow"
            interpretation = f"Moderate traffic ({traffic_factor:.0%} delay)"
        elif traffic_factor < 1.0:
            status = "orange"
            interpretation = f"Heavy traffic ({traffic_factor:.0%} delay)"
        else:
            status = "red"
            interpretation = f"Severe congestion ({traffic_factor:.0%} delay)"

        return {
            "origin": list(origin),
            "destination": list(destination),
            "traffic_factor": round(traffic_factor, 3),
            "interpretation": interpretation,
            "status": status,
            "timestamp": app.state.traffic_agent.last_update.isoformat() if app.state.traffic_agent.last_update else None
        }

    except Exception as e:
        logger.error(f"Failed to get segment traffic: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SECTION 4: Add traffic info to existing route endpoint
# ============================================================================

@app.post("/api/route", tags=["routing"])
async def calculate_route(request: RouteRequest):
    """
    Calculate optimal route considering flood risk AND traffic conditions.

    NOTE: This is an enhancement to your existing /api/route endpoint.
    The traffic factor is automatically included in edge weights.
    """
    # ... existing route calculation code ...

    # After route is calculated, add traffic statistics
    if app.state.traffic_agent and app.state.traffic_agent.last_update:
        route_result["traffic_info"] = {
            "enabled": True,
            "last_update": app.state.traffic_agent.last_update.isoformat(),
            "note": "Route considers real-time traffic conditions"
        }
    else:
        route_result["traffic_info"] = {
            "enabled": False,
            "note": "Route calculated without traffic data"
        }

    return route_result


# ============================================================================
# SECTION 5: Optional - Automated periodic updates using BackgroundTasks
# ============================================================================

from fastapi import BackgroundTasks
import asyncio

async def periodic_traffic_update():
    """
    Background task that periodically updates traffic data.

    This runs independently of user requests and ensures traffic
    data stays fresh according to the configured update_interval.
    """
    while True:
        try:
            if app.state.traffic_agent:
                # Check if update is needed
                if app.state.traffic_agent._should_update():
                    logger.info("Starting scheduled traffic update...")
                    stats = app.state.traffic_agent.update_traffic_data()
                    logger.info(
                        f"Scheduled traffic update complete: "
                        f"{stats['edges_updated']} edges updated"
                    )

            # Wait 1 hour before checking again
            await asyncio.sleep(3600)

        except Exception as e:
            logger.error(f"Error in periodic traffic update: {e}")
            await asyncio.sleep(3600)  # Wait before retrying


@app.on_event("startup")
async def start_background_tasks():
    """Start background tasks on application startup."""
    # ... existing startup code ...

    # Start periodic traffic updates
    asyncio.create_task(periodic_traffic_update())
    logger.info("✅ Started periodic traffic update task")


# ============================================================================
# SECTION 6: Statistics endpoint enhancement
# ============================================================================

@app.get("/api/statistics", tags=["system"])
async def get_system_statistics():
    """
    Get comprehensive system statistics including traffic monitoring.

    This enhances your existing /api/statistics endpoint to include
    traffic agent metrics.
    """
    stats = {
        # ... existing statistics ...
    }

    # Add traffic statistics if available
    if app.state.traffic_agent:
        stats["traffic"] = app.state.traffic_agent.get_statistics()
    else:
        stats["traffic"] = {
            "enabled": False,
            "message": "Traffic monitoring not configured"
        }

    return stats


# ============================================================================
# EXAMPLE: Complete minimal main.py integration
# ============================================================================

"""
Minimal example showing only the essential changes to main.py:

1. Add import:
   from app.agents.traffic_agent import TrafficAgent

2. In startup_event():
   try:
       app.state.traffic_agent = TrafficAgent("traffic_001", graph_env)
   except ValueError:
       app.state.traffic_agent = None

3. Add endpoint:
   @app.post("/api/admin/update-traffic")
   async def update_traffic():
       if not app.state.traffic_agent:
           raise HTTPException(503, "Traffic not enabled")
       return {"stats": app.state.traffic_agent.update_traffic_data()}

That's it! The traffic data will automatically be used by RoutingAgent
because the graph edge weights are updated with traffic_factor.
"""
