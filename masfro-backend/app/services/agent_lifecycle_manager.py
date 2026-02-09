# filename: app/services/agent_lifecycle_manager.py

"""
Agent Lifecycle Manager for MAS-FRO Multi-Agent System

This service solves the "Dormant Agent" problem by periodically calling step()
on registered agents, enabling proper MessageQueue-based communication.

The key insight is that agents like HazardAgent have step() methods that process
messages from the MessageQueue, but nothing was calling these methods. This service
provides the missing execution loop.

Author: MAS-FRO Development Team
Date: February 2026
"""

import asyncio
import logging
import threading
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

from app.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class AgentLifecycleManager:
    """
    Background service that periodically calls step() on registered agents.

    This solves the "Dormant Agent" problem by ensuring agents process
    their message queues and perform periodic maintenance tasks.

    Key Features:
    - Configurable tick rate (default: 1Hz = 1 step/second)
    - Pauses during simulation mode (defers to SimulationManager)
    - Thread-safe agent execution
    - Statistics tracking for debugging

    Example:
        >>> manager = AgentLifecycleManager(tick_interval_seconds=1.0)
        >>> manager.register_agent(hazard_agent, priority=1)
        >>> await manager.start()
        >>> # ... agents now receive periodic step() calls
        >>> await manager.stop()
    """

    def __init__(
        self,
        tick_interval_seconds: float = 1.0,
        simulation_manager: Optional[Any] = None
    ):
        """
        Initialize the AgentLifecycleManager.

        Args:
            tick_interval_seconds: How often to call step() on agents (default: 1.0s)
            simulation_manager: Optional SimulationManager reference for coordination
        """
        self.tick_interval = tick_interval_seconds
        self.simulation_manager = simulation_manager
        self.is_running = False
        self.task: Optional[asyncio.Task] = None

        # Agent registry: {agent_id: (agent, priority)}
        self._agents: Dict[str, Tuple[BaseAgent, int]] = {}

        # Thread safety for agent registry access
        self._lock = threading.Lock()

        # Statistics for monitoring
        self.stats = {
            "total_ticks": 0,
            "successful_ticks": 0,
            "skipped_ticks_simulation": 0,
            "agent_step_counts": {},
            "agent_step_errors": {},
            "last_tick_time": None,
            "started_at": None,
            "last_error": None
        }

        logger.info(
            f"AgentLifecycleManager initialized: "
            f"tick_interval={tick_interval_seconds}s, "
            f"simulation_manager={'configured' if simulation_manager else 'not configured'}"
        )

    def register_agent(self, agent: BaseAgent, priority: int = 0) -> None:
        """
        Register an agent to receive periodic step() calls.

        Args:
            agent: Agent instance to register
            priority: Execution priority (lower = executed first)
        """
        with self._lock:
            agent_id = agent.agent_id
            self._agents[agent_id] = (agent, priority)
            self.stats["agent_step_counts"][agent_id] = 0
            self.stats["agent_step_errors"][agent_id] = 0

            logger.info(
                f"Agent registered with lifecycle manager: {agent_id} "
                f"(priority={priority})"
            )

    def unregister_agent(self, agent_id: str) -> bool:
        """
        Remove an agent from lifecycle management.

        Args:
            agent_id: ID of agent to unregister

        Returns:
            True if agent was found and removed, False otherwise
        """
        with self._lock:
            if agent_id in self._agents:
                del self._agents[agent_id]
                logger.info(f"Agent unregistered from lifecycle manager: {agent_id}")
                return True
            return False

    async def start(self) -> None:
        """
        Start the background lifecycle loop.

        Creates an asyncio task that periodically calls step() on all
        registered agents.
        """
        if self.is_running:
            logger.warning("AgentLifecycleManager already running")
            return

        self.is_running = True
        self.stats["started_at"] = datetime.now()
        self.task = asyncio.create_task(self._lifecycle_loop())

        agent_count = len(self._agents)
        logger.info(
            f"AgentLifecycleManager started: "
            f"{agent_count} agent(s), tick_interval={self.tick_interval}s"
        )

    async def stop(self) -> None:
        """
        Stop the lifecycle loop gracefully.

        Waits for the current tick to complete before stopping.
        """
        if not self.is_running:
            logger.warning("AgentLifecycleManager not running")
            return

        logger.info("Stopping AgentLifecycleManager...")
        self.is_running = False

        if self.task:
            try:
                # Wait for current tick to complete with timeout
                await asyncio.wait_for(self.task, timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning("Lifecycle loop stop timed out, cancelling task")
                self.task.cancel()
            except asyncio.CancelledError:
                pass

        logger.info(
            f"AgentLifecycleManager stopped: "
            f"total_ticks={self.stats['total_ticks']}, "
            f"successful={self.stats['successful_ticks']}, "
            f"skipped_for_simulation={self.stats['skipped_ticks_simulation']}"
        )

    async def _lifecycle_loop(self) -> None:
        """
        Main background loop that periodically ticks all registered agents.

        This loop runs continuously until stop() is called. Each iteration:
        1. Checks if simulation is running (skip if so)
        2. Calls step() on all registered agents in priority order
        3. Sleeps for the configured interval
        """
        logger.info("AgentLifecycleManager loop started")

        while self.is_running:
            try:
                # Check if we should skip this tick
                if self._should_skip_tick():
                    self.stats["skipped_ticks_simulation"] += 1
                    await asyncio.sleep(self.tick_interval)
                    continue

                # Execute tick on all agents
                self.stats["total_ticks"] += 1
                tick_result = await self._tick_agents()

                if not tick_result.get("errors"):
                    self.stats["successful_ticks"] += 1

                self.stats["last_tick_time"] = datetime.now()

                # Log periodically (every 60 ticks)
                if self.stats["total_ticks"] % 60 == 0:
                    logger.debug(
                        f"AgentLifecycleManager tick #{self.stats['total_ticks']}: "
                        f"agents_executed={len(tick_result.get('agents_executed', []))}"
                    )

            except Exception as e:
                self.stats["last_error"] = str(e)
                logger.error(f"AgentLifecycleManager tick error: {e}")

            # Sleep until next tick
            await asyncio.sleep(self.tick_interval)

        logger.info("AgentLifecycleManager loop stopped")

    def _should_skip_tick(self) -> bool:
        """
        Check if we should skip this tick.

        Returns True if SimulationManager is running (it handles agent
        execution during simulation).

        Returns:
            True if tick should be skipped, False otherwise
        """
        if self.simulation_manager is not None:
            # Check if simulation is actively running
            if hasattr(self.simulation_manager, 'is_running'):
                if self.simulation_manager.is_running:
                    return True
        return False

    async def _tick_agents(self) -> Dict[str, Any]:
        """
        Execute step() on all registered agents in priority order.

        Returns:
            Dict with tick results including agents executed and any errors
        """
        tick_result = {
            "tick_number": self.stats["total_ticks"],
            "agents_executed": [],
            "errors": []
        }

        # Get sorted list of agents by priority
        with self._lock:
            sorted_agents = sorted(
                self._agents.items(),
                key=lambda x: x[1][1]  # Sort by priority
            )

        # Execute step() on each agent
        for agent_id, (agent, priority) in sorted_agents:
            try:
                # Run agent.step() in a thread to avoid blocking
                await asyncio.to_thread(agent.step)

                tick_result["agents_executed"].append(agent_id)
                self.stats["agent_step_counts"][agent_id] = \
                    self.stats["agent_step_counts"].get(agent_id, 0) + 1

            except Exception as e:
                error_msg = f"{agent_id}: {str(e)}"
                tick_result["errors"].append(error_msg)
                self.stats["agent_step_errors"][agent_id] = \
                    self.stats["agent_step_errors"].get(agent_id, 0) + 1
                logger.error(f"Agent step failed: {error_msg}")

        return tick_result

    def get_status(self) -> Dict[str, Any]:
        """
        Get current lifecycle manager status and statistics.

        Returns:
            Dict with status information for monitoring API
        """
        uptime = None
        if self.stats["started_at"]:
            uptime = (datetime.now() - self.stats["started_at"]).total_seconds()

        with self._lock:
            agent_list = [
                {"id": agent_id, "priority": priority}
                for agent_id, (agent, priority) in self._agents.items()
            ]

        return {
            "is_running": self.is_running,
            "tick_interval_seconds": self.tick_interval,
            "uptime_seconds": uptime,
            "registered_agents": agent_list,
            "simulation_coordination": self.simulation_manager is not None,
            "statistics": {
                "total_ticks": self.stats["total_ticks"],
                "successful_ticks": self.stats["successful_ticks"],
                "skipped_ticks_simulation": self.stats["skipped_ticks_simulation"],
                "agent_step_counts": self.stats["agent_step_counts"],
                "agent_step_errors": self.stats["agent_step_errors"],
                "last_tick_time": (
                    self.stats["last_tick_time"].isoformat()
                    if self.stats["last_tick_time"] else None
                ),
                "started_at": (
                    self.stats["started_at"].isoformat()
                    if self.stats["started_at"] else None
                ),
                "last_error": self.stats["last_error"]
            }
        }


# Global instance
_lifecycle_manager: Optional[AgentLifecycleManager] = None


def get_lifecycle_manager() -> Optional[AgentLifecycleManager]:
    """Get the global lifecycle manager instance."""
    return _lifecycle_manager


def set_lifecycle_manager(manager: AgentLifecycleManager) -> None:
    """Set the global lifecycle manager instance."""
    global _lifecycle_manager
    _lifecycle_manager = manager
