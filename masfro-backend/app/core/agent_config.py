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

import yaml
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List

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

    # Evacuation
    max_centers_to_evaluate: int = 5
    prefer_capacity_over_distance: bool = False

    def validate(self) -> None:
        """Validate configuration values."""
        assert self.safest_risk_penalty >= self.balanced_risk_penalty, \
            "safest_risk_penalty must be >= balanced_risk_penalty"
        assert self.balanced_risk_penalty >= self.fastest_risk_penalty, \
            "balanced_risk_penalty must be >= fastest_risk_penalty"
        assert self.max_node_distance_m > 0, "max_node_distance_m must be positive"
        assert 0 < self.high_risk_threshold <= 1, "high_risk_threshold must be in (0, 1]"
        assert 0 < self.critical_risk_threshold <= 1, "critical_risk_threshold must be in (0, 1]"
        assert self.high_risk_threshold < self.critical_risk_threshold, \
            "high_risk_threshold must be < critical_risk_threshold"


@dataclass
class HazardConfig:
    """Configuration for HazardAgent."""

    # Cache management
    max_flood_cache: int = 100
    max_scout_cache: int = 1000
    cleanup_interval_sec: int = 300
    use_deque: bool = True

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
    decay_function: str = "gaussian"  # linear, exponential, gaussian

    # GeoTIFF
    enable_geotiff: bool = True
    default_return_period: str = "rr01"
    default_time_step: int = 1

    # Depth-to-risk formula
    depth_to_risk_method: str = "sigmoid"
    sigmoid_steepness: float = 8.0  # k parameter
    sigmoid_inflection: float = 0.3  # x0 parameter (FEMA: 50% risk at 0.3m)
    max_depth_m: float = 2.0

    # Rainfall thresholds (mm/hr) for rain risk calculation
    rainfall_light_mm: float = 2.5
    rainfall_moderate_mm: float = 7.5
    rainfall_heavy_mm: float = 15.0
    rainfall_extreme_mm: float = 30.0

    # Visual override thresholds (configurable)
    visual_override_risk_threshold: float = 0.7
    visual_override_confidence_threshold: float = 0.75

    def validate(self) -> None:
        """Validate configuration values."""
        total_weight = self.weight_flood_depth + self.weight_crowdsourced + self.weight_historical
        assert abs(total_weight - 1.0) < 0.01, \
            f"Risk weights must sum to 1.0, got {total_weight}"
        assert self.max_flood_cache > 0, "max_flood_cache must be positive"
        assert self.max_scout_cache > 0, "max_scout_cache must be positive"
        assert self.risk_radius_m > 0, "risk_radius_m must be positive"
        assert self.decay_function in ("linear", "exponential", "gaussian"), \
            f"Invalid decay_function: {self.decay_function}"
        assert 0 < self.visual_override_risk_threshold <= 1.0, \
            "visual_override_risk_threshold must be in (0, 1]"
        assert 0 < self.visual_override_confidence_threshold <= 1.0, \
            "visual_override_confidence_threshold must be in (0, 1]"


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

    # Risk thresholds — dam levels (meters above NHWL)
    dam_alert_m: float = 0.5
    dam_alarm_m: float = 1.0
    dam_critical_m: float = 2.0

    def validate(self) -> None:
        """Validate configuration values."""
        assert self.max_safe_depth_m > 0, "max_safe_depth_m must be positive"
        assert self.max_safe_depth_m <= 0.5, \
            "max_safe_depth_m should not exceed 0.5m (FEMA safety limit)"
        assert self.water_level_alert_m < self.water_level_alarm_m < self.water_level_critical_m, \
            "water_level thresholds must be ordered: alert < alarm < critical"
        assert self.dam_alert_m < self.dam_alarm_m < self.dam_critical_m, \
            "dam thresholds must be ordered: alert < alarm < critical"


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

    def validate(self) -> None:
        """Validate configuration values."""
        assert self.batch_size > 0, "batch_size must be positive"
        assert 0 <= self.min_confidence <= 1, "min_confidence must be in [0, 1]"
        assert self.temporal_dedup_window_minutes >= 0, \
            "temporal_dedup_window_minutes must be non-negative"


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

    # Routing
    always_use_safest_mode: bool = True
    check_center_capacity: bool = False
    warn_if_far: bool = True

    def validate(self) -> None:
        """Validate configuration values."""
        assert self.max_route_history > 0, "max_route_history must be positive"
        assert 0 <= self.default_confidence <= 1, "default_confidence must be in [0, 1]"


