# filename: masfro-backend/main.py

"""
FastAPI Backend for Multi-Agent System for Flood Route Optimization (MAS-FRO)

This is the main entry point for the MAS-FRO backend API. It initializes all
agents in the multi-agent system and provides REST API endpoints for route
requests and system monitoring.

Author: MAS-FRO Development Team
Date: November 2025
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, Query
from pydantic import BaseModel
from typing import List, Tuple, Optional, Dict, Any, Set
from fastapi import BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import logging
import asyncio
import json
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

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

# Simulation Manager imports
from app.services.simulation_manager import get_simulation_manager, SimulationManager

# Database imports
from app.database import get_db, FloodDataRepository, check_connection, init_db

# Logging configuration
from app.core.logging_config import setup_logging, get_logger

# API Routes
from app.api import graph_router, set_graph_environment

# Initialize structured logging (will be called again in startup event for safety)
setup_logging()
logger = get_logger(__name__)


# --- Utility Functions ---

class DateTimeEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that handles datetime and Decimal objects.

    Converts datetime objects to ISO format strings for JSON serialization.
    """
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def to_json_serializable(data: Any) -> str:
    """
    Convert data to JSON string with datetime handling.

    Args:
        data: Data to convert (dict, list, or primitive)

    Returns:
        JSON string with all datetime objects converted
    """
    return json.dumps(data, cls=DateTimeEncoder)


