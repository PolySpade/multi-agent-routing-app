# filename: app/agents/base_agent.py

"""
Base agent class for MAS-FRO multi-agent system.

Provides common functionality and interface for all agents.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..environment.graph_manager import DynamicGraphEnvironment


class BaseAgent:
    """
    A base class for all agents in the MAS-FRO simulation.

    Provides common attributes like an ID and a reference to the environment,
    and defines a common interface ('step') for the simulation loop.
    """
    
    def __init__(self, agent_id: str, environment: "DynamicGraphEnvironment") -> None:
        """
        Initialize the base agent.

        Args:
            agent_id: Unique identifier for this agent
            environment: Reference to the DynamicGraphEnvironment instance
        """
        from ..core.logging_config import get_logger
        
        self.agent_id = agent_id
        self.environment = environment
        self.logger = get_logger(f"app.agents.{agent_id}")
        self.logger.info(f"Agent {self.agent_id} created")

    def step(self) -> None:
        """
        Represents a single time-step of action for the agent.
        This method must be implemented by each child agent.
        
        Raises:
            NotImplementedError: This method must be implemented by subclasses
        """
        raise NotImplementedError("Each agent must implement its own step() method.")