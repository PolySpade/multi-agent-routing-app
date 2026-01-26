"""
API Routes Package

Contains all API route modules for the MAS-FRO backend.
"""

from fastapi import APIRouter

# Existing routers (to be kept for backward compatibility)
from .graph_routes import router as graph_router, set_graph_environment
from .evacuation_routes import router as evacuation_router

# New modular routers
from .routing_endpoints import router as routing_router
from .simulation_endpoints import router as simulation_router
from .general_endpoints import router as general_router


def create_v1_router() -> APIRouter:
    """
    Create and configure the /api/v1 router with all sub-routers.

    Returns:
        Configured APIRouter with all endpoints
    """
    api_v1_router = APIRouter(prefix="/api/v1")

    # Include new modular routers
    api_v1_router.include_router(general_router)
    api_v1_router.include_router(routing_router)
    api_v1_router.include_router(simulation_router, prefix="/simulation")

    # Include existing routers
    api_v1_router.include_router(graph_router)
    api_v1_router.include_router(evacuation_router)

    return api_v1_router


__all__ = [
    "graph_router",
    "set_graph_environment",
    "evacuation_router",
    "create_v1_router",
    "routing_router",
    "simulation_router",
    "general_router"
]
