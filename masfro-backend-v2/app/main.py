# filename: masfro-backend-v2/main.py

"""
FastAPI Backend for Multi-Agent System for Flood Route Optimization (MAS-FRO) v2

This is the main entry point for the MAS-FRO backend API. It initializes all
agents in the multi-agent system and provides REST API endpoints for route
requests and system monitoring.

v2 Enhancements:
- Qwen 3 LLM integration for enhanced text understanding
- Qwen 3-VL vision model for flood image analysis
- /api/llm/health endpoint for LLM status monitoring
- Visual Override logic in HazardAgent

Author: MAS-FRO Development Team
Date: February 2026
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, Query
from pydantic import BaseModel, field_validator
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
import pandas as pd

# Agent imports
from app.environment.graph_manager import DynamicGraphEnvironment
from app.agents.flood_agent import FloodAgent
from app.agents.scout_agent import ScoutAgent
from app.agents.hazard_agent import HazardAgent
from app.agents.evacuation_manager_agent import EvacuationManagerAgent
from app.agents.routing_agent import RoutingAgent
from app.agents.orchestrator_agent import OrchestratorAgent

# No direct algorithm imports needed - RoutingAgent handles all pathfinding

# Communication imports
from app.communication.message_queue import MessageQueue
from app.communication.acl_protocol import ACLMessage, Performative

# Scheduler imports
from app.services.flood_data_scheduler import FloodDataScheduler, set_scheduler, get_scheduler

# Simulation Manager imports
from app.services.simulation_manager import get_simulation_manager, SimulationManager

# Agent Lifecycle Manager imports
from app.services.agent_lifecycle_manager import (
    AgentLifecycleManager,
    set_lifecycle_manager,
    get_lifecycle_manager
)

# LLM Service
from app.services.llm_service import LLMService, get_llm_service

# Database imports
from app.database import get_db, FloodDataRepository, check_connection, init_db

# Logging and configuration
from app.core.logging_config import setup_logging, get_logger
from app.core.config import settings
from app.core.auth import verify_api_key

# Agent Viewer Service
from app.services.agent_viewer_service import get_agent_viewer_service
from app.api.agent_viewer_endpoints import router as agent_viewer_router

# API Routes
# API Routes
from app.api import graph_router, set_graph_environment, evacuation_router
from app.models.requests import RouteRequest, FeedbackRequest
from app.models.responses import RouteResponse

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

# --- 1. Data Models (using Pydantic) ---
# Models are imported from app.models.requests and app.models.responses
# See imports at top of file


# --- 2. FastAPI Application Setup ---

app = FastAPI(
    title="MAS-FRO API",
    description="Multi-Agent System for Flood Route Optimization API",
    version="2.0.0"
)

# CORS configuration - Explicit whitelist only
origins = settings.ALLOWED_ORIGINS.split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Explicit whitelist only
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    max_age=3600
)

# Serve static files (flood maps, data)
app.mount("/data", StaticFiles(directory="app/data"), name="data")
# Mount Agent Viewer Dashboard
import os
os.makedirs("app/static/agent_viewer", exist_ok=True)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include API routers
app.include_router(graph_router)
app.include_router(evacuation_router)
app.include_router(agent_viewer_router, prefix="/api/v1")

# --- 3. Initialize Multi-Agent System ---

logger.info("Initializing MAS-FRO Multi-Agent System...")

# Initialize environment
environment = DynamicGraphEnvironment()

# Set environment for graph API routes
set_graph_environment(environment)

# Initialize message queue for agent communication
message_queue = MessageQueue()

# Initialize agents with MessageQueue for MAS communication
hazard_agent = HazardAgent(
    "hazard_agent_001",
    environment,
    message_queue=message_queue,  # MAS communication
    enable_geotiff=True
)

# FloodAgent with REAL API integration and MAS communication
flood_agent = FloodAgent(
    "flood_agent_001",
    environment,
    message_queue=message_queue,  # MAS communication
    use_simulated=False,  # Disable simulated data
    use_real_apis=True,   # Enable PAGASA + OpenWeatherMap
    hazard_agent_id="hazard_agent_001"  # Target agent for messages
)

routing_agent = RoutingAgent(
    "routing_agent_001",
    environment,
    message_queue=message_queue,
    llm_service=get_llm_service()
)
evacuation_manager = EvacuationManagerAgent(
    "evac_manager_001",
    environment,
    message_queue=message_queue,
    hazard_agent_id="hazard_agent_001",
    llm_service=get_llm_service()
)

# Load mock sources config for ScoutAgent scraper mode
try:
    from app.core.agent_config import AgentConfigLoader as _acl
    _mock_cfg = _acl().get_mock_sources_config()
    _scout_use_scraper = _mock_cfg.enabled
    _scout_scraper_url = _mock_cfg.base_url
except Exception:
    _scout_use_scraper = False
    _scout_scraper_url = "http://localhost:8081"

# ScoutAgent in simulation mode with MAS communication
# For simulation: uses synthetic data with ML processing enabled
# When mock_sources.enabled=true, switches to live scraper mode
scout_agent = ScoutAgent(
    "scout_agent_001",
    environment,
    message_queue=message_queue,    # MAS communication
    hazard_agent_id="hazard_agent_001",  # Target agent for messages
    simulation_scenario=1,          # Light scenario
    use_ml_in_simulation=True,      # Enable ML models for prediction
    use_scraper=_scout_use_scraper,
    scraper_base_url=_scout_scraper_url
)

# NOTE: FloodAgent, HazardAgent, ScoutAgent, and EvacuationManager now communicate via MessageQueue (MAS architecture)
# Direct agent references removed - all communication through MessageQueue
# EvacuationManager → HazardAgent: Uses MessageQueue
# EvacuationManager → RoutingAgent: Still uses direct reference (routing is synchronous, not message-based)
evacuation_manager.set_routing_agent(routing_agent)

# Initialize FloodAgent scheduler (5-minute intervals) with WebSocket broadcasting
# NOTE: FloodAgent sends data to HazardAgent via MessageQueue (MAS architecture)
# HazardAgent.step() is called by AgentLifecycleManager to process messages
flood_scheduler = FloodDataScheduler(
    flood_agent,
    interval_seconds=300,
    ws_manager=ws_manager
)
set_scheduler(flood_scheduler)

# Initialize Simulation Manager
simulation_manager = get_simulation_manager()
simulation_manager.set_agents(
    flood_agent=flood_agent,
    scout_agent=scout_agent,
    hazard_agent=hazard_agent,
    routing_agent=routing_agent,
    evacuation_manager=evacuation_manager,
    environment=environment,
    ws_manager=ws_manager
)

# --- Initialize ORCHESTRATOR (The Boss) ---
sub_agents = {
    'scout': scout_agent,
    'flood': flood_agent,
    'routing': routing_agent,
    'evacuation': evacuation_manager,
    'hazard': hazard_agent
}
orchestrator_llm = get_llm_service()
orchestrator_agent = OrchestratorAgent(
    "orchestrator_main", environment, message_queue, sub_agents,
    llm_service=orchestrator_llm
)
logger.info("Orchestrator Agent initialized with MQ support, LLM brain, and all sub-agents")

# Register agents with the viewer service so endpoints can access them without circular imports
get_agent_viewer_service().register_agents(sub_agents)

# --- Initialize Agent Lifecycle Manager ---
# This service periodically calls step() on agents to process MessageQueue messages
# Solves the "Dormant Agent" problem where messages were sent but never processed
# All agents are now registered so they can process orchestrator REQUEST messages
agent_lifecycle_manager = AgentLifecycleManager(
    tick_interval_seconds=1.0,  # 1 Hz - call step() every second
    simulation_manager=simulation_manager  # Pauses when simulation is running
)
agent_lifecycle_manager.register_agent(orchestrator_agent, priority=0)  # Orchestrator runs first
agent_lifecycle_manager.register_agent(hazard_agent, priority=1)        # HazardAgent processes messages
agent_lifecycle_manager.register_agent(scout_agent, priority=2)         # ScoutAgent handles requests
agent_lifecycle_manager.register_agent(flood_agent, priority=3)         # FloodAgent handles requests
agent_lifecycle_manager.register_agent(routing_agent, priority=4)       # RoutingAgent handles requests
agent_lifecycle_manager.register_agent(evacuation_manager, priority=5)  # EvacManager handles requests
set_lifecycle_manager(agent_lifecycle_manager)
logger.info("AgentLifecycleManager initialized with all 6 agents")

logger.info("MAS-FRO system initialized successfully")

# --- 3.5. Startup and Shutdown Events ---

@app.on_event("startup")
async def startup_event():
    """Start background tasks on application startup."""
    # Initialize logging system (ensure logs directory exists)
    setup_logging()

    # Re-attach Agent Viewer Logging Handler (must be AFTER setup_logging
    # because dictConfig replaces handlers)
    get_agent_viewer_service().setup_logging()
    
    logger.info("="*60)
    logger.info("MAS-FRO Backend Starting Up")
    logger.info("="*60)
    logger.info("Structured logging initialized - logs written to logs/masfro.log")
    
    # Check database connection (optional - app works without it)
    logger.info("Checking database connection...")
    try:
        if check_connection():
            logger.info("Database connection successful")
            # Initialize database tables (if not exist)
            init_db()
        else:
            logger.warning("Database connection failed - historical data storage disabled")
    except Exception as e:
        logger.warning(f"Database unavailable: {e} - continuing without database")

    # Load initial flood data to populate risk scores
    logger.info("Loading initial flood risk data...")
    try:
        # Load default GeoTIFF data (light scenario, time step 1)
        from pathlib import Path
        geotiff_path = Path(__file__).parent / "data" / "timed_floodmaps" / "rr01" / "rr01-1.tif"

        if geotiff_path.exists() and hazard_agent:
            logger.info(f"Loading initial risk data from {geotiff_path}")

            # Process GeoTIFF to get flood data
            import rasterio
            with rasterio.open(geotiff_path) as src:
                flood_array = src.read(1)
                transform = src.transform

            # Convert to edge risk scores (simplified version)
            edge_updates = {}
            for u, v, key, data in environment.graph.edges(keys=True, data=True):
                # Get edge midpoint coordinates
                u_coords = environment.graph.nodes[u]
                v_coords = environment.graph.nodes[v]
                mid_lat = (u_coords['y'] + v_coords['y']) / 2
                mid_lon = (u_coords['x'] + v_coords['x']) / 2

                # Sample flood depth at edge location
                row, col = ~transform * (mid_lon, mid_lat)
                row, col = int(row), int(col)

                if 0 <= row < flood_array.shape[0] and 0 <= col < flood_array.shape[1]:
                    flood_depth = float(flood_array[row, col])
                    # Convert depth to risk score (0-1)
                    if flood_depth < 0.1:
                        risk_score = 0.0
                    elif flood_depth < 0.5:
                        risk_score = 0.3
                    elif flood_depth < 1.0:
                        risk_score = 0.6
                    elif flood_depth < 2.0:
                        risk_score = 0.8
                    else:
                        risk_score = 0.95  # Near impassable

                    edge_updates[(u, v, key)] = risk_score

            # Apply updates to graph (using individual method, consistent with HazardAgent)
            for (u, v, key), risk in edge_updates.items():
                environment.update_edge_risk(u, v, key, risk)
            logger.info(f"Initial flood data loaded: Updated {len(edge_updates)} edges with risk scores")

            # Log sample of high-risk edges
            high_risk_count = sum(1 for risk in edge_updates.values() if risk >= 0.7)
            logger.info(f"High-risk edges (>= 70%): {high_risk_count}")

        else:
            logger.warning(f"GeoTIFF data not found at {geotiff_path} - graph will start with zero risk")

    except Exception as e:
        logger.error(f"Failed to load initial flood data: {e}")
        logger.warning("Continuing with zero risk scores - all roads passable")

    # Start scheduler
    logger.info("Starting background scheduler...")
    scheduler = get_scheduler()
    if scheduler:
        await scheduler.start()
        logger.info("Automated flood data collection started (every 5 minutes)")
    else:
        logger.warning("Scheduler not initialized")

    # Start agent lifecycle manager
    logger.info("Starting agent lifecycle manager...")
    lifecycle_manager = get_lifecycle_manager()
    if lifecycle_manager:
        await lifecycle_manager.start()
        logger.info("Agent lifecycle manager started (1 Hz tick rate)")
    else:
        logger.warning("Agent lifecycle manager not initialized")


@app.on_event("shutdown")
async def shutdown_event():
    """Stop background tasks on application shutdown."""
    logger.info("="*60)
    logger.info("MAS-FRO Backend Shutting Down")
    logger.info("="*60)

    # Stop agent lifecycle manager first (so it doesn't process during shutdown)
    logger.info("Stopping agent lifecycle manager...")
    lifecycle_manager = get_lifecycle_manager()
    if lifecycle_manager:
        await lifecycle_manager.stop()
        logger.info("Agent lifecycle manager stopped gracefully")

    # Stop scheduler
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
        "version": "2.0.0",
        "status": "operational"
    }

@app.get("/api/health", tags=["General"])
async def health_check():
    """System health check."""
    graph_status = "loaded" if environment.graph else "not_loaded"

    # v2: Include LLM status
    llm_status = "unknown"
    try:
        from app.services.llm_service import get_llm_service
        llm_service = get_llm_service()
        llm_status = "available" if llm_service.is_available() else "unavailable"
    except Exception:
        llm_status = "not_configured"

    return {
        "status": "healthy",
        "version": "2.0.0",
        "graph_status": graph_status,
        "llm_status": llm_status,
        "agents": {
            "flood_agent": "active" if flood_agent else "inactive",
            "hazard_agent": "active" if hazard_agent else "inactive",
            "routing_agent": "active" if routing_agent else "inactive",
            "evacuation_manager": "active" if evacuation_manager else "inactive"
        }
    }


@app.get("/api/llm/health", tags=["LLM"])
async def llm_health_check():
    """
    LLM Service health check endpoint.

    Returns detailed information about the Qwen 3 LLM integration status,
    including model availability and cache statistics.

    Returns:
        Dict with LLM health information
    """
    try:
        from app.services.llm_service import get_llm_service
        llm_service = get_llm_service()
        return llm_service.get_health()
    except ImportError:
        return {
            "available": False,
            "error": "LLM service module not found",
            "ollama_installed": False
        }
    except Exception as e:
        return {
            "available": False,
            "error": str(e)
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

        # Merged preferences logic
        final_preferences = request.preferences or {}
        
        # 1. Smart Parsing: If query is present, extract preferences
        if request.query:
            try:
                smart_prefs = routing_agent.parse_routing_request(request.query)
                if smart_prefs:
                    logger.info(f"Smart preferences parsed from query '{request.query}': {smart_prefs}")
                    # Merge smart prefs (user explicit prefs override smart prefs if conflict)
                    final_preferences = {**smart_prefs, **final_preferences}
            except Exception as e:
                logger.warning(f"Failed to parse smart routing request: {e}")

        # Use RoutingAgent to calculate route
        route_result = routing_agent.calculate_route(
            start=request.start_location,
            end=request.end_location,
            preferences=final_preferences
        )

        if not route_result.get("path"):
            raise HTTPException(
                status_code=404,
                detail="No safe route found between these locations."
            )

        # 2. Smart Explanation: Generate explanation if LLM is available
        explanation = None
        if request.query or final_preferences:
            try:
                explanation = routing_agent.explain_route(route_result)
            except Exception as e:
                logger.warning(f"Failed to generate route explanation: {e}")

        # Generate route ID
        import uuid
        route_id = str(uuid.uuid4())

        # Serialize warnings: convert RouteWarning objects to dicts
        raw_warnings = route_result.get("warnings", [])
        serialized_warnings = []
        for w in raw_warnings:
            if hasattr(w, 'to_dict'):
                serialized_warnings.append(w.to_dict())
            elif hasattr(w, 'to_legacy_string'):
                serialized_warnings.append(w.to_legacy_string())
            else:
                serialized_warnings.append(str(w))

        return RouteResponse(
            route_id=route_id,
            status="success",
            path=route_result["path"],
            distance=route_result.get("distance"),
            estimated_time=route_result.get("estimated_time"),
            risk_level=route_result.get("risk_level"),
            max_risk=route_result.get("max_risk"),
            num_segments=route_result.get("num_segments"),
            warnings=serialized_warnings,
            explanation=explanation
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

class EvacuationCenterRequest(BaseModel):
    location: List[float]

@app.post("/api/evacuation-center", tags=["Routing"])
async def get_nearest_evacuation_center(request: EvacuationCenterRequest):
    """
    Find nearest evacuation center and calculate route.

    Returns the closest safe evacuation center with route information.
    """
    location = tuple(request.location)
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

        import json, math

        def _sanitize(obj):
            if isinstance(obj, float):
                return None if (math.isnan(obj) or math.isinf(obj)) else obj
            if isinstance(obj, dict):
                return {k: _sanitize(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_sanitize(v) for v in obj]
            return obj

        return _sanitize({
            "status": "success",
            "evacuation_center": result["center"],
            "route": {
                "path": result["path"],
                "distance": result["metrics"]["total_distance"],
                "estimated_time": result["metrics"]["estimated_time"],
                "risk_level": result["metrics"]["average_risk"]
            },
            "alternatives": result.get("alternatives", [])
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Evacuation center lookup error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error finding evacuation center: {str(e)}"
        )

# --- ORCHESTRATOR API ---

class MissionRequest(BaseModel):
    mission_type: str
    params: Dict[str, Any]

@app.post("/api/orchestrator/mission", tags=["Orchestrator"])
async def create_orchestrator_mission(request: MissionRequest):
    """
    Start a new orchestrator mission via MQ-based coordination.

    Creates a mission with a state machine that coordinates sub-agents
    via MessageQueue. Returns a mission_id for status polling.

    Mission types:
    - assess_risk: Scout -> Flood -> Hazard pipeline
    - coordinated_evacuation: Evacuation Manager handles distress call
    - route_calculation: Routing Agent calculates a route
    - cascade_risk_update: Flood -> Hazard data refresh
    """
    if not orchestrator_agent:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    try:
        result = orchestrator_agent.start_mission(
            request.mission_type,
            request.params
        )
        return result
    except Exception as e:
        logger.error(f"Orchestrator mission creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/orchestrator/command", tags=["Orchestrator"])
async def send_orchestrator_command(request: MissionRequest):
    """
    Start a mission (legacy endpoint, redirects to /api/orchestrator/mission).
    """
    return await create_orchestrator_mission(request)

@app.get("/api/orchestrator/mission/{mission_id}", tags=["Orchestrator"])
async def get_orchestrator_mission_status(mission_id: str):
    """
    Check the status of an orchestrator mission.

    Poll this endpoint after creating a mission to track progress.
    Missions transition through states like AWAITING_SCOUT -> AWAITING_FLOOD -> COMPLETED.
    """
    if not orchestrator_agent:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    status = orchestrator_agent.get_mission_status(mission_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Mission {mission_id} not found")
    return status

@app.get("/api/orchestrator/missions", tags=["Orchestrator"])
async def list_orchestrator_missions():
    """List all orchestrator missions (active and recently completed)."""
    if not orchestrator_agent:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    active = orchestrator_agent.get_active_missions()
    completed = [
        orchestrator_agent._mission_to_dict(m)
        for m in orchestrator_agent._completed_missions
    ]
    return {"active": active, "completed": completed}


class ChatRequest(BaseModel):
    message: str

    @field_validator("message")
    @classmethod
    def message_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Message must not be empty")
        return v.strip()

@app.post("/api/orchestrator/chat", tags=["Orchestrator"])
async def orchestrator_chat(request: ChatRequest):
    """
    Natural language interface to the orchestrator.

    Send a message in plain language and the LLM will interpret it,
    create the appropriate mission, and return tracking info.

    Examples:
    - "Is it safe to travel from Tumana to Concepcion?"
    - "Check the flood risk in Barangay Nangka"
    - "I need to evacuate from Malanday, the water is rising!"
    - "Update the flood data"
    """
    if not orchestrator_agent:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    try:
        result = await asyncio.to_thread(
            orchestrator_agent.chat_and_execute, request.message
        )
        return result
    except Exception as e:
        logger.error(f"Orchestrator chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/orchestrator/mission/{mission_id}/summary", tags=["Orchestrator"])
async def get_mission_summary(mission_id: str):
    """
    Get an LLM-generated human-readable summary of a mission's results.
    """
    if not orchestrator_agent:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    result = await asyncio.to_thread(
        orchestrator_agent.summarize_mission, mission_id
    )
    if result.get("status") == "error" and "not found" in result.get("message", ""):
        raise HTTPException(status_code=404, detail=result["message"])
    return result


@app.post("/api/admin/collect-flood-data", tags=["Admin"], dependencies=[Depends(verify_api_key)])
async def trigger_flood_data_collection():
    """
    Manually trigger flood data collection from FloodAgent.

    This endpoint is useful for testing the agent communication workflow
    and forcing an update of flood conditions.
    """
    logger.info("Manual flood data collection triggered")

    try:
        # Trigger FloodAgent to collect and forward data
        data = flood_agent.collect_flood_data()
        if data:
            flood_agent.send_flood_data_via_message(data)

        return {
            "status": "success",
            "message": "Flood data collection completed",
            "locations_updated": len(data) if data else 0,
            "data_summary": list(data.keys()) if data else []
        }

    except Exception as e:
        logger.error(f"Flood data collection error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error collecting flood data: {str(e)}"
        )

@app.post("/api/admin/geotiff/enable", tags=["Admin"], dependencies=[Depends(verify_api_key)])
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

@app.post("/api/admin/geotiff/disable", tags=["Admin"], dependencies=[Depends(verify_api_key)])
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

@app.post("/api/admin/geotiff/set-scenario", tags=["Admin"], dependencies=[Depends(verify_api_key)])
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
        data = flood_agent.collect_flood_data()
        if data:
            flood_agent.send_flood_data_via_message(data)

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
        result = await sim_manager.start(mode=mode)

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
        result = await sim_manager.stop()

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
        result = await sim_manager.reset()

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


# --- Agent Lifecycle Manager Endpoints ---

@app.get("/api/lifecycle/status", tags=["Lifecycle"])
async def get_lifecycle_status():
    """
    Get agent lifecycle manager status.

    Returns current lifecycle manager status including:
    - Running state
    - Tick interval configuration
    - Registered agents
    - Tick statistics
    """
    try:
        lifecycle_manager = get_lifecycle_manager()
        if not lifecycle_manager:
            raise HTTPException(
                status_code=503,
                detail="Agent lifecycle manager not initialized"
            )

        status = lifecycle_manager.get_status()
        return {
            "status": "healthy" if status["is_running"] else "stopped",
            **status
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Lifecycle status error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving lifecycle status: {str(e)}"
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
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    hours: int = 24,
    success_only: bool = True,
    db: Session = Depends(get_db)
):
    """
    Get historical flood data collections within a time range.

    Args:
        page: Page number (1-indexed)
        page_size: Number of collections per page (1-100)
        hours: Number of hours of history (default: 24)
        success_only: Only return successful collections (default: True)

    Returns:
        Paginated list of flood data collections
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

        # Convert to list of dicts for pagination
        collections_list = [
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

        # Apply pagination
        from app.core.pagination import paginate
        paginated = paginate(collections_list, page=page, page_size=page_size)

        return {
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "hours": hours
            },
            "items": paginated.items,
            "total": paginated.total,
            "page": paginated.page,
            "page_size": paginated.page_size,
            "total_pages": paginated.total_pages
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

# ============================================================================
# Agent Data Endpoints - For Frontend Display
# ============================================================================

@app.get("/api/agents/scout/reports", tags=["Agent Data"])
async def get_scout_reports(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    hours: int = Query(24, ge=1, le=168, description="Hours of history")
):
    """
    Get crowdsourced flood reports from ScoutAgent.

    Returns recent flood reports collected from social media (Twitter/X)
    that have been processed and validated by the NLP system.

    Args:
        page: Page number (1-indexed)
        page_size: Number of reports per page (1-100)
        hours: Number of hours of history to include (1-168)

    Returns:
        Paginated list of validated flood reports with location, severity, and timestamp
    """
    try:
        if not hazard_agent:
            raise HTTPException(
                status_code=503,
                detail="HazardAgent not initialized"
            )

        # Get reports from HazardAgent's scout data cache
        all_reports = hazard_agent.scout_data_cache or []

        # Filter by time if timestamps available
        from datetime import datetime, timedelta
        cutoff_time = datetime.now() - timedelta(hours=hours)

        filtered_reports = []
        for report in all_reports:
            # Check if report has timestamp and is within time range
            if "timestamp" in report:
                try:
                    report_time = datetime.fromisoformat(report["timestamp"].replace("Z", "+00:00"))
                    if report_time >= cutoff_time:
                        filtered_reports.append(report)
                except (ValueError, AttributeError):
                    # Include reports with invalid timestamps
                    filtered_reports.append(report)
            else:
                # Include reports without timestamps
                filtered_reports.append(report)

        # Apply pagination
        from app.core.pagination import paginate
        paginated = paginate(filtered_reports, page=page, page_size=page_size)

        return {
            "status": "success",
            "time_range_hours": hours,
            "items": paginated.items,
            "total": paginated.total,
            "page": paginated.page,
            "page_size": paginated.page_size,
            "total_pages": paginated.total_pages,
            "scout_agent_active": scout_agent is not None,
            "note": "Reports are from crowdsourced social media data processed by NLP"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving scout reports: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving scout reports: {str(e)}"
        )


@app.post("/api/agents/scout/collect", tags=["Agent Data"])
async def trigger_scout_collection():
    """
    Manually trigger ScoutAgent to collect real-time Twitter/X data.

    This endpoint allows manual triggering of scout data collection
    outside of simulation mode. ScoutAgent will:
    1. Search Twitter/X for flood-related tweets
    2. Process them with NLP
    3. Forward validated reports to HazardAgent
    4. Make them available via /api/agents/scout/reports

    Returns:
        Collection results with tweet counts and processing status

    Example:
        POST /api/agents/scout/collect
    """
    logger.info("Manual scout collection triggered via API")

    try:
        if not scout_agent:
            raise HTTPException(
                status_code=503,
                detail="ScoutAgent not initialized"
            )

        # Check if in simulation mode
        if scout_agent.simulation_mode:
            return {
                "status": "skipped",
                "message": "ScoutAgent is in simulation mode. Use simulation endpoints instead.",
                "simulation_mode": True
            }

        # Trigger scout collection
        start_time = datetime.now()

        # Call step() in a thread to avoid blocking
        new_tweets = await asyncio.to_thread(scout_agent.step)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        return {
            "status": "success",
            "tweets_collected": len(new_tweets) if new_tweets else 0,
            "duration_seconds": round(duration, 2),
            "timestamp": end_time.isoformat(),
            "message": f"Collected and processed {len(new_tweets) if new_tweets else 0} new tweets",
            "note": "Check /api/agents/scout/reports to view processed reports"
        }

    except Exception as e:
        logger.error(f"Error in manual scout collection: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error collecting scout data: {str(e)}"
        )


@app.get("/api/agents/flood/current-status", tags=["Agent Data"])
async def get_flood_agent_status():
    """
    Get current flood status from FloodAgent.

    Returns the latest flood data including river levels, weather conditions,
    and risk assessments from official sources (PAGASA + OpenWeatherMap).

    Returns:
        Current flood conditions and weather data
    """
    try:
        if not flood_agent:
            raise HTTPException(
                status_code=503,
                detail="FloodAgent not initialized"
            )

        # Get latest flood data from HazardAgent cache
        flood_data_dict = hazard_agent.flood_data_cache if hazard_agent else {}

        # flood_data_cache is a dict, not a list
        # Extract timestamp from any available data source
        last_update = None
        if flood_data_dict:
            for source_data in flood_data_dict.values():
                if isinstance(source_data, dict) and source_data.get("timestamp"):
                    last_update = source_data.get("timestamp")
                    break

        return {
            "status": "success",
            "data_points": len(flood_data_dict),
            "flood_data": flood_data_dict,
            "last_update": last_update,
            "data_source": "PAGASA + OpenWeatherMap APIs",
            "note": "Data is automatically collected every 5 minutes"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving flood status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving flood status: {str(e)}"
        )


@app.get("/api/agents/evacuation/centers", tags=["Agent Data"])
async def get_evacuation_centers():
    """
    Get list of all evacuation centers in Marikina City.

    Returns information about official evacuation centers including
    their locations, capacity, and current status.

    Returns:
        List of evacuation centers with coordinates and metadata
    """
    try:
        if not routing_agent:
            raise HTTPException(
                status_code=503,
                detail="RoutingAgent not initialized"
            )

        # Get evacuation centers from RoutingAgent
        centers = []
        if hasattr(routing_agent, 'evacuation_centers') and not routing_agent.evacuation_centers.empty:
            # Convert DataFrame to list of dicts
            for _, row in routing_agent.evacuation_centers.iterrows():
                lat = row.get("latitude")
                lon = row.get("longitude")
                # Skip rows with NaN coordinates
                if pd.isna(lat) or pd.isna(lon):
                    continue
                def _safe_str(val, default=""):
                    return str(val) if pd.notna(val) else default

                def _safe_int(val, default=0):
                    try:
                        return int(val) if pd.notna(val) else default
                    except (ValueError, TypeError, OverflowError):
                        return default

                centers.append({
                    "name": _safe_str(row.get("name"), "Unknown"),
                    "location": _safe_str(row.get("address")),
                    "barangay": _safe_str(row.get("barangay")),
                    "coordinates": {
                        "lat": float(lat),
                        "lon": float(lon)
                    },
                    "capacity": _safe_int(row.get("capacity")),
                    "type": _safe_str(row.get("type")),
                    "facilities": _safe_str(row.get("facilities")).split(", ") if pd.notna(row.get("facilities")) else [],
                    "contact": _safe_str(row.get("contact")),
                    "is_active": True
                })

        import json, math

        def _sanitize(obj):
            """Recursively replace NaN/Inf floats with None for JSON compliance."""
            if isinstance(obj, float):
                return None if (math.isnan(obj) or math.isinf(obj)) else obj
            if isinstance(obj, dict):
                return {k: _sanitize(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_sanitize(v) for v in obj]
            return obj

        result = {
            "status": "success",
            "total_centers": len(centers),
            "centers": _sanitize(centers),
            "note": "Official evacuation centers from Marikina City database"
        }
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving evacuation centers: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving evacuation centers: {str(e)}"
        )


@app.get("/api/agents/status", tags=["Agent Data"])
async def get_all_agents_status():
    """
    Get comprehensive status of all agents in the system.

    Returns real-time status information about all agents including:
    - ScoutAgent: Active reports, simulation mode
    - FloodAgent: Data sources, last update
    - HazardAgent: Cached data counts, GeoTIFF status
    - RoutingAgent: Routes calculated, performance metrics
    - EvacuationManagerAgent: Active evacuations, statistics

    Returns:
        Comprehensive system status across all agents
    """
    try:
        status = {
            "scout_agent": {
                "active": scout_agent is not None,
                "simulation_mode": scout_agent.simulation_mode if scout_agent else None,
                "reports_cached": len(hazard_agent.scout_data_cache) if hazard_agent else 0,
                "status": "active" if scout_agent else "inactive"
            },
            "flood_agent": {
                "active": flood_agent is not None,
                "data_points": len(hazard_agent.flood_data_cache) if hazard_agent else 0,
                "use_real_apis": flood_agent.use_real_apis if flood_agent else False,
                "status": "active" if flood_agent else "inactive"
            },
            "hazard_agent": {
                "active": hazard_agent is not None,
                "geotiff_enabled": hazard_agent.is_geotiff_enabled() if hazard_agent else False,
                "current_scenario": {
                    "return_period": hazard_agent.return_period if hazard_agent else None,
                    "time_step": hazard_agent.time_step if hazard_agent else None
                } if hazard_agent else None,
                "total_cached_data": (
                    len(hazard_agent.flood_data_cache) + len(hazard_agent.scout_data_cache)
                ) if hazard_agent else 0,
                "status": "active" if hazard_agent else "inactive"
            },
            "routing_agent": {
                "active": routing_agent is not None,
                "status": "active" if routing_agent else "inactive"
            },
            "evacuation_manager": {
                "active": evacuation_manager is not None,
                "evacuation_centers": (
                    len(routing_agent.evacuation_centers)
                    if routing_agent and hasattr(routing_agent, 'evacuation_centers') and not routing_agent.evacuation_centers.empty
                    else 0
                ),
                "status": "active" if evacuation_manager else "inactive"
            },
            "system": {
                "graph_loaded": environment.graph is not None,
                "total_nodes": environment.graph.number_of_nodes() if environment.graph else 0,
                "total_edges": environment.graph.number_of_edges() if environment.graph else 0
            }
        }

        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "agents": status
        }

    except Exception as e:
        logger.error(f"Error retrieving agents status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving agents status: {str(e)}"
        )


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


