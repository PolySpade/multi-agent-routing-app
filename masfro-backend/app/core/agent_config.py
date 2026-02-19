# filename: app/core/agent_config.py

"""
Agent Configuration System for MAS-FRO

This module provides centralized configuration management for all agents.
Configuration is loaded from config/agents.yaml and validated before use.

Usage:
    from app.core.agent_config import AgentConfigLoader

    config_loader = AgentConfigLoader()
    routing_config = config_loader.get_routing_config()
    hazard_config = config_loader.get_hazard_config()

Author: MAS-FRO Development Team
Date: January 2026
"""

import os
import yaml
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class RoutingConfig:
    """Configuration for RoutingAgent."""

    # Risk penalties (length-proportional: cost = length * (1 + risk * weight))
    safest_risk_penalty: float = 100.0
    balanced_risk_penalty: float = 3.0
    fastest_risk_penalty: float = 0.0

    # Node search
    max_node_distance_m: float = 500.0
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600
    cache_max_entries: int = 10000

    # Warnings
    long_route_threshold_m: float = 10000.0
    high_risk_threshold: float = 0.7
    critical_risk_threshold: float = 0.9
    moderate_risk_threshold: float = 0.5
    fastest_mode_avg_risk_threshold: float = 0.3  # avg_risk above this triggers fastest-mode warning

    # Evacuation
    max_centers_to_evaluate: int = 5
    prefer_capacity_over_distance: bool = False

    def validate(self) -> None:
        """Validate configuration values."""
        if not self.safest_risk_penalty >= self.balanced_risk_penalty:
            raise ValueError("safest_risk_penalty must be >= balanced_risk_penalty")
        if not self.balanced_risk_penalty >= self.fastest_risk_penalty:
            raise ValueError("balanced_risk_penalty must be >= fastest_risk_penalty")
        if not self.max_node_distance_m > 0:
            raise ValueError("max_node_distance_m must be positive")
        if not 0 < self.high_risk_threshold <= 1:
            raise ValueError("high_risk_threshold must be in (0, 1]")
        if not 0 < self.critical_risk_threshold <= 1:
            raise ValueError("critical_risk_threshold must be in (0, 1]")
        if not self.high_risk_threshold < self.critical_risk_threshold:
            raise ValueError("high_risk_threshold must be < critical_risk_threshold")


