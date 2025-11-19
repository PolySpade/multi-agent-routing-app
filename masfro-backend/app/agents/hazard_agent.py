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
from app.core.timezone_utils import get_philippine_time
import math

if TYPE_CHECKING:
    from ..environment.graph_manager import DynamicGraphEnvironment

# GeoTIFF service import
try:
    from services.geotiff_service import get_geotiff_service
except ImportError:
    from app.services.geotiff_service import get_geotiff_service

# LocationGeocoder import
try:
    from app.ml_models.location_geocoder import LocationGeocoder
except ImportError:
    LocationGeocoder = None

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
        environment: "DynamicGraphEnvironment",
        enable_geotiff: bool = False
    ) -> None:
        """
        Initialize the HazardAgent.

        Args:
            agent_id: Unique identifier for this agent
            environment: DynamicGraphEnvironment instance for graph updates
            enable_geotiff: Enable GeoTIFF flood simulation (default: True)
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

        # GeoTIFF simulation control flag
        self.geotiff_enabled = enable_geotiff

        # GeoTIFF service for flood depth queries
        if self.geotiff_enabled:
            try:
                self.geotiff_service = get_geotiff_service()
                logger.info(f"{self.agent_id} initialized GeoTIFFService (ENABLED)")
            except Exception as e:
                logger.error(f"Failed to initialize GeoTIFFService: {e}")
                self.geotiff_service = None
                self.geotiff_enabled = False
        else:
            self.geotiff_service = None
            logger.info(f"{self.agent_id} GeoTIFF integration DISABLED")

        # Flood prediction configuration (default: rr01, time_step 1)
        self.return_period = "rr01"  # Default return period
        self.time_step = 1  # Default time step (1 hour)

        # Risk decay configuration - Realistic flood recession modeling
        self.enable_risk_decay = True  # Enable time-based risk decay
        self.scout_decay_rate_fast = 0.10  # 10% per minute (rain-based flooding, drains quickly)
        self.scout_decay_rate_slow = 0.03  # 3% per minute (river/dam flooding, slow recession)
        self.flood_decay_rate = 0.05  # 5% per minute (official data decay)
        self.scout_report_ttl_minutes = 45  # Scout reports expire after 45 min
        self.flood_data_ttl_minutes = 90  # Flood data expires after 90 min
        self.risk_floor_without_validation = 0.15  # Minimum risk until scout validates "clear"
        self.min_risk_threshold = 0.01  # Clear risk below this value

        # ML model placeholder (to be integrated later)
        self.flood_predictor = None

        # Initialize LocationGeocoder for coordinate-based risk updates
        try:
            if LocationGeocoder:
                self.geocoder = LocationGeocoder()
                logger.info(f"{self.agent_id} LocationGeocoder initialized")
            else:
                self.geocoder = None
                logger.warning(f"{self.agent_id} LocationGeocoder not available")
        except Exception as e:
            logger.error(f"Failed to initialize LocationGeocoder: {e}")
            self.geocoder = None

        # Risk trend tracking
        self.previous_average_risk = 0.0
        self.last_update_time = None
        self.risk_history = []  # List of (timestamp, avg_risk) tuples

        logger.info(
            f"{self.agent_id} initialized with risk weights: {self.risk_weights}, "
            f"return_period: {self.return_period}, time_step: {self.time_step}, "
            f"geotiff_enabled: {self.geotiff_enabled}, "
            f"risk_decay: {'ENABLED' if self.enable_risk_decay else 'DISABLED'}"
        )

    def clear_caches(self) -> None:
        """
        Clear all cached data.

        This method should be called when resetting the simulation or
        when you want to start fresh with new data.
        """
        self.flood_data_cache.clear()
        self.scout_data_cache.clear()
        logger.info(f"{self.agent_id} caches cleared")

    def calculate_data_age_minutes(self, timestamp: Any) -> float:
        """
        Calculate age of data in minutes from its timestamp.

        Args:
            timestamp: datetime object or ISO string

        Returns:
            Age in minutes
        """
        from datetime import datetime, timezone
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except:
                logger.warning(f"Invalid timestamp format: {timestamp}")
                return 0.0

        if timestamp is None:
            return 0.0

        # Make both datetimes timezone-aware for comparison
        current_time = datetime.now(timezone.utc)

        # If timestamp is naive, assume it's UTC
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        age_seconds = (current_time - timestamp).total_seconds()
        return max(0.0, age_seconds / 60.0)

    def apply_time_decay(self, base_value: float, age_minutes: float, decay_rate: float) -> float:
        """
        Apply exponential decay to a value based on age.

        Formula: value × e^(-decay_rate × age)

        Args:
            base_value: Original value (e.g., risk score)
            age_minutes: Age of data in minutes
            decay_rate: Decay rate per minute (e.g., 0.1 = 10% per minute)

        Returns:
            Decayed value

        Example:
            >>> apply_time_decay(0.8, 10, 0.1)  # 0.8 risk, 10 min old, 10%/min decay
            0.294  # Decayed to ~37% of original
        """
        import math
        if age_minutes <= 0:
            return base_value
        decay_factor = math.exp(-decay_rate * age_minutes)
        return base_value * decay_factor

    def determine_decay_rate(self, report_type: str = "flood") -> float:
        """
        Determine appropriate decay rate based on flood type and current conditions.

        Rain-based flooding: Fast decay (water drains quickly)
        River/dam flooding: Slow decay (water recedes slowly)

        Args:
            report_type: Type of report ("rain_report", "flood", "clear")

        Returns:
            Decay rate per minute
        """
        # Check if rivers/dams are still elevated (persistent flooding)
        river_elevated = self._check_river_levels_elevated()

        if river_elevated:
            # Slow decay - river/dam still flooded
            return self.scout_decay_rate_slow
        elif report_type == "rain_report":
            # Fast decay - rain-based flooding drains quickly
            return self.scout_decay_rate_fast
        else:
            # Default moderate decay
            return (self.scout_decay_rate_fast + self.scout_decay_rate_slow) / 2

    def _check_river_levels_elevated(self) -> bool:
        """
        Check if river levels or dam levels are still elevated.

        Returns:
            True if any river/dam is above normal (alert/alarm/critical)
        """
        for location, data in self.flood_data_cache.items():
            status = data.get('status', 'normal')
            if status in ['alert', 'alarm', 'critical']:
                return True

            # Check water level vs alert level
            water_level = data.get('water_level_m')
            alert_level = data.get('alert_level_m')
            if water_level and alert_level and water_level >= alert_level * 0.9:
                return True  # Within 90% of alert level

        return False

    def clean_expired_data(self) -> Dict[str, int]:
        """
        Remove expired data from caches based on TTL.

        Returns:
            Dict with counts of expired items
        """
        from datetime import datetime
        current_time = datetime.now()
        expired_counts = {"scouts": 0, "flood_locations": 0}

        # Clean expired scout reports
        original_scout_count = len(self.scout_data_cache)
        self.scout_data_cache = [
            report for report in self.scout_data_cache
            if self.calculate_data_age_minutes(report.get('timestamp')) < self.scout_report_ttl_minutes
        ]
        expired_counts["scouts"] = original_scout_count - len(self.scout_data_cache)

        # Clean expired flood data
        expired_locations = []
        for location, data in self.flood_data_cache.items():
            age = self.calculate_data_age_minutes(data.get('timestamp'))
            if age >= self.flood_data_ttl_minutes:
                expired_locations.append(location)

        for location in expired_locations:
            del self.flood_data_cache[location]
        expired_counts["flood_locations"] = len(expired_locations)

        if expired_counts["scouts"] > 0 or expired_counts["flood_locations"] > 0:
            logger.info(
                f"{self.agent_id} cleaned expired data: "
                f"{expired_counts['scouts']} scout reports, "
                f"{expired_counts['flood_locations']} flood locations"
            )

        return expired_counts

    def check_scout_validation_for_area(self, lat: float, lon: float, radius_m: float = 1000) -> bool:
        """
        Check if scouts have validated clearance (report_type="clear") near a location.

        Args:
            lat: Latitude
            lon: Longitude
            radius_m: Search radius in meters

        Returns:
            True if any scout reported "clear" within radius in last 15 minutes
        """
        from datetime import datetime, timedelta
        current_time = datetime.now()
        validation_window = timedelta(minutes=15)

        for report in self.scout_data_cache:
            # Check if it's a "clear" report
            if report.get('report_type') != 'clear':
                continue

            # Check if it's recent
            timestamp = report.get('timestamp')
            if timestamp:
                age = self.calculate_data_age_minutes(timestamp)
                if age > 15:  # Too old
                    continue

            # Check if it's nearby
            coords = report.get('coordinates', {})
            if not coords:
                continue

            report_lat = coords.get('lat')
            report_lon = coords.get('lon')
            if report_lat is None or report_lon is None:
                continue

            # Calculate distance (simple approximation)
            import math
            lat_diff = (report_lat - lat) * 111000  # 111km per degree latitude
            lon_diff = (report_lon - lon) * 111000 * math.cos(math.radians(lat))
            distance = math.sqrt(lat_diff**2 + lon_diff**2)

            if distance <= radius_m:
                return True  # Found validation!

        return False  # No validation found

    def step(self):
        """
        Perform one step of the agent's operation.

        In each step, the agent:
        1. Processes any new data from caches
        2. Fuses data from multiple sources
        3. Calculates risk scores
        4. Updates the graph environment
        """
        logger.debug(f"{self.agent_id} performing step at {get_philippine_time()}")

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
            "timestamp": get_philippine_time()
        }

    def update_risk(
        self,
        flood_data: Dict[str, Any],
        scout_data: List[Dict[str, Any]],
        time_step: int
    ) -> Dict[str, Any]:
        """
        Update risk assessment based on external data (called by SimulationManager).

        This method is the entry point for the tick-based architecture. It receives
        data from the SimulationManager, updates the HazardAgent's internal caches,
        sets the GeoTIFF scenario, and updates the graph.

        Args:
            flood_data: Flood data from FloodAgent
            scout_data: Scout reports from ScoutAgent
            time_step: Current simulation time step (1-18)

        Returns:
            Dict with update results
                Format:
                {
                    "locations_processed": int,
                    "edges_updated": int,
                    "time_step": int,
                    "timestamp": str
                }

        Example:
            >>> result = hazard_agent.update_risk(
            ...     flood_data={"Sto Nino": {...}},
            ...     scout_data=[{...}],
            ...     time_step=5
            ... )
        """
        logger.info(
            f"{self.agent_id} updating risk assessment - "
            f"flood_data: {len(flood_data)} points, "
            f"scout_data: {len(scout_data)} reports, "
            f"time_step: {time_step}/18"
        )

        # FIXED: Don't clear caches - accumulate data across ticks
        # Only clear when explicitly needed (e.g., simulation reset)

        # Clean expired data first (time-based decay)
        if self.enable_risk_decay:
            expired_counts = self.clean_expired_data()
            if expired_counts["scouts"] > 0 or expired_counts["flood_locations"] > 0:
                logger.debug(
                    f"Expired data removed: {expired_counts['scouts']} scouts, "
                    f"{expired_counts['flood_locations']} flood locations"
                )

        # Update flood data cache (only if new data received)
        if flood_data:
            for location, data in flood_data.items():
                flood_data_entry = {
                    "location": location,
                    "flood_depth": data.get("flood_depth", 0.0),
                    "rainfall_1h": data.get("rainfall_1h", 0.0),
                    "rainfall_24h": data.get("rainfall_24h", 0.0),
                    "timestamp": data.get("timestamp")
                }
                self.flood_data_cache[location] = flood_data_entry
            logger.debug(f"Updated flood_data_cache with {len(flood_data)} locations")

        # Update scout data cache (accumulate new reports)
        if scout_data:
            self.scout_data_cache.extend(scout_data)
            logger.debug(f"Added {len(scout_data)} scout reports (total: {len(self.scout_data_cache)})")

        # Ensure GeoTIFF is set to current time step (already done by SimulationManager)
        # This is a safety check
        if self.time_step != time_step:
            logger.warning(
                f"HazardAgent time_step mismatch: expected {time_step}, "
                f"got {self.time_step}. Correcting..."
            )
            self.time_step = time_step

        # ADDED: Process scout data spatially if coordinates are present
        # Separate coordinate-based reports from location-name reports
        reports_with_coords = []
        reports_without_coords = []

        if scout_data:
            for report in scout_data:
                if (report.get('coordinates') and
                    isinstance(report.get('coordinates'), dict) and
                    report['coordinates'].get('lat') is not None and
                    report['coordinates'].get('lon') is not None):
                    reports_with_coords.append(report)
                else:
                    reports_without_coords.append(report)

            if reports_with_coords:
                logger.info(
                    f"{self.agent_id} applying SPATIAL risk updates for "
                    f"{len(reports_with_coords)} coordinate-based scout reports"
                )
                self.process_scout_data_with_coordinates(reports_with_coords)

            if reports_without_coords:
                logger.info(
                    f"{self.agent_id} will apply GLOBAL risk for "
                    f"{len(reports_without_coords)} location-name scout reports"
                )

        # Process data and update graph
        # Pass flag to exclude coordinate-based reports from global processing
        fused_data = self.fuse_data(exclude_coordinate_reports=True)
        risk_scores = self.calculate_risk_scores(fused_data)
        self.update_environment(risk_scores)

        # Calculate risk trend metrics
        current_time = get_philippine_time()
        average_risk = sum(risk_scores.values()) / len(risk_scores) if risk_scores else 0.0

        # Determine trend
        risk_trend = "stable"
        risk_change_rate = 0.0

        if self.last_update_time and self.enable_risk_decay:
            time_diff_minutes = (current_time - self.last_update_time).total_seconds() / 60.0
            if time_diff_minutes > 0:
                risk_delta = average_risk - self.previous_average_risk
                risk_change_rate = risk_delta / time_diff_minutes

                # Classify trend (threshold: 0.001 per minute = 0.06 per hour)
                if risk_change_rate > 0.001:
                    risk_trend = "increasing"
                elif risk_change_rate < -0.001:
                    risk_trend = "decreasing"

        # Track risk history (keep last 20 data points)
        self.risk_history.append((current_time, average_risk))
        if len(self.risk_history) > 20:
            self.risk_history = self.risk_history[-20:]

        # Update tracking variables
        self.previous_average_risk = average_risk
        self.last_update_time = current_time

        # Calculate cache statistics
        active_scouts = len(self.scout_data_cache)
        oldest_scout_age = 0.0
        if self.scout_data_cache:
            ages = [self.calculate_data_age_minutes(r.get('timestamp')) for r in self.scout_data_cache]
            oldest_scout_age = max(ages) if ages else 0.0

        logger.info(
            f"{self.agent_id} risk update complete - "
            f"processed {len(fused_data)} locations, "
            f"updated {len(risk_scores)} edges, "
            f"avg_risk={average_risk:.4f}, trend={risk_trend}"
        )

        return {
            "locations_processed": len(fused_data),
            "edges_updated": len(risk_scores),
            "time_step": time_step,
            "timestamp": current_time.isoformat(),
            "average_risk": round(average_risk, 4),
            "risk_trend": risk_trend,
            "risk_change_rate": round(risk_change_rate, 6),
            "active_reports": active_scouts,
            "oldest_report_age_min": round(oldest_scout_age, 1)
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

        # Note: No immediate processing triggered. Use process_flood_data_batch()
        # for optimal performance, or call process_and_update() manually when ready.

    def process_flood_data_batch(self, data: Dict[str, Dict[str, Any]]) -> None:
        """
        Process multiple flood data points in batch (optimized).

        This method is more efficient than calling process_flood_data() multiple
        times, as it updates the cache for all locations first, then triggers
        risk calculation only once.

        Args:
            data: Dict mapping locations to flood data
                Expected format:
                {
                    "IPO": {
                        "flood_depth": float,
                        "rainfall_1h": float,
                        "rainfall_24h": float,
                        "timestamp": datetime
                    },
                    "LA MESA": {...},
                    ...
                }

        Example:
            >>> batch_data = {
            ...     "IPO": {"flood_depth": 1.5, "timestamp": datetime.now()},
            ...     "LA MESA": {"flood_depth": 2.0, "timestamp": datetime.now()}
            ... }
            >>> hazard_agent.process_flood_data_batch(batch_data)
        """
        logger.info(
            f"{self.agent_id} received batched flood data for {len(data)} locations"
        )

        valid_count = 0
        invalid_count = 0

        # Update cache for all locations
        for location, location_data in data.items():
            flood_data = {
                "location": location,
                "flood_depth": location_data.get("flood_depth", 0.0),
                "rainfall_1h": location_data.get("rainfall_1h", 0.0),
                "rainfall_24h": location_data.get("rainfall_24h", 0.0),
                "timestamp": location_data.get("timestamp")
            }

            # Validate data before caching
            if self._validate_flood_data(flood_data):
                self.flood_data_cache[location] = flood_data
                valid_count += 1
            else:
                logger.warning(f"Invalid flood data for location: {location}")
                invalid_count += 1

        logger.info(
            f"{self.agent_id} cached {valid_count} valid data points "
            f"({invalid_count} invalid)"
        )

        # Trigger processing ONCE after all data cached
        if valid_count > 0:
            logger.info(
                f"{self.agent_id} triggering hazard processing after batch update"
            )
            self.process_and_update()
        else:
            logger.warning(
                f"{self.agent_id} no valid data to process in batch"
            )

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

    def fuse_data(self, exclude_coordinate_reports: bool = False) -> Dict[str, Any]:
        """
        Fuse data from multiple sources (FloodAgent and ScoutAgent).

        Combines official flood measurements with crowdsourced reports to
        create a comprehensive risk assessment. Uses weighted averaging
        based on data source reliability and timeliness.

        Args:
            exclude_coordinate_reports: If True, exclude scout reports that have
                coordinates (as they are processed spatially, not globally)

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
        logger.debug(
            f"{self.agent_id} fusing data from multiple sources "
            f"(exclude_coordinate_reports={exclude_coordinate_reports})"
        )

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
            # Skip coordinate-based reports if requested (they're processed spatially)
            if exclude_coordinate_reports:
                has_coords = (
                    report.get('coordinates') and
                    isinstance(report.get('coordinates'), dict) and
                    report['coordinates'].get('lat') is not None and
                    report['coordinates'].get('lon') is not None
                )
                if has_coords:
                    continue  # Skip this report - already processed spatially

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
            report_type = report.get("report_type", "flood")

            # Apply time-based decay to severity
            if self.enable_risk_decay:
                age_minutes = self.calculate_data_age_minutes(report.get('timestamp'))
                decay_rate = self.determine_decay_rate(report_type)
                severity = self.apply_time_decay(severity, age_minutes, decay_rate)

                logger.debug(
                    f"Scout report at {location}: age={age_minutes:.1f}min, "
                    f"decay_rate={decay_rate:.3f}, decayed_severity={severity:.3f}"
                )

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
        # Check if GeoTIFF is enabled
        if not self.geotiff_enabled:
            logger.info("GeoTIFF integration disabled - skipping flood depth queries")
            return {}

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

    def enable_geotiff(self) -> None:
        """
        Enable GeoTIFF flood simulation.

        If GeoTIFF service was not initialized, attempts to initialize it.

        Example:
            >>> hazard_agent.enable_geotiff()
        """
        if self.geotiff_enabled:
            logger.info(f"{self.agent_id} GeoTIFF already enabled")
            return

        # Try to initialize service if not available
        if not self.geotiff_service:
            try:
                self.geotiff_service = get_geotiff_service()
                logger.info(f"{self.agent_id} GeoTIFFService initialized")
            except Exception as e:
                logger.error(f"Failed to initialize GeoTIFFService: {e}")
                return

        self.geotiff_enabled = True
        logger.info(f"{self.agent_id} GeoTIFF flood simulation ENABLED")

    def disable_geotiff(self) -> None:
        """
        Disable GeoTIFF flood simulation.

        When disabled, risk calculation will only use FloodAgent and ScoutAgent data.

        Example:
            >>> hazard_agent.disable_geotiff()
        """
        if not self.geotiff_enabled:
            logger.info(f"{self.agent_id} GeoTIFF already disabled")
            return

        self.geotiff_enabled = False
        logger.info(f"{self.agent_id} GeoTIFF flood simulation DISABLED")

    def is_geotiff_enabled(self) -> bool:
        """
        Check if GeoTIFF flood simulation is currently enabled.

        Returns:
            True if enabled, False otherwise

        Example:
            >>> if hazard_agent.is_geotiff_enabled():
            ...     print("GeoTIFF simulation active")
        """
        return self.geotiff_enabled

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

        # Apply time-based decay to existing spatial risk scores
        # This allows risk from old scout reports to naturally decay over time
        risk_scores = {}
        if self.enable_risk_decay:
            # Apply decay to preserved spatial risk
            for u, v, key in self.environment.graph.edges(keys=True):
                existing_risk = self.environment.graph[u][v][key].get('risk_score', 0.0)
                if existing_risk > 0.0:
                    # Get edge metadata to check when it was last updated
                    edge_data = self.environment.graph[u][v][key]
                    last_update = edge_data.get('last_risk_update')

                    if last_update:
                        age_minutes = self.calculate_data_age_minutes(last_update)
                        # Use spatial risk decay rate (8% per minute)
                        decay_rate = 0.08
                        decayed_risk = self.apply_time_decay(existing_risk, age_minutes, decay_rate)

                        # Only preserve risk above minimum threshold
                        if decayed_risk > self.min_risk_threshold:
                            risk_scores[(u, v, key)] = decayed_risk
                    else:
                        # No timestamp - preserve as-is for backward compatibility
                        risk_scores[(u, v, key)] = existing_risk
        else:
            # Decay disabled - preserve existing risk (old behavior)
            for u, v, key in self.environment.graph.edges(keys=True):
                existing_risk = self.environment.graph[u][v][key].get('risk_score', 0.0)
                if existing_risk > 0.0:
                    risk_scores[(u, v, key)] = existing_risk

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
                # Environmental risk acts as an additive modifier
                environmental_factor = risk_level * (
                    self.risk_weights["crowdsourced"] + self.risk_weights["historical"]
                )

                # FIXED: Allow risk to decrease by replacing instead of using max()
                # Current risk reflects GeoTIFF + decayed spatial risk
                # Environmental factor adds current weather/river conditions
                combined_risk = current_risk + environmental_factor
                risk_scores[edge_tuple] = min(combined_risk, 1.0)  # Cap at 1.0

        # Count risk distribution
        if risk_scores:
            low_risk = sum(1 for r in risk_scores.values() if r < 0.3)
            mod_risk = sum(1 for r in risk_scores.values() if 0.3 <= r < 0.6)
            high_risk = sum(1 for r in risk_scores.values() if 0.6 <= r < 0.8)
            crit_risk = sum(1 for r in risk_scores.values() if r >= 0.8)

            logger.info(
                f"Calculated risk scores for {len(risk_scores)} edges. "
                f"Distribution: low={low_risk}, moderate={mod_risk}, high={high_risk}, critical={crit_risk}"
            )
        else:
            logger.info("No risk scores calculated (no flooded edges detected)")

        return risk_scores

    def update_environment(self, risk_scores: Dict[Tuple, float]) -> None:
        """
        Update the Dynamic Graph Environment with calculated risk scores.

        Also tracks the last update timestamp for time-based decay.

        Args:
            risk_scores: Dict mapping edge tuples to risk scores
        """
        from datetime import datetime
        logger.debug(f"{self.agent_id} updating environment with risk scores")

        if not self.environment or not hasattr(self.environment, 'update_edge_risk'):
            logger.warning("Environment not configured for risk updates")
            return

        current_time = datetime.now()

        for (u, v, key), risk in risk_scores.items():
            try:
                self.environment.update_edge_risk(u, v, key, risk)

                # Track when this edge was last updated (for decay calculation)
                if self.enable_risk_decay:
                    edge_data = self.environment.graph[u][v][key]
                    edge_data['last_risk_update'] = current_time
            except Exception as e:
                logger.error(f"Failed to update edge ({u}, {v}, {key}): {e}")

        logger.info(f"Updated {len(risk_scores)} edges in the environment")

    def get_nearest_node(self, lat: float, lon: float) -> Optional[int]:
        """
        Find the nearest graph node to a coordinate.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            Node ID of nearest node, or None if graph not available

        Example:
            >>> node_id = hazard_agent.get_nearest_node(14.6507, 121.1009)
        """
        if not self.environment or not self.environment.graph:
            return None

        try:
            # Use OSMnx to find nearest node
            import osmnx as ox
            nearest_node = ox.distance.nearest_nodes(
                self.environment.graph,
                lon,  # OSMnx uses (lon, lat) order
                lat
            )
            return nearest_node
        except Exception as e:
            logger.error(f"Error finding nearest node to ({lat}, {lon}): {e}")
            return None

    def calculate_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        """
        Calculate distance between two coordinates in meters using Haversine formula.

        Args:
            lat1: Latitude of point 1
            lon1: Longitude of point 1
            lat2: Latitude of point 2
            lon2: Longitude of point 2

        Returns:
            Distance in meters

        Example:
            >>> distance = hazard_agent.calculate_distance(14.65, 121.10, 14.66, 121.11)
        """
        # Earth radius in meters
        R = 6371000

        # Convert to radians
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        # Haversine formula
        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        distance = R * c
        return distance

    def get_nodes_within_radius(
        self,
        lat: float,
        lon: float,
        radius_m: float = 500
    ) -> List[int]:
        """
        Find all graph nodes within radius of a point.

        Args:
            lat: Center latitude
            lon: Center longitude
            radius_m: Radius in meters (default: 500m)

        Returns:
            List of node IDs within radius

        Example:
            >>> nearby_nodes = hazard_agent.get_nodes_within_radius(14.65, 121.10, 1000)
        """
        if not self.environment or not self.environment.graph:
            return []

        nearby_nodes = []

        try:
            for node in self.environment.graph.nodes():
                node_data = self.environment.graph.nodes[node]
                node_lat = float(node_data.get('y', 0))
                node_lon = float(node_data.get('x', 0))

                distance = self.calculate_distance(lat, lon, node_lat, node_lon)

                if distance <= radius_m:
                    nearby_nodes.append(node)

        except Exception as e:
            logger.error(f"Error finding nodes within radius: {e}")

        return nearby_nodes

    def update_node_risk(
        self,
        node_id: int,
        risk_level: float,
        source: str = "scout"
    ) -> None:
        """
        Update risk for all edges connected to a node.

        Args:
            node_id: Node ID
            risk_level: Risk level (0-1)
            source: Data source identifier

        Example:
            >>> hazard_agent.update_node_risk(12345, 0.8, "scout_twitter")
        """
        if not self.environment or not self.environment.graph:
            return

        try:
            # Get all edges connected to this node
            edges_updated = 0

            for u, v, key in self.environment.graph.edges(node_id, keys=True):
                self.environment.update_edge_risk(u, v, key, risk_level)
                edges_updated += 1

            # Also check incoming edges
            for u, v, key in self.environment.graph.in_edges(node_id, keys=True):
                self.environment.update_edge_risk(u, v, key, risk_level)
                edges_updated += 1

            logger.debug(
                f"Updated {edges_updated} edges connected to node {node_id} "
                f"with risk {risk_level:.2f} (source: {source})"
            )

        except Exception as e:
            logger.error(f"Error updating node risk for node {node_id}: {e}")

    def process_scout_data_with_coordinates(
        self,
        scout_reports: List[Dict[str, Any]]
    ) -> None:
        """
        Process crowdsourced data with coordinate-based risk updates.

        Enhanced version of process_scout_data that handles geographic coordinates
        and propagates risk spatially across the graph.

        Args:
            scout_reports: List of crowdsourced reports with coordinates
                Expected format:
                [
                    {
                        "location": str,
                        "coordinates": {"lat": float, "lon": float},
                        "severity": float,  # 0-1 scale
                        "report_type": str,
                        "confidence": float,
                        "timestamp": datetime
                    },
                    ...
                ]

        Example:
            >>> reports = [{
            ...     "location": "Nangka",
            ...     "coordinates": {"lat": 14.6507, "lon": 121.1009},
            ...     "severity": 0.8,
            ...     "confidence": 0.9
            ... }]
            >>> hazard_agent.process_scout_data_with_coordinates(reports)
        """
        logger.info(
            f"{self.agent_id} processing {len(scout_reports)} scout reports "
            f"with coordinate-based risk updates"
        )

        reports_processed = 0
        nodes_updated = 0

        for report in scout_reports:
            try:
                # Validate report
                if not self._validate_scout_data(report):
                    logger.warning(f"Invalid scout report: {report}")
                    continue

                # Check for duplicates before adding to cache
                # Deduplicate based on location + text (same report)
                is_duplicate = False
                report_location = report.get('location', '')
                report_text = report.get('text', '')

                for existing in self.scout_data_cache:
                    if (existing.get('location') == report_location and
                        existing.get('text') == report_text):
                        is_duplicate = True
                        break

                # Add to cache only if not duplicate
                if not is_duplicate:
                    self.scout_data_cache.append(report)
                else:
                    logger.debug(f"Skipping duplicate scout report: {report_location}")

                # Check if report has coordinates
                coords = report.get('coordinates')
                if not coords or not isinstance(coords, dict):
                    # No coordinates - use legacy processing
                    continue

                lat = coords.get('lat')
                lon = coords.get('lon')

                if lat is None or lon is None:
                    continue

                # Extract severity and confidence
                severity = report.get('severity', 0.0)
                confidence = report.get('confidence', 0.5)

                # Calculate actual risk level
                risk_level = severity * confidence

                # Find nearest graph node
                nearest_node = self.get_nearest_node(lat, lon)

                if nearest_node is None:
                    logger.warning(
                        f"Could not find nearest node for location {report.get('location')} "
                        f"at ({lat}, {lon})"
                    )
                    continue

                # Update risk at the nearest node
                self.update_node_risk(nearest_node, risk_level, source="scout_direct")
                nodes_updated += 1

                # Propagate risk to nearby nodes (spatial diffusion)
                # Risk decays with distance
                radius_m = 500  # 500 meter radius
                nearby_nodes = self.get_nodes_within_radius(lat, lon, radius_m)

                for node in nearby_nodes:
                    if node == nearest_node:
                        continue  # Already updated

                    # Get node coordinates
                    node_data = self.environment.graph.nodes[node]
                    node_lat = float(node_data.get('y', 0))
                    node_lon = float(node_data.get('x', 0))

                    # Calculate distance
                    distance = self.calculate_distance(lat, lon, node_lat, node_lon)

                    # Apply distance decay: risk decreases linearly with distance
                    decay_factor = 1.0 - (distance / radius_m)
                    decayed_risk = risk_level * decay_factor

                    # Only update if decayed risk is significant
                    if decayed_risk > 0.05:
                        self.update_node_risk(node, decayed_risk, source="scout_propagated")
                        nodes_updated += 1

                reports_processed += 1

            except Exception as e:
                logger.error(f"Error processing scout report: {e}", exc_info=True)
                continue

        logger.info(
            f"Processed {reports_processed}/{len(scout_reports)} scout reports, "
            f"updated {nodes_updated} graph nodes with coordinate-based risk"
        )

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
        current_time = get_philippine_time()

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