@app.get("/api/debug/hazard-cache", tags=["Debug"])
async def get_hazard_cache_debug():
    """
    Debug endpoint to inspect HazardAgent cache contents.

    Returns raw cache data for debugging simulation data flow.
    Useful for diagnosing issues with simulation data not appearing in AgentDataPanel.

    Returns:
        Cache contents, sizes, and simulation manager state
    """
    if not hazard_agent:
        raise HTTPException(
            status_code=503,
            detail="HazardAgent not initialized"
        )

    return {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "flood_data_cache": hazard_agent.flood_data_cache,
        "scout_data_cache": hazard_agent.scout_data_cache,
        "cache_sizes": {
            "flood": len(hazard_agent.flood_data_cache),
            "scout": len(hazard_agent.scout_data_cache)
        },
        "simulation_manager_state": {
            "state": simulation_manager._state.value if simulation_manager else None,
            "mode": simulation_manager._mode.value if simulation_manager else None,
            "tick_count": simulation_manager.tick_count if simulation_manager else 0,
            "time_step": simulation_manager.current_time_step if simulation_manager else 0,
            "simulation_clock": simulation_manager._simulation_clock if simulation_manager else 0,
            "event_queue_size": len(simulation_manager._event_queue) if simulation_manager else 0
        }
    }