@dataclass
class HazardConfig:
    """Configuration for HazardAgent."""

    # Cache management
    max_flood_cache: int = 100
    max_scout_cache: int = 1000
    cleanup_interval_sec: int = 300
    use_deque: bool = True
    max_risk_history: int = 20

    # Risk weights (must sum to 1.0)
    weight_flood_depth: float = 0.5
    weight_crowdsourced: float = 0.3
    weight_historical: float = 0.2

    # Risk decay
    enable_risk_decay: bool = True
    scout_fast_rate: float = 0.10
    scout_slow_rate: float = 0.03
    flood_rate: float = 0.05
    scout_ttl_minutes: int = 45
    flood_ttl_minutes: int = 90
    risk_floor: float = 0.15
    min_threshold: float = 0.01

    # Spatial risk
    enable_spatial_filtering: bool = True
    risk_radius_m: float = 800.0
    use_spatial_index: bool = True
    grid_size_degrees: float = 0.01
    decay_function: str = "linear"  # linear, exponential, gaussian

    # Depth-to-risk formula
    depth_to_risk_method: str = "sigmoid"
    sigmoid_steepness: float = 8.0  # k parameter
    sigmoid_inflection: float = 0.3  # x0 parameter (FEMA: 50% risk at 0.3m)
    max_depth_m: float = 2.0
    flow_velocity_mps: float = 0.5  # Assumed urban flood velocity for energy head (Kreibich 2009)

    # Infrastructure risk (road type vulnerability)
    infra_risk_weight: float = 0.1  # Additive weight; motorway=low, residential=high vulnerability

    # Rainfall thresholds (mm/hr) for rain risk calculation
    rainfall_light_mm: float = 2.5
    rainfall_moderate_mm: float = 7.5
    rainfall_heavy_mm: float = 15.0
    rainfall_extreme_mm: float = 30.0

    # Rainfall risk scores (score assigned per rainfall intensity tier)
    rainfall_risk_extreme: float = 0.8
    rainfall_risk_heavy: float = 0.6
    rainfall_risk_moderate: float = 0.4
    rainfall_risk_light: float = 0.2
    rainfall_risk_weight: float = 0.5  # weight of rainfall contribution vs depth

    # Data source confidence
    flood_data_confidence: float = 0.8  # confidence boost for official flood agency data

    # Scout data fusion
    scout_confidence_weight: float = 0.6  # multiplier on scout weighted sums -> confidence
    scout_confidence_boost_cap: float = 0.2  # max confidence boost from multiple sources
    scout_confidence_boost_per_source: float = 0.05  # per-source confidence boost increment

    # Geocoding
    geocoding_fuzzy_threshold: float = 0.6  # minimum fuzzy match ratio for geocoder

    # Dam threat levels (status -> threat score for city-wide modifier)
    dam_alert_threat: float = 0.3
    dam_alarm_threat: float = 0.6

    # Risk classification thresholds (for area risk assessment)
    risk_critical_threshold: float = 0.9  # max_risk >= this -> "critical"
    risk_high_threshold: float = 0.7     # max_risk >= this -> "high"
    risk_moderate_threshold: float = 0.4  # avg_risk >= this -> "moderate"
    risk_low_threshold: float = 0.1      # avg_risk >= this -> "low"

    # Infrastructure risk
    infra_depth_multiplier: float = 0.5  # depth factor for road vulnerability scaling

    # Flood depth tier floors (meters) — calibrated to FEMA sigmoid (k=8, x0=0.3):
    # alert=0.15m -> ~27% risk, alarm=0.30m -> 50% risk, critical=0.60m -> ~92% risk
    depth_tier_floor_critical: float = 0.6
    depth_tier_floor_alarm: float = 0.3
    depth_tier_floor_alert: float = 0.15

    # Default confidence for scout reports without explicit confidence
    report_default_confidence: float = 0.5

    # Visual override thresholds (configurable)
    visual_override_risk_threshold: float = 0.7
    visual_override_confidence_threshold: float = 0.75

    # Dam threat modifier (city-wide flood risk from upstream dams)
    enable_dam_threat_modifier: bool = True
    # Dams with actual hydrological relevance to Marikina (used for threat modifier)
    # ANGAT/IPO/LA MESA: regional weather proxies; CALIRAYA: Laguna de Bay backflow risk
    dam_relevant_names: list[str] = field(default_factory=lambda: ["ANGAT", "IPO", "LA MESA", "CALIRAYA"])
    # All PAGASA-monitored dam names (used to skip geocoding — dams can't map to local edges)
    dam_all_names: list[str] = field(default_factory=lambda: ["ANGAT", "IPO", "LA MESA", "CALIRAYA", "AMBUKLAO", "BINGA", "MAGAT DAM", "PANTABANGAN", "SAN ROQUE"])
    dam_additive_weight: float = 0.05
    dam_multiplicative_weight: float = 0.3
    dam_threat_decay_minutes: float = 120.0

    # DEM (Digital Elevation Model) terrain risk
    enable_dem: bool = False
    dem_file_path: str = "app/data/marikina_dem.tif"
    dem_weight_terrain_risk: float = 0.15
    dem_neighborhood_radius_pixels: int = 5
    dem_low_elevation_threshold: float = -2.0
    dem_slope_drain_threshold: float = 5.0
    dem_enable_flood_depth_estimation: bool = True
    dem_river_station_interpolation_radius_m: float = 2000.0

    # Multi-scale relative elevation (Fix 3)
    dem_regional_radius_pixels: int = 65

    # Barrier awareness — prevent IDW flooding across ridges (Fix 1)
    dem_barrier_check_enabled: bool = True
    dem_barrier_sample_points: int = 5

    # Slope velocity penalty during active flooding (Fix 2)
    dem_velocity_penalty_enabled: bool = True
    dem_wet_slope_depth_threshold: float = 0.1
    dem_velocity_constant: float = 0.5

    # Terrain prior fades with real data (Fix 4)
    dem_prior_fade_enabled: bool = False

    # Water level interpretation for flood depth estimation.
    # True  = water_level_m is depth above ground at the gauge (WSE = ground + level)
    # False = water_level_m is already a water surface elevation (WSE = level as-is)
    dem_water_level_is_depth: bool = True

    # River proximity risk prior
    # Edges near waterways carry inherent baseline risk that amplifies during flooding.
    # Formula: river_risk = type_weight * exp(-distance_m / decay_distance_m)
    enable_river_proximity: bool = False
    river_cache_file: str = "app/data/marikina_waterways.geojson"
    river_weight: float = 0.20
    river_decay_distance_m: float = 200.0
    river_fetch_place: str = "Marikina, Metro Manila, Philippines"

    def validate(self) -> None:
        """Validate configuration values."""
        total_weight = self.weight_flood_depth + self.weight_crowdsourced + self.weight_historical
        if not abs(total_weight - 1.0) < 0.01:
            raise ValueError(f"Risk weights must sum to 1.0, got {total_weight}")
        if not self.max_flood_cache > 0:
            raise ValueError("max_flood_cache must be positive")
        if not self.max_scout_cache > 0:
            raise ValueError("max_scout_cache must be positive")
        if not self.risk_radius_m > 0:
            raise ValueError("risk_radius_m must be positive")
        if self.decay_function not in ("linear", "exponential", "gaussian"):
            raise ValueError(f"Invalid decay_function: {self.decay_function}")
        if not 0 < self.visual_override_risk_threshold <= 1.0:
            raise ValueError("visual_override_risk_threshold must be in (0, 1]")
        if not 0 < self.visual_override_confidence_threshold <= 1.0:
            raise ValueError("visual_override_confidence_threshold must be in (0, 1]")
        if not 0 <= self.dam_additive_weight <= 0.2:
            raise ValueError(f"dam_additive_weight must be in [0, 0.2], got {self.dam_additive_weight}")
        if not 0 <= self.dam_multiplicative_weight <= 1.0:
            raise ValueError(f"dam_multiplicative_weight must be in [0, 1.0], got {self.dam_multiplicative_weight}")