@dataclass
class OrchestratorConfig:
    """Configuration for OrchestratorAgent."""

    # Mission timeouts (seconds)
    default_timeout: float = 60.0
    assess_risk_timeout: float = 120.0
    evacuation_timeout: float = 60.0
    route_timeout: float = 30.0
    cascade_timeout: float = 120.0

    # Concurrency limits
    max_concurrent_missions: int = 10
    max_completed_history: int = 100

    # Retry policy
    max_retries: int = 2
    retry_delay_seconds: float = 5.0

    def validate(self) -> None:
        """Validate configuration values."""
        assert self.default_timeout > 0, "default_timeout must be positive"
        assert self.max_concurrent_missions > 0, "max_concurrent_missions must be positive"
        assert self.max_completed_history > 0, "max_completed_history must be positive"
        assert self.max_retries >= 0, "max_retries must be non-negative"


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
        assert self.log_level in valid_levels, f"Invalid log_level: {self.log_level}"


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

    def reload(self) -> None:
        """Reload configuration from file (for hot-reloading)."""
        self._load_config()
        logger.info("Configuration reloaded")

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
            max_centers_to_evaluate=evac.get('max_centers_to_evaluate', 5),
            prefer_capacity_over_distance=evac.get('prefer_capacity_over_distance', False),
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
        geotiff = cfg.get('geotiff', {})
        formulas = cfg.get('formulas', {})
        depth_cfg = formulas.get('depth_to_risk', {})
        rainfall_cfg = formulas.get('rainfall_thresholds_mm', {})
        visual_override = cfg.get('visual_override', {})

        config = HazardConfig(
            max_flood_cache=caches.get('max_flood_entries', 100),
            max_scout_cache=caches.get('max_scout_entries', 1000),
            cleanup_interval_sec=caches.get('cleanup_interval_sec', 300),
            use_deque=caches.get('use_deque', True),
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
            enable_geotiff=geotiff.get('enable', True),
            default_return_period=geotiff.get('default_return_period', 'rr01'),
            default_time_step=geotiff.get('default_time_step', 1),
            depth_to_risk_method=depth_cfg.get('method', 'sigmoid'),
            sigmoid_steepness=depth_cfg.get('sigmoid_steepness', 8.0),
            sigmoid_inflection=depth_cfg.get('sigmoid_inflection', 0.3),
            max_depth_m=depth_cfg.get('max_depth_m', 2.0),
            rainfall_light_mm=rainfall_cfg.get('light', 2.5),
            rainfall_moderate_mm=rainfall_cfg.get('moderate', 7.5),
            rainfall_heavy_mm=rainfall_cfg.get('heavy', 15.0),
            rainfall_extreme_mm=rainfall_cfg.get('extreme', 30.0),
            visual_override_risk_threshold=visual_override.get('risk_threshold', 0.7),
            visual_override_confidence_threshold=visual_override.get('confidence_threshold', 0.75),
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
        )
        config.validate()
        return config

    def get_mock_sources_config(self) -> MockSourcesConfig:
        """Get mock data sources configuration."""
        import os
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
            max_concurrent_missions=cfg.get('max_concurrent_missions', 10),
            max_completed_history=cfg.get('max_completed_history', 100),
            max_retries=retry.get('max_retries', 2),
            retry_delay_seconds=retry.get('retry_delay_seconds', 5.0),
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
