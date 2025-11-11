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
from typing import Dict, Any, List, Tuple, Optional, TYPE_CHECKING
import logging
from datetime import datetime

if TYPE_CHECKING:
    from ..environment.graph_manager import DynamicGraphEnvironment

# GeoTIFF service import
try:
    from services.geotiff_service import get_geotiff_service
except ImportError:
    from app.services.geotiff_service import get_geotiff_service

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

    def __init__(
        self,
        agent_id: str,
        environment: "DynamicGraphEnvironment"
    ) -> None:
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

        # GeoTIFF service for flood depth queries
        try:
            self.geotiff_service = get_geotiff_service()
            logger.info(f"{self.agent_id} initialized GeoTIFFService")
        except Exception as e:
            logger.error(f"Failed to initialize GeoTIFFService: {e}")
            self.geotiff_service = None

        # Flood prediction configuration (default: rr01, time_step 1)
        self.return_period = "rr01"  # Default return period
        self.time_step = 1  # Default time step (1 hour)

        # ML model placeholder (to be integrated later)
        self.flood_predictor = None

        logger.info(
            f"{self.agent_id} initialized with risk weights: {self.risk_weights}, "
            f"return_period: {self.return_period}, time_step: {self.time_step}"
        )

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

        # Trigger risk calculation and graph update after receiving flood data
        logger.info(f"{self.agent_id} triggering hazard processing after flood data update")
        self.process_and_update()

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

    def get_flood_depth_at_edge(
        self,
        u: int,
        v: int,
        return_period: Optional[str] = None,
        time_step: Optional[int] = None
    ) -> Optional[float]:
        """
        Query flood depth for a specific edge from GeoTIFF data.

        Args:
            u: Source node ID
            v: Target node ID
            return_period: Return period (rr01-rr04), uses default if None
            time_step: Time step (1-18), uses default if None

        Returns:
            Average flood depth along edge in meters, or None if unavailable
        """
        if not self.geotiff_service or not self.environment or not self.environment.graph:
            return None

        rp = return_period or self.return_period
        ts = time_step or self.time_step

        try:
            # Get node coordinates
            u_data = self.environment.graph.nodes[u]
            v_data = self.environment.graph.nodes[v]

            u_lon, u_lat = float(u_data['x']), float(u_data['y'])
            v_lon, v_lat = float(v_data['x']), float(v_data['y'])

            # Query flood depth at both endpoints
            depth_u = self.geotiff_service.get_flood_depth_at_point(
                u_lon, u_lat, rp, ts
            )
            depth_v = self.geotiff_service.get_flood_depth_at_point(
                v_lon, v_lat, rp, ts
            )

            # Calculate average depth (if at least one endpoint has data)
            depths = [d for d in [depth_u, depth_v] if d is not None]
            if depths:
                avg_depth = sum(depths) / len(depths)
                return avg_depth
            else:
                return None

        except Exception as e:
            logger.debug(f"Error querying flood depth for edge ({u},{v}): {e}")
            return None

    def get_edge_flood_depths(
        self,
        return_period: Optional[str] = None,
        time_step: Optional[int] = None
    ) -> Dict[Tuple, float]:
        """
        Query flood depths for all edges in the graph.

        Args:
            return_period: Return period (rr01-rr04), uses default if None
            time_step: Time step (1-18), uses default if None

        Returns:
            Dict mapping edge tuples to flood depths in meters
                Format: {(u, v, key): depth, ...}
        """
        if not self.geotiff_service or not self.environment or not self.environment.graph:
            logger.warning("GeoTIFF service or graph not available")
            return {}

        edge_depths = {}
        rp = return_period or self.return_period
        ts = time_step or self.time_step

        logger.info(f"Querying flood depths for all edges (rp={rp}, ts={ts})")

        edge_count = 0
        flooded_count = 0

        for u, v, key in self.environment.graph.edges(keys=True):
            depth = self.get_flood_depth_at_edge(u, v, rp, ts)

            if depth is not None and depth > 0.01:  # Threshold: 1cm
                edge_depths[(u, v, key)] = depth
                flooded_count += 1

            edge_count += 1

        logger.info(
            f"Flood depth query complete: {flooded_count}/{edge_count} edges flooded "
            f"(>{0.01}m)"
        )

        return edge_depths

    def set_flood_scenario(
        self, return_period: str = "rr01", time_step: int = 1
    ) -> None:
        """
        Dynamically configure the flood scenario for GeoTIFF queries.

        This allows the HazardAgent to switch between different flood scenarios
        (return periods) and time steps for flood prediction.

        Args:
            return_period: Return period to use (rr01, rr02, rr03, rr04)
                - rr01: 2-year return period
                - rr02: 5-year return period
                - rr03: 10-year return period
                - rr04: 25-year return period
            time_step: Time step in hours (1-18)

        Raises:
            ValueError: If return_period or time_step is invalid

        Example:
            >>> hazard_agent.set_flood_scenario("rr03", 12)  # 10-year, 12 hours
        """
        valid_return_periods = ["rr01", "rr02", "rr03", "rr04"]
        if return_period not in valid_return_periods:
            raise ValueError(
                f"Invalid return_period '{return_period}'. Must be one of {valid_return_periods}"
            )

        if not 1 <= time_step <= 18:
            raise ValueError(f"Invalid time_step {time_step}. Must be between 1 and 18")

        self.return_period = return_period
        self.time_step = time_step

        logger.info(
            f"{self.agent_id} flood scenario updated: "
            f"return_period={return_period}, time_step={time_step}"
        )

    def calculate_risk_scores(self, fused_data: Dict[str, Any]) -> Dict[Tuple, float]:
        """
        Calculate risk scores for road segments based on GeoTIFF flood depths and fused data.

        Combines:
        1. GeoTIFF flood depth data (spatial flood extents)
        2. Fused data from FloodAgent and ScoutAgent (river levels, weather, crowdsourced)

        Args:
            fused_data: Fused data from multiple sources

        Returns:
            Dict mapping edge tuples to risk scores (0.0-1.0)
                Format: {(u, v, key): risk_score, ...}
        """
        logger.debug(f"{self.agent_id} calculating risk scores with GeoTIFF integration")

        if not self.environment or not hasattr(self.environment, 'graph') or not self.environment.graph:
            logger.warning("Graph environment not available for risk calculation")
            return {}

        risk_scores = {}

        # Query GeoTIFF flood depths for all edges
        edge_flood_depths = self.get_edge_flood_depths()

        # Convert flood depths to risk scores
        # Risk mapping: depth -> risk_score
        #   0.0-0.3m: low risk (0.0-0.3)
        #   0.3-0.6m: moderate risk (0.3-0.6)
        #   0.6-1.0m: high risk (0.6-0.8)
        #   >1.0m: critical risk (0.8-1.0)
        for edge_tuple, depth in edge_flood_depths.items():
            if depth <= 0.3:
                risk_from_depth = depth  # Linear: 0.3m = 0.3 risk
            elif depth <= 0.6:
                risk_from_depth = 0.3 + (depth - 0.3) * 1.0  # 0.3-0.6m -> 0.3-0.6 risk
            elif depth <= 1.0:
                risk_from_depth = 0.6 + (depth - 0.6) * 0.5  # 0.6-1.0m -> 0.6-0.8 risk
            else:
                risk_from_depth = min(0.8 + (depth - 1.0) * 0.2, 1.0)  # >1.0m -> 0.8-1.0 risk

            risk_scores[edge_tuple] = risk_from_depth * self.risk_weights["flood_depth"]

        # Add risk from fused data (river levels, weather, crowdsourced)
        # Apply a base risk from environmental conditions
        for location, data in fused_data.items():
            risk_level = data["risk_level"]

            # Apply environmental risk to all edges (global modifier)
            # This represents system-wide conditions (heavy rain, rising river levels)
            for edge_tuple in list(self.environment.graph.edges(keys=True)):
                current_risk = risk_scores.get(edge_tuple, 0.0)

                # Combine GeoTIFF risk with environmental risk
                # Environmental risk acts as a multiplier/modifier
                environmental_factor = risk_level * (
                    self.risk_weights["crowdsourced"] + self.risk_weights["historical"]
                )

                # Take max to preserve highest risk
                combined_risk = max(current_risk, current_risk + environmental_factor)
                risk_scores[edge_tuple] = min(combined_risk, 1.0)  # Cap at 1.0

        # Count risk distribution
        if risk_scores:
            low_risk = sum(1 for r in risk_scores.values() if r < 0.3)
            mod_risk = sum(1 for r in risk_scores.values() if 0.3 <= r < 0.6)
            high_risk = sum(1 for r in risk_scores.values() if 0.6 <= r < 0.8)
            crit_risk = sum(1 for r in risk_scores.values() if r >= 0.8)

            logger.info(
                f"Calculated risk scores for {len(risk_scores)} edges using GeoTIFF data. "
                f"Distribution: low={low_risk}, moderate={mod_risk}, high={high_risk}, critical={crit_risk}"
            )
        else:
            logger.info("No risk scores calculated (no flooded edges detected)")

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