@dataclass
class FloodConfig:
    """Configuration for FloodAgent."""

    # Update frequency
    update_interval_sec: int = 300

    # API settings
    enable_real_apis: bool = True
    enable_simulated_fallback: bool = True
    scraper_timeout_sec: int = 30
    api_timeout_sec: int = 10

    # Passability (SAFETY CRITICAL)
    passability_method: str = "velocity_depth_product"
    max_safe_depth_m: float = 0.3  # FEMA standard
    flow_velocity_mps: float = 0.5
    danger_threshold: float = 0.6

    # Risk thresholds — rainfall (mm/hr)
    rainfall_light_mm: float = 2.5
    rainfall_moderate_mm: float = 7.5
    rainfall_heavy_mm: float = 15.0
    rainfall_extreme_mm: float = 30.0

    # Risk thresholds — water level deviations (meters above normal)
    water_level_alert_m: float = 0.5
    water_level_alarm_m: float = 1.0
    water_level_critical_m: float = 2.0

    # Risk scores per water level status
    water_level_risk_critical: float = 1.0
    water_level_risk_alarm: float = 0.8
    water_level_risk_alert: float = 0.5
    water_level_risk_normal: float = 0.2

    # Risk thresholds — dam levels (meters above NHWL)
    dam_alert_m: float = 0.5
    dam_alarm_m: float = 1.0
    dam_critical_m: float = 2.0

    # Risk scores per dam status
    dam_risk_critical: float = 1.0
    dam_risk_alarm: float = 0.8
    dam_risk_alert: float = 0.5
    dam_risk_watch: float = 0.3
    dam_risk_normal: float = 0.1

    def validate(self) -> None:
        """Validate configuration values."""
        if not self.max_safe_depth_m > 0:
            raise ValueError("max_safe_depth_m must be positive")
        if not self.max_safe_depth_m <= 0.5:
            raise ValueError("max_safe_depth_m should not exceed 0.5m (FEMA safety limit)")
        if not self.water_level_alert_m < self.water_level_alarm_m < self.water_level_critical_m:
            raise ValueError("water_level thresholds must be ordered: alert < alarm < critical")
        if not self.dam_alert_m < self.dam_alarm_m < self.dam_critical_m:
            raise ValueError("dam thresholds must be ordered: alert < alarm < critical")


@dataclass
class ScoutConfig:
    """Configuration for ScoutAgent."""

    # Batch processing
    batch_size: int = 10
    max_queue_size: int = 1000

    # Simulation
    default_scenario: int = 1
    use_ml_prediction: bool = True

    # NLP
    min_confidence: float = 0.6
    extract_severity: bool = True
    extract_location: bool = True

    # Temporal deduplication
    temporal_dedup_window_minutes: float = 10.0

    # Scraper mode (for mock server integration)
    use_scraper: bool = False
    scraper_base_url: str = "http://localhost:8081"

    # Scraper throttle
    scraper_throttle_interval_seconds: float = 15.0
    # Default confidence
    default_confidence: float = 0.5

    def validate(self) -> None:
        """Validate configuration values."""
        if not self.batch_size > 0:
            raise ValueError("batch_size must be positive")
        if not 0 <= self.min_confidence <= 1:
            raise ValueError("min_confidence must be in [0, 1]")
        if not self.temporal_dedup_window_minutes >= 0:
            raise ValueError("temporal_dedup_window_minutes must be non-negative")


@dataclass
class MockSourcesConfig:
    """Configuration for mock data sources."""

    enabled: bool = False
    base_url: str = "http://localhost:8081"

    # Individual endpoint URLs (override base_url when set)
    river_scraper_url: Optional[str] = None
    dam_scraper_url: Optional[str] = None
    weather_api_url: Optional[str] = None
    advisory_pagasa_url: Optional[str] = None
    advisory_rss_url: Optional[str] = None
    social_feed_url: Optional[str] = None
    social_api_url: Optional[str] = None

    def get_river_scraper_url(self) -> str:
        return self.river_scraper_url or f"{self.base_url}/pagasa/water/map.do"

    def get_dam_scraper_url(self) -> str:
        return self.dam_scraper_url or f"{self.base_url}/pagasa/flood"

    def get_weather_base_url(self) -> str:
        return self.weather_api_url or f"{self.base_url}/weather"

    def get_advisory_pagasa_url(self) -> str:
        return self.advisory_pagasa_url or f"{self.base_url}/pagasa/flood"

    def get_advisory_rss_url(self) -> str:
        return self.advisory_rss_url or f"{self.base_url}/news/rss"

    def get_social_feed_url(self) -> str:
        return self.social_feed_url or f"{self.base_url}/social/feed"

    def get_social_api_url(self) -> str:
        return self.social_api_url or f"{self.base_url}/social/api/tweets"