@app.get("/api/debug/simulation-events", tags=["Debug"])
async def get_simulation_events_debug():
    """
    Debug endpoint to inspect simulation event queue.

    Shows upcoming events and their timing to help debug
    why events might not be processing.

    Returns:
        Event queue contents and processing status
    """
    if not simulation_manager:
        raise HTTPException(
            status_code=503,
            detail="SimulationManager not initialized"
        )

    # Get next 10 events without removing them
    upcoming_events = simulation_manager._event_queue[:10] if simulation_manager._event_queue else []

    return {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "simulation_clock": simulation_manager._simulation_clock,
        "total_events_remaining": len(simulation_manager._event_queue),
        "upcoming_events": upcoming_events,
        "simulation_state": {
            "state": simulation_manager._state.value,
            "mode": simulation_manager._mode.value,
            "tick_count": simulation_manager.tick_count,
            "time_step": simulation_manager.current_time_step,
            "is_running": simulation_manager.is_running,
            "is_paused": simulation_manager.is_paused
        }
    }


@app.get("/api/debug/graph-risk-scores", tags=["Debug"])
async def get_graph_risk_scores_debug():
    """
    Debug endpoint to check current risk scores on graph edges.

    Helps verify that flood data is loaded and roads are being blocked correctly.

    Returns:
        Risk score statistics and samples of high-risk edges
    """
    if not environment or not environment.graph:
        raise HTTPException(
            status_code=503,
            detail="Graph environment not initialized"
        )

    graph = environment.graph
    total_edges = graph.number_of_edges()

    # Collect risk score statistics
    risk_scores = []
    high_risk_edges = []  # risk >= 0.7
    impassable_edges = []  # risk >= 0.9

    for u, v, key, data in graph.edges(keys=True, data=True):
        risk = data.get('risk_score', 0.0)
        risk_scores.append(risk)

        if risk >= 0.9:
            # Get edge coordinates
            u_coords = graph.nodes[u]
            v_coords = graph.nodes[v]
            impassable_edges.append({
                "edge": f"({u}, {v}, {key})",
                "risk_score": round(risk, 3),
                "length": round(data.get('length', 0), 1),
                "start": {"lat": round(u_coords['y'], 5), "lon": round(u_coords['x'], 5)},
                "end": {"lat": round(v_coords['y'], 5), "lon": round(v_coords['x'], 5)}
            })
        elif risk >= 0.7:
            u_coords = graph.nodes[u]
            v_coords = graph.nodes[v]
            high_risk_edges.append({
                "edge": f"({u}, {v}, {key})",
                "risk_score": round(risk, 3),
                "length": round(data.get('length', 0), 1),
                "start": {"lat": round(u_coords['y'], 5), "lon": round(u_coords['x'], 5)},
                "end": {"lat": round(v_coords['y'], 5), "lon": round(v_coords['x'], 5)}
            })

    # Calculate statistics
    risk_scores = sorted(risk_scores, reverse=True)
    safe_edges = sum(1 for r in risk_scores if r < 0.3)
    moderate_edges = sum(1 for r in risk_scores if 0.3 <= r < 0.7)
    high_risk_count = len(high_risk_edges)
    impassable_count = len(impassable_edges)

    return {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "graph_stats": {
            "total_edges": total_edges,
            "safe_edges": safe_edges,
            "moderate_risk_edges": moderate_edges,
            "high_risk_edges": high_risk_count,
            "impassable_edges": impassable_count
        },
        "risk_distribution": {
            "min_risk": round(min(risk_scores) if risk_scores else 0, 3),
            "max_risk": round(max(risk_scores) if risk_scores else 0, 3),
            "avg_risk": round(sum(risk_scores) / len(risk_scores) if risk_scores else 0, 3),
            "median_risk": round(risk_scores[len(risk_scores)//2] if risk_scores else 0, 3)
        },
        "sample_impassable_edges": impassable_edges[:10],  # First 10
        "sample_high_risk_edges": high_risk_edges[:10],  # First 10
        "blocking_info": {
            "max_risk_threshold": 0.9,
            "edges_that_will_block": impassable_count,
            "percentage_blocked": round((impassable_count / total_edges * 100) if total_edges > 0 else 0, 2)
        }
    }