def convert_datetimes_to_strings(obj: Any) -> Any:
    """
    Recursively convert all datetime objects to ISO format strings.

    Args:
        obj: Object to convert (can be dict, list, datetime, or primitive)

    Returns:
        Converted object with all datetime instances as ISO strings
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: convert_datetimes_to_strings(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_datetimes_to_strings(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_datetimes_to_strings(item) for item in obj)
    else:
        return obj


# --- WebSocket Connection Manager ---

class ConnectionManager:
    """
    Manages WebSocket connections for real-time flood updates.

    Broadcasts:
    - Flood data updates (every 5 minutes from scheduler)
    - Critical water level alerts (Alarm/Critical thresholds)
    - Scheduler status updates
    - System notifications
    """

    def __init__(self):
        """Initialize connection manager."""
        import threading
        self.active_connections: Set[WebSocket] = set()
        self._lock = threading.Lock()  # Thread safety for connection set
        self.last_flood_state: Optional[Dict[str, Any]] = None
        self.critical_stations: Set[str] = set()  # Track critical river stations

    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection."""
        await websocket.accept()
        with self._lock:
            self.active_connections.add(websocket)
            count = len(self.active_connections)
        logger.info(
            f"WebSocket connected. Total connections: {count}"
        )

    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection."""
        with self._lock:
            self.active_connections.discard(websocket)
            count = len(self.active_connections)
        logger.info(
            f"WebSocket disconnected. "
            f"Total connections: {count}"
        )

    async def broadcast(self, message: dict):
        """
        Broadcast message to all connected clients.

        Uses custom JSON encoder to handle datetime objects.
        """
        from starlette.websockets import WebSocketDisconnect
        
        disconnected = set()

        # Serialize message with custom encoder for datetime handling
        try:
            json_str = to_json_serializable(message)
            logger.debug(f"Successfully serialized message of type: {message.get('type')}")
        except Exception as e:
            logger.error(f"JSON serialization error: {e}")
            logger.error(f"Message keys: {message.keys()}")
            logger.error(f"Message type field: {message.get('type')}")
            # Try to identify which field has the datetime issue
            for key, value in message.items():
                try:
                    json.dumps({key: value}, cls=DateTimeEncoder)
                except Exception as field_error:
                    logger.error(f"Field '{key}' caused error: {field_error}, value type: {type(value)}")
            raise  # Re-raise to prevent sending bad data

        # Create a copy of connections to avoid modification during iteration
        with self._lock:
            connections_copy = list(self.active_connections)
        
        for connection in connections_copy:
            try:
                # Check if connection is still in active set (might be removed by another thread)
                with self._lock:
                    if connection not in self.active_connections:
                        continue
                    
                await connection.send_text(json_str)
                logger.debug("send_text successful")
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected during broadcast")
                disconnected.add(connection)
            except Exception as e:
                # Handle any connection errors gracefully
                logger.warning(f"Failed to send to WebSocket: {type(e).__name__}: {e}")
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

    async def broadcast_flood_update(self, flood_data: Dict[str, Any]):
        """
        Broadcast flood data update to all connected clients.

        Args:
            flood_data: Dictionary containing river levels and weather data
        """
        if not self.active_connections:
            return  # No clients to broadcast to

        # Pre-convert ALL datetime objects to ISO format strings recursively
        clean_flood_data = convert_datetimes_to_strings(flood_data)

        message = {
            "type": "flood_update",
            "data": clean_flood_data,  # Now guaranteed to have no datetime objects
            "timestamp": datetime.now().isoformat(),
            "source": "flood_agent"
        }

        await self.broadcast(message)
        logger.info(f"Broadcasted flood update to {len(self.active_connections)} clients")

    async def broadcast_critical_alert(
        self,
        station_name: str,
        water_level: float,
        risk_level: str,
        message_text: str
    ):
        """
        Broadcast critical water level alert to all connected clients.

        Args:
            station_name: Name of the river station
            water_level: Current water level in meters
            risk_level: Risk classification (ALERT, ALARM, CRITICAL)
            message_text: Human-readable alert message
        """
        alert = {
            "type": "critical_alert",
            "severity": risk_level.lower(),
            "station": station_name,
            "water_level": water_level,
            "risk_level": risk_level,
            "message": message_text,
            "timestamp": datetime.now().isoformat(),  # Convert to string
            "action_required": risk_level in ["ALARM", "CRITICAL"]
        }

        await self.broadcast(alert)
        logger.warning(
            f"🚨 CRITICAL ALERT broadcasted: {station_name} - {risk_level} "
            f"({water_level}m) to {len(self.active_connections)} clients"
        )

    async def broadcast_scheduler_update(self, status: Dict[str, Any]):
        """
        Broadcast scheduler status update.

        Args:
            status: Scheduler status dictionary with run information
        """
        message = {
            "type": "scheduler_update",
            "status": status,
            "timestamp": datetime.now().isoformat()  # Convert to string
        }

        await self.broadcast(message)
        logger.debug(f"Broadcasted scheduler update to {len(self.active_connections)} clients")

    async def check_and_alert_critical_levels(self, flood_data: Dict[str, Any]):
        """
        Check flood data for critical water levels and broadcast alerts.

        Args:
            flood_data: Flood data from FloodAgent containing river levels
        """
        if "river_levels" not in flood_data:
            return

        river_levels = flood_data["river_levels"]

        for station_name, data in river_levels.items():
            risk_level = data.get("risk_level", "NORMAL")
            water_level = data.get("water_level", 0.0)

            # Alert on ALARM or CRITICAL levels
            if risk_level in ["ALARM", "CRITICAL"]:
                # Check if this is a new critical station
                station_key = f"{station_name}_{risk_level}"
                if station_key not in self.critical_stations:
                    self.critical_stations.add(station_key)

                    # Create alert message
                    if risk_level == "CRITICAL":
                        message = (
                            f"⚠️ CRITICAL FLOOD WARNING: {station_name} has reached "
                            f"CRITICAL water level ({water_level:.2f}m). "
                            f"EVACUATE IMMEDIATELY if you are in the affected area!"
                        )
                    else:  # ALARM
                        message = (
                            f"⚠️ FLOOD ALARM: {station_name} water level is at "
                            f"{water_level:.2f}m (ALARM level). "
                            f"Prepare for possible evacuation."
                        )

                    await self.broadcast_critical_alert(
                        station_name=station_name,
                        water_level=water_level,
                        risk_level=risk_level,
                        message_text=message
                    )

            # Clear from critical set if level drops below ALARM
            elif risk_level in ["NORMAL", "ALERT"]:
                # Remove all critical/alarm entries for this station
                to_remove = {
                    key for key in self.critical_stations
                    if key.startswith(station_name)
                }
                self.critical_stations -= to_remove


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

# Include API routers
app.include_router(graph_router)

# --- 3. Initialize Multi-Agent System ---

logger.info("Initializing MAS-FRO Multi-Agent System...")

# Initialize environment
environment = DynamicGraphEnvironment()

# Set environment for graph API routes
set_graph_environment(environment)

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

# Initialize FloodAgent scheduler (5-minute intervals) with WebSocket broadcasting
flood_scheduler = FloodDataScheduler(
    flood_agent,
    interval_seconds=300,
    ws_manager=ws_manager
)
set_scheduler(flood_scheduler)

# Initialize Simulation Manager
simulation_manager = get_simulation_manager()

logger.info("MAS-FRO system initialized successfully")

# --- 3.5. Startup and Shutdown Events ---

@app.on_event("startup")
async def startup_event():
    """Start background tasks on application startup."""
    # Initialize logging system (ensure logs directory exists)
    setup_logging()
    logger.info("="*60)
    logger.info("MAS-FRO Backend Starting Up")
    logger.info("="*60)
    logger.info("Structured logging initialized - logs written to logs/masfro.log")
    
    # Check database connection
    logger.info("Checking database connection...")
    if check_connection():
        logger.info("Database connection successful")
        # Initialize database tables (if not exist)
        init_db()
    else:
        logger.error("Database connection failed - historical data storage disabled")

    # Start scheduler
    logger.info("Starting background scheduler...")
    scheduler = get_scheduler()
    if scheduler:
        await scheduler.start()
        logger.info("Automated flood data collection started (every 5 minutes)")
    else:
        logger.warning("Scheduler not initialized")


@app.on_event("shutdown")
async def shutdown_event():
    """Stop background tasks on application shutdown."""
    logger.info("="*60)
    logger.info("MAS-FRO Backend Shutting Down")
    logger.info("="*60)
    logger.info("Stopping background scheduler...")
    scheduler = get_scheduler()
    if scheduler:
        await scheduler.stop()
        logger.info("Scheduler stopped gracefully")
    logger.info("MAS-FRO backend shutdown complete")


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

@app.post("/api/admin/geotiff/enable", tags=["Admin"])
async def enable_geotiff_simulation():
    """
    Enable GeoTIFF flood simulation in HazardAgent.

    When enabled, risk calculations will include spatial flood depth data
    from GeoTIFF files (50% weight).
    """
    logger.info("GeoTIFF simulation enable request received")

    try:
        hazard_agent.enable_geotiff()

        return {
            "status": "success",
            "message": "GeoTIFF flood simulation enabled",
            "geotiff_enabled": hazard_agent.is_geotiff_enabled(),
            "return_period": hazard_agent.return_period,
            "time_step": hazard_agent.time_step
        }

    except Exception as e:
        logger.error(f"Error enabling GeoTIFF: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error enabling GeoTIFF simulation: {str(e)}"
        )

@app.post("/api/admin/geotiff/disable", tags=["Admin"])
async def disable_geotiff_simulation():
    """
    Disable GeoTIFF flood simulation in HazardAgent.

    When disabled, risk calculations will only use FloodAgent (PAGASA + OpenWeatherMap)
    and ScoutAgent data (50% environmental weight).
    """
    logger.info("GeoTIFF simulation disable request received")

    try:
        hazard_agent.disable_geotiff()

        return {
            "status": "success",
            "message": "GeoTIFF flood simulation disabled",
            "geotiff_enabled": hazard_agent.is_geotiff_enabled(),
            "note": "Risk calculation now uses only FloodAgent and ScoutAgent data"
        }

    except Exception as e:
        logger.error(f"Error disabling GeoTIFF: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error disabling GeoTIFF simulation: {str(e)}"
        )

@app.get("/api/admin/geotiff/status", tags=["Admin"])
async def get_geotiff_status():
    """
    Get current GeoTIFF simulation status and configuration.

    Returns information about whether GeoTIFF is enabled, current scenario,
    and flood prediction parameters.
    """
    try:
        return {
            "status": "success",
            "geotiff_enabled": hazard_agent.is_geotiff_enabled(),
            "geotiff_service_available": hazard_agent.geotiff_service is not None,
            "current_scenario": {
                "return_period": hazard_agent.return_period,
                "time_step": hazard_agent.time_step,
                "description": {
                    "rr01": "2-year flood",
                    "rr02": "5-year flood",
                    "rr03": "10-year flood",
                    "rr04": "25-year flood"
                }.get(hazard_agent.return_period, "unknown")
            },
            "risk_weights": hazard_agent.risk_weights
        }

    except Exception as e:
        logger.error(f"Error getting GeoTIFF status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting GeoTIFF status: {str(e)}"
        )

@app.post("/api/admin/geotiff/set-scenario", tags=["Admin"])
async def set_flood_scenario(
    return_period: str,
    time_step: int
):
    """
    Set the flood scenario for GeoTIFF simulation.

    Args:
        return_period: Return period (rr01, rr02, rr03, rr04)
            - rr01: 2-year flood
            - rr02: 5-year flood
            - rr03: 10-year flood
            - rr04: 25-year flood
        time_step: Time step in hours (1-18)

    Example:
        POST /api/admin/geotiff/set-scenario?return_period=rr04&time_step=18
    """
    logger.info(f"Flood scenario change request: {return_period}, step {time_step}")

    try:
        # Set the scenario
        hazard_agent.set_flood_scenario(return_period, time_step)

        # Trigger immediate update to apply new scenario
        data = flood_agent.collect_and_forward_data()

        return {
            "status": "success",
            "message": f"Flood scenario updated to {return_period} step {time_step}",
            "scenario": {
                "return_period": hazard_agent.return_period,
                "time_step": hazard_agent.time_step,
                "description": {
                    "rr01": "2-year flood",
                    "rr02": "5-year flood",
                    "rr03": "10-year flood",
                    "rr04": "25-year flood"
                }.get(return_period, "unknown")
            },
            "update_triggered": True,
            "locations_updated": len(data) if data else 0
        }

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error setting flood scenario: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error setting flood scenario: {str(e)}"
        )


# ============================================================================
# Simulation Control Endpoints
# ============================================================================

@app.post("/api/simulation/start", tags=["Simulation"])
async def start_simulation(
    mode: str = Query(
        "light",
        description="Simulation mode: light, medium, or heavy"
    )
):
    """
    Start the simulation with specified flood scenario mode.

    Args:
        mode: Simulation mode (light, medium, heavy)
            - light: < 0.5m depth, low risk areas
            - medium: 0.5m - 1.0m depth, moderate risk
            - heavy: > 1.0m depth, high risk zones

    Returns:
        Simulation start result with state information

    Example:
        POST /api/simulation/start?mode=medium
    """
    logger.info(f"Simulation start request received - Mode: {mode}")

    try:
        sim_manager = get_simulation_manager()
        result = sim_manager.start(mode=mode)

        # Broadcast simulation state change via WebSocket
        await ws_manager.broadcast({
            "type": "simulation_state",
            "event": "started",
            "data": result,
            "timestamp": datetime.now().isoformat()
        })

        logger.info(
            f"Simulation started successfully - "
            f"Mode: {result['mode']}, State: {result['state']}"
        )

        return result

    except ValueError as e:
        logger.warning(f"Invalid simulation start request: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error starting simulation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error starting simulation: {str(e)}"
        )


@app.post("/api/simulation/stop", tags=["Simulation"])
async def stop_simulation():
    """
    Stop (pause) the currently running simulation.

    This endpoint pauses the simulation and stops data input processing.
    The simulation state is preserved and can be resumed with start.

    Returns:
        Simulation stop result with runtime information

    Example:
        POST /api/simulation/stop
    """
    logger.info("Simulation stop request received")

    try:
        sim_manager = get_simulation_manager()
        result = sim_manager.stop()

        # Broadcast simulation state change via WebSocket
        await ws_manager.broadcast({
            "type": "simulation_state",
            "event": "stopped",
            "data": result,
            "timestamp": datetime.now().isoformat()
        })

        logger.info(
            f"Simulation stopped successfully - "
            f"Runtime: {result['total_runtime_seconds']}s"
        )

        return result

    except ValueError as e:
        logger.warning(f"Invalid simulation stop request: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error stopping simulation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error stopping simulation: {str(e)}"
        )


@app.post("/api/simulation/reset", tags=["Simulation"])
async def reset_simulation():
    """
    Reset the simulation to initial state.

    This endpoint:
    - Resets simulation state to STOPPED
    - Clears all simulation data
    - Resets runtime counters
    - Resets mode to LIGHT
    - Clears graph risk scores (resets to baseline)

    Returns:
        Simulation reset result with previous state information

    Example:
        POST /api/simulation/reset
    """
    logger.info("Simulation reset request received")

    try:
        sim_manager = get_simulation_manager()
        result = sim_manager.reset()

        # Reset graph to baseline (clear all risk scores)
        if environment.graph:
            logger.info("Resetting graph risk scores to baseline")
            # Reset all edge risk scores to 0.0
            for u, v, key in environment.graph.edges(keys=True):
                environment.graph[u][v][key]["risk_score"] = 0.0
            logger.info(f"Reset {environment.graph.number_of_edges()} edges to baseline risk")

        # Broadcast simulation state change via WebSocket
        await ws_manager.broadcast({
            "type": "simulation_state",
            "event": "reset",
            "data": result,
            "timestamp": datetime.now().isoformat()
        })

        logger.info(
            f"Simulation reset successfully - "
            f"Previous state: {result['previous_state']}, "
            f"Previous runtime: {result['previous_runtime_seconds']}s"
        )

        return result

    except Exception as e:
        logger.error(f"Error resetting simulation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error resetting simulation: {str(e)}"
        )


@app.get("/api/simulation/status", tags=["Simulation"])
async def get_simulation_status():
    """
    Get current simulation status and state.

    Returns comprehensive information about:
    - Current state (stopped, running, paused)
    - Current mode (light, medium, heavy)
    - Runtime statistics
    - Start/pause timestamps

    Returns:
        Complete simulation status information

    Example:
        GET /api/simulation/status
    """
    try:
        sim_manager = get_simulation_manager()
        status = sim_manager.get_status()

        return {
            "status": "success",
            "simulation": status,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error retrieving simulation status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving simulation status: {str(e)}"
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


# --- 5. Historical Flood Data Endpoints ---

@app.get("/api/flood-data/latest", tags=["Flood Data History"])
async def get_latest_flood_data(db: Session = Depends(get_db)):
    """
    Get the most recent flood data collection.

    Returns the latest flood data including river levels and weather conditions.
    """
    try:
        repo = FloodDataRepository(db)
        collection = repo.get_latest_collection()

        if not collection:
            raise HTTPException(
                status_code=404,
                detail="No flood data collections found"
            )

        return {
            "collection_id": str(collection.id),
            "collected_at": collection.collected_at.isoformat(),
            "data_source": collection.data_source,
            "success": collection.success,
            "duration_seconds": collection.duration_seconds,
            "river_stations_count": collection.river_stations_count,
            "weather_data_available": collection.weather_data_available,
            "river_levels": [
                {
                    "station_name": river.station_name,
                    "water_level": river.water_level,
                    "risk_level": river.risk_level,
                    "alert_level": river.alert_level,
                    "alarm_level": river.alarm_level,
                    "critical_level": river.critical_level,
                }
                for river in collection.river_levels
            ],
            "weather_data": {
                "rainfall_1h": collection.weather_data.rainfall_1h if collection.weather_data else None,
                "rainfall_24h_forecast": collection.weather_data.rainfall_24h_forecast if collection.weather_data else None,
                "intensity": collection.weather_data.intensity if collection.weather_data else None,
                "temperature": collection.weather_data.temperature if collection.weather_data else None,
                "humidity": collection.weather_data.humidity if collection.weather_data else None,
            } if collection.weather_data else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving latest flood data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving flood data: {str(e)}"
        )


@app.get("/api/flood-data/history", tags=["Flood Data History"])
async def get_flood_data_history(
    hours: int = 24,
    success_only: bool = True,
    db: Session = Depends(get_db)
):
    """
    Get historical flood data collections within a time range.

    Args:
        hours: Number of hours of history (default: 24)
        success_only: Only return successful collections (default: True)

    Returns:
        List of flood data collections
    """
    try:
        repo = FloodDataRepository(db)
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)

        collections = repo.get_collections_in_range(
            start_time=start_time,
            end_time=end_time,
            success_only=success_only
        )

        return {
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "hours": hours
            },
            "total_collections": len(collections),
            "collections": [
                {
                    "collection_id": str(c.id),
                    "collected_at": c.collected_at.isoformat(),
                    "success": c.success,
                    "duration_seconds": c.duration_seconds,
                    "river_stations_count": c.river_stations_count,
                    "weather_data_available": c.weather_data_available,
                    "error_message": c.error_message if not c.success else None
                }
                for c in collections
            ]
        }

    except Exception as e:
        logger.error(f"Error retrieving flood data history: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving history: {str(e)}"
        )


@app.get("/api/flood-data/river/{station_name}/history", tags=["Flood Data History"])
async def get_river_level_history(
    station_name: str,
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """
    Get historical water levels for a specific river station.

    Args:
        station_name: Name of the river station
        hours: Number of hours of history (default: 24)

    Returns:
        Historical river level data
    """
    try:
        repo = FloodDataRepository(db)
        river_levels = repo.get_river_level_history(
            station_name=station_name,
            hours=hours
        )

        if not river_levels:
            raise HTTPException(
                status_code=404,
                detail=f"No data found for station '{station_name}'"
            )

        return {
            "station_name": station_name,
            "time_range_hours": hours,
            "data_points": len(river_levels),
            "history": [
                {
                    "recorded_at": river.recorded_at.isoformat(),
                    "water_level": river.water_level,
                    "risk_level": river.risk_level,
                    "alert_level": river.alert_level,
                    "alarm_level": river.alarm_level,
                    "critical_level": river.critical_level,
                }
                for river in river_levels
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving river level history: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving river history: {str(e)}"
        )


@app.get("/api/flood-data/critical-alerts", tags=["Flood Data History"])
async def get_critical_alerts(
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """
    Get history of critical water level alerts (ALARM and CRITICAL levels).

    Args:
        hours: Number of hours of history (default: 24)

    Returns:
        List of critical alerts
    """
    try:
        repo = FloodDataRepository(db)
        alerts = repo.get_critical_alerts_history(hours=hours)

        return {
            "time_range_hours": hours,
            "total_alerts": len(alerts),
            "critical_alerts": [
                {
                    "station_name": alert.station_name,
                    "recorded_at": alert.recorded_at.isoformat(),
                    "water_level": alert.water_level,
                    "risk_level": alert.risk_level,
                    "critical_level": alert.critical_level,
                    "severity": "CRITICAL" if alert.risk_level == "CRITICAL" else "ALARM"
                }
                for alert in alerts
            ]
        }

    except Exception as e:
        logger.error(f"Error retrieving critical alerts: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving alerts: {str(e)}"
        )


@app.get("/api/flood-data/statistics", tags=["Flood Data History"])
async def get_database_statistics(
    days: int = 7,
    db: Session = Depends(get_db)
):
    """
    Get summary statistics for historical flood data.

    Args:
        days: Number of days for statistics (default: 7)

    Returns:
        Database statistics including collection counts and success rates
    """
    try:
        repo = FloodDataRepository(db)
        stats = repo.get_statistics(days=days)

        return {
            "status": "success",
            "statistics": stats
        }

    except Exception as e:
        logger.error(f"Error retrieving database statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving statistics: {str(e)}"
        )


# ============================================================================
# GeoTIFF Flood Map Endpoints
# ============================================================================

@app.get("/api/geotiff/available-maps")
async def get_available_flood_maps():
    """
    Get list of all available GeoTIFF flood maps.

    Returns list of available return periods and time steps.
    """
    try:
        from app.services.geotiff_service import get_geotiff_service

        service = get_geotiff_service()
        maps = service.get_available_maps()

        return {
            "status": "success",
            "total_maps": len(maps),
            "maps": maps,
            "return_periods": service.return_periods,
            "time_steps": service.time_steps
        }

    except Exception as e:
        logger.error(f"Error getting available maps: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving available maps: {str(e)}"
        )


@app.get("/api/geotiff/flood-map")
async def get_flood_map(
    return_period: str = Query(
        "rr01",
        description="Return period (rr01, rr02, rr03, rr04)"
    ),
    time_step: int = Query(
        1,
        ge=1,
        le=18,
        description="Time step (1-18 hours)"
    )
):
    """
    Get flood map metadata for specific return period and time step.

    Returns bounds, statistics, and metadata but not the full raster data.
    Use /api/geotiff/tiff endpoint to get the actual TIFF file.
    """
    try:
        from app.services.geotiff_service import get_geotiff_service

        service = get_geotiff_service()
        data, metadata = service.load_flood_map(return_period, time_step)

        return {
            "status": "success",
            "metadata": metadata,
            "note": "Use /api/geotiff/tiff endpoint to download the actual TIFF file"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting flood map: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving flood map: {str(e)}"
        )


@app.get("/api/geotiff/flood-depth")
async def get_flood_depth_at_point(
    lon: float = Query(..., description="Longitude (WGS84)"),
    lat: float = Query(..., description="Latitude (WGS84)"),
    return_period: str = Query(
        "rr01",
        description="Return period (rr01, rr02, rr03, rr04)"
    ),
    time_step: int = Query(
        1,
        ge=1,
        le=18,
        description="Time step (1-18 hours)"
    )
):
    """
    Get flood depth at a specific coordinate.

    Useful for checking flood depth at a specific location without
    downloading the entire TIFF file.
    """
    try:
        from app.services.geotiff_service import get_geotiff_service

        service = get_geotiff_service()
        depth = service.get_flood_depth_at_point(
            lon, lat, return_period, time_step
        )

        if depth is None:
            return {
                "status": "success",
                "lon": lon,
                "lat": lat,
                "return_period": return_period,
                "time_step": time_step,
                "flood_depth": None,
                "message": "No flood depth data at this location (out of bounds or no data)"
            }

        return {
            "status": "success",
            "lon": lon,
            "lat": lat,
            "return_period": return_period,
            "time_step": time_step,
            "flood_depth": depth,
            "flood_depth_cm": round(depth * 100, 2),
            "is_flooded": depth > 0.01  # >1cm threshold
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error querying flood depth: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error querying flood depth: {str(e)}"
        )


@app.get("/data/timed_floodmaps/{return_period}/{filename}")
async def serve_geotiff_file(return_period: str, filename: str):
    """
    Serve GeoTIFF files directly for frontend visualization.

    Example: /data/timed_floodmaps/rr01/rr01-1.tif
    """
    from fastapi.responses import FileResponse
    from pathlib import Path

    # Validate return period
    valid_periods = ["rr01", "rr02", "rr03", "rr04"]
    if return_period not in valid_periods:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid return period. Valid: {valid_periods}"
        )

    # Validate filename pattern
    if not filename.endswith(".tif") or not filename.startswith(return_period):
        raise HTTPException(
            status_code=400,
            detail="Invalid filename format"
        )

    file_path = Path(f"app/data/timed_floodmaps/{return_period}/{filename}")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=file_path,
        media_type="image/tiff",
        filename=filename
    )