@dataclass
class EvacuationConfig:
    """Configuration for EvacuationManagerAgent."""

    # History tracking
    max_route_history: int = 1000
    max_feedback_history: int = 1000
    use_deque: bool = True

    # Feedback
    default_confidence: float = 0.7
    weight_recent_feedback: float = 0.8
    feedback_ttl_hours: int = 24

    # Feedback confidence values per type
    blocked_with_photo_confidence: float = 0.9
    blocked_no_photo_confidence: float = 0.8
    traffic_confidence: float = 0.5

    # Routing
    always_use_safest_mode: bool = True
    check_center_capacity: bool = False
    warn_if_far: bool = True

    def validate(self) -> None:
        """Validate configuration values."""
        if not self.max_route_history > 0:
            raise ValueError("max_route_history must be positive")
        if not 0 <= self.default_confidence <= 1:
            raise ValueError("default_confidence must be in [0, 1]")


@dataclass
class OrchestratorConfig:
    """Configuration for OrchestratorAgent."""

    # Mission timeouts (seconds)
    default_timeout: float = 60.0
    assess_risk_timeout: float = 120.0
    evacuation_timeout: float = 60.0
    route_timeout: float = 30.0
    cascade_timeout: float = 120.0
    multi_step_timeout: float = 180.0

    # Concurrency limits
    max_concurrent_missions: int = 10
    max_completed_history: int = 100
    max_chat_turns: int = 20

    # Retry policy
    max_retries: int = 2
    retry_delay_seconds: float = 5.0

    # Location matching
    location_match_threshold: float = 0.5  # minimum substring overlap score for barangay match

    def validate(self) -> None:
        """Validate configuration values."""
        if not self.default_timeout > 0:
            raise ValueError("default_timeout must be positive")
        if not self.max_concurrent_missions > 0:
            raise ValueError("max_concurrent_missions must be positive")
        if not self.max_completed_history > 0:
            raise ValueError("max_completed_history must be positive")
        if not self.max_retries >= 0:
            raise ValueError("max_retries must be non-negative")


@dataclass
class RoutingAlgorithmsConfig:
    """Configuration for routing algorithm parameters."""
    base_speed_kmh: float = 30.0
    speed_reduction_factor: float = 0.3
    evac_weight_distance: float = 0.4
    evac_weight_risk: float = 0.5
    evac_weight_capacity: float = 0.1

    def validate(self) -> None:
        if not self.base_speed_kmh > 0:
            raise ValueError("base_speed_kmh must be positive")
        total = self.evac_weight_distance + self.evac_weight_risk + self.evac_weight_capacity
        if not abs(total - 1.0) < 0.01:
            raise ValueError(f"Evacuation score weights must sum to 1.0, got {total}")


@dataclass
class GlobalConfig:
    """Global configuration for all agents."""

    # Logging
    log_level: str = "INFO"
    log_agent_steps: bool = False
    log_message_queue: bool = True

    # Message Queue
    max_queue_size: int = 10000
    message_ttl_seconds: int = 300
    enable_dead_letter: bool = True
    max_dead_letters: int = 100

    # Performance
    enable_profiling: bool = False
    profile_slow_operations: bool = True
    slow_operation_threshold_ms: int = 100

    # Validation bounds
    min_latitude: float = 4.0
    max_latitude: float = 21.0
    min_longitude: float = 116.0
    max_longitude: float = 127.0

    def validate(self) -> None:
        """Validate configuration values."""
        valid_levels = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
        if self.log_level not in valid_levels:
            raise ValueError(f"Invalid log_level: {self.log_level}")


def _deep_merge(base: dict, overrides: dict) -> dict:
    """Recursively merge *overrides* into *base* (mutates *base*)."""
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


