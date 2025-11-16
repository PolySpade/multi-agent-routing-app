# filename: app/agents/traffic_agent.py

"""
Traffic Agent for Multi-Agent System for Flood Route Optimization (MAS-FRO)

Monitors real-time traffic conditions using Google Maps Traffic API and
updates the road network graph with current traffic factors.

Author: MAS-FRO Development Team
Date: November 2025
"""

from .base_agent import BaseAgent
from typing import Dict, Any, Optional, TYPE_CHECKING
import logging
from datetime import datetime

if TYPE_CHECKING:
    from ..environment.graph_manager import DynamicGraphEnvironment

logger = logging.getLogger(__name__)


class TrafficAgent(BaseAgent):
    """
    Agent responsible for real-time traffic monitoring in MAS-FRO system.

    This agent periodically fetches traffic data from Google Maps and updates
    the road network graph with current congestion levels. Traffic factors
    are integrated into route costs alongside flood risk scores.

    Attributes:
        agent_id: Unique identifier for this agent
        environment: Reference to DynamicGraphEnvironment
        traffic_service: Google Traffic Service instance
        update_interval: How often to refresh traffic data (seconds)
        sample_interval: Sample every Nth edge to conserve API calls
        last_update: Timestamp of last traffic update

    Example:
        >>> env = DynamicGraphEnvironment()
        >>> agent = TrafficAgent("traffic_001", env)
        >>> stats = agent.update_traffic_data()
        >>> print(f"Updated {stats['edges_updated']} edges")
    """

    def __init__(
        self,
        agent_id: str,
        environment: "DynamicGraphEnvironment",
        update_interval: int = 300,  # 5 minutes
        sample_interval: int = 20,   # Sample every 20th edge
        api_key: Optional[str] = None
    ) -> None:
        """
        Initialize the TrafficAgent.

        Args:
            agent_id: Unique identifier for this agent
            environment: DynamicGraphEnvironment instance
            update_interval: Traffic update frequency in seconds (default: 300)
            sample_interval: Sample every Nth edge (default: 20)
            api_key: Google Maps API key (optional, uses env var if not provided)
        """
        super().__init__(agent_id, environment)

        # Import here to avoid circular dependencies
        from ..services.google_traffic_service import GoogleTrafficService

        self.traffic_service = GoogleTrafficService(
            api_key=api_key,
            cache_duration=update_interval
        )
        self.update_interval = update_interval
        self.sample_interval = sample_interval
        self.last_update: Optional[datetime] = None

        logger.info(
            f"{self.agent_id} initialized with "
            f"update_interval={update_interval}s, "
            f"sample_interval={sample_interval}"
        )

    def step(self):
        """
        Perform one step of traffic monitoring.

        This method is called periodically by the system scheduler.
        It checks if it's time to update traffic data and refreshes
        the graph if needed.
        """
        if self._should_update():
            logger.info(f"{self.agent_id} starting traffic data update")
            self.update_traffic_data()

    def update_traffic_data(self) -> Dict[str, Any]:
        """
        Fetch current traffic data and update the graph.

        Returns:
            Dictionary with update statistics:
                {
                    "edges_updated": int,
                    "edges_skipped": int,
                    "avg_traffic_factor": float,
                    "max_traffic_factor": float,
                    "elapsed_seconds": float,
                    "timestamp": datetime
                }

        Example:
            >>> agent = TrafficAgent("traffic_001", env)
            >>> stats = agent.update_traffic_data()
            >>> print(f"Average traffic delay: {stats['avg_traffic_factor']:.1%}")
        """
        logger.info(f"{self.agent_id} collecting traffic data...")

        if not self.environment or not self.environment.graph:
            logger.error("Graph environment not available")
            return {
                "error": "Graph not loaded",
                "timestamp": datetime.now()
            }

        try:
            # Update graph with traffic data
            stats = self.traffic_service.update_graph_traffic(
                self.environment.graph,
                sample_interval=self.sample_interval
            )

            # Update timestamp
            self.last_update = datetime.now()
            stats["timestamp"] = self.last_update

            logger.info(
                f"{self.agent_id} traffic update complete: "
                f"{stats['edges_updated']} edges updated, "
                f"avg_traffic={stats['avg_traffic_factor']:.3f}"
            )

            # Send ACL message to other agents
            self._notify_agents(stats)

            return stats

        except Exception as e:
            logger.error(f"{self.agent_id} failed to update traffic data: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now()
            }

    def get_current_traffic(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float]
    ) -> float:
        """
        Get current traffic factor for a specific route segment.

        Args:
            origin: Starting coordinates (latitude, longitude)
            destination: Ending coordinates (latitude, longitude)

        Returns:
            Traffic factor (0.0 = free-flow, higher = more delay)
        """
        return self.traffic_service.get_traffic_factor(origin, destination)

    def _should_update(self) -> bool:
        """
        Check if it's time to update traffic data.

        Returns:
            True if update is needed, False otherwise
        """
        if self.last_update is None:
            return True

        elapsed = (datetime.now() - self.last_update).total_seconds()
        return elapsed >= self.update_interval

    def _notify_agents(self, stats: Dict[str, Any]):
        """
        Notify other agents about traffic update via ACL message.

        Args:
            stats: Traffic update statistics
        """
        from ..communication.acl_protocol import ACLMessage, Performative

        message = ACLMessage(
            performative=Performative.INFORM,
            sender=self.agent_id,
            receiver="broadcast",
            content={
                "type": "traffic_update",
                "statistics": {
                    "edges_updated": stats.get("edges_updated", 0),
                    "avg_traffic_factor": stats.get("avg_traffic_factor", 0.0),
                    "max_traffic_factor": stats.get("max_traffic_factor", 0.0),
                    "timestamp": stats.get("timestamp", datetime.now()).isoformat()
                }
            }
        )

        logger.debug(f"{self.agent_id} broadcasting traffic update notification")
        # Note: In production, this would be sent through the message queue

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get traffic agent statistics.

        Returns:
            Dictionary with agent and service statistics
        """
        service_stats = self.traffic_service.get_statistics()

        return {
            "agent_id": self.agent_id,
            "update_interval": self.update_interval,
            "sample_interval": self.sample_interval,
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "service_stats": service_stats
        }

    def clear_cache(self):
        """Clear the traffic data cache."""
        self.traffic_service.clear_cache()
        logger.info(f"{self.agent_id} cleared traffic cache")
