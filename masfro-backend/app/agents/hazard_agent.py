# filename: app/agents/hazard_agent.py

"""
Hazard Agent for Multi-Agent System for Flood Route Optimization (MAS-FRO)

This module implements the HazardAgent class, which serves as the central data
fusion and risk assessment hub in the MAS-FRO system. The agent receives data
from both FloodAgent (official sources) and ScoutAgent (crowdsourced data),
validates and fuses the information, and updates the Dynamic Graph Environment
with risk scores.

Key Responsibilities:
- Data validation and fusion from multiple sources
- Risk score calculation for road segments
- Dynamic graph environment updates
- Integration with ML models for flood prediction

Author: MAS-FRO Development Team
Date: November 2025
"""

from .base_agent import BaseAgent
from typing import Dict, Any, List, Tuple, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class HazardAgent(BaseAgent):
    """
    Central data fusion and risk assessment agent.

    This agent receives flood-related data from FloodAgent (official
    environmental data) and ScoutAgent (crowdsourced VGI data), validates
    and combines the information, calculates risk scores for road segments,
    and updates the Dynamic Graph Environment to reflect current hazard
    conditions.

    The agent implements a weighted fusion strategy that balances official
    data reliability with crowdsourced data timeliness.

    Attributes:
        agent_id: Unique identifier for this agent instance
        environment: Reference to DynamicGraphEnvironment
        flood_data_cache: Cache of recent flood data from FloodAgent
        scout_data_cache: Cache of recent crowdsourced data from ScoutAgent
        risk_weights: Weights for risk calculation components

    Example:
        >>> env = DynamicGraphEnvironment()
        >>> agent = HazardAgent("hazard_001", env)
        >>> agent.process_flood_data(flood_data)
        >>> agent.process_scout_data(scout_reports)
        >>> agent.update_risk_scores()
    """

    def __init__(self, agent_id: str, environment):
        """
        Initialize the HazardAgent.

        Args:
            agent_id: Unique identifier for this agent
            environment: DynamicGraphEnvironment instance for graph updates
        """
        super().__init__(agent_id, environment)

        # Data caches for fusion
        self.flood_data_cache: Dict[str, Any] = {}
        self.scout_data_cache: List[Dict[str, Any]] = []

        # Risk calculation weights
        self.risk_weights = {
            "flood_depth": 0.5,  # Official flood depth weight
            "crowdsourced": 0.3,  # Crowdsourced report weight
            "historical": 0.2  # Historical flood data weight
        }

        # ML model placeholder (to be integrated later)
        self.flood_predictor = None

        logger.info(f"{self.agent_id} initialized with risk weights: {self.risk_weights}")

    def step(self):
        """
        Perform one step of the agent's operation.

        In each step, the agent:
        1. Processes any new data from caches
        2. Fuses data from multiple sources
        3. Calculates risk scores
        4. Updates the graph environment
        """
        logger.debug(f"{self.agent_id} performing step at {datetime.now()}")

        # Process cached data and update risk scores
        if self.flood_data_cache or self.scout_data_cache:
            self.process_and_update()

    def process_and_update(self) -> Dict[str, Any]:
        """
        Process all cached data and update graph environment.

        This method performs the complete hazard assessment workflow:
        1. Fuse data from multiple sources
        2. Calculate risk scores
        3. Update graph environment

        Returns:
            Dict with processing results
        """
        logger.info(f"{self.agent_id} processing hazard data...")

        fused_data = self.fuse_data()
        risk_scores = self.calculate_risk_scores(fused_data)
        self.update_environment(risk_scores)

        return {
            "locations_processed": len(fused_data),
            "edges_updated": len(risk_scores),
            "timestamp": datetime.now()
        }

    def process_flood_data(self, flood_data: Dict[str, Any]) -> None:
        """
        Process official flood data from FloodAgent.

        Args:
            flood_data: Dictionary containing flood measurements
                Expected format:
                {
                    "location": str,
                    "flood_depth": float,  # meters
                    "rainfall": float,  # mm
                    "river_level": float,  # meters
                    "timestamp": datetime
                }
        """
        logger.info(f"{self.agent_id} received flood data: {flood_data.get('location')}")

        # Validate data
        if not self._validate_flood_data(flood_data):
            logger.warning(f"Invalid flood data received: {flood_data}")
            return

        # Update cache
        location = flood_data.get("location")
        self.flood_data_cache[location] = flood_data

        logger.debug(f"Flood data cached for location: {location}")

    def process_scout_data(self, scout_reports: List[Dict[str, Any]]) -> None:
        """
        Process crowdsourced data from ScoutAgent.

        Args:
            scout_reports: List of crowdsourced reports
                Expected format:
                [
                    {
                        "location": str,
                        "severity": float,  # 0-1 scale
                        "report_type": str,  # "flood", "blockage", "clear"
                        "confidence": float,  # 0-1 scale
                        "timestamp": datetime
                    },
                    ...
                ]
        """
        logger.info(f"{self.agent_id} received {len(scout_reports)} scout reports")

        # Validate and add to cache
        for report in scout_reports:
            if self._validate_scout_data(report):
                self.scout_data_cache.append(report)
            else:
                logger.warning(f"Invalid scout report: {report}")

        logger.debug(f"Scout data cache size: {len(self.scout_data_cache)}")

    def fuse_data(self) -> Dict[str, Any]:
        """
        Fuse data from multiple sources (FloodAgent and ScoutAgent).

        Combines official flood measurements with crowdsourced reports to
        create a comprehensive risk assessment. Uses weighted averaging
        based on data source reliability and timeliness.

        Returns:
            Dict mapping locations to fused risk information
                Format:
                {
                    "location_name": {
                        "risk_level": float,  # 0-1 scale
                        "flood_depth": float,
                        "confidence": float,
                        "sources": list
                    },
                    ...
                }
        """
        logger.debug(f"{self.agent_id} fusing data from multiple sources")

        fused_data = {}

        # Process official flood data
        for location, data in self.flood_data_cache.items():
            if location not in fused_data:
                fused_data[location] = {
                    "risk_level": 0.0,
                    "flood_depth": 0.0,
                    "confidence": 0.0,
                    "sources": []
                }

            # Calculate base risk from flood depth
            flood_depth = data.get("flood_depth", 0.0)
            depth_risk = min(flood_depth / 2.0, 1.0)  # Normalize to 0-1

            fused_data[location]["risk_level"] += depth_risk * self.risk_weights["flood_depth"]
            fused_data[location]["flood_depth"] = flood_depth
            fused_data[location]["confidence"] += 0.8  # High confidence for official data
            fused_data[location]["sources"].append("flood_agent")

        # Integrate crowdsourced data
        for report in self.scout_data_cache:
            location = report.get("location")
            if not location:
                continue

            if location not in fused_data:
                fused_data[location] = {
                    "risk_level": 0.0,
                    "flood_depth": 0.0,
                    "confidence": 0.0,
                    "sources": []
                }

            severity = report.get("severity", 0.0)
            confidence = report.get("confidence", 0.5)

            fused_data[location]["risk_level"] += severity * self.risk_weights["crowdsourced"] * confidence
            fused_data[location]["confidence"] += confidence * 0.6  # Lower weight for crowdsourced
            fused_data[location]["sources"].append("scout_agent")

        # Normalize risk levels to 0-1 scale
        for location in fused_data:
            fused_data[location]["risk_level"] = min(fused_data[location]["risk_level"], 1.0)
            fused_data[location]["confidence"] = min(fused_data[location]["confidence"], 1.0)

        logger.info(f"Data fusion complete for {len(fused_data)} locations")
        return fused_data

    def calculate_risk_scores(self, fused_data: Dict[str, Any]) -> Dict[Tuple, float]:
        """
        Calculate risk scores for road segments based on fused data.

        Args:
            fused_data: Fused data from multiple sources

        Returns:
            Dict mapping edge tuples to risk scores
                Format: {(u, v, key): risk_score, ...}
        """
        logger.debug(f"{self.agent_id} calculating risk scores")

        if not self.environment or not hasattr(self.environment, 'graph') or not self.environment.graph:
            logger.warning("Graph environment not available for risk calculation")
            return {}

        risk_scores = {}

        # For each location with flood data, update nearby edges
        for location, data in fused_data.items():
            risk_level = data["risk_level"]
            logger.debug(f"Location {location} has risk level: {risk_level:.2f}")

            # Apply risk to all edges (simplified approach for MVP)
            # In production, this would:
            # 1. Geocode location names to coordinates
            # 2. Find edges within radius
            # 3. Apply distance-based decay

            # For now, apply a base risk increase to all edges
            # This simulates system-wide flood conditions
            try:
                graph = self.environment.graph
                for u, v, key in list(graph.edges(keys=True))[:100]:  # Limit for performance
                    # Create edge tuple
                    edge_tuple = (u, v, key)

                    # If edge already has a risk score, take the max
                    current_risk = risk_scores.get(edge_tuple, 0.0)
                    new_risk = max(current_risk, risk_level * 0.5)  # 50% of reported risk
                    risk_scores[edge_tuple] = new_risk

            except Exception as e:
                logger.error(f"Error calculating risk for location {location}: {e}")

        logger.info(f"Calculated risk scores for {len(risk_scores)} edges")
        return risk_scores

    def update_environment(self, risk_scores: Dict[Tuple, float]) -> None:
        """
        Update the Dynamic Graph Environment with calculated risk scores.

        Args:
            risk_scores: Dict mapping edge tuples to risk scores
        """
        logger.debug(f"{self.agent_id} updating environment with risk scores")

        if not self.environment or not hasattr(self.environment, 'update_edge_risk'):
            logger.warning("Environment not configured for risk updates")
            return

        for (u, v, key), risk in risk_scores.items():
            try:
                self.environment.update_edge_risk(u, v, key, risk)
            except Exception as e:
                logger.error(f"Failed to update edge ({u}, {v}, {key}): {e}")

        logger.info(f"Updated {len(risk_scores)} edges in the environment")

    def _validate_flood_data(self, flood_data: Dict[str, Any]) -> bool:
        """
        Validate official flood data structure and values.

        Args:
            flood_data: Flood data to validate

        Returns:
            True if valid, False otherwise
        """
        required_fields = ["location", "flood_depth", "timestamp"]
        for field in required_fields:
            if field not in flood_data:
                return False

        # Validate ranges
        if not 0 <= flood_data.get("flood_depth", -1) <= 10:  # Max 10m depth
            return False

        return True

    def _validate_scout_data(self, scout_data: Dict[str, Any]) -> bool:
        """
        Validate crowdsourced data structure and values.

        Args:
            scout_data: Scout data to validate

        Returns:
            True if valid, False otherwise
        """
        required_fields = ["location", "severity", "timestamp"]
        for field in required_fields:
            if field not in scout_data:
                return False

        # Validate ranges
        severity = scout_data.get("severity", -1)
        if not 0 <= severity <= 1:
            return False

        confidence = scout_data.get("confidence", 1.0)
        if not 0 <= confidence <= 1:
            return False

        return True

    def clear_old_data(self, max_age_seconds: int = 3600) -> None:
        """
        Clear cached data older than the specified age.

        Args:
            max_age_seconds: Maximum age of data to keep (default: 1 hour)
        """
        current_time = datetime.now()

        # Clear old flood data
        locations_to_remove = []
        for location, data in self.flood_data_cache.items():
            timestamp = data.get("timestamp")
            if timestamp and (current_time - timestamp).total_seconds() > max_age_seconds:
                locations_to_remove.append(location)

        for location in locations_to_remove:
            del self.flood_data_cache[location]

        # Clear old scout data
        self.scout_data_cache = [
            report for report in self.scout_data_cache
            if (current_time - report.get("timestamp", current_time)).total_seconds() <= max_age_seconds
        ]

        logger.info(
            f"Cleared {len(locations_to_remove)} old flood records and "
            f"purged old scout data (remaining: {len(self.scout_data_cache)})"
        )