class AgentConfigLoader:
    """
    Load and validate agent configurations from YAML file.

    Provides type-safe access to configuration values with defaults
    and validation. Supports hot-reloading for development.

    Example:
        >>> loader = AgentConfigLoader()
        >>> routing = loader.get_routing_config()
        >>> print(routing.balanced_risk_penalty)
        3.0
    """

    _instance: Optional['AgentConfigLoader'] = None
    _config: Dict[str, Any] = {}

    def __new__(cls, config_path: Optional[str] = None):
        """Singleton pattern for global config access."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the configuration loader.

        Args:
            config_path: Path to agents.yaml. If None, uses default location.
        """
        if self._initialized:
            return

        if config_path is None:
            # Try multiple possible locations
            possible_paths = [
                Path("config/agents.yaml"),
                Path("masfro-backend/config/agents.yaml"),
                Path(__file__).parent.parent.parent / "config" / "agents.yaml",
            ]
            for path in possible_paths:
                if path.exists():
                    config_path = str(path)
                    break

        self.config_path = Path(config_path) if config_path else None
        self._load_config()
        self._initialized = True

    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        if self.config_path is None or not self.config_path.exists():
            logger.warning(
                f"Config file not found at {self.config_path}. Using defaults."
            )
            self._config = {}
            return

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f) or {}
            logger.info(f"Loaded agent configuration from {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to load config from {self.config_path}: {e}")
            self._config = {}

    # ── Hot-reload helpers ──

    def reload(self) -> None:
        """Re-read YAML from disk into the in-memory config dict."""
        self._load_config()
        logger.info("Configuration reloaded from disk")

    def update_section(self, section: str, updates: dict) -> None:
        """Merge *updates* into the in-memory config for *section*."""
        if section not in self._config:
            self._config[section] = {}
        _deep_merge(self._config[section], updates)

    def save_to_file(self) -> None:
        """Write the current in-memory config dict back to the YAML file."""
        if self.config_path is None:
            raise ValueError("No config file path configured")
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(
                self._config, f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )
        logger.info(f"Configuration saved to {self.config_path}")

    def get_raw_config(self) -> dict:
        """Return the raw config dict (for API / UI exposure)."""
        return dict(self._config)

    def get_routing_config(self) -> RoutingConfig:
        """Get RoutingAgent configuration."""
        cfg = self._config.get('routing_agent', {})
        penalties = cfg.get('risk_penalties', {})
        search = cfg.get('search', {})
        warnings = cfg.get('warnings', {})
        evac = cfg.get('evacuation', {})

        config = RoutingConfig(
            safest_risk_penalty=penalties.get('safest_mode', 100.0),
            balanced_risk_penalty=penalties.get('balanced_mode', 3.0),
            fastest_risk_penalty=penalties.get('fastest_mode', 0.0),
            max_node_distance_m=search.get('max_node_distance_m', 500.0),
            cache_enabled=search.get('cache_enabled', True),
            cache_ttl_seconds=search.get('cache_ttl_seconds', 3600),
            cache_max_entries=search.get('cache_max_entries', 10000),
            long_route_threshold_m=warnings.get('long_route_threshold_m', 10000.0),
            high_risk_threshold=warnings.get('high_risk_threshold', 0.7),
            critical_risk_threshold=warnings.get('critical_risk_threshold', 0.9),
            moderate_risk_threshold=warnings.get('moderate_risk_threshold', 0.5),
            fastest_mode_avg_risk_threshold=warnings.get('fastest_mode_avg_risk_threshold', 0.3),
            max_centers_to_evaluate=evac.get('max_centers_to_evaluate', 5),
            prefer_capacity_over_distance=evac.get('prefer_capacity_over_distance', False),
        )
        config.validate()
        return config

    def get_algorithms_config(self) -> RoutingAlgorithmsConfig:
        """Get routing algorithm configuration."""
        cfg = self._config.get('routing_agent', {})
        algos = cfg.get('algorithms', {})
        evac_weights = algos.get('evacuation_score_weights', {})

        config = RoutingAlgorithmsConfig(
            base_speed_kmh=algos.get('base_speed_kmh', 30.0),
            speed_reduction_factor=algos.get('speed_reduction_factor', 0.3),
            evac_weight_distance=evac_weights.get('distance', 0.4),
            evac_weight_risk=evac_weights.get('risk', 0.5),
            evac_weight_capacity=evac_weights.get('capacity', 0.1),
        )
        config.validate()
        return config

    def get_hazard_config(self) -> HazardConfig:
        """Get HazardAgent configuration."""
        cfg = self._config.get('hazard_agent', {})
        caches = cfg.get('caches', {})
        weights = cfg.get('risk_weights', {})
        decay = cfg.get('risk_decay', {})
        ttl = decay.get('ttl_minutes', {})
        spatial = cfg.get('spatial', {})
        formulas = cfg.get('formulas', {})
        depth_cfg = formulas.get('depth_to_risk', {})
        rainfall_cfg = formulas.get('rainfall_thresholds_mm', {})
        rainfall_risk = formulas.get('rainfall_risk_scores', {})
        fusion_cfg = cfg.get('data_fusion', {})
        visual_override = cfg.get('visual_override', {})
        dam_threat = cfg.get('dam_threat_modifier', {})
        risk_cls = cfg.get('risk_classification', {})
        dem = cfg.get('dem', {})
        river = cfg.get('river_proximity', {})

        config = HazardConfig(
            max_flood_cache=caches.get('max_flood_entries', 100),
            max_scout_cache=caches.get('max_scout_entries', 1000),
            cleanup_interval_sec=caches.get('cleanup_interval_sec', 300),
            use_deque=caches.get('use_deque', True),
            max_risk_history=caches.get('max_risk_history', 20),
            weight_flood_depth=weights.get('flood_depth', 0.5),
            weight_crowdsourced=weights.get('crowdsourced', 0.3),
            weight_historical=weights.get('historical', 0.2),
            enable_risk_decay=decay.get('enable', True),
            scout_fast_rate=decay.get('scout_fast_rate', 0.10),
            scout_slow_rate=decay.get('scout_slow_rate', 0.03),
            flood_rate=decay.get('flood_rate', 0.05),
            scout_ttl_minutes=ttl.get('scout_reports', 45),
            flood_ttl_minutes=ttl.get('flood_data', 90),
            risk_floor=decay.get('risk_floor', 0.15),
            min_threshold=decay.get('min_threshold', 0.01),
            enable_spatial_filtering=spatial.get('enable_filtering', True),
            risk_radius_m=spatial.get('risk_radius_m', 800.0),
            use_spatial_index=spatial.get('use_spatial_index', True),
            grid_size_degrees=spatial.get('grid_size_degrees', 0.01),
            decay_function=spatial.get('decay_function', 'gaussian'),
            depth_to_risk_method=depth_cfg.get('method', 'sigmoid'),
            sigmoid_steepness=depth_cfg.get('sigmoid_steepness', 8.0),
            sigmoid_inflection=depth_cfg.get('sigmoid_inflection', 0.3),
            max_depth_m=depth_cfg.get('max_depth_m', 2.0),
            flow_velocity_mps=depth_cfg.get('flow_velocity_mps', 0.5),
            infra_risk_weight=weights.get('infra_risk_weight', 0.1),
            rainfall_light_mm=rainfall_cfg.get('light', 2.5),
            rainfall_moderate_mm=rainfall_cfg.get('moderate', 7.5),
            rainfall_heavy_mm=rainfall_cfg.get('heavy', 15.0),
            rainfall_extreme_mm=rainfall_cfg.get('extreme', 30.0),
            visual_override_risk_threshold=visual_override.get('risk_threshold', 0.7),
            visual_override_confidence_threshold=visual_override.get('confidence_threshold', 0.75),
            enable_dam_threat_modifier=dam_threat.get('enable', True),
            dam_relevant_names=dam_threat.get('relevant_dams', ["ANGAT", "IPO", "LA MESA", "CALIRAYA"]),
            dam_all_names=dam_threat.get('all_dam_names', ["ANGAT", "IPO", "LA MESA", "CALIRAYA", "AMBUKLAO", "BINGA", "MAGAT DAM", "PANTABANGAN", "SAN ROQUE"]),
            dam_additive_weight=dam_threat.get('additive_weight', 0.05),
            dam_multiplicative_weight=dam_threat.get('multiplicative_weight', 0.3),
            dam_threat_decay_minutes=dam_threat.get('threat_decay_minutes', 120.0),
            enable_dem=dem.get('enable', False),
            dem_file_path=dem.get('file_path', 'app/data/marikina_dem.tif'),
            dem_weight_terrain_risk=dem.get('weight_terrain_risk', 0.15),
            dem_neighborhood_radius_pixels=dem.get('neighborhood_radius_pixels', 5),
            dem_low_elevation_threshold=dem.get('low_elevation_threshold', -2.0),
            dem_slope_drain_threshold=dem.get('slope_drain_threshold', 5.0),
            dem_enable_flood_depth_estimation=dem.get('enable_flood_depth_estimation', True),
            dem_river_station_interpolation_radius_m=dem.get('river_station_interpolation_radius_m', 2000.0),
            dem_regional_radius_pixels=dem.get('regional_radius_pixels', 65),
            dem_barrier_check_enabled=dem.get('barrier_check_enabled', True),
            dem_barrier_sample_points=dem.get('barrier_sample_points', 5),
            dem_velocity_penalty_enabled=dem.get('velocity_penalty_enabled', True),
            dem_wet_slope_depth_threshold=dem.get('wet_slope_depth_threshold', 0.1),
            dem_velocity_constant=dem.get('velocity_constant', 0.5),
            dem_prior_fade_enabled=dem.get('prior_fade_enabled', False),
            dem_water_level_is_depth=dem.get('water_level_is_depth', True),
            enable_river_proximity=river.get('enable', False),
            river_cache_file=river.get('cache_file', 'app/data/marikina_waterways.geojson'),
            river_weight=river.get('weight', 0.20),
            river_decay_distance_m=river.get('decay_distance_m', 200.0),
            river_fetch_place=river.get('fetch_place', 'Marikina, Metro Manila, Philippines'),
            # Rainfall risk scores
            rainfall_risk_extreme=rainfall_risk.get('extreme', 0.8),
            rainfall_risk_heavy=rainfall_risk.get('heavy', 0.6),
            rainfall_risk_moderate=rainfall_risk.get('moderate', 0.4),
            rainfall_risk_light=rainfall_risk.get('light', 0.2),
            rainfall_risk_weight=rainfall_risk.get('weight', 0.5),
            # Data fusion
            flood_data_confidence=fusion_cfg.get('flood_data_confidence', 0.8),
            scout_confidence_weight=fusion_cfg.get('scout_confidence_weight', 0.6),
            scout_confidence_boost_cap=fusion_cfg.get('scout_confidence_boost_cap', 0.2),
            scout_confidence_boost_per_source=fusion_cfg.get('scout_confidence_boost_per_source', 0.05),
            geocoding_fuzzy_threshold=fusion_cfg.get('geocoding_fuzzy_threshold', 0.6),
            # Dam threat levels
            dam_alert_threat=dam_threat.get('alert_threat', 0.3),
            dam_alarm_threat=dam_threat.get('alarm_threat', 0.6),
            # Risk classification
            risk_critical_threshold=risk_cls.get('critical', 0.9),
            risk_high_threshold=risk_cls.get('high', 0.7),
            risk_moderate_threshold=risk_cls.get('moderate', 0.4),
            risk_low_threshold=risk_cls.get('low', 0.1),
            # Infrastructure
            infra_depth_multiplier=weights.get('infra_depth_multiplier', 0.5),
            # Depth tier floors
            depth_tier_floor_critical=depth_cfg.get('tier_floor_critical', 0.6),
            depth_tier_floor_alarm=depth_cfg.get('tier_floor_alarm', 0.3),
            depth_tier_floor_alert=depth_cfg.get('tier_floor_alert', 0.15),
            report_default_confidence=fusion_cfg.get('report_default_confidence', 0.5),
        )
        config.validate()
        return config

    def get_flood_config(self) -> FloodConfig:
        """Get FloodAgent configuration."""
        cfg = self._config.get('flood_agent', {})
        apis = cfg.get('apis', {})
        timeouts = apis.get('timeouts_sec', {})
        passability = cfg.get('passability', {})
        thresholds = cfg.get('risk_thresholds', {})
        rainfall = thresholds.get('rainfall_mm', {})
        water_levels = thresholds.get('water_level_deviations_m', {})
        dam_levels = thresholds.get('dam_levels_m', {})
        risk_scores = thresholds.get('risk_scores', {})

        config = FloodConfig(
            update_interval_sec=cfg.get('update_interval_sec', 300),
            enable_real_apis=apis.get('enable_real_apis', True),
            enable_simulated_fallback=apis.get('enable_simulated_fallback', True),
            scraper_timeout_sec=timeouts.get('scraper_timeout', 30),
            api_timeout_sec=timeouts.get('api_timeout', 10),
            passability_method=passability.get('method', 'velocity_depth_product'),
            max_safe_depth_m=passability.get('max_safe_depth_m', 0.3),
            flow_velocity_mps=passability.get('flow_velocity_mps', 0.5),
            danger_threshold=passability.get('danger_threshold', 0.6),
            rainfall_light_mm=rainfall.get('light', 2.5),
            rainfall_moderate_mm=rainfall.get('moderate', 7.5),
            rainfall_heavy_mm=rainfall.get('heavy', 15.0),
            rainfall_extreme_mm=rainfall.get('extreme', 30.0),
            water_level_alert_m=water_levels.get('alert', 0.5),
            water_level_alarm_m=water_levels.get('alarm', 1.0),
            water_level_critical_m=water_levels.get('critical', 2.0),
            dam_alert_m=dam_levels.get('alert', 0.5),
            dam_alarm_m=dam_levels.get('alarm', 1.0),
            dam_critical_m=dam_levels.get('critical', 2.0),
            water_level_risk_critical=risk_scores.get('water_level_critical', 1.0),
            water_level_risk_alarm=risk_scores.get('water_level_alarm', 0.8),
            water_level_risk_alert=risk_scores.get('water_level_alert', 0.5),
            water_level_risk_normal=risk_scores.get('water_level_normal', 0.2),
            dam_risk_critical=risk_scores.get('dam_critical', 1.0),
            dam_risk_alarm=risk_scores.get('dam_alarm', 0.8),
            dam_risk_alert=risk_scores.get('dam_alert', 0.5),
            dam_risk_watch=risk_scores.get('dam_watch', 0.3),
            dam_risk_normal=risk_scores.get('dam_normal', 0.1),
        )
        config.validate()
        return config

    def get_scout_config(self) -> ScoutConfig:
        """Get ScoutAgent configuration."""
        cfg = self._config.get('scout_agent', {})
        sim = cfg.get('simulation', {})
        nlp = cfg.get('nlp', {})
        dedup = cfg.get('deduplication', {})
        scraper = cfg.get('scraper', {})

        config = ScoutConfig(
            batch_size=cfg.get('batch_size', 10),
            max_queue_size=cfg.get('max_queue_size', 1000),
            default_scenario=sim.get('default_scenario', 1),
            use_ml_prediction=sim.get('use_ml_prediction', True),
            min_confidence=nlp.get('min_confidence', 0.6),
            extract_severity=nlp.get('extract_severity', True),
            extract_location=nlp.get('extract_location', True),
            temporal_dedup_window_minutes=dedup.get('temporal_window_minutes', 10.0),
            use_scraper=scraper.get('enable', False),
            scraper_base_url=scraper.get('base_url', 'http://localhost:8081'),
            scraper_throttle_interval_seconds=cfg.get('scraper_throttle_interval_seconds', 15.0),
            default_confidence=cfg.get('default_confidence', 0.5),
        )
        config.validate()
        return config

    def get_mock_sources_config(self) -> MockSourcesConfig:
        """Get mock data sources configuration."""
        cfg = self._config.get('mock_sources', {})
        urls = cfg.get('urls', {})

        # Environment variables override YAML config
        enabled = os.environ.get('USE_MOCK_SOURCES', '').lower() in ('true', '1', 'yes')
        if not enabled:
            enabled = cfg.get('enabled', False)

        base_url = os.environ.get('MOCK_SERVER_URL') or cfg.get('base_url', 'http://localhost:8081')

        return MockSourcesConfig(
            enabled=enabled,
            base_url=base_url,
            river_scraper_url=os.environ.get('MOCK_PAGASA_URL') or urls.get('river_scraper'),
            dam_scraper_url=os.environ.get('MOCK_DAM_URL') or urls.get('dam_scraper'),
            weather_api_url=os.environ.get('MOCK_WEATHER_URL') or urls.get('weather_api'),
            advisory_pagasa_url=urls.get('advisory_pagasa'),
            advisory_rss_url=os.environ.get('MOCK_RSS_URL') or urls.get('advisory_rss'),
            social_feed_url=os.environ.get('MOCK_SOCIAL_URL') or urls.get('social_feed'),
            social_api_url=urls.get('social_api'),
        )

    def get_evacuation_config(self) -> EvacuationConfig:
        """Get EvacuationManagerAgent configuration."""
        cfg = self._config.get('evacuation_manager_agent', {})
        history = cfg.get('history', {})
        feedback = cfg.get('feedback', {})
        evac = cfg.get('evacuation', {})

        config = EvacuationConfig(
            max_route_history=history.get('max_route_history', 1000),
            max_feedback_history=history.get('max_feedback_history', 1000),
            use_deque=history.get('use_deque', True),
            default_confidence=feedback.get('default_confidence', 0.7),
            weight_recent_feedback=feedback.get('weight_recent_feedback', 0.8),
            feedback_ttl_hours=feedback.get('feedback_ttl_hours', 24),
            always_use_safest_mode=evac.get('always_use_safest_mode', True),
            check_center_capacity=evac.get('check_center_capacity', False),
            warn_if_far=evac.get('warn_if_far', True),
            blocked_with_photo_confidence=feedback.get('blocked_with_photo_confidence', 0.9),
            blocked_no_photo_confidence=feedback.get('blocked_no_photo_confidence', 0.8),
            traffic_confidence=feedback.get('traffic_confidence', 0.5),
        )
        config.validate()
        return config

    def get_orchestrator_config(self) -> OrchestratorConfig:
        """Get OrchestratorAgent configuration."""
        cfg = self._config.get('orchestrator_agent', {})
        timeouts = cfg.get('timeouts', {})
        retry = cfg.get('retry', {})

        config = OrchestratorConfig(
            default_timeout=timeouts.get('default', 60.0),
            assess_risk_timeout=timeouts.get('assess_risk', 120.0),
            evacuation_timeout=timeouts.get('coordinated_evacuation', 60.0),
            route_timeout=timeouts.get('route_calculation', 30.0),
            cascade_timeout=timeouts.get('cascade_risk_update', 120.0),
            multi_step_timeout=timeouts.get('multi_step', 180.0),
            max_concurrent_missions=cfg.get('max_concurrent_missions', 10),
            max_completed_history=cfg.get('max_completed_history', 100),
            max_chat_turns=cfg.get('max_chat_turns', 20),
            max_retries=retry.get('max_retries', 2),
            retry_delay_seconds=retry.get('retry_delay_seconds', 5.0),
            location_match_threshold=cfg.get('location_match_threshold', 0.5),
        )
        config.validate()
        return config

    def get_global_config(self) -> GlobalConfig:
        """Get global configuration."""
        cfg = self._config.get('global', {})
        logging_cfg = cfg.get('logging', {})
        mq = cfg.get('message_queue', {})
        perf = cfg.get('performance', {})
        validation = self._config.get('validation', {})
        coords = validation.get('coordinates', {})

        config = GlobalConfig(
            log_level=logging_cfg.get('level', 'INFO'),
            log_agent_steps=logging_cfg.get('log_agent_steps', False),
            log_message_queue=logging_cfg.get('log_message_queue', True),
            max_queue_size=mq.get('max_queue_size', 10000),
            message_ttl_seconds=mq.get('message_ttl_seconds', 300),
            enable_dead_letter=mq.get('enable_dead_letter', True),
            max_dead_letters=mq.get('max_dead_letters', 100),
            enable_profiling=perf.get('enable_profiling', False),
            profile_slow_operations=perf.get('profile_slow_operations', True),
            slow_operation_threshold_ms=perf.get('slow_operation_threshold_ms', 100),
            min_latitude=coords.get('min_latitude', 4.0),
            max_latitude=coords.get('max_latitude', 21.0),
            min_longitude=coords.get('min_longitude', 116.0),
            max_longitude=coords.get('max_longitude', 127.0),
        )
        config.validate()
        return config


# Convenience function for quick access
def get_config() -> AgentConfigLoader:
    """Get the singleton configuration loader instance."""
    return AgentConfigLoader()
