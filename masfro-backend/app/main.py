# filename: masfro-backend/main.py

"""
FastAPI Backend for Multi-Agent System for Flood Route Optimization (MAS-FRO)

This is the main entry point for the MAS-FRO backend API. It initializes all
agents in the multi-agent system and provides REST API endpoints for route
requests and system monitoring.

Author: MAS-FRO Development Team
Date: November 2025
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List, Tuple, Optional, Dict, Any, Set
from fastapi import BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import logging
import asyncio
import json
from datetime import datetime

# Agent imports
from app.environment.graph_manager import DynamicGraphEnvironment
from app.agents.flood_agent import FloodAgent
from app.agents.scout_agent import ScoutAgent
from app.agents.hazard_agent import HazardAgent
from app.agents.evacuation_manager_agent import EvacuationManagerAgent
from app.agents.routing_agent import RoutingAgent

# No direct algorithm imports needed - RoutingAgent handles all pathfinding

# Communication imports
from app.communication.message_queue import MessageQueue
from app.communication.acl_protocol import ACLMessage, Performative

# Scheduler imports
from app.services.flood_data_scheduler import FloodDataScheduler, set_scheduler, get_scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- WebSocket Connection Manager ---

class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        """Initialize connection manager."""
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(
            f"WebSocket connected. Total connections: {len(self.active_connections)}"
        )

    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection."""
        self.active_connections.discard(websocket)
        logger.info(
            f"WebSocket disconnected. "
            f"Total connections: {len(self.active_connections)}"
        )

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to WebSocket: {e}")
                disconnected.add(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to specific client."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)


# Initialize WebSocket manager
ws_manager = ConnectionManager()

# --- 1. Data Models (using Pydantic) ---

class RouteRequest(BaseModel):
    """Request model for route calculation."""
    start_location: Tuple[float, float]  # (latitude, longitude)
    end_location: Tuple[float, float]
    preferences: Optional[Dict[str, Any]] = None

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

class FeedbackRequest(BaseModel):
    """Request model for user feedback."""
    route_id: str
    feedback_type: str  # "clear", "blocked", "flooded", "traffic"
    location: Optional[Tuple[float, float]] = None
    severity: Optional[float] = None
    description: Optional[str] = None

# --- 2. FastAPI Application Setup ---

app = FastAPI(
    title="MAS-FRO API",
    description="Multi-Agent System for Flood Route Optimization API",
    version="1.0.0"
)

# CORS configuration
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Serve static files (flood maps, data)
app.mount("/data", StaticFiles(directory="app/data"), name="data")

# --- 3. Initialize Multi-Agent System ---

logger.info("Initializing MAS-FRO Multi-Agent System...")

# Initialize environment
environment = DynamicGraphEnvironment()

# Initialize message queue for agent communication
message_queue = MessageQueue()

# Initialize agents
hazard_agent = HazardAgent("hazard_agent_001", environment)

# FloodAgent with REAL API integration
flood_agent = FloodAgent(
    "flood_agent_001",
    environment,
    hazard_agent=hazard_agent,
    use_simulated=False,  # Disable simulated data
    use_real_apis=True    # Enable PAGASA + OpenWeatherMap
)

routing_agent = RoutingAgent("routing_agent_001", environment)
evacuation_manager = EvacuationManagerAgent("evac_manager_001", environment)

# ScoutAgent requires Twitter/X credentials - initialize when needed
# Example:
#   scout_agent = ScoutAgent(
#       "scout_agent_001",
#       environment,
#       email="your_email@example.com",
#       password="your_password",
#       hazard_agent=hazard_agent
#   )
#   scout_agent.set_hazard_agent(hazard_agent)
scout_agent = None

# Link agents (create agent network)
flood_agent.set_hazard_agent(hazard_agent)
evacuation_manager.set_hazard_agent(hazard_agent)
evacuation_manager.set_routing_agent(routing_agent)

# Initialize FloodAgent scheduler (5-minute intervals)
flood_scheduler = FloodDataScheduler(flood_agent, interval_seconds=300)
set_scheduler(flood_scheduler)

logger.info("MAS-FRO system initialized successfully")

# --- 3.5. Startup and Shutdown Events ---

@app.on_event("startup")
async def startup_event():
    """Start background tasks on application startup."""
    logger.info("Starting background scheduler...")
    scheduler = get_scheduler()
    if scheduler:
        await scheduler.start()
        logger.info("✅ Automated flood data collection started (every 5 minutes)")
    else:
        logger.warning("Scheduler not initialized")


@app.on_event("shutdown")
async def shutdown_event():
    """Stop background tasks on application shutdown."""
    logger.info("Stopping background scheduler...")
    scheduler = get_scheduler()
    if scheduler:
        await scheduler.stop()
        logger.info("✅ Scheduler stopped gracefully")


# --- 4. API Endpoints ---

@app.get("/", tags=["General"])
async def read_root():
    """Health check endpoint."""
    return {
        "message": "Welcome to MAS-FRO Backend API",
        "version": "1.0.0",
        "status": "operational"
    }

@app.get("/api/health", tags=["General"])
async def health_check():
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

@app.post("/api/route", tags=["Routing"], response_model=RouteResponse)
async def get_route(request: RouteRequest):
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
        import uuid
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

@app.post("/api/feedback", tags=["Feedback"])
async def submit_feedback(feedback: FeedbackRequest):
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

@app.post("/api/evacuation-center", tags=["Routing"])
async def get_nearest_evacuation_center(
    location: Tuple[float, float]
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

@app.post("/api/admin/collect-flood-data", tags=["Admin"])
async def trigger_flood_data_collection():
    """
    Manually trigger flood data collection from FloodAgent.

    This endpoint is useful for testing the agent communication workflow
    and forcing an update of flood conditions.
    """
    logger.info("Manual flood data collection triggered")

    try:
        # Trigger FloodAgent to collect and forward data
        data = flood_agent.collect_and_forward_data()

        return {
            "status": "success",
            "message": "Flood data collection completed",
            "locations_updated": len(data),
            "data_summary": list(data.keys()) if data else []
        }

    except Exception as e:
        logger.error(f"Flood data collection error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error collecting flood data: {str(e)}"
        )

@app.websocket("/ws/route-updates")
async def websocket_route_updates(websocket: WebSocket):
    """
    WebSocket endpoint for real-time route and risk updates.

    Clients can connect to receive live updates about:
    - Flood risk level changes
    - Route recalculations
    - System status updates
    - Hazard alerts
    """
    await ws_manager.connect(websocket)

    try:
        # Send initial connection message
        await ws_manager.send_personal_message(
            {
                "type": "connection",
                "status": "connected",
                "message": "Connected to MAS-FRO real-time updates",
                "timestamp": datetime.now().isoformat()
            },
            websocket
        )

        # Send initial system status
        graph_status = "loaded" if environment.graph else "not_loaded"
        await ws_manager.send_personal_message(
            {
                "type": "system_status",
                "graph_status": graph_status,
                "agents": {
                    "flood_agent": "active" if flood_agent else "inactive",
                    "hazard_agent": "active" if hazard_agent else "inactive",
                    "routing_agent": "active" if routing_agent else "inactive",
                    "evacuation_manager": "active" if evacuation_manager else "inactive"
                },
                "timestamp": datetime.now().isoformat()
            },
            websocket
        )

        # Keep connection alive and listen for messages
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_json()

                # Handle different message types
                if data.get("type") == "ping":
                    await ws_manager.send_personal_message(
                        {
                            "type": "pong",
                            "timestamp": datetime.now().isoformat()
                        },
                        websocket
                    )

                elif data.get("type") == "request_update":
                    # Send current risk levels and system status
                    stats = evacuation_manager.get_route_statistics()
                    await ws_manager.send_personal_message(
                        {
                            "type": "statistics_update",
                            "data": stats,
                            "timestamp": datetime.now().isoformat()
                        },
                        websocket
                    )

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")
                await ws_manager.send_personal_message(
                    {
                        "type": "error",
                        "message": str(e),
                        "timestamp": datetime.now().isoformat()
                    },
                    websocket
                )

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)


@app.get("/api/statistics", tags=["Monitoring"])
async def get_statistics():
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

@app.get("/api/scheduler/status", tags=["Scheduler"])
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

@app.get("/api/scheduler/stats", tags=["Scheduler"])
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

@app.post("/api/scheduler/trigger", tags=["Scheduler"])
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
