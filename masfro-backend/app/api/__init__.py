"""
API Routes Package

Contains all API route modules for the MAS-FRO backend.
"""

from .graph_routes import router as graph_router, set_graph_environment

__all__ = ["graph_router", "set_graph_environment"]
