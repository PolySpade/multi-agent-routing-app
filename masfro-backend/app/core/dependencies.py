"""
FastAPI dependency functions.

Provides dependency injection for agents, managers, and other services.
"""

from fastapi import HTTPException
from app.core.state import get_app_state


def get_environment():
    """Get DynamicGraphEnvironment instance."""
    state = get_app_state()
    if not state.environment:
        raise HTTPException(
            status_code=503,
            detail="Environment not initialized"
        )
    return state.environment


def get_hazard_agent():
    """Get HazardAgent instance."""
    state = get_app_state()
    if not state.hazard_agent:
        raise HTTPException(
            status_code=503,
            detail="HazardAgent not initialized"
        )
    return state.hazard_agent


def get_routing_agent():
    """Get RoutingAgent instance."""
    state = get_app_state()
    if not state.routing_agent:
        raise HTTPException(
            status_code=503,
            detail="RoutingAgent not initialized"
        )
    return state.routing_agent


def get_flood_agent():
    """Get FloodAgent instance."""
    state = get_app_state()
    if not state.flood_agent:
        raise HTTPException(
            status_code=503,
            detail="FloodAgent not initialized"
        )
    return state.flood_agent


def get_evacuation_manager():
    """Get EvacuationManagerAgent instance."""
    state = get_app_state()
    if not state.evacuation_manager:
        raise HTTPException(
            status_code=503,
            detail="EvacuationManagerAgent not initialized"
        )
    return state.evacuation_manager


def get_websocket_manager():
    """Get WebSocket ConnectionManager instance."""
    state = get_app_state()
    if not state.websocket_manager:
        raise HTTPException(
            status_code=503,
            detail="WebSocket manager not initialized"
        )
    return state.websocket_manager


def get_message_queue():
    """Get MessageQueue instance."""
    state = get_app_state()
    if not state.message_queue:
        raise HTTPException(
            status_code=503,
            detail="MessageQueue not initialized"
        )
    return state.message_queue
