"""
Application-wide state management for MAS-FRO.

Holds references to all agents, environment, and managers.
"""

from typing import Optional
from app.environment.graph_manager import DynamicGraphEnvironment
from app.agents.hazard_agent import HazardAgent
from app.agents.routing_agent import RoutingAgent
from app.agents.flood_agent import FloodAgent
from app.agents.scout_agent import ScoutAgent
from app.agents.evacuation_manager_agent import EvacuationManagerAgent
from app.communication.message_queue import MessageQueue
from app.core.websocket_manager import ConnectionManager


class AppState:
    """
    Application-wide state container.

    Holds all agents, environment, and managers for easy access
    across the application.
    """

    def __init__(self):
        # Environment
        self.environment: Optional[DynamicGraphEnvironment] = None

        # Agents
        self.hazard_agent: Optional[HazardAgent] = None
        self.routing_agent: Optional[RoutingAgent] = None
        self.flood_agent: Optional[FloodAgent] = None
        self.scout_agent: Optional[ScoutAgent] = None
        self.evacuation_manager: Optional[EvacuationManagerAgent] = None
        self.orchestrator_agent = None

        # Communication
        self.message_queue: Optional[MessageQueue] = None

        # Managers
        self.websocket_manager: Optional[ConnectionManager] = None


# Global application state instance
_app_state: Optional[AppState] = None


def get_app_state() -> AppState:
    """Get the global application state instance."""
    global _app_state
    if _app_state is None:
        _app_state = AppState()
    return _app_state


def set_app_state(state: AppState):
    """Set the global application state instance."""
    global _app_state
    _app_state = state
