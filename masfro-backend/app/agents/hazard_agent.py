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
from collections import deque
import hashlib
import logging
import time
from datetime import datetime, timedelta, timezone
from app.core.timezone_utils import get_philippine_time
from app.core.agent_config import get_config, HazardConfig
from app.core.sim_clock import sim_clock
import math

if TYPE_CHECKING:
    from ..environment.graph_manager import DynamicGraphEnvironment
    from ..communication.message_queue import MessageQueue

# DEM service import (optional — missing at install time is OK)
try:
    from ..services.dem_service import get_dem_service
except ImportError:
    get_dem_service = None

# River proximity service import (optional — geopandas/shapely may not be present)
try:
    from ..services.river_proximity_service import get_river_proximity_service
except ImportError:
    get_river_proximity_service = None

# LocationGeocoder import (optional)
try:
    from ..ml_models.location_geocoder import LocationGeocoder
except ImportError:
    LocationGeocoder = None

# Haversine distance for spatial queries
from ..core.geo_utils import haversine_distance

# ACL Protocol imports for MAS communication
from ..communication.acl_protocol import ACLMessage, Performative, create_inform_message

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
        message_queue: Optional["MessageQueue"] = None
    ) -> None:
        """
        Initialize the HazardAgent.

        Args:
            agent_id: Unique identifier for this agent
            environment: DynamicGraphEnvironment instance for graph updates
            message_queue: MessageQueue instance for MAS communication
        """
        super().__init__(agent_id, environment, message_queue=message_queue)

        # Load configuration from YAML
        try:
            self._config = get_config().get_hazard_config()
        except Exception as e:
            logger.warning(f"Failed to load hazard config, using defaults: {e}")
            self._config = HazardConfig()

        # Data caches for fusion (sizes from config)
        self.flood_data_cache: Dict[str, Any] = {}
        # Use deque with maxlen for automatic LRU eviction (prevents memory leaks)
        self.scout_data_cache: deque = deque(maxlen=self._config.max_scout_cache)
        # O(1) deduplication set: stores (location, text_hash) tuples
        self.scout_cache_keys: set = set()

        # Flag to track if there's new unprocessed data (prevents redundant processing)
        # This solves the "log flooding" issue where step() would process every second
        # even when no new data had arrived
        self._has_unprocessed_data: bool = False

        # DEM service for terrain-based risk
        self.dem_enabled = self._config.enable_dem
        self.dem_service = None
        self._node_elevations: Dict = {}
        if self.dem_enabled:
            try:
                if get_dem_service is not None:
                    self.dem_service = get_dem_service(
                        self._config.dem_file_path,
                        regional_radius_pixels=self._config.dem_regional_radius_pixels,
                    )
                    logger.info(f"{self.agent_id} initialized DEMService (ENABLED)")
                else:
                    logger.warning(f"{self.agent_id} DEM service module not available")
                    self.dem_enabled = False
            except Exception as e:
                logger.error(f"Failed to initialize DEMService: {e}")
                self.dem_service = None
                self.dem_enabled = False
        else:
            logger.info(f"{self.agent_id} DEM integration DISABLED")

        # Static terrain/river priors seeded at startup — keyed by (u, v, key).
        # Used in the decay block to isolate dynamic flood risk from the static prior
        # so that the prior never compounds on itself each calculate_risk_scores() cycle.
        self._seeded_priors: Dict[Tuple, float] = {}

        # River proximity service for waterway-distance risk prior
        self.river_enabled = self._config.enable_river_proximity
        self.river_service = None
        self._node_river_data: Dict = {}
        if self.river_enabled:
            try:
                if get_river_proximity_service is not None:
                    self.river_service = get_river_proximity_service(
                        cache_file=self._config.river_cache_file,
                        fetch_place=self._config.river_fetch_place,
                    )
                    logger.info(f"{self.agent_id} initialized RiverProximityService (ENABLED)")
                else:
                    logger.warning(f"{self.agent_id} river proximity module not available")
                    self.river_enabled = False
            except Exception as e:
                logger.error(f"Failed to initialize RiverProximityService: {e}")
                self.river_service = None
                self.river_enabled = False
        else:
            logger.info(f"{self.agent_id} river proximity DISABLED")

        # Apply mutable config-derived attributes (shared with reload_config)
        self._apply_config()

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
        self.risk_history: deque = deque(maxlen=self._config.max_risk_history)  # Deque of (timestamp, avg_risk) tuples

        # Spatial index for optimized edge queries (Issue #16: configurable grid size)
        self.spatial_index: Optional[Dict[Tuple[int, int], List[Tuple]]] = None
        self.spatial_index_grid_size = self._config.grid_size_degrees  # Configurable grid cell size
        self._build_spatial_index()

        # Vehicle passability cache: maps (lat, lon) -> list of passable vehicle types
        self.vehicle_passability_cache: Dict[Tuple[float, float], List[str]] = {}

        # Automatic cleanup tracking
        self._last_cleanup = time.time()

        # Dead letter queue for failed message processing
        self.max_failed_messages = 100  # Limit size to prevent memory issues
        self.failed_messages: deque = deque(maxlen=self.max_failed_messages)
        self._last_retry = time.time()  # Track when we last retried failed messages
        self.retry_interval_seconds = 120  # Retry failed messages every 2 minutes

        logger.info(
            f"{self.agent_id} initialized with risk weights: {self.risk_weights}, "
            f"dem_enabled: {self.dem_enabled}, "
            f"river_proximity_enabled: {self.river_enabled}, "
            f"risk_decay: {'ENABLED' if self.enable_risk_decay else 'DISABLED'}, "
            f"spatial_filtering: {'ENABLED' if self.enable_spatial_filtering else 'DISABLED'} "
            f"(radius={self.environmental_risk_radius_m}m)"
        )

    def _apply_config(self) -> None:
        """Apply mutable config-derived attributes from self._config.

        Called from both __init__ and reload_config to keep them in sync.
        """
        self.risk_weights = {
            "flood_depth": self._config.weight_flood_depth,
            "crowdsourced": self._config.weight_crowdsourced,
            "historical": self._config.weight_historical,
        }
        self.enable_risk_decay = self._config.enable_risk_decay
        self.scout_decay_rate_fast = self._config.scout_fast_rate
        self.scout_decay_rate_slow = self._config.scout_slow_rate
        self.flood_decay_rate = self._config.flood_rate
        self.scout_report_ttl_minutes = self._config.scout_ttl_minutes
        self.flood_data_ttl_minutes = self._config.flood_ttl_minutes
        self.risk_floor_without_validation = self._config.risk_floor
        self.min_risk_threshold = self._config.min_threshold
        self.environmental_risk_radius_m = self._config.risk_radius_m
        self.enable_spatial_filtering = self._config.enable_spatial_filtering
        self.decay_function = self._config.decay_function

    def reload_config(self) -> None:
        """Hot-reload configuration from the singleton config loader."""
        try:
            self._config = get_config().get_hazard_config()
        except Exception as e:
            logger.warning(f"Failed to reload hazard config: {e}")
            return
        self._apply_config()
        logger.info(f"{self.agent_id} configuration reloaded")

    def get_agent_stats(self) -> Dict[str, Any]:
        """Get hazard agent statistics for the Agent Viewer dashboard."""
        return {
            "agent_id": self.agent_id,
            "dem_enabled": self.dem_enabled,
            "dem_service_available": self.dem_service is not None,
            "dem_nodes_with_elevation": len(self._node_elevations),
            "river_proximity_enabled": self.river_enabled,
            "river_service_available": self.river_service is not None,
            "river_nodes_computed": len(self._node_river_data),
            "geocoder_available": self.geocoder is not None,
            "flood_data_cached": len(self.flood_data_cache),
            "scout_reports_cached": len(self.scout_data_cache),
            "risk_decay_enabled": self.enable_risk_decay,
            "last_update": self.last_update_time.isoformat() if self.last_update_time else None,
        }

    def get_vehicle_passability(
        self, lat: float, lon: float, radius_m: float = 500.0
    ) -> Optional[List[str]]:
        """
        Query vehicle passability at or near a coordinate.

        Tries exact match first (rounded to 5 decimals), then proximity search
        within the given radius.

        Args:
            lat: Latitude
            lon: Longitude
            radius_m: Search radius in meters (default 500m)

        Returns:
            List of passable vehicle types, or None if no data
        """
        coord_key = (round(lat, 5), round(lon, 5))

        # Exact match
        if coord_key in self.vehicle_passability_cache:
            return self.vehicle_passability_cache[coord_key]

        # Proximity search
        for (clat, clon), vehicles in self.vehicle_passability_cache.items():
            dist = haversine_distance((lat, lon), (clat, clon))
            if dist <= radius_m:
                return vehicles

        return None

    def _add_to_scout_cache(self, report: Dict[str, Any], cache_key: tuple) -> None:
        was_full = len(self.scout_data_cache) == self.scout_data_cache.maxlen
        self.scout_data_cache.append(report)
        self.scout_cache_keys.add(cache_key)
        if was_full:
            self.scout_cache_keys = set()
            for r in self.scout_data_cache:
                loc = r.get('location', '')
                if isinstance(loc, (list, tuple)):
                    loc = str(loc)
                txt = r.get('text', '')
                h = hashlib.md5(txt.encode()).hexdigest()[:16] if txt else ''
                self.scout_cache_keys.add((loc, h))

    def clear_caches(self) -> None:
        """
        Clear all cached data.

        This method should be called when resetting the simulation or
        when you want to start fresh with new data.
        """
        self.flood_data_cache.clear()
        self.scout_data_cache.clear()
        self.scout_cache_keys.clear()  # Clear deduplication set
        self.vehicle_passability_cache.clear()
        logger.info(f"{self.agent_id} caches cleared")

    def calculate_data_age_minutes(self, timestamp: Any) -> float:
        """
        Calculate age of data in minutes from its timestamp.

        Args:
            timestamp: datetime object or ISO string

        Returns:
            Age in minutes
        """
        if timestamp is None:
            return 999.0

        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                logger.warning(f"Invalid timestamp format: {timestamp}")
                return 999.0

        # Make both datetimes timezone-aware for comparison
        current_time = sim_clock.now()

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

    def _calculate_dam_threat_level(self) -> float:
        """
        Calculate city-wide dam threat level from upstream dam data.

        Scans flood_data_cache for entries matching the configured relevant dam
        names (ANGAT, IPO, LA MESA, CALIRAYA) and returns the maximum threat score (0.0-1.0).
        Data older than dam_threat_decay_minutes is ignored.

        Returns:
            Maximum dam threat level (0.0-1.0)
        """
        if not self._config.enable_dam_threat_modifier:
            return 0.0

        relevant_names = {name.upper() for name in self._config.dam_relevant_names}
        max_threat = 0.0

        for location, data in self.flood_data_cache.items():
            # Check if this cache entry is a relevant dam
            loc_upper = location.upper().strip() if isinstance(location, str) else ""
            if loc_upper not in relevant_names:
                continue

            # Check data freshness
            age_minutes = self.calculate_data_age_minutes(data.get('timestamp'))
            if age_minutes > self._config.dam_threat_decay_minutes:
                logger.debug(
                    f"Dam data for '{location}' is stale ({age_minutes:.0f}min old), skipping"
                )
                continue

            # Extract threat score from risk_score or derive from status
            threat = data.get('risk_score', 0.0)
            if threat <= 0:
                status = data.get('status', 'normal').lower()
                status_map = {
                    'normal': 0.0,
                    'alert': self._config.dam_alert_threat,
                    'alarm': self._config.dam_alarm_threat,
                    'critical': 1.0,
                }
                threat = status_map.get(status, 0.0)

            if threat > max_threat:
                max_threat = threat
                logger.debug(
                    f"Dam '{location}': threat={threat:.3f} (status={data.get('status', 'unknown')}, "
                    f"age={age_minutes:.0f}min)"
                )

        return min(max_threat, 1.0)

    def _should_cleanup(self) -> bool:
        """
        Check if periodic cleanup is due.

        Returns:
            True if cleanup should run, False otherwise
        """
        now = time.time()
        if now - self._last_cleanup >= self._config.cleanup_interval_sec:
            self._last_cleanup = now
            return True
        return False

    def _should_retry(self) -> bool:
        """
        Check if periodic retry of failed messages is due.

        Returns:
            True if retry should run, False otherwise
        """
        now = time.time()
        if now - self._last_retry >= self.retry_interval_seconds:
            self._last_retry = now
            return True
        return False

    def clean_expired_data(self) -> Dict[str, int]:
        """
        Remove expired AND enforce size limits on caches.

        Performs both time-based (TTL) and size-based (LRU) eviction.

        Returns:
            Dict with counts of expired/evicted items
        """
        current_time = datetime.now()
        expired_counts = {"scouts": 0, "flood_locations": 0, "scouts_size_evicted": 0, "flood_size_evicted": 0}

        # Time-based eviction: Clean expired scout reports from deque
        # Note: deque with maxlen handles size-based eviction automatically
        original_scout_count = len(self.scout_data_cache)
        # Filter to keep only non-expired reports
        valid_reports = [
            report for report in self.scout_data_cache
            if self.calculate_data_age_minutes(report.get('timestamp')) < self.scout_report_ttl_minutes
        ]
        expired_counts["scouts"] = original_scout_count - len(valid_reports)

        # Rebuild deque with valid reports if any were expired
        if expired_counts["scouts"] > 0:
            self.scout_data_cache.clear()
            for report in valid_reports:
                self.scout_data_cache.append(report)

            # Rebuild deduplication set from remaining cache entries
            self.scout_cache_keys.clear()
            for report in self.scout_data_cache:
                report_location = report.get('location', '')
                if isinstance(report_location, (list, tuple)):
                    report_location = str(report_location)
                report_text = report.get('text', '')
                text_hash = hashlib.md5(report_text.encode()).hexdigest()[:16] if report_text else ''
                self.scout_cache_keys.add((report_location, text_hash))

        # Note: Size-based eviction is now automatic with deque(maxlen=...)
        # No manual size check needed - deque automatically evicts oldest entries

        # Time-based eviction: Clean expired flood data
        expired_locations = []
        for location, data in self.flood_data_cache.items():
            age = self.calculate_data_age_minutes(data.get('timestamp'))
            if age >= self.flood_data_ttl_minutes:
                expired_locations.append(location)

        for location in expired_locations:
            del self.flood_data_cache[location]
        expired_counts["flood_locations"] = len(expired_locations)

        # Size-based eviction: LRU for flood cache
        if len(self.flood_data_cache) > self._config.max_flood_cache:
            # Sort by timestamp and keep newest entries
            sorted_items = sorted(
                self.flood_data_cache.items(),
                key=lambda x: x[1].get('timestamp', datetime.min) if isinstance(x[1].get('timestamp'), datetime) else datetime.min,
                reverse=True
            )
            evicted_count = len(self.flood_data_cache) - self._config.max_flood_cache
            self.flood_data_cache = dict(sorted_items[:self._config.max_flood_cache])
            expired_counts["flood_size_evicted"] = evicted_count
            logger.warning(f"{self.agent_id} flood cache trimmed: {evicted_count} entries evicted (LRU)")

        if any(v > 0 for v in expired_counts.values()):
            logger.info(
                f"{self.agent_id} cleaned data: "
                f"{expired_counts['scouts']} scout reports expired, "
                f"{expired_counts['scouts_size_evicted']} scout evicted (size), "
                f"{expired_counts['flood_locations']} flood locations expired, "
                f"{expired_counts['flood_size_evicted']} flood evicted (size)"
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
        1. Polls message queue for incoming messages
        2. Dispatches messages to appropriate handlers
        3. Periodically cleans expired/oversized caches (every 5 minutes)
        4. Periodically retries failed messages from dead letter queue (every 2 minutes)
        5. Processes any cached data
        6. Fuses data from multiple sources
        7. Calculates risk scores
        8. Updates the graph environment
        9. Saves graph state snapshot (every 10 minutes)
        """
        logger.debug(f"{self.agent_id} performing step at {get_philippine_time()}")

        # Step 1: Process all pending messages from queue
        if self.message_queue:
            self._process_pending_messages()

        # Step 2: Automatic periodic cleanup (every 5 minutes)
        if self._should_cleanup():
            self.clean_expired_data()

        # Step 3: Automatic periodic retry of failed messages (every 2 minutes)
        if self.failed_messages and self._should_retry():
            retry_stats = self.retry_failed_messages()
            if retry_stats["retried"] > 0:
                logger.info(
                    f"{self.agent_id} automatic retry completed: "
                    f"{retry_stats['succeeded']} succeeded, "
                    f"{retry_stats['failed']} failed"
                )

        # Step 4: Process cached data and update risk scores (only if new data arrived)
        # This prevents redundant processing every tick when no new data exists
        if self._has_unprocessed_data:
            self.process_and_update()
            self._has_unprocessed_data = False

        # Step 5: Periodic graph state snapshot (every 10 minutes)
        self.environment.maybe_snapshot()

    def _process_pending_messages(self) -> None:
        """
        Poll message queue and dispatch all pending messages.

        Processes messages until queue is empty, dispatching each to the
        appropriate handler based on performative and content type.
        """
        messages_processed = 0

        # Poll queue until empty (non-blocking)
        while True:
            message = self.message_queue.receive_message(
                agent_id=self.agent_id,
                timeout=0.0,
                block=False
            )

            if message is None:
                break  # Queue is empty

            messages_processed += 1
            logger.debug(
                f"{self.agent_id} received message from {message.sender} "
                f"(performative: {message.performative})"
            )

            # Dispatch to handler based on performative
            try:
                if message.performative == Performative.INFORM:
                    self._handle_inform_message(message)
                elif message.performative == Performative.REQUEST:
                    self._handle_request_message(message)
                else:
                    logger.warning(
                        f"{self.agent_id} received unsupported performative: "
                        f"{message.performative}"
                    )
            except Exception as e:
                logger.error(
                    f"{self.agent_id} error processing message from "
                    f"{message.sender}: {e}",
                    exc_info=True
                )

                # Save to dead letter queue for later retry
                # deque(maxlen=...) handles eviction automatically
                self.failed_messages.append({
                    'message': message,
                    'error': str(e),
                    'timestamp': datetime.now(),
                    'retry_count': 0
                })

        if messages_processed > 0:
            logger.info(
                f"{self.agent_id} processed {messages_processed} messages from queue"
            )

    def retry_failed_messages(self) -> Dict[str, int]:
        """
        Retry messages from dead letter queue.

        Attempts to reprocess messages that previously failed, with a maximum
        of 3 retry attempts per message. Messages that fail after 3 retries
        are permanently discarded.

        Returns:
            Dict with retry statistics:
                {
                    "retried": int,  # Number of messages attempted
                    "succeeded": int,  # Number of successful retries
                    "failed": int,  # Number of messages that failed again
                    "discarded": int  # Number of messages permanently discarded
                }
        """
        if not self.failed_messages:
            return {"retried": 0, "succeeded": 0, "failed": 0, "discarded": 0}

        logger.info(
            f"{self.agent_id} attempting to retry {len(self.failed_messages)} "
            f"failed messages"
        )

        stats = {"retried": 0, "succeeded": 0, "failed": 0, "discarded": 0}

        # Copy and clear the failed messages list
        retry_list = self.failed_messages.copy()
        self.failed_messages.clear()

        for entry in retry_list:
            stats["retried"] += 1
            message = entry['message']
            retry_count = entry['retry_count']

            # Check if message has exceeded max retries
            if retry_count >= 3:
                stats["discarded"] += 1
                logger.error(
                    f"{self.agent_id} permanently discarding message from "
                    f"{message.sender} after {retry_count} failed retries"
                )
                continue

            # Attempt to reprocess the message
            try:
                if message.performative == Performative.INFORM:
                    self._handle_inform_message(message)
                elif message.performative == Performative.REQUEST:
                    self._handle_request_message(message)
                else:
                    logger.warning(
                        f"{self.agent_id} received unsupported performative "
                        f"during retry: {message.performative}"
                    )

                stats["succeeded"] += 1
                logger.info(
                    f"{self.agent_id} successfully retried message from "
                    f"{message.sender} (previous failures: {retry_count})"
                )

            except Exception as e:
                stats["failed"] += 1
                logger.warning(
                    f"{self.agent_id} retry failed for message from "
                    f"{message.sender}: {e}"
                )

                # Increment retry count and re-add to failed messages
                entry['retry_count'] += 1
                entry['error'] = str(e)
                entry['timestamp'] = datetime.now()
                self.failed_messages.append(entry)

        logger.info(
            f"{self.agent_id} retry complete: {stats['succeeded']} succeeded, "
            f"{stats['failed']} failed again, {stats['discarded']} discarded"
        )

        return stats

    def _handle_inform_message(self, message: ACLMessage) -> None:
        """
        Handle INFORM messages containing data from other agents.

        Args:
            message: ACLMessage with Performative.INFORM
        """
        info_type = message.content.get("info_type")
        data = message.content.get("data")

        logger.debug(
            f"{self.agent_id} handling INFORM message: info_type={info_type}"
        )

        if info_type == "flood_data_batch":
            # Process flood data from FloodAgent
            self._handle_flood_data_batch(data, message.sender)
        elif info_type == "scout_report_batch":
            # Process scout reports from ScoutAgent
            self._handle_scout_report_batch(data, message.sender)
        else:
            logger.warning(
                f"{self.agent_id} received unknown info_type: {info_type}"
            )

    def _handle_request_message(self, message: ACLMessage) -> None:
        """
        Handle REQUEST messages asking for actions to be performed.

        Supports actions from orchestrator and other agents.
        Sends INFORM reply with conversation_id for correlation.

        Args:
            message: ACLMessage with Performative.REQUEST
        """
        action = message.content.get("action")
        data = message.content.get("data", {})

        logger.debug(
            f"{self.agent_id} handling REQUEST message: action={action}"
        )

        if action in ("calculate_risk", "process_and_update"):
            # Force risk calculation and graph update
            result_data = {"status": "unknown"}
            try:
                update_result = self.process_and_update()
                result_data["status"] = "success"
                result_data["update_result"] = update_result
            except Exception as e:
                result_data["status"] = "error"
                result_data["error"] = str(e)

            logger.info(
                f"{self.agent_id}: {action} -> {result_data['status']}"
            )

            # Send INFORM reply to requester (for orchestrator correlation)
            if message.sender and self.message_queue:
                try:
                    reply = create_inform_message(
                        sender=self.agent_id,
                        receiver=message.sender,
                        info_type="risk_update_result",
                        data=result_data,
                        conversation_id=message.conversation_id,
                        in_reply_to=message.reply_with,
                    )
                    self.message_queue.send_message(reply)
                except Exception as e:
                    logger.error(
                        f"{self.agent_id}: failed to reply to "
                        f"{message.sender}: {e}"
                    )

        elif action == "query_risk_at_location":
            # Query current map risk at a specific location
            lat = data.get("lat")
            lon = data.get("lon")
            radius_m = data.get("radius_m", 500)
            result_data = {"status": "error", "error": "Missing lat/lon"}

            if lat is not None and lon is not None:
                try:
                    result_data = self.get_risk_at_location(
                        float(lat), float(lon), float(radius_m)
                    )
                except Exception as e:
                    result_data = {"status": "error", "error": str(e)}

            logger.info(
                f"{self.agent_id}: query_risk_at_location "
                f"({lat}, {lon}) -> {result_data.get('risk_level', 'error')}"
            )

            if message.sender and self.message_queue:
                try:
                    reply = create_inform_message(
                        sender=self.agent_id,
                        receiver=message.sender,
                        info_type="location_risk_result",
                        data=result_data,
                        conversation_id=message.conversation_id,
                        in_reply_to=message.reply_with,
                    )
                    self.message_queue.send_message(reply)
                except Exception as e:
                    logger.error(
                        f"{self.agent_id}: failed to reply to "
                        f"{message.sender}: {e}"
                    )
        else:
            logger.warning(
                f"{self.agent_id} received unknown action: {action}"
            )

    def _handle_flood_data_batch(self, data: Dict[str, Any], sender: str) -> None:
        """
        Handle flood data batch from FloodAgent.

        Args:
            data: Dictionary of flood data by location
            sender: ID of sending agent
        """
        logger.info(
            f"{self.agent_id} received flood data batch from {sender}: "
            f"{len(data)} locations"
        )

        # Use existing batch processing method
        self.process_flood_data_batch(data)

    def _geocode_report(self, report: Dict[str, Any]) -> bool:
        """
        Attempt to geocode a scout report that lacks coordinates.

        Uses LocationGeocoder to resolve the report's location name to
        (lat, lon) coordinates. If successful, adds 'coordinates' dict
        to the report in-place.

        Args:
            report: Scout report dict (modified in-place if geocoding succeeds)

        Returns:
            True if coordinates were resolved, False otherwise
        """
        if not self.geocoder:
            return False

        # Already has valid coordinates
        coords = report.get('coordinates')
        if (coords and isinstance(coords, dict)
                and coords.get('lat') is not None
                and coords.get('lon') is not None):
            return True

        location_name = report.get('location', '')
        if not location_name:
            return False

        # Try geocoding with fuzzy match
        resolved = self.geocoder.get_coordinates(location_name, fuzzy=True, threshold=self._config.geocoding_fuzzy_threshold)
        if resolved:
            lat, lon = resolved
            report['coordinates'] = {'lat': lat, 'lon': lon}
            report['geocoded'] = True  # Flag so we know this was resolved
            logger.info(
                f"{self.agent_id} geocoded '{location_name}' -> "
                f"({lat:.4f}, {lon:.4f})"
            )
            return True

        logger.debug(
            f"{self.agent_id} failed to geocode location: '{location_name}'"
        )
        return False

    def _handle_scout_report_batch(self, data: Dict[str, Any], sender: str) -> None:
        """
        Handle scout report batch from ScoutAgent.

        Args:
            data: Dict containing scout reports and metadata:
                  - "reports": List of scout reports
                  - "has_coordinates": Boolean flag indicating coordinate availability
                  - "report_count": Number of reports
                  - "skipped_count": Number of reports skipped (optional)
            sender: ID of sending agent
        """
        reports = data.get("reports", [])
        has_coordinates = data.get("has_coordinates", False)
        report_count = data.get("report_count", len(reports))

        logger.info(
            f"{self.agent_id} received scout report batch from {sender}: "
            f"{report_count} reports ({'with' if has_coordinates else 'without'} coordinates)"
        )

        if has_coordinates:
            # Process reports with coordinates (spatial filtering enabled)
            self.process_scout_data_with_coordinates(reports)
        else:
            # Attempt geocoding for reports without coordinates
            geocoded_reports = []
            ungeocodable_reports = []

            for report in reports:
                if self._geocode_report(report):
                    geocoded_reports.append(report)
                else:
                    ungeocodable_reports.append(report)

            if geocoded_reports:
                logger.info(
                    f"{self.agent_id} geocoded {len(geocoded_reports)}/{len(reports)} "
                    f"scout reports -> routing to spatial processing"
                )
                self.process_scout_data_with_coordinates(geocoded_reports)

            if ungeocodable_reports:
                logger.warning(
                    f"{self.agent_id} {len(ungeocodable_reports)} reports could not "
                    f"be geocoded -> using global risk fallback"
                )
                for report in ungeocodable_reports:
                    self.process_scout_data([report])

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

        if risk_scores:
            average_risk = sum(risk_scores.values()) / len(risk_scores)
            self.risk_history.append((get_philippine_time(), average_risk))

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
        and updates the graph.

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

        # Track risk history (deque with maxlen handles eviction automatically)
        self.risk_history.append((current_time, average_risk))

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
            "timestamp": current_time.isoformat(),
            "average_risk": round(average_risk, 2),
            "risk_trend": risk_trend,
            "risk_change_rate": round(risk_change_rate, 4),
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

        # Proactive cache eviction when approaching size limit
        if len(self.flood_data_cache) >= self._config.max_flood_cache:
            self.clean_expired_data()

        # Update cache
        location = flood_data.get("location")
        self.flood_data_cache[location] = flood_data

        # Mark that we have new data to process on next step()
        self._has_unprocessed_data = True

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

        # Proactive cache eviction when approaching size limit
        if len(self.flood_data_cache) + len(data) >= self._config.max_flood_cache:
            self.clean_expired_data()

        # Update cache for all locations
        for location, location_data in data.items():
            # Skip non-dict entries (e.g. "advisories" key contains a list)
            if not isinstance(location_data, dict):
                logger.debug(
                    f"{self.agent_id} skipping non-dict entry '{location}' "
                    f"(type={type(location_data).__name__})"
                )
                continue

            # Normalize heterogeneous field names from FloodAgent sources:
            #   River data: water_level_m, risk_score, status
            #   Dam data:   reservoir_water_level_m, deviation_from_nhwl_m
            #   Weather:    current_rainfall_mm, rainfall_24h_mm, forecast_6h_mm
            #   Simulated:  flood_depth, rainfall_1h, rainfall_24h
            source = location_data.get("source", "")

            flood_depth = location_data.get("flood_depth", 0.0)
            rainfall_1h = location_data.get("rainfall_1h", 0.0)
            rainfall_24h = location_data.get("rainfall_24h", 0.0)

            if "PAGASA_API" in source and "water_level_m" in location_data:
                # River station: graduated flood depth using all three
                # PAGASA thresholds (per-station values scraped from the table).
                # Tier floors are calibrated to the FEMA sigmoid (k=8, x0=0.3):
                #   alert  → floor 0.15m → ~27% risk
                #   alarm  → floor 0.30m → 50% risk
                #   critical → floor 0.60m → ~92% risk
                wl = location_data.get("water_level_m", 0.0) or 0.0
                alert = location_data.get("alert_level_m")
                alarm = location_data.get("alarm_level_m")
                critical = location_data.get("critical_level_m")

                if alert and wl > alert:
                    overflow = wl - alert
                    if critical and wl >= critical:
                        tier_floor = self._config.depth_tier_floor_critical
                    elif alarm and wl >= alarm:
                        tier_floor = self._config.depth_tier_floor_alarm
                    else:
                        tier_floor = self._config.depth_tier_floor_alert
                    flood_depth = max(flood_depth, overflow, tier_floor)

            elif "Dam_Monitoring" in source and "deviation_from_nhwl_m" in location_data:
                # Dam: graduated flood depth using FloodAgent's pre-computed
                # status (derived from dam_alert/alarm/critical config thresholds)
                # and the physical NHWL deviation.
                dev = location_data.get("deviation_from_nhwl_m")
                status = location_data.get("status", "normal")

                if dev is not None and dev > 0:
                    capped_dev = min(dev, 5.0)
                    if status == "critical":
                        tier_floor = self._config.depth_tier_floor_critical
                    elif status == "alarm":
                        tier_floor = self._config.depth_tier_floor_alarm
                    elif status in ("alert", "watch"):
                        tier_floor = self._config.depth_tier_floor_alert
                    else:
                        tier_floor = 0.0
                    flood_depth = max(flood_depth, capped_dev, tier_floor)

            elif "OpenWeatherMap" in source or "current_rainfall_mm" in location_data:
                # Weather data: map field names
                rainfall_1h = max(rainfall_1h, location_data.get("current_rainfall_mm", 0.0))
                rainfall_24h = max(rainfall_24h, location_data.get("rainfall_24h_mm", 0.0))

            flood_data = {
                "location": location,
                "flood_depth": flood_depth,
                "rainfall_1h": rainfall_1h,
                "rainfall_24h": rainfall_24h,
                "timestamp": location_data.get("timestamp")
            }

            # Preserve status and risk_score for dam entries (used by dam threat modifier)
            if "Dam_Monitoring" in source:
                flood_data["status"] = location_data.get("status", "normal")
                flood_data["risk_score"] = location_data.get("risk_score", 0.0)

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

        Attempts geocoding for reports without coordinates. Successfully
        geocoded reports are routed to spatial processing; others are
        cached by location name for global risk fusion.

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

        # Validate, deduplicate, geocode, and add to cache
        valid_count = 0
        geocoded_reports = []

        for report in scout_reports:
            if not self._validate_scout_data(report):
                logger.warning(f"Invalid scout report: {report}")
                continue

            # O(1) deduplication check (same pattern as process_scout_data_with_coordinates)
            report_location = report.get('location', '')
            if isinstance(report_location, (list, tuple)):
                report_location = str(report_location)
            report_text = report.get('text', '')
            text_hash = hashlib.md5(report_text.encode()).hexdigest()[:16] if report_text else ''
            cache_key = (report_location, text_hash)

            if cache_key in self.scout_cache_keys:
                logger.debug(f"Skipping duplicate scout report: {report_location}")
                continue

            # Try geocoding before caching
            if self._geocode_report(report):
                geocoded_reports.append(report)

            self._add_to_scout_cache(report, cache_key)
            valid_count += 1

        # Route geocoded reports to spatial processing for precise edge updates
        if geocoded_reports:
            logger.info(
                f"{self.agent_id} geocoded {len(geocoded_reports)}/{valid_count} "
                f"reports in process_scout_data -> spatial processing"
            )
            self.process_scout_data_with_coordinates(geocoded_reports)

        # Mark that we have new data to process on next step()
        if valid_count > 0:
            self._has_unprocessed_data = True

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

            # Calculate base risk using energy head formula (Kreibich et al. 2009)
            # E = h + v²/(2g): combines flood depth with kinetic energy from flow velocity.
            # Fast shallow water raises energy head and thus risk vs. the same depth static.
            flood_depth = data.get("flood_depth", 0.0)
            if flood_depth <= 0:
                depth_risk = 0.0
            else:
                v = self._config.flow_velocity_mps
                energy_head = flood_depth + (v ** 2) / (2 * 9.81)
                k = self._config.sigmoid_steepness
                x0 = self._config.sigmoid_inflection
                depth_risk = 1.0 / (1.0 + math.exp(-k * (energy_head - x0)))

            # Calculate rainfall risk (predictive/early warning)
            rainfall_1h = data.get("rainfall_1h", 0.0)
            rain_risk = 0.0
            if rainfall_1h > self._config.rainfall_extreme_mm:
                rain_risk = self._config.rainfall_risk_extreme
            elif rainfall_1h > self._config.rainfall_heavy_mm:
                rain_risk = self._config.rainfall_risk_heavy
            elif rainfall_1h > self._config.rainfall_moderate_mm:
                rain_risk = self._config.rainfall_risk_moderate
            elif rainfall_1h > self._config.rainfall_light_mm:
                rain_risk = self._config.rainfall_risk_light

            # Combine: If flood depth is known, it dominates. If not, rainfall provides early warning
            combined_hydro_risk = max(depth_risk, rain_risk * self._config.rainfall_risk_weight)

            fused_data[location]["risk_level"] += combined_hydro_risk * self.risk_weights["flood_depth"]
            fused_data[location]["flood_depth"] = flood_depth
            fused_data[location]["confidence"] += self._config.flood_data_confidence
            fused_data[location]["sources"].append("flood_agent")

            # Log rainfall contribution if present
            if rainfall_1h > 0:
                logger.debug(
                    f"Location {location}: rainfall_1h={rainfall_1h:.1f}mm/hr, "
                    f"rain_risk={rain_risk:.2f}, depth_risk={depth_risk:.2f}, "
                    f"combined={combined_hydro_risk:.2f}"
                )

        # Integrate crowdsourced data using weighted averaging (not accumulation)
        # Track weighted sums and total weights for proper averaging
        scout_weighted_sums: Dict[str, float] = {}
        scout_total_weights: Dict[str, float] = {}
        scout_sources: Dict[str, List[str]] = {}

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

            # Skip "clear" reports from risk accumulation
            # (clearance is handled by check_scout_validation_for_area)
            if report_type == "clear":
                continue

            # Use estimated_depth_m if available (from ScoutAgent vision/text)
            estimated_depth = report.get('estimated_depth_m')
            if estimated_depth and estimated_depth > 0:
                k = self._config.sigmoid_steepness
                x0 = self._config.sigmoid_inflection
                depth_risk = 1.0 / (1.0 + math.exp(-k * (estimated_depth - x0)))
                severity = max(severity, depth_risk)

            # Apply time-based decay to severity
            if self.enable_risk_decay:
                age_minutes = self.calculate_data_age_minutes(report.get('timestamp'))
                decay_rate = self.determine_decay_rate(report_type)
                severity = self.apply_time_decay(severity, age_minutes, decay_rate)

                logger.debug(
                    f"Scout report at {location}: age={age_minutes:.1f}min, "
                    f"decay_rate={decay_rate:.3f}, decayed_severity={severity:.3f}"
                )

            # Use weighted averaging instead of accumulation
            # Weight = confidence (0-1), value = severity (0-1)
            weight = confidence
            if location not in scout_weighted_sums:
                scout_weighted_sums[location] = 0.0
                scout_total_weights[location] = 0.0
                scout_sources[location] = []

            scout_weighted_sums[location] += severity * weight
            scout_total_weights[location] += weight
            scout_sources[location].append(report.get('source', 'scout_agent'))

        # Apply weighted average for each location
        for location in scout_weighted_sums:
            if scout_total_weights[location] > 0:
                # Weighted average of severities
                avg_severity = scout_weighted_sums[location] / scout_total_weights[location]

                # Apply crowdsourced weight to the averaged severity
                scout_risk = avg_severity * self.risk_weights["crowdsourced"]

                # Confidence boost for multiple independent sources
                unique_sources = len(set(scout_sources[location]))
                confidence_boost = min(
                    self._config.scout_confidence_boost_cap,
                    self._config.scout_confidence_boost_per_source * unique_sources,
                )
                scout_risk = min(1.0, scout_risk + confidence_boost)

                # Add to existing risk (from flood_agent data)
                fused_data[location]["risk_level"] += scout_risk
                fused_data[location]["confidence"] += (
                    min(scout_total_weights[location], 1.0) * self._config.scout_confidence_weight
                )
                fused_data[location]["sources"].append("scout_agent")

        # Normalize risk levels and pre-geocode locations for spatial filtering
        geocoded_count = 0
        for location in fused_data:
            fused_data[location]["risk_level"] = min(fused_data[location]["risk_level"], 1.0)
            fused_data[location]["confidence"] = min(fused_data[location]["confidence"], 1.0)

            # Pre-geocode: attach coordinates so calculate_risk_scores can
            # apply spatial filtering without a second geocoding call
            # Skip dams and weather — they can't be geocoded to local edges
            # and are handled city-wide
            if self.geocoder and isinstance(location, str):
                all_dam_names = {n.upper() for n in self._config.dam_all_names}
                if location.upper().strip() in all_dam_names:
                    fused_data[location]["_is_dam"] = True
                    continue
                # Weather data is city-wide, not a specific location
                if location.endswith("_weather"):
                    fused_data[location]["_is_weather"] = True
                    continue
                coords = self.geocoder.get_coordinates(location, fuzzy=True, threshold=self._config.geocoding_fuzzy_threshold)
                if coords:
                    fused_data[location]["_coords"] = coords
                    geocoded_count += 1

        logger.info(
            f"Data fusion complete for {len(fused_data)} locations "
            f"({geocoded_count} geocoded for spatial filtering)"
        )
        return fused_data

    def _build_spatial_index(self) -> None:
        """
        Build grid-based spatial index for fast edge lookups.

        Creates a dictionary mapping grid cells to edge lists. Each grid cell is
        identified by (grid_x, grid_y) coordinates based on edge midpoint.

        This reduces edge query complexity from O(E) to O(E/G) where G is the
        number of grid cells typically containing edges.

        Grid size: ~1.1km (0.01 degrees at equator)
        """
        if not self.environment or not hasattr(self.environment, 'graph'):
            logger.warning("Graph environment not available - spatial index not built")
            return

        self.spatial_index = {}
        edges_indexed = 0

        for u, v, key in self.environment.graph.edges(keys=True):
            try:
                u_data = self.environment.graph.nodes[u]
                v_data = self.environment.graph.nodes[v]

                u_lat = u_data.get('y')
                u_lon = u_data.get('x')
                v_lat = v_data.get('y')
                v_lon = v_data.get('x')

                if None in (u_lat, u_lon, v_lat, v_lon):
                    continue

                # Calculate edge midpoint
                mid_lat = (u_lat + v_lat) / 2
                mid_lon = (u_lon + v_lon) / 2

                # Determine grid cell
                grid_x = int(mid_lon / self.spatial_index_grid_size)
                grid_y = int(mid_lat / self.spatial_index_grid_size)
                grid_cell = (grid_x, grid_y)

                # Add edge to grid cell
                if grid_cell not in self.spatial_index:
                    self.spatial_index[grid_cell] = []
                self.spatial_index[grid_cell].append((u, v, key, mid_lat, mid_lon))
                edges_indexed += 1

            except (KeyError, TypeError):
                continue

        logger.info(
            f"{self.agent_id} built spatial index: {edges_indexed} edges in "
            f"{len(self.spatial_index)} grid cells "
            f"(avg {edges_indexed/max(len(self.spatial_index), 1):.1f} edges/cell)"
        )

    def find_edges_within_radius(
        self,
        lat: float,
        lon: float,
        radius_m: float
    ) -> List[Tuple[int, int, int]]:
        """
        Find all graph edges within a radius of a geographic point.

        OPTIMIZED: Uses grid-based spatial index to reduce search space from O(E)
        to O(E/G) where G is grid granularity. Only checks edges in nearby grid
        cells instead of entire graph.

        Performance: ~100x faster for typical queries (800m radius, 35k edges)
        - Old: Iterates all 35,932 edges (~35ms per query)
        - New: Checks only ~200-400 edges in nearby cells (~0.3ms per query)

        Args:
            lat: Latitude of center point
            lon: Longitude of center point
            radius_m: Radius in meters

        Returns:
            List of edge tuples (u, v, key) within the radius
        """
        if not self.environment or not hasattr(self.environment, 'graph'):
            logger.warning("Graph environment not available for spatial query")
            return []

        # Use spatial index if available
        if self.spatial_index:
            return self._find_edges_with_spatial_index(lat, lon, radius_m)
        else:
            # Fallback to brute force (slow but functional)
            return self._find_edges_brute_force(lat, lon, radius_m)

    def _find_edges_with_spatial_index(
        self,
        lat: float,
        lon: float,
        radius_m: float
    ) -> List[Tuple[int, int, int]]:
        """
        Find edges using spatial index (FAST - O(E/G) complexity).

        Args:
            lat: Latitude of center point
            lon: Longitude of center point
            radius_m: Radius in meters

        Returns:
            List of edge tuples (u, v, key) within the radius
        """
        nearby_edges = []
        center_coord = (lat, lon)

        # Determine which grid cells to check
        # Calculate bounding box in grid coordinates
        # Approximate: 1 degree latitude ~ 111km, 1 degree longitude ~ 111km * cos(lat)
        lat_delta = (radius_m / 111000.0) / self.spatial_index_grid_size
        lon_delta = (radius_m / (111000.0 * math.cos(math.radians(lat)))) / self.spatial_index_grid_size

        center_grid_x = int(lon / self.spatial_index_grid_size)
        center_grid_y = int(lat / self.spatial_index_grid_size)

        # Check grid cells in bounding box
        x_range = int(math.ceil(lon_delta)) + 1
        y_range = int(math.ceil(lat_delta)) + 1

        cells_checked = 0
        edges_checked = 0

        for dx in range(-x_range, x_range + 1):
            for dy in range(-y_range, y_range + 1):
                grid_cell = (center_grid_x + dx, center_grid_y + dy)

                if grid_cell not in self.spatial_index:
                    continue

                cells_checked += 1

                # Check edges in this grid cell
                for edge_data in self.spatial_index[grid_cell]:
                    u, v, key, mid_lat, mid_lon = edge_data
                    edges_checked += 1

                    edge_midpoint = (mid_lat, mid_lon)
                    distance_m = haversine_distance(center_coord, edge_midpoint)

                    if distance_m <= radius_m:
                        nearby_edges.append((u, v, key))

        logger.debug(
            f"Spatial query (indexed): Found {len(nearby_edges)} edges within {radius_m}m "
            f"of ({lat:.4f}, {lon:.4f}) - checked {edges_checked} edges in "
            f"{cells_checked} grid cells"
        )

        return nearby_edges

    def _find_edges_brute_force(
        self,
        lat: float,
        lon: float,
        radius_m: float
    ) -> List[Tuple[int, int, int]]:
        """
        Find edges by checking all edges (SLOW - O(E) complexity).

        Fallback method when spatial index is unavailable.

        Args:
            lat: Latitude of center point
            lon: Longitude of center point
            radius_m: Radius in meters

        Returns:
            List of edge tuples (u, v, key) within the radius
        """
        nearby_edges = []
        center_coord = (lat, lon)

        for u, v, key in self.environment.graph.edges(keys=True):
            try:
                u_data = self.environment.graph.nodes[u]
                v_data = self.environment.graph.nodes[v]

                u_lat = u_data.get('y')
                u_lon = u_data.get('x')
                v_lat = v_data.get('y')
                v_lon = v_data.get('x')

                if None in (u_lat, u_lon, v_lat, v_lon):
                    continue

                mid_lat = (u_lat + v_lat) / 2
                mid_lon = (u_lon + v_lon) / 2
                edge_midpoint = (mid_lat, mid_lon)

                distance_m = haversine_distance(center_coord, edge_midpoint)

                if distance_m <= radius_m:
                    nearby_edges.append((u, v, key))

            except (KeyError, TypeError):
                continue

        logger.debug(
            f"Spatial query (brute force): Found {len(nearby_edges)} edges within "
            f"{radius_m}m of ({lat:.4f}, {lon:.4f})"
        )

        return nearby_edges

    # --- DEM Terrain Risk Methods ---

    def precompute_node_elevations(self) -> int:
        """
        Precompute DEM elevations for all graph nodes (called once at startup).

        Returns:
            Number of nodes with valid elevation data.
        """
        if not self.dem_service or not self.environment or not self.environment.graph:
            logger.warning("Cannot precompute DEM elevations: service or graph unavailable")
            return 0

        self._node_elevations = self.dem_service.precompute_node_elevations(
            self.environment.graph
        )
        return sum(
            1 for v in self._node_elevations.values()
            if v.get("elevation") is not None
        )

    # --- River Proximity Methods ---

    def precompute_river_proximity(self) -> int:
        """
        Precompute river proximity distances for all graph nodes (called once at startup).

        Returns:
            Number of nodes with river proximity data.
        """
        if not self.river_service or not self.environment or not self.environment.graph:
            logger.warning(
                "Cannot precompute river proximity: service or graph unavailable"
            )
            return 0

        self._node_river_data = self.river_service.precompute_node_distances(
            self.environment.graph,
            decay_distance_m=self._config.river_decay_distance_m,
        )
        return len(self._node_river_data)

    def _calculate_river_proximity_risk(self, u: int, v: int, key: int) -> float:
        """
        Calculate river-proximity risk for an edge.

        Uses the conservative max of the two endpoint risks so that an edge
        touching a riverbank node is risky regardless of the other endpoint.

        Args:
            u: Start node ID
            v: End node ID
            key: Edge key (unused, kept for API consistency with _calculate_terrain_risk)

        Returns:
            River proximity risk in [0, 1].
        """
        u_data = self._node_river_data.get(u)
        v_data = self._node_river_data.get(v)

        u_risk = u_data["river_risk"] if u_data else 0.0
        v_risk = v_data["river_risk"] if v_data else 0.0

        # Conservative: either endpoint near a river makes the edge risky
        return max(u_risk, v_risk)

    def seed_initial_risk_priors(self) -> int:
        """
        Seed the graph with static terrain/waterway risk priors at startup.

        Applies DEM terrain risk (Block 1) and river proximity risk to all
        graph edges without requiring any flood or scout data. Called once
        after precomputation so edges near rivers/low terrain show non-zero
        risk immediately — before the first agent step fires.

        Returns:
            Number of edges seeded with non-zero risk.
        """
        if (not self.environment
                or not hasattr(self.environment, 'graph')
                or not self.environment.graph):
            logger.warning("Cannot seed risk priors: graph environment not available")
            return 0

        risk_scores: Dict[Tuple, float] = {}

        # DEM terrain prior (mirrors Block 1 in calculate_risk_scores)
        if self.dem_enabled and self._node_elevations:
            dem_weight = self._config.dem_weight_terrain_risk
            for u, v, key in self.environment.graph.edges(keys=True):
                terrain_risk = self._calculate_terrain_risk(u, v, key)
                if terrain_risk <= 0.0:
                    continue
                current = risk_scores.get((u, v, key), 0.0)
                if current > 0.0:
                    contribution = current * terrain_risk * dem_weight
                else:
                    contribution = terrain_risk * dem_weight
                risk_scores[(u, v, key)] = min(1.0, current + contribution)

        # River proximity prior (mirrors River Proximity Block)
        if self.river_enabled and self._node_river_data:
            river_weight = self._config.river_weight
            for u, v, key in self.environment.graph.edges(keys=True):
                river_risk = self._calculate_river_proximity_risk(u, v, key)
                if river_risk <= 0.0:
                    continue
                current = risk_scores.get((u, v, key), 0.0)
                if current <= 0.0:
                    risk_scores[(u, v, key)] = river_risk * river_weight
                else:
                    added = min(river_risk * river_weight, 1.0 - current)
                    risk_scores[(u, v, key)] = min(1.0, current + added)

        if risk_scores:
            # Store in _seeded_priors so the decay block in calculate_risk_scores()
            # can subtract them before amplification — preventing the static prior
            # from compounding with itself on every data collection cycle.
            self._seeded_priors = dict(risk_scores)

            # Write directly to graph edges WITHOUT setting last_risk_update.
            # No timestamp = decay block treats them as "preserve as-is" on
            # first access, but _seeded_priors handles isolation going forward.
            for (u, v, key), risk in risk_scores.items():
                try:
                    self.environment.graph[u][v][key]['risk_score'] = risk
                except Exception:
                    pass
            logger.info(
                f"Seeded {len(risk_scores)} edges with static risk priors "
                f"(DEM={'enabled' if self.dem_enabled and self._node_elevations else 'off'}, "
                f"river={'enabled' if self.river_enabled and self._node_river_data else 'off'})"
            )
        else:
            logger.info("No static risk priors to seed (both DEM and river proximity off or empty)")

        return len(risk_scores)

    def _calculate_terrain_risk(self, u: int, v: int, key: int) -> float:
        """
        Calculate terrain-based flood risk for an edge based on DEM data.

        Uses relative elevation (depression detection) and slope (drainage).
        Low-lying areas get higher risk; steep slopes get a drainage discount.

        Args:
            u: Start node ID
            v: End node ID
            key: Edge key

        Returns:
            Terrain risk score in [0, 1].
        """
        u_data = self._node_elevations.get(u)
        v_data = self._node_elevations.get(v)

        if not u_data or not v_data:
            return 0.0

        u_rel = u_data.get("relative_elevation")
        v_rel = v_data.get("relative_elevation")
        u_slope = u_data.get("slope")
        v_slope = v_data.get("slope")

        # Need at least relative elevation for one endpoint
        if u_rel is None and v_rel is None:
            return 0.0

        # Average relative elevation (use 0.0 for missing) — local scale
        avg_rel_elev = 0.0
        count = 0
        if u_rel is not None:
            avg_rel_elev += u_rel
            count += 1
        if v_rel is not None:
            avg_rel_elev += v_rel
            count += 1
        avg_rel_elev /= count

        # --- Fix 3: Multi-scale relative elevation ---
        # Regional scale catches wide floodplains where local window sees "flat"
        u_reg_rel = u_data.get("regional_relative_elevation")
        v_reg_rel = v_data.get("regional_relative_elevation")
        if u_reg_rel is not None or v_reg_rel is not None:
            avg_reg_rel_elev = 0.0
            reg_count = 0
            if u_reg_rel is not None:
                avg_reg_rel_elev += u_reg_rel
                reg_count += 1
            if v_reg_rel is not None:
                avg_reg_rel_elev += v_reg_rel
                reg_count += 1
            avg_reg_rel_elev /= reg_count
            # Take worst case (minimum = most depressed = highest risk)
            avg_rel_elev = min(avg_rel_elev, avg_reg_rel_elev)

        # Sigmoid: 50% risk at threshold, ~98% at 2x threshold below
        threshold = self._config.dem_low_elevation_threshold
        base_risk = 1.0 / (1.0 + math.exp(2.0 * (avg_rel_elev - threshold)))

        # Drainage discount from slope (steeper = drains faster)
        avg_slope = 0.0
        slope_count = 0
        if u_slope is not None:
            avg_slope += u_slope
            slope_count += 1
        if v_slope is not None:
            avg_slope += v_slope
            slope_count += 1
        if slope_count > 0:
            avg_slope /= slope_count

        drain_threshold = self._config.dem_slope_drain_threshold
        drain_factor = min(1.0, avg_slope / drain_threshold) if drain_threshold > 0 else 0.0

        # Drainage discount for dry slopes (velocity penalty removed — flood_depth
        # is no longer stored on graph edges)
        terrain_risk = base_risk * (1.0 - 0.3 * drain_factor)

        return max(0.0, min(1.0, terrain_risk))

    def _build_water_surface_map(self) -> Dict[str, Dict[str, float]]:
        """
        Build a map of water surface elevations from flood data cache + DEM.

        WSE calculation depends on ``dem_water_level_is_depth`` config:
        - True:  water_level_m is depth above ground -> WSE = ground_elev + water_level
        - False: water_level_m is already a water surface elevation -> WSE = water_level

        Returns:
            Dict of station_name -> {lat, lon, water_surface_elev}.
        """
        water_surface_map: Dict[str, Dict[str, float]] = {}

        if not self.dem_service:
            return water_surface_map

        water_level_is_depth = self._config.dem_water_level_is_depth

        for station_name, data in self.flood_data_cache.items():
            water_level = data.get("water_level_m") or data.get("water_level", 0.0)
            if not water_level or water_level <= 0:
                continue

            lat = data.get("latitude") or data.get("lat")
            lon = data.get("longitude") or data.get("lon")
            if lat is None or lon is None:
                continue

            try:
                lat, lon = float(lat), float(lon)
            except (ValueError, TypeError):
                continue

            if water_level_is_depth:
                # water_level is depth above ground at gauge -> add DEM ground elevation
                ground_elev = self.dem_service.get_elevation(lon, lat)
                if ground_elev is None:
                    continue
                wse = ground_elev + water_level
            else:
                # water_level is already referenced to a geodetic datum (MSL, etc.)
                wse = water_level

            water_surface_map[station_name] = {
                "lat": lat,
                "lon": lon,
                "water_surface_elev": wse,
            }

        return water_surface_map

    def _estimate_flood_depth_from_dem(
        self,
        u: int,
        v: int,
        water_surface_map: Dict[str, Dict[str, float]],
    ) -> Optional[float]:
        """
        Estimate flood depth at an edge midpoint using IDW-interpolated water surface.

        Args:
            u: Start node
            v: End node
            water_surface_map: Output of _build_water_surface_map()

        Returns:
            Estimated flood depth in meters, or None if cannot estimate.
        """
        if not water_surface_map or not self.dem_service:
            return None

        graph = self.environment.graph
        u_data = graph.nodes.get(u, {})
        v_data = graph.nodes.get(v, {})

        u_lon, u_lat = u_data.get('x'), u_data.get('y')
        v_lon, v_lat = v_data.get('x'), v_data.get('y')

        if None in (u_lon, u_lat, v_lon, v_lat):
            return None

        mid_lon = (u_lon + v_lon) / 2.0
        mid_lat = (u_lat + v_lat) / 2.0

        # Get ground elevation at midpoint
        ground_elev = self.dem_service.get_elevation(mid_lon, mid_lat)
        if ground_elev is None:
            return None

        # IDW interpolation of water surface from nearby stations
        radius_m = self._config.dem_river_station_interpolation_radius_m
        _dist_func = haversine_distance

        weight_sum = 0.0
        wse_weighted_sum = 0.0

        for station_data in water_surface_map.values():
            station_lat = station_data["lat"]
            station_lon = station_data["lon"]
            station_wse = station_data["water_surface_elev"]

            dist = _dist_func(
                (mid_lat, mid_lon),
                (station_lat, station_lon),
            )
            if dist > radius_m:
                continue

            # --- Fix 1: Barrier check (ridge/levee blocks water flow) ---
            if self._config.dem_barrier_check_enabled and self.dem_service:
                clear = self.dem_service.check_line_of_sight(
                    station_lon, station_lat, mid_lon, mid_lat,
                    max_elevation=station_wse,
                    num_samples=self._config.dem_barrier_sample_points,
                )
                if not clear:
                    continue  # Ridge/levee blocks this station

            # IDW power=2
            w = 1.0 / max(dist * dist, 1.0)  # avoid div-by-zero
            weight_sum += w
            wse_weighted_sum += w * station_wse

        if weight_sum == 0.0:
            return None

        interpolated_wse = wse_weighted_sum / weight_sum
        return max(0.0, interpolated_wse - ground_elev)

    def calculate_risk_scores(self, fused_data: Dict[str, Any]) -> Dict[Tuple, float]:
        """
        Calculate risk scores for road segments based on fused data.

        Combines:
        1. DEM terrain risk data (elevation-based flood susceptibility)
        2. Fused data from FloodAgent and ScoutAgent (river levels, weather, crowdsourced)

        Args:
            fused_data: Fused data from multiple sources

        Returns:
            Dict mapping edge tuples to risk scores (0.0-1.0)
                Format: {(u, v, key): risk_score, ...}
        """
        logger.debug(f"{self.agent_id} calculating risk scores")

        if not self.environment or not hasattr(self.environment, 'graph') or not self.environment.graph:
            logger.warning("Graph environment not available for risk calculation")
            return {}

        # Apply time-based decay to existing spatial risk scores.
        # IMPORTANT: subtract the static seeded prior before carrying over so that
        # DEM Block 1 / River block only amplify true dynamic (flood/scout) risk,
        # not the static terrain prior — preventing unbounded compounding each cycle.
        risk_scores = {}
        if self.enable_risk_decay:
            for u, v, key in self.environment.graph.edges(keys=True):
                existing_risk = self.environment.graph[u][v][key].get('risk_score', 0.0)
                seeded = self._seeded_priors.get((u, v, key), 0.0)
                dynamic_risk = max(0.0, existing_risk - seeded)
                if dynamic_risk > 0.0:
                    edge_data = self.environment.graph[u][v][key]
                    last_update = edge_data.get('last_risk_update')
                    if last_update:
                        age_minutes = self.calculate_data_age_minutes(last_update)
                        decayed_risk = self.apply_time_decay(
                            dynamic_risk, age_minutes, self.flood_decay_rate
                        )
                        if decayed_risk > self.min_risk_threshold:
                            risk_scores[(u, v, key)] = decayed_risk
                    else:
                        risk_scores[(u, v, key)] = dynamic_risk
        else:
            for u, v, key in self.environment.graph.edges(keys=True):
                existing_risk = self.environment.graph[u][v][key].get('risk_score', 0.0)
                seeded = self._seeded_priors.get((u, v, key), 0.0)
                dynamic_risk = max(0.0, existing_risk - seeded)
                if dynamic_risk > 0.0:
                    risk_scores[(u, v, key)] = dynamic_risk

        # --- DEM Block 1: Terrain prior risk (hybrid additive + multiplicative) ---
        # Zero-risk edges: additive prior — low-lying areas get baseline risk
        #   even before any flood/scout data arrives.
        # Existing-risk edges: multiplicative amplification — terrain makes
        #   already-flooded depressions riskier.
        # Track terrain contributions per edge for Fix 4 (prior fade)
        terrain_contributions: Dict[Tuple, float] = {}
        if self.dem_enabled and self._node_elevations:
            dem_weight = self._config.dem_weight_terrain_risk
            terrain_prior = 0
            terrain_amplified = 0
            for u, v, key in self.environment.graph.edges(keys=True):
                terrain_risk = self._calculate_terrain_risk(u, v, key)
                if terrain_risk <= 0.0:
                    continue
                current = risk_scores.get((u, v, key), 0.0)
                if current > 0.0:
                    # Multiplicative: amplify existing risk
                    contribution = current * terrain_risk * dem_weight
                    terrain_amplified += 1
                else:
                    # Additive: standalone prior for zero-risk edges
                    contribution = terrain_risk * dem_weight
                    terrain_prior += 1
                risk_scores[(u, v, key)] = min(1.0, current + contribution)
                terrain_contributions[(u, v, key)] = contribution
            if terrain_prior + terrain_amplified > 0:
                logger.info(
                    f"Applied DEM terrain risk (weight={dem_weight}, hybrid): "
                    f"{terrain_prior} edges with prior, "
                    f"{terrain_amplified} edges amplified"
                )

        # --- DEM Block 2: Flood depth estimation from water surface ---
        if (self.dem_enabled and self.dem_service
                and self._config.dem_enable_flood_depth_estimation):
            water_surface_map = self._build_water_surface_map()
            if water_surface_map:
                dem_depth_applied = 0
                for u, v, key in self.environment.graph.edges(keys=True):
                    dem_depth = self._estimate_flood_depth_from_dem(
                        u, v, water_surface_map
                    )
                    if dem_depth is not None and dem_depth > 0.0:
                        # Compute risk contribution from DEM depth and add directly.
                        # flood_depth is not stored on the edge; risk_score is the
                        # only persistent output of this pipeline.
                        k = self._config.sigmoid_steepness
                        x0 = self._config.sigmoid_inflection
                        fd_weight = self.risk_weights["flood_depth"]
                        new_depth_risk = (
                            1.0 / (1.0 + math.exp(-k * (dem_depth - x0))) * fd_weight
                        )
                        if new_depth_risk > 0:
                            current = risk_scores.get((u, v, key), 0.0)
                            risk_scores[(u, v, key)] = min(1.0, current + new_depth_risk)
                            dem_depth_applied += 1
                if dem_depth_applied > 0:
                    logger.info(
                        f"DEM flood depth estimation upgraded {dem_depth_applied} edges "
                        f"from {len(water_surface_map)} station(s)"
                    )

        # --- River Proximity Block: waterway-distance risk prior ---
        # Mirrors DEM Block 1 (hybrid additive + multiplicative):
        #   Zero-risk edges: additive prior (riverbank roads are inherently flood-prone).
        #   Already-flooded edges: multiplicative amplification (active floods hit
        #   riverside roads harder due to overflow and inundation).
        if self.river_enabled and self._node_river_data:
            river_weight = self._config.river_weight
            river_prior = 0
            river_amplified = 0
            for u, v, key in self.environment.graph.edges(keys=True):
                river_risk = self._calculate_river_proximity_risk(u, v, key)
                if river_risk <= 0.0:
                    continue
                current = risk_scores.get((u, v, key), 0.0)
                if current <= 0.0:
                    # Zero-risk edge: additive prior from river proximity
                    risk_scores[(u, v, key)] = river_risk * river_weight
                    river_prior += 1
                else:
                    # Already has risk: multiplicative amplification
                    added = min(river_risk * river_weight, 1.0 - current)
                    risk_scores[(u, v, key)] = min(1.0, current + added)
                    river_amplified += 1
            if river_prior + river_amplified > 0:
                logger.info(
                    f"River proximity prior: {river_prior} edges set, "
                    f"{river_amplified} edges amplified"
                )

        # Add risk from fused data (river levels, weather, crowdsourced)
        # Apply environmental risk spatially (only to edges near reported location)
        all_dam_names = {n.upper() for n in self._config.dam_all_names}
        for location_name, data in fused_data.items():
            # Skip dam entries — relevant dams handled city-wide by dam threat
            # modifier; irrelevant dams (no connection to Marikina) are dropped
            if data.get("_is_dam") or (
                isinstance(location_name, str) and location_name.upper().strip() in all_dam_names
            ):
                continue

            # Weather data is city-wide — skip spatial geocoding
            if data.get("_is_weather"):
                continue

            risk_level = data["risk_level"]

            if risk_level <= 0:
                continue  # Skip locations with no risk

            # Calculate environmental risk factor
            environmental_factor = risk_level * (
                self.risk_weights["crowdsourced"] + self.risk_weights["historical"]
            )

            # Spatial filtering: Apply risk only to edges near the reported location
            if self.enable_spatial_filtering and self.geocoder:
                # Check for pre-geocoded coordinates from fuse_data()
                pre_geocoded = data.get("_coords")
                if pre_geocoded:
                    location_coords = pre_geocoded
                elif isinstance(location_name, (list, tuple)) and len(location_name) == 2:
                    # Already coordinates
                    try:
                        lat, lon = float(location_name[0]), float(location_name[1])
                        location_coords = (lat, lon)
                    except (ValueError, TypeError):
                        location_coords = None
                elif isinstance(location_name, str):
                    location_coords = self.geocoder.get_coordinates(location_name, fuzzy=True)
                else:
                    location_coords = None

                if location_coords:
                    lat, lon = location_coords

                    # Find edges within configured radius
                    nearby_edges = self.find_edges_within_radius(
                        lat=lat,
                        lon=lon,
                        radius_m=self.environmental_risk_radius_m
                    )

                    # Apply environmental risk only to nearby edges
                    for edge_tuple in nearby_edges:
                        current_risk = risk_scores.get(edge_tuple, 0.0)
                        combined_risk = current_risk + environmental_factor
                        risk_scores[edge_tuple] = min(combined_risk, 1.0)  # Cap at 1.0

                    logger.info(
                        f"Applied environmental risk ({environmental_factor:.3f}) from "
                        f"'{location_name}' at ({lat:.4f}, {lon:.4f}) "
                        f"to {len(nearby_edges)} edges within "
                        f"{self.environmental_risk_radius_m}m"
                    )
                else:
                    # Could not geocode location - skip rather than pollute all edges
                    logger.warning(
                        f"No coordinates found for '{location_name}' "
                        f"(risk={risk_level:.3f}) - skipping spatial risk update. "
                        f"Consider adding this location to location.csv"
                    )
            else:
                # Spatial filtering disabled - apply globally (old behavior)
                for edge_tuple in list(self.environment.graph.edges(keys=True)):
                    current_risk = risk_scores.get(edge_tuple, 0.0)
                    combined_risk = current_risk + environmental_factor
                    risk_scores[edge_tuple] = min(combined_risk, 1.0)

        # Apply city-wide dam threat modifier
        if self._config.enable_dam_threat_modifier:
            dam_threat = self._calculate_dam_threat_level()
            if dam_threat > 0.0:
                dam_additive = dam_threat * self._config.dam_additive_weight
                dam_mult = dam_threat * self._config.dam_multiplicative_weight
                dam_modified = 0

                for edge_tuple in list(self.environment.graph.edges(keys=True)):
                    existing = risk_scores.get(edge_tuple, 0.0)
                    modified = min(1.0, existing + dam_additive + existing * dam_mult)
                    if modified > 0.0:
                        risk_scores[edge_tuple] = modified
                        if modified != existing:
                            dam_modified += 1

                logger.info(
                    f"Dam threat level: {dam_threat:.3f} "
                    f"(additive={dam_additive:.4f}, multiplicative={dam_mult:.4f}). "
                    f"Applied dam threat modifier to {dam_modified} edges"
                )
            else:
                logger.debug("Dam threat level: 0.000 (no relevant dam data or all normal)")

        # --- Fix 4: Terrain prior fades with real data ---
        # When real sensor data confirms an area is safe (low non-terrain risk),
        # the DEM terrain prior should fade so it doesn't override actual observations.
        if self._config.dem_prior_fade_enabled and terrain_contributions:
            fade_adjusted = 0
            for edge_key, original_contribution in terrain_contributions.items():
                current_total = risk_scores.get(edge_key, 0.0)
                if current_total <= 0.0 or original_contribution <= 0.0:
                    continue
                # Real data risk = total minus terrain contribution
                real_data_risk = current_total - original_contribution
                # Confidence in real data: high when real sensors dominate
                real_confidence = max(0.0, min(1.0, real_data_risk / current_total))
                # Fade terrain contribution proportionally to real data confidence
                adjusted_contribution = original_contribution * (1.0 - real_confidence)
                reduction = original_contribution - adjusted_contribution
                if reduction > 0.001:
                    risk_scores[edge_key] = max(0.0, current_total - reduction)
                    fade_adjusted += 1
            if fade_adjusted > 0:
                logger.debug(
                    f"Terrain prior fade: adjusted {fade_adjusted} edges"
                )

        # --- Infrastructure risk: road type vulnerability (Kreibich et al. 2009) ---
        # Motorways and trunk roads have better drainage and higher elevation than
        # residential/unclassified roads. Apply an additive modifier per edge using
        # the OSM 'highway' attribute that is already present on all OSMnx graph edges.
        if self._config.infra_risk_weight > 0.0:
            _ROAD_VULNERABILITY: Dict[str, float] = {
                "motorway": 0.1,
                "trunk": 0.1,
                "primary": 0.2,
                "secondary": 0.3,
                "tertiary": 0.4,
                "residential": 0.5,
                "unclassified": 0.6,
            }
            infra_applied = 0
            for u, v, key in self.environment.graph.edges(keys=True):
                edge_data = self.environment.graph[u][v][key]
                highway = edge_data.get("highway", "unclassified")
                # OSMnx may store highway as a list when an edge has multiple tags
                if isinstance(highway, list):
                    highway = highway[0]
                base_vuln = _ROAD_VULNERABILITY.get(str(highway).lower(), 0.5)
                infra_risk = min(base_vuln, 1.0)
                if infra_risk > 0.0:
                    current = risk_scores.get((u, v, key), 0.0)
                    risk_scores[(u, v, key)] = min(
                        1.0, current + infra_risk * self._config.infra_risk_weight
                    )
                    infra_applied += 1
            logger.debug(f"Infrastructure risk applied to {infra_applied} edges")

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

                distance = haversine_distance((lat, lon), (node_lat, node_lon))

                if distance <= radius_m:
                    nearby_nodes.append(node)

        except Exception as e:
            logger.error(f"Error finding nodes within radius: {e}")

        return nearby_nodes

    def get_risk_at_location(
        self,
        lat: float,
        lon: float,
        radius_m: float = 500,
    ) -> Dict[str, Any]:
        """
        Query the current map risk around a coordinate.

        Finds all graph edges within radius_m of (lat, lon) and returns
        aggregate risk statistics plus the flood/scout cache data for
        the area. This represents the risk that is currently displayed
        on the map.

        Args:
            lat: Latitude of the query point
            lon: Longitude of the query point
            radius_m: Search radius in meters (default 500)

        Returns:
            Dict with risk summary for the location
        """
        if not self.environment or not self.environment.graph:
            return {"status": "error", "message": "Graph not available"}

        nearby_nodes = self.get_nodes_within_radius(lat, lon, radius_m)
        if not nearby_nodes:
            return {
                "status": "ok",
                "location": {"lat": lat, "lon": lon},
                "radius_m": radius_m,
                "nearby_nodes": 0,
                "edges_checked": 0,
                "avg_risk": 0.0,
                "max_risk": 0.0,
                "risk_level": "unknown",
                "high_risk_edges": 0,
                "impassable_edges": 0,
                "message": "No graph nodes found within radius",
            }

        # Collect risk scores from edges connected to nearby nodes
        edge_risks = []
        seen_edges = set()
        graph = self.environment.graph

        for node in nearby_nodes:
            for u, v, key in graph.edges(node, keys=True):
                edge_id = (min(u, v), max(u, v), key)
                if edge_id not in seen_edges:
                    seen_edges.add(edge_id)
                    risk = graph[u][v][key].get("risk_score", 0.0)
                    edge_risks.append(risk)

        if not edge_risks:
            avg_risk = 0.0
            max_risk = 0.0
        else:
            avg_risk = sum(edge_risks) / len(edge_risks)
            max_risk = max(edge_risks)

        # Classify risk level
        if max_risk >= self._config.risk_critical_threshold:
            risk_level = "critical"
        elif max_risk >= self._config.risk_high_threshold:
            risk_level = "high"
        elif avg_risk >= self._config.risk_moderate_threshold:
            risk_level = "moderate"
        elif avg_risk >= self._config.risk_low_threshold:
            risk_level = "low"
        else:
            risk_level = "minimal"

        high_risk = sum(1 for r in edge_risks if r >= self._config.risk_high_threshold)
        impassable = sum(1 for r in edge_risks if r >= self._config.risk_critical_threshold)

        # Include relevant flood cache entries near the location
        nearby_flood_data = {}
        for loc_key, flood_entry in self.flood_data_cache.items():
            entry_coords = flood_entry.get("coordinates")
            if entry_coords:
                try:
                    elat = float(entry_coords[0]) if isinstance(entry_coords, (list, tuple)) else float(entry_coords.get("lat", 0))
                    elon = float(entry_coords[1]) if isinstance(entry_coords, (list, tuple)) else float(entry_coords.get("lon", 0))
                    # Rough distance check (~0.005 degrees is ~500m)
                    if abs(elat - lat) < 0.01 and abs(elon - lon) < 0.01:
                        nearby_flood_data[loc_key] = {
                            "water_level": flood_entry.get("water_level"),
                            "rainfall": flood_entry.get("rainfall"),
                            "status": flood_entry.get("status"),
                            "timestamp": flood_entry.get("timestamp"),
                        }
                except (ValueError, TypeError, IndexError):
                    pass

        return {
            "status": "ok",
            "location": {"lat": round(lat, 5), "lon": round(lon, 5)},
            "radius_m": radius_m,
            "nearby_nodes": len(nearby_nodes),
            "edges_checked": len(edge_risks),
            "avg_risk": round(avg_risk, 2),
            "max_risk": round(max_risk, 2),
            "risk_level": risk_level,
            "high_risk_edges": high_risk,
            "impassable_edges": impassable,
            "nearby_flood_data": nearby_flood_data,
            "risk_history": [
                {"timestamp": str(ts), "avg_risk": round(r, 2)}
                for ts, r in self.risk_history[-5:]
            ],
        }

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

            # Log with coordinates if available
            node_data = self.environment.graph.nodes.get(node_id, {})
            node_lon = node_data.get('x')
            node_lat = node_data.get('y')
            coord_str = f" at ({node_lat:.4f}, {node_lon:.4f})" if node_lat and node_lon else ""
            logger.info(
                f"Updated {edges_updated} edges connected to node {node_id}{coord_str} "
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

        v2 Enhancement: Visual Override Logic
        When a scout report has visual_evidence=True AND risk_score > 0.8 AND
        confidence > 0.8, the visual evidence overrides official sensor data.
        This enables faster response to ground-truth conditions.

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
                        "timestamp": datetime,
                        "visual_evidence": bool,  # v2: from Qwen 3-VL
                        "estimated_depth_m": float  # v2: from Qwen 3-VL
                    },
                    ...
                ]

        Example:
            >>> reports = [{
            ...     "location": "Nangka",
            ...     "coordinates": {"lat": 14.6507, "lon": 121.1009},
            ...     "severity": 0.8,
            ...     "confidence": 0.9,
            ...     "visual_evidence": True,
            ...     "estimated_depth_m": 0.5
            ... }]
            >>> hazard_agent.process_scout_data_with_coordinates(reports)
        """
        logger.info(
            f"{self.agent_id} processing {len(scout_reports)} scout reports "
            f"with coordinate-based risk updates"
        )

        reports_processed = 0
        nodes_updated = 0
        visual_overrides = 0

        for report in scout_reports:
            try:
                # Validate report
                if not self._validate_scout_data(report):
                    logger.warning(f"Invalid scout report: {report}")
                    continue

                # Check for duplicates using O(1) set lookup (not O(N) linear search)
                report_location = report.get('location', '')
                if isinstance(report_location, (list, tuple)):
                    report_location = str(report_location)
                report_text = report.get('text', '')

                # Create hash key for deduplication (location + text hash)
                text_hash = hashlib.md5(report_text.encode()).hexdigest()[:16] if report_text else ''
                cache_key = (report_location, text_hash)

                # O(1) duplicate check using set
                if cache_key in self.scout_cache_keys:
                    logger.debug(f"Skipping duplicate scout report: {report_location}")
                else:
                    self._add_to_scout_cache(report, cache_key)

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
                confidence = report.get('confidence', self._config.report_default_confidence)

                # ========== VISUAL OVERRIDE LOGIC (v2) ==========
                # Check if this report qualifies for Visual Override
                visual_evidence = report.get('visual_evidence', False)
                risk_score = report.get('risk_score', severity)

                is_visual_override = (
                    visual_evidence and
                    risk_score > self._config.visual_override_risk_threshold and
                    confidence > self._config.visual_override_confidence_threshold
                )

                if is_visual_override:
                    # Visual Override: Use visual evidence directly
                    # This overrides any conflicting official sensor data
                    risk_level = risk_score  # Use visual risk directly, not weighted
                    visual_overrides += 1

                    # Get estimated depth from visual analysis
                    estimated_depth_m = report.get('estimated_depth_m')

                    # Store vehicle passability at this coordinate
                    vehicles_passable = report.get('vehicles_passable')
                    if vehicles_passable and lat is not None and lon is not None:
                        coord_key = (round(lat, 5), round(lon, 5))
                        self.vehicle_passability_cache[coord_key] = vehicles_passable

                    logger.warning(
                        f"[VISUAL OVERRIDE] High-confidence visual evidence at {report_location}: "
                        f"risk={risk_score:.2f}, confidence={confidence:.2f}, "
                        f"depth={estimated_depth_m}m - OVERRIDING official data"
                    )
                else:
                    # Standard processing: Calculate actual risk level
                    risk_level = severity * confidence
                    logger.info(
                        f"Scout report '{report_location}' at ({lat:.4f}, {lon:.4f}): "
                        f"risk={risk_level:.2f} (severity={severity:.2f}, confidence={confidence:.2f})"
                    )

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
                # Risk decays with distance using configured radius
                nearby_nodes = self.get_nodes_within_radius(
                    lat, lon, self.environmental_risk_radius_m
                )

                for node in nearby_nodes:
                    if node == nearest_node:
                        continue  # Already updated

                    # Get node coordinates
                    node_data = self.environment.graph.nodes[node]
                    node_lat = float(node_data.get('y', 0))
                    node_lon = float(node_data.get('x', 0))

                    if haversine_distance is not None:
                        distance = haversine_distance((lat, lon), (node_lat, node_lon))
                    else:
                        distance = self._haversine_fallback((lat, lon), (node_lat, node_lon))

                    # Apply Gaussian distance decay (physically correct for flood diffusion)
                    # Formula: exp(-(d/σ)²) where σ = radius/3 (99.7% coverage at boundary)
                    sigma = self.environmental_risk_radius_m / 3.0
                    decay_factor = math.exp(-((distance / sigma) ** 2))
                    decayed_risk = risk_level * decay_factor

                    # Only update if decayed risk is significant
                    if decayed_risk > 0.05:
                        self.update_node_risk(node, decayed_risk, source="scout_propagated")
                        nodes_updated += 1

                reports_processed += 1

            except Exception as e:
                logger.error(f"Error processing scout report: {e}", exc_info=True)
                continue

        # Mark that we have new data to process on next step()
        if reports_processed > 0:
            self._has_unprocessed_data = True

        # Log summary with visual override count
        override_msg = f", {visual_overrides} visual overrides applied" if visual_overrides > 0 else ""
        logger.info(
            f"Processed {reports_processed}/{len(scout_reports)} scout reports, "
            f"updated {nodes_updated} graph nodes with coordinate-based risk{override_msg}"
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

