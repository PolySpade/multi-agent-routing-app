"""
Simulation Manager Service

Manages the simulation state and controls for the MAS-FRO system.
Handles start, stop, and reset operations for the multi-agent simulation.

Author: MAS-FRO Development Team
Date: November 2025
"""

from typing import Optional, Dict, Any, Literal
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SimulationState(str, Enum):
    """Simulation state enumeration."""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"


class SimulationMode(str, Enum):
    """Simulation flood scenario modes."""
    LIGHT = "light"
    MEDIUM = "medium"
    HEAVY = "heavy"


class SimulationManager:
    """
    Manages simulation lifecycle and state.

    This class controls the multi-agent simulation system, including
    starting, stopping, and resetting the simulation environment.
    """

    def __init__(self):
        """Initialize simulation manager."""
        self._state: SimulationState = SimulationState.STOPPED
        self._mode: SimulationMode = SimulationMode.LIGHT
        self._started_at: Optional[datetime] = None
        self._paused_at: Optional[datetime] = None
        self._total_runtime_seconds: float = 0.0
        self._simulation_data: Dict[str, Any] = {}

        logger.info("SimulationManager initialized")

    @property
    def state(self) -> SimulationState:
        """Get current simulation state."""
        return self._state

    @property
    def mode(self) -> SimulationMode:
        """Get current simulation mode."""
        return self._mode

    @property
    def is_running(self) -> bool:
        """Check if simulation is currently running."""
        return self._state == SimulationState.RUNNING

    @property
    def is_stopped(self) -> bool:
        """Check if simulation is stopped."""
        return self._state == SimulationState.STOPPED

    @property
    def is_paused(self) -> bool:
        """Check if simulation is paused."""
        return self._state == SimulationState.PAUSED

    def start(self, mode: str = "light") -> Dict[str, Any]:
        """
        Start the simulation.

        Args:
            mode: Simulation mode (light, medium, heavy)

        Returns:
            Dictionary with start result and metadata

        Raises:
            ValueError: If simulation is already running
        """
        if self._state == SimulationState.RUNNING:
            raise ValueError("Simulation is already running")

        # Validate mode
        try:
            self._mode = SimulationMode(mode.lower())
        except ValueError:
            raise ValueError(f"Invalid simulation mode: {mode}. Must be light, medium, or heavy")

        # Update state
        previous_state = self._state
        self._state = SimulationState.RUNNING
        self._started_at = datetime.now()

        logger.info(
            f"Simulation STARTED - Mode: {self._mode.value.upper()}, "
            f"Previous state: {previous_state.value}"
        )

        return {
            "status": "success",
            "message": f"Simulation started in {self._mode.value} mode",
            "state": self._state.value,
            "mode": self._mode.value,
            "started_at": self._started_at.isoformat(),
            "previous_state": previous_state.value
        }

    def stop(self) -> Dict[str, Any]:
        """
        Stop (pause) the simulation.

        Returns:
            Dictionary with stop result and metadata

        Raises:
            ValueError: If simulation is not running
        """
        if self._state != SimulationState.RUNNING:
            raise ValueError("Simulation is not running")

        # Update runtime
        if self._started_at:
            runtime = (datetime.now() - self._started_at).total_seconds()
            self._total_runtime_seconds += runtime

        # Update state
        self._state = SimulationState.PAUSED
        self._paused_at = datetime.now()

        logger.info(
            f"Simulation STOPPED (paused) - Total runtime: {self._total_runtime_seconds:.2f}s"
        )

        return {
            "status": "success",
            "message": "Simulation stopped (paused)",
            "state": self._state.value,
            "mode": self._mode.value,
            "paused_at": self._paused_at.isoformat(),
            "total_runtime_seconds": round(self._total_runtime_seconds, 2)
        }

    def reset(self) -> Dict[str, Any]:
        """
        Reset the simulation to initial state.

        Clears all simulation data, resets state to stopped, and
        clears runtime counters.

        Returns:
            Dictionary with reset result and metadata
        """
        previous_state = self._state
        previous_mode = self._mode
        previous_runtime = self._total_runtime_seconds

        # Reset all state
        self._state = SimulationState.STOPPED
        self._mode = SimulationMode.LIGHT
        self._started_at = None
        self._paused_at = None
        self._total_runtime_seconds = 0.0
        self._simulation_data.clear()

        logger.info(
            f"Simulation RESET - Previous state: {previous_state.value}, "
            f"Previous mode: {previous_mode.value}, "
            f"Previous runtime: {previous_runtime:.2f}s"
        )

        return {
            "status": "success",
            "message": "Simulation reset to initial state",
            "state": self._state.value,
            "mode": self._mode.value,
            "previous_state": previous_state.value,
            "previous_mode": previous_mode.value,
            "previous_runtime_seconds": round(previous_runtime, 2),
            "reset_at": datetime.now().isoformat()
        }

    def get_status(self) -> Dict[str, Any]:
        """
        Get current simulation status.

        Returns:
            Dictionary with complete simulation status
        """
        status = {
            "state": self._state.value,
            "mode": self._mode.value,
            "is_running": self.is_running,
            "is_stopped": self.is_stopped,
            "is_paused": self.is_paused,
            "total_runtime_seconds": round(self._total_runtime_seconds, 2),
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "paused_at": self._paused_at.isoformat() if self._paused_at else None,
        }

        # Calculate current runtime if running
        if self.is_running and self._started_at:
            current_runtime = (datetime.now() - self._started_at).total_seconds()
            status["current_session_seconds"] = round(current_runtime, 2)

        return status

    def set_data(self, key: str, value: Any) -> None:
        """
        Store simulation data.

        Args:
            key: Data key
            value: Data value
        """
        self._simulation_data[key] = value

    def get_data(self, key: str, default: Any = None) -> Any:
        """
        Retrieve simulation data.

        Args:
            key: Data key
            default: Default value if key not found

        Returns:
            Data value or default
        """
        return self._simulation_data.get(key, default)

    def clear_data(self) -> None:
        """Clear all simulation data."""
        self._simulation_data.clear()


# Global simulation manager instance
_simulation_manager: Optional[SimulationManager] = None


def get_simulation_manager() -> SimulationManager:
    """
    Get or create the global simulation manager instance.

    Returns:
        SimulationManager instance
    """
    global _simulation_manager
    if _simulation_manager is None:
        _simulation_manager = SimulationManager()
    return _simulation_manager


def set_simulation_manager(manager: SimulationManager) -> None:
    """
    Set the global simulation manager instance.

    Args:
        manager: SimulationManager instance
    """
    global _simulation_manager
    _simulation_manager = manager
