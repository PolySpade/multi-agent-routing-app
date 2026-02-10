# filename: app/agents/flood_agent.py

"""
Flood Agent for Multi-Agent System for Flood Route Optimization (MAS-FRO)

This module implements the FloodAgent class, which collects official
environmental data from authoritative sources such as PAGASA (Philippine
Atmospheric, Geophysical and Astronomical Services Administration) rain gauges,
river level sensors, and DOST-NOAH flood monitoring systems.

The agent is responsible for:
- Scraping/fetching official rainfall data
- Monitoring river water levels
- Collecting flood depth measurements
- Forwarding validated data to HazardAgent

v2 Enhancements:
- Qwen 3 LLM integration for PAGASA text bulletin parsing
- parse_text_advisory() method for unstructured advisory text
- collect_and_parse_advisories() for batch advisory processing

Author: MAS-FRO Development Team
Date: February 2026
"""

from .base_agent import BaseAgent
from typing import Dict, Any, Optional, List, Set, Tuple, TYPE_CHECKING
import asyncio
import hashlib
import logging
from datetime import datetime
import requests
from bs4 import BeautifulSoup

if TYPE_CHECKING:
    from ..environment.graph_manager import DynamicGraphEnvironment
    from ..communication.message_queue import MessageQueue

# ACL Protocol imports
try:
    from communication.acl_protocol import ACLMessage, Performative, create_inform_message
except ImportError:
    from app.communication.acl_protocol import ACLMessage, Performative, create_inform_message

try:
    from services.data_sources import DataCollector
    from services.river_scraper_service import RiverScraperService
    from services.weather_service import OpenWeatherMapService
    from services.dam_water_scraper_service import DamWaterScraperService
    from services.advisory_scraper_service import AdvisoryScraperService
except ImportError:
    from app.services.data_sources import DataCollector
    from app.services.river_scraper_service import RiverScraperService
    from app.services.weather_service import OpenWeatherMapService
    from app.services.dam_water_scraper_service import DamWaterScraperService
    from app.services.advisory_scraper_service import AdvisoryScraperService

logger = logging.getLogger(__name__)


class FloodAgent(BaseAgent):
    """
    Agent for collecting official environmental flood data.

    This agent monitors official data sources including PAGASA rain gauges,
    river level sensors, and flood monitoring stations. It validates the data
    and forwards it to the HazardAgent for integration into the risk
    assessment system.

    Data sources prioritize official government agencies for reliability:
    - PAGASA: Philippine weather bureau (rainfall, weather forecasts)
    - DOST-NOAH: Nationwide Operational Assessment of Hazards
    - MMDA: Metropolitan Manila Development Authority (flood reports)

    Attributes:
        agent_id: Unique identifier for this agent instance
        environment: Reference to DynamicGraphEnvironment
        pagasa_api_url: URL for PAGASA data API
        river_sensor_url: URL for river level sensor data
        data_update_interval: Seconds between data fetches
        last_update: Timestamp of last successful data fetch

    Example:
        >>> env = DynamicGraphEnvironment()
        >>> agent = FloodAgent("flood_001", env)
        >>> agent.step()  # Fetches latest data and updates environment
    """

    def __init__(
        self,
        agent_id: str,
        environment: "DynamicGraphEnvironment",
        message_queue: Optional["MessageQueue"] = None,
        use_simulated: bool = False,
        use_real_apis: bool = True,
        hazard_agent_id: str = "hazard_agent_001",
        enable_llm: bool = True
    ) -> None:
        """
        Initialize the FloodAgent.

        Args:
            agent_id: Unique identifier for this agent
            environment: DynamicGraphEnvironment instance
            message_queue: MessageQueue instance for MAS communication
            use_simulated: Use simulated data for testing (default: False)
            use_real_apis: Use real API services (default: True)
            hazard_agent_id: ID of HazardAgent to send messages to
            enable_llm: Enable Qwen 3 LLM for advisory parsing (default: True)
        """
        super().__init__(agent_id, environment, message_queue=message_queue)
        self.hazard_agent_id = hazard_agent_id
        self.use_real_apis = use_real_apis

        # ========== LLM SERVICE INITIALIZATION (v2) ==========
        self.llm_service = None
        self.use_llm = False

        if enable_llm:
            try:
                from ..services.llm_service import get_llm_service
                self.llm_service = get_llm_service()
                if self.llm_service.is_available():
                    self.use_llm = True
                    logger.info(f"{self.agent_id} LLM Service initialized for advisory parsing")
                else:
                    logger.warning(f"{self.agent_id} LLM Service not available")
            except Exception as e:
                logger.warning(f"{self.agent_id} failed to initialize LLM Service: {e}")

        # Load mock sources config
        mock_cfg = None
        try:
            from ..core.agent_config import AgentConfigLoader
            mock_cfg = AgentConfigLoader().get_mock_sources_config()
        except Exception as e:
            logger.debug(f"{self.agent_id} mock sources config not available: {e}")

        # Initialize real API services
        if use_real_apis:
            # Determine URLs: use mock URLs if enabled, else None (default to real)
            river_url = mock_cfg.get_river_scraper_url() if (mock_cfg and mock_cfg.enabled) else None
            dam_url = mock_cfg.get_dam_scraper_url() if (mock_cfg and mock_cfg.enabled) else None
            weather_url = mock_cfg.get_weather_base_url() if (mock_cfg and mock_cfg.enabled) else None
            pagasa_url = mock_cfg.get_advisory_pagasa_url() if (mock_cfg and mock_cfg.enabled) else None
            rss_url = mock_cfg.get_advisory_rss_url() if (mock_cfg and mock_cfg.enabled) else None

            if mock_cfg and mock_cfg.enabled:
                logger.info(f"{self.agent_id} using MOCK data sources at {mock_cfg.base_url}")

            # PAGASA River Scraper Service
            try:
                self.river_scraper = RiverScraperService(base_url=river_url)
                logger.info(f"{self.agent_id} initialized RiverScraperService")
            except Exception as e:
                logger.error(f"Failed to initialize RiverScraperService: {e}")
                self.river_scraper = None

            # OpenWeatherMap Service
            try:
                self.weather_service = OpenWeatherMapService(base_url=weather_url)
                logger.info(f"{self.agent_id} initialized OpenWeatherMapService")
            except ValueError as e:
                logger.warning(f"OpenWeatherMap not available: {e}")
                self.weather_service = None
            except Exception as e:
                logger.error(f"Failed to initialize OpenWeatherMapService: {e}")
                self.weather_service = None

            # Dam Water Scraper Service
            try:
                self.dam_scraper = DamWaterScraperService(url=dam_url)
                logger.info(f"{self.agent_id} initialized DamWaterScraperService")
            except Exception as e:
                logger.error(f"Failed to initialize DamWaterScraperService: {e}")
                self.dam_scraper = None

            # Advisory Scraper Service (Text/RSS)
            try:
                self.advisory_scraper = AdvisoryScraperService(
                    max_age_hours=24, pagasa_url=pagasa_url, rss_url=rss_url
                )
                logger.info(f"{self.agent_id} initialized AdvisoryScraperService")
            except Exception as e:
                logger.error(f"Failed to initialize AdvisoryScraperService: {e}")
                self.advisory_scraper = None
        else:
            self.river_scraper = None
            self.weather_service = None
            self.dam_scraper = None
            self.advisory_scraper = None
            logger.info(f"{self.agent_id} real APIs disabled")

        # Initialize data collector (fallback for simulated data)
        self.data_collector = DataCollector(
            use_simulated=use_simulated,
            enable_pagasa=False,
            enable_noah=False,
            enable_mmda=False
        )

        # Load configuration from agents.yaml via FloodConfig
        try:
            from ..core.agent_config import AgentConfigLoader
            self._config = AgentConfigLoader().get_flood_config()
        except Exception as e:
            logger.warning(f"{self.agent_id} failed to load FloodConfig, using defaults: {e}")
            from ..core.agent_config import FloodConfig
            self._config = FloodConfig()

        self.data_update_interval = self._config.update_interval_sec
        self.last_update: Optional[datetime] = None

        # Data caches
        self.rainfall_data: Dict[str, Any] = {}
        self.river_levels: Dict[str, Any] = {}
        self.flood_depth_data: Dict[str, Any] = {}
        self.dam_levels: Dict[str, Any] = {}

        # Advisory deduplication — track hashes of already-processed advisories
        self._processed_advisory_hashes: Set[str] = set()

        # API failure tracking — alert after consecutive failures
        self._consecutive_api_failures: int = 0
        self._api_failure_alert_threshold: int = 3
        self._last_successful_real_fetch: Optional[datetime] = None

        logger.info(
            f"{self.agent_id} initialized with update interval "
            f"{self.data_update_interval}s, real_apis={use_real_apis}, "
            f"simulated={use_simulated}"
        )

    def step(self):
        """
        Perform one step of the agent's operation.

        Processes any pending MQ requests from orchestrator, then
        fetches latest official flood data from all configured sources,
        validates the data, and sends it to the HazardAgent via MessageQueue
        using ACL protocol.
        """
        # Process any orchestrator REQUEST messages first
        self._process_mq_requests()

        logger.debug(f"{self.agent_id} performing step at {datetime.now()}")

        # Check if update is needed
        if self._should_update():
            collected_data = self.collect_flood_data()
            if collected_data:
                self.send_flood_data_via_message(collected_data)

    def _process_mq_requests(self) -> None:
        """Process incoming REQUEST messages from orchestrator via MQ."""
        if not self.message_queue:
            return

        while True:
            msg = self.message_queue.receive_message(
                agent_id=self.agent_id, timeout=0.0, block=False
            )
            if msg is None:
                break

            if msg.performative == Performative.REQUEST:
                action = msg.content.get("action")

                if action == "collect_data":
                    self._handle_collect_data_request(msg)
                else:
                    logger.warning(
                        f"{self.agent_id}: unknown REQUEST action '{action}' "
                        f"from {msg.sender}"
                    )
            else:
                logger.debug(
                    f"{self.agent_id}: ignoring {msg.performative} from {msg.sender}"
                )

    def _handle_collect_data_request(self, msg: ACLMessage) -> None:
        """Handle collect_data REQUEST: force data collection and reply."""
        result = {"status": "unknown", "locations_collected": 0}

        try:
            collected_data = self.collect_flood_data()
            if collected_data:
                # Send data to hazard agent via normal flow
                self.send_flood_data_via_message(collected_data)
                result["status"] = "success"
                result["locations_collected"] = len(collected_data)
            else:
                result["status"] = "no_data"
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

        logger.info(
            f"{self.agent_id}: collect_data -> {result['status']} "
            f"({result['locations_collected']} locations)"
        )

        # Send INFORM reply to requester
        reply = create_inform_message(
            sender=self.agent_id,
            receiver=msg.sender,
            info_type="collect_data_result",
            data=result,
            conversation_id=msg.conversation_id,
            in_reply_to=msg.reply_with,
        )
        try:
            self.message_queue.send_message(reply)
        except Exception as e:
            logger.error(f"{self.agent_id}: failed to reply to {msg.sender}: {e}")

    def inject_manual_advisory(self, advisory_content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Manually inject a news/advisory into the agent.
        
        Args:
            advisory_content: Dictionary containing advisory data (text, source, etc.)
            
        Returns:
            Processed data status
        """
        logger.info(f"{self.agent_id} received manual advisory injection")

        try:
            # Create a synthetic data structure compatible with collect_flood_data
            # We treat this as a "manual" source
            
            # If text is provided, try to parse it using the same logic as real advisories
            text = advisory_content.get("text", "")
            location = advisory_content.get("location", "Marikina")
            
            # Use LLM (if enabled) or regex parsing (if implemented) to structure it
            # For now, we wrap it as a simple flood report
            
            manual_data = {
                "source": "manual_injection",
                "timestamp": datetime.now(),
                "type": advisory_content.get("type", "news"),
                "text": text,
                "location": location,
                "severity": advisory_content.get("severity", "unknown")
            }
            
            # Forward directly to Hazard Agent via MessageQueue
            if self.message_queue:
                message = create_inform_message(
                    sender=self.agent_id,
                    receiver=self.hazard_agent_id,
                    info_type="flood_report",
                    data=manual_data
                )
                self.message_queue.send_message(message)
                logger.info(f"Manual advisory forwarded to {self.hazard_agent_id}")
                return {"status": "success", "data": manual_data}
            else:
                return {"status": "error", "message": "No MessageQueue available"}

        except Exception as e:
            logger.error(f"{self.agent_id} manual injection error: {e}")
            return {"status": "error", "message": str(e)}

    def collect_flood_data(self) -> Dict[str, Any]:
        """
        Collect flood data from ALL sources (real APIs + fallback simulated).

        Priority order:
        1. Real APIs (PAGASA river levels + OpenWeatherMap) if available
        2. Simulated data as fallback if no real data collected

        Returns:
            Combined data that was collected
        """
        logger.info(f"{self.agent_id} collecting flood data from all sources...")

        combined_data = {}

        # ========== PRIORITY 1: REAL API DATA ==========
        if self.use_real_apis:
            # Fetch real river levels from PAGASA
            if self.river_scraper:
                try:
                    river_data = self.fetch_real_river_levels()
                    if river_data:
                        combined_data.update(river_data)
                        logger.info(
                            f"[OK] Collected REAL river data: {len(river_data)} stations"
                        )
                except Exception as e:
                    logger.error(f"Failed to fetch real river data: {e}")

            # Fetch real weather from OpenWeatherMap
            if self.weather_service:
                try:
                    weather_data = self.fetch_real_weather_data()
                    if weather_data:
                        location = weather_data.get("location", "Marikina")
                        combined_data[f"{location}_weather"] = weather_data
                        logger.info(
                            f"[OK] Collected REAL weather data for {location}"
                        )
                except Exception as e:
                    logger.error(f"Failed to fetch real weather data: {e}")

            # Fetch real dam levels from PAGASA
            if self.dam_scraper:
                try:
                    dam_data = self.fetch_real_dam_levels()
                    if dam_data:
                        # Add each dam as a separate data point
                        for dam_name, dam_info in dam_data.items():
                            combined_data[dam_name] = dam_info
                        logger.info(
                            f"[OK] Collected REAL dam data: {len(dam_data)} dams"
                        )
                except Exception as e:
                    logger.error(f"Failed to fetch real dam data: {e}")

            # Fetch and parse real text advisories (PAGASA)
            if self.advisory_scraper:
                try:
                    advisories = self.collect_and_parse_advisories()  # Auto-discovery
                    if advisories:
                        combined_data["advisories"] = advisories
                        logger.info(f"[OK] Collected {len(advisories)} REAL text advisories")
                except Exception as e:
                    logger.error(f"Failed to collect advisories: {e}")

        # ========== API FAILURE TRACKING ==========
        if self.use_real_apis:
            if combined_data:
                # Reset failure counter on any successful real data
                if self._consecutive_api_failures > 0:
                    logger.info(
                        f"[RECOVERY] Real API data restored after "
                        f"{self._consecutive_api_failures} consecutive failures"
                    )
                self._consecutive_api_failures = 0
                self._last_successful_real_fetch = datetime.now()
            else:
                self._consecutive_api_failures += 1
                if self._consecutive_api_failures >= self._api_failure_alert_threshold:
                    staleness = ""
                    if self._last_successful_real_fetch:
                        elapsed = (datetime.now() - self._last_successful_real_fetch).total_seconds()
                        staleness = f" Last success: {elapsed:.0f}s ago."
                    logger.critical(
                        f"[ALERT] All real APIs failed {self._consecutive_api_failures} "
                        f"consecutive times!{staleness} System is operating on STALE "
                        f"or SIMULATED data — risk scores may be inaccurate."
                    )

        # ========== FALLBACK: SIMULATED DATA ==========
        # Only use if no real data was collected
        if not combined_data and self.data_collector:
            logger.warning(
                f"[WARN] No real data available (failures={self._consecutive_api_failures}), "
                f"falling back to simulated data"
            )
            simulated = self.data_collector.collect_flood_data(
                location="Marikina",
                coordinates=(14.6507, 121.1029)
            )
            processed = self._process_collected_data(simulated)
            combined_data.update(processed)

        # ========== DATA COLLECTION COMPLETE ==========
        if combined_data:
            logger.info(
                f"[COLLECTED] {len(combined_data)} data points ready for fusion phase"
            )
        else:
            logger.warning("[WARN] No data collected from any source!")

        self.last_update = datetime.now()
        return combined_data

    async def collect_flood_data_async(self) -> Dict[str, Any]:
        """
        Async version of collect_flood_data — runs blocking fetches in parallel threads.

        Uses asyncio.to_thread to avoid blocking the event loop while external
        services (river scraper, weather API, dam scraper, advisory scraper) respond.

        Returns:
            Combined data from all sources
        """
        logger.info(f"{self.agent_id} collecting flood data ASYNC from all sources...")

        combined_data = {}

        if self.use_real_apis:
            tasks = []

            if self.river_scraper:
                tasks.append(("river", asyncio.to_thread(self.fetch_real_river_levels)))
            if self.weather_service:
                tasks.append(("weather", asyncio.to_thread(self.fetch_real_weather_data)))
            if self.dam_scraper:
                tasks.append(("dam", asyncio.to_thread(self.fetch_real_dam_levels)))
            if self.advisory_scraper:
                tasks.append(("advisory", asyncio.to_thread(self.collect_and_parse_advisories)))

            # Run all fetches concurrently
            results = await asyncio.gather(
                *(t[1] for t in tasks), return_exceptions=True
            )

            for (label, _), result in zip(tasks, results):
                if isinstance(result, Exception):
                    logger.error(f"Async {label} fetch failed: {result}")
                    continue

                if label == "river" and result:
                    combined_data.update(result)
                    logger.info(f"[OK] Collected REAL river data: {len(result)} stations")
                elif label == "weather" and result:
                    location = result.get("location", "Marikina")
                    combined_data[f"{location}_weather"] = result
                    logger.info(f"[OK] Collected REAL weather data for {location}")
                elif label == "dam" and result:
                    for dam_name, dam_info in result.items():
                        combined_data[dam_name] = dam_info
                    logger.info(f"[OK] Collected REAL dam data: {len(result)} dams")
                elif label == "advisory" and result:
                    combined_data["advisories"] = result
                    logger.info(f"[OK] Collected {len(result)} REAL text advisories")

        # Fallback: simulated data
        if not combined_data and self.data_collector:
            logger.warning("[WARN] No real data available, falling back to simulated data")
            simulated = self.data_collector.collect_flood_data(
                location="Marikina", coordinates=(14.6507, 121.1029)
            )
            processed = self._process_collected_data(simulated)
            combined_data.update(processed)

        if combined_data:
            logger.info(f"[COLLECTED ASYNC] {len(combined_data)} data points ready")
        else:
            logger.warning("[WARN] No data collected from any source!")

        self.last_update = datetime.now()
        return combined_data

    def _process_collected_data(self, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process collected data into format suitable for HazardAgent.

        Args:
            collected_data: Raw data from DataCollector

        Returns:
            Processed data dict with standardized format
        """
        processed = {}

        if "sources" not in collected_data:
            return processed

        sources = collected_data["sources"]

        # Process simulated data
        if "simulated" in sources:
            sim_data = sources["simulated"]
            location = collected_data.get("location", "Marikina")

            # Extract rainfall
            if "rainfall" in sim_data:
                rainfall = sim_data["rainfall"]
                if location not in processed:
                    processed[location] = {}
                processed[location].update({
                    "rainfall_1h": rainfall.get("rainfall_mm", 0.0),
                    "rainfall_24h": rainfall.get("rainfall_mm", 0.0) * 24,
                    "timestamp": rainfall.get("timestamp")
                })

            # Extract flood depth
            if "flood_depth" in sim_data:
                depth_info = sim_data["flood_depth"]
                if location not in processed:
                    processed[location] = {}
                processed[location].update({
                    "flood_depth": depth_info.get("flood_depth_cm", 0.0) / 100.0,
                    "risk_level": depth_info.get("risk_level", "low"),
                    "timestamp": depth_info.get("timestamp")
                })

        # Process PAGASA data
        if "pagasa" in sources:
            pagasa_data = sources["pagasa"]
            if pagasa_data.get("available"):
                location = pagasa_data.get("station", "PAGASA")
                if location not in processed:
                    processed[location] = {}
                processed[location].update({
                    "rainfall_mm": pagasa_data.get("rainfall_mm", 0.0),
                    "source": "PAGASA",
                    "timestamp": pagasa_data.get("timestamp")
                })

        # Process NOAH data
        if "noah" in sources:
            noah_data = sources["noah"]
            location = noah_data.get("location", "NOAH")
            if location not in processed:
                processed[location] = {}
            processed[location].update({
                "hazard_level": noah_data.get("hazard_level"),
                "source": "NOAH",
                "timestamp": noah_data.get("timestamp")
            })

        # Process MMDA data
        if "mmda" in sources:
            mmda_reports = sources["mmda"]
            if isinstance(mmda_reports, list):
                for report in mmda_reports:
                    location = report.get("area", "Unknown")
                    if location not in processed:
                        processed[location] = {}
                    processed[location].update({
                        "flood_level": report.get("flood_level"),
                        "status": report.get("status"),
                        "source": "MMDA",
                        "timestamp": report.get("timestamp")
                    })

        logger.debug(f"Processed data for {len(processed)} locations")
        return processed

    def fetch_real_river_levels(self) -> Dict[str, Any]:
        """
        Fetch REAL river level data from PAGASA using RiverScraperService.

        Returns:
            Dict containing river level measurements with risk assessment
        """
        logger.info(f"{self.agent_id} fetching REAL river levels from PAGASA API")

        if not self.river_scraper:
            logger.warning("RiverScraperService not available")
            return {}

        try:
            # Fetch from PAGASA API
            stations = self.river_scraper.get_river_levels()

            if not stations:
                logger.warning("No river data returned from PAGASA API")
                return {}

            # Process and format data
            river_data = {}

            # Key Marikina River stations to monitor (substring matching)
            marikina_keywords = [
                "sto nino", "sto. nino", "santo nino",
                "nangka",
                "tumana",
                "montalban",
                "rosario",
            ]

            for station in stations:
                station_name = station.get("station_name", "")

                # Focus on Marikina-relevant stations (case-insensitive substring match)
                if not any(kw in station_name.lower() for kw in marikina_keywords):
                    continue

                water_level = station.get("water_level_m")
                alert_level = self._parse_float(station.get("alert_level_m"))
                alarm_level = self._parse_float(station.get("alarm_level_m"))
                critical_level = self._parse_float(station.get("critical_level_m"))

                # Calculate risk status using config thresholds as fallback
                status = "normal"
                risk_score = 0.0

                if water_level is not None:
                    # Prefer station-reported thresholds, fall back to config
                    eff_critical = critical_level or self._config.water_level_critical_m
                    eff_alarm = alarm_level or self._config.water_level_alarm_m
                    eff_alert = alert_level or self._config.water_level_alert_m

                    if water_level >= eff_critical:
                        status = "critical"
                        risk_score = 1.0
                    elif water_level >= eff_alarm:
                        status = "alarm"
                        risk_score = 0.8
                    elif water_level >= eff_alert:
                        status = "alert"
                        risk_score = 0.5
                    else:
                        status = "normal"
                        risk_score = 0.2

                river_data[station_name] = {
                    "water_level_m": water_level,
                    "alert_level_m": alert_level,
                    "alarm_level_m": alarm_level,
                    "critical_level_m": critical_level,
                    "status": status,
                    "risk_score": risk_score,
                    "timestamp": datetime.now(),
                    "source": "PAGASA_API"
                }

            # Log each river level in the specific required format
            for station_name, station_data in river_data.items():
                water_level = station_data.get('water_level_m', 0.0)
                if water_level is not None:
                    logger.info(
                        f"River level is {water_level:.2f}m at {station_name}"
                    )

            logger.info(
                f"Fetched river data for {len(river_data)} Marikina stations. "
                f"Statuses: {[s['status'] for s in river_data.values()]}"
            )

            # Cache the data
            self.river_levels = river_data
            return river_data

        except Exception as e:
            logger.error(f"Error fetching real river levels: {e}")
            return {}

    def fetch_real_weather_data(
        self,
        lat: float = 14.6507,
        lon: float = 121.1029
    ) -> Dict[str, Any]:
        """
        Fetch REAL weather and rainfall data from OpenWeatherMap API.

        Args:
            lat: Latitude for weather query (default: Marikina City Hall)
            lon: Longitude for weather query (default: Marikina City Hall)

        Returns:
            Dict containing current weather and rainfall forecast
        """
        logger.info(f"{self.agent_id} fetching REAL weather from OpenWeatherMap")

        if not self.weather_service:
            logger.warning("OpenWeatherMapService not available (API key missing)")
            return {}

        try:
            # Fetch forecast from OpenWeatherMap
            forecast = self.weather_service.get_forecast(lat, lon)

            if not forecast:
                logger.warning("No weather data returned from OpenWeatherMap")
                return {}

            # Extract current conditions
            current = forecast.get("current", {})
            hourly = forecast.get("hourly", [])

            # Current rainfall
            current_rain = current.get("rain", {}).get("1h", 0.0)

            # Forecast next 6 hours of rainfall
            forecast_6h = []
            total_forecast_rain = 0.0

            for hour in hourly[:6]:
                rain_1h = hour.get("rain", {}).get("1h", 0.0)
                dt_val = hour.get("dt")
                forecast_6h.append({
                    "timestamp": datetime.fromtimestamp(dt_val) if dt_val else None,
                    "rain_mm": rain_1h,
                    "temp_c": hour.get("temp"),
                    "humidity_pct": hour.get("humidity"),
                    "pop": hour.get("pop")
                })
                total_forecast_rain += rain_1h

            # Calculate 24h accumulated rainfall
            hourly_24h = hourly[:24]
            rainfall_24h = sum(
                h.get("rain", {}).get("1h", 0.0) for h in hourly_24h
            )

            # Determine rainfall intensity
            intensity = self._calculate_rainfall_intensity(current_rain)

            weather_data = {
                "location": "Marikina",
                "coordinates": (lat, lon),
                "current_rainfall_mm": current_rain,
                "rainfall_24h_mm": rainfall_24h,
                "forecast_6h_mm": total_forecast_rain,
                "intensity": intensity,
                "temperature_c": current.get("temp"),
                "humidity_pct": current.get("humidity"),
                "pressure_hpa": current.get("pressure"),
                "forecast_hourly": forecast_6h,
                "timestamp": datetime.now(),
                "source": "OpenWeatherMap_API"
            }

            # Log in the specific required format
            logger.info(
                f"Rainfall in Marikina is {current_rain:.2f}mm"
            )

            logger.info(
                f"Weather data: {current_rain:.1f}mm/hr current, "
                f"{rainfall_24h:.1f}mm 24h forecast, "
                f"intensity={intensity}"
            )

            # Cache the data
            self.rainfall_data["Marikina"] = weather_data
            return weather_data

        except Exception as e:
            logger.error(f"Error fetching real weather data: {e}")
            return {}

    def fetch_real_dam_levels(self) -> Dict[str, Any]:
        """
        Fetch REAL dam water level data from PAGASA using DamWaterScraperService.

        Returns:
            Dict containing dam water levels with risk assessment
        """
        logger.info(f"{self.agent_id} fetching REAL dam levels from PAGASA")

        if not self.dam_scraper:
            logger.warning("DamWaterScraperService not available")
            return {}

        try:
            # Fetch from PAGASA flood page
            dams = self.dam_scraper.get_dam_levels()

            if not dams:
                logger.warning("No dam data returned from PAGASA")
                return {}

            # Process and format data
            dam_data = {}

            for dam in dams:
                dam_name = dam.get("Dam Name", "Unknown")

                # Extract key metrics
                latest_rwl = dam.get("Latest RWL (m)")
                latest_dev_nhwl = dam.get("Latest Dev from NHWL (m)")
                nhwl = dam.get("NHWL (m)")
                rule_curve = dam.get("Latest Rule Curve (m)")
                dev_rule_curve = dam.get("Latest Dev from Rule Curve (m)")

                # Calculate risk status based on deviation from NHWL (config thresholds)
                status = "normal"
                risk_score = 0.0

                if latest_dev_nhwl is not None:
                    if latest_dev_nhwl >= self._config.dam_critical_m:
                        status = "critical"
                        risk_score = 1.0
                    elif latest_dev_nhwl >= self._config.dam_alarm_m:
                        status = "alarm"
                        risk_score = 0.8
                    elif latest_dev_nhwl >= self._config.dam_alert_m:
                        status = "alert"
                        risk_score = 0.5
                    elif latest_dev_nhwl >= 0.0:
                        status = "watch"
                        risk_score = 0.3
                    else:
                        status = "normal"
                        risk_score = 0.1

                dam_data[dam_name] = {
                    "dam_name": dam_name,
                    "reservoir_water_level_m": latest_rwl,
                    "normal_high_water_level_m": nhwl,
                    "deviation_from_nhwl_m": latest_dev_nhwl,
                    "rule_curve_elevation_m": rule_curve,
                    "deviation_from_rule_curve_m": dev_rule_curve,
                    "status": status,
                    "risk_score": risk_score,
                    "latest_time": dam.get("Latest Time"),
                    "latest_date": dam.get("Latest Date"),
                    "water_level_change_hr": dam.get("Water Level Deviation (Hr)"),
                    "water_level_change_amt": dam.get("Water Level Deviation (Amt)"),
                    "timestamp": datetime.now(),
                    "source": "PAGASA_Dam_Monitoring"
                }

            # Log each dam level in the specific required format
            for dam_name, dam_info in dam_data.items():
                rwl = dam_info.get('reservoir_water_level_m', 0.0)
                if rwl is not None:
                    logger.info(
                        f"Dam Level is {rwl:.2f}m at {dam_name}"
                    )

            logger.info(
                f"Fetched dam data for {len(dam_data)} dams. "
                f"Statuses: {[d['status'] for d in dam_data.values()]}"
            )

            # Cache the data
            self.dam_levels = dam_data
            return dam_data

        except Exception as e:
            logger.error(f"Error fetching real dam levels: {e}")
            return {}

    def _parse_float(self, value) -> Optional[float]:
        """
        Helper to safely parse float values.

        Args:
            value: Value to parse

        Returns:
            Float value or None if parsing fails
        """
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _calculate_rainfall_intensity(self, rainfall_mm: float) -> str:
        """
        Calculate rainfall intensity category based on mm/hr.

        Uses thresholds from FloodConfig (agents.yaml).

        Args:
            rainfall_mm: Rainfall in mm/hr

        Returns:
            Intensity category string
        """
        if rainfall_mm <= 0:
            return "none"
        elif rainfall_mm <= self._config.rainfall_light_mm:
            return "light"
        elif rainfall_mm <= self._config.rainfall_moderate_mm:
            return "moderate"
        elif rainfall_mm <= self._config.rainfall_heavy_mm:
            return "heavy"
        elif rainfall_mm <= self._config.rainfall_extreme_mm:
            return "intense"
        else:
            return "torrential"

    def send_flood_data_via_message(self, data: Dict[str, Any]) -> None:
        """
        Send collected flood data to HazardAgent via MessageQueue using ACL protocol.

        Uses INFORM performative to provide flood information to the HazardAgent.
        The message contains batched data from all sources for optimal performance.

        Args:
            data: Combined flood data from all sources
                Format: {
                    "location_name": {
                        "flood_depth": float,
                        "rainfall_1h": float,
                        "rainfall_24h": float,
                        "timestamp": datetime,
                        "source": str
                    },
                    ...
                }
        """
        if not self.message_queue:
            logger.warning(
                f"{self.agent_id} has no MessageQueue - data not sent "
                "(falling back to direct communication)"
            )
            return

        logger.info(
            f"{self.agent_id} sending flood data for {len(data)} locations "
            f"to {self.hazard_agent_id} via MessageQueue"
        )

        try:
            # Create ACL INFORM message with flood data
            message = create_inform_message(
                sender=self.agent_id,
                receiver=self.hazard_agent_id,
                info_type="flood_data_batch",
                data=data
            )

            # Send via message queue
            self.message_queue.send_message(message)

            logger.info(
                f"{self.agent_id} successfully sent INFORM message to "
                f"{self.hazard_agent_id} ({len(data)} locations)"
            )

        except Exception as e:
            logger.error(
                f"{self.agent_id} failed to send message to {self.hazard_agent_id}: {e}"
            )

    def _should_update(self) -> bool:
        """
        Check if it's time to fetch new data.

        Returns:
            True if update interval has elapsed, False otherwise
        """
        if self.last_update is None:
            return True

        # Both self.last_update and datetime.now() are naive (no timezone); keep consistent
        elapsed = (datetime.now() - self.last_update).total_seconds()
        return elapsed >= self.data_update_interval

    def _scrape_webpage(self, url: str) -> Optional[BeautifulSoup]:
        """
        Helper method to scrape a webpage.

        Args:
            url: URL to scrape

        Returns:
            BeautifulSoup object if successful, None otherwise
        """
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.content, "html.parser")
        except Exception as e:
            logger.error(f"Failed to scrape {url}: {e}")
            return None

    # ========== LLM-ENHANCED METHODS (v2) ==========

    def parse_text_advisory(self, advisory_text: str) -> Dict[str, Any]:
        """
        Parse PAGASA text advisory using Qwen 3 LLM.

        Uses LLM to extract structured information from unstructured
        weather advisories, including warning levels, affected areas,
        and expected rainfall amounts.

        Args:
            advisory_text: Raw PAGASA advisory text

        Returns:
            Dict with parsed advisory information:
            {
                "advisory_type": str,       # "rainfall", "flood", "dam", etc.
                "warning_level": str,       # "blue", "yellow", "orange", "red"
                "affected_areas": List[str],
                "expected_rainfall_mm": float,
                "river_status": Dict[str, str],
                "dam_status": Dict[str, str],
                "key_points": List[str],
                "parsed_successfully": bool
            }

        Example:
            >>> advisory = "PAGASA Heavy Rainfall Warning for Metro Manila..."
            >>> result = flood_agent.parse_text_advisory(advisory)
            >>> print(result['warning_level'])
            'orange'
        """
        if not advisory_text or not advisory_text.strip():
            logger.warning("Empty advisory text provided")
            return {"parsed_successfully": False, "error": "Empty advisory text"}

        # Try LLM parsing first
        if self.use_llm and self.llm_service:
            try:
                llm_result = self.llm_service.parse_pagasa_advisory(advisory_text)
                if llm_result:
                    llm_result['parsed_successfully'] = True
                    llm_result['parsing_method'] = 'configured_llm'

                    logger.info(
                        f"[LLM] Advisory parsed: type={llm_result.get('advisory_type')}, "
                        f"level={llm_result.get('warning_level')}, "
                        f"areas={len(llm_result.get('affected_areas', []))}"
                    )
                    return llm_result

            except Exception as e:
                logger.warning(f"LLM advisory parsing failed: {e}")

        # Fallback to rule-based parsing
        return self._parse_advisory_rule_based(advisory_text)

    def _parse_advisory_rule_based(self, advisory_text: str) -> Dict[str, Any]:
        """
        Fallback rule-based parser for PAGASA advisories.

        Uses keyword matching and pattern recognition when LLM is unavailable.

        Args:
            advisory_text: Raw advisory text

        Returns:
            Dict with basic parsed information
        """
        result = {
            "parsed_successfully": True,
            "parsing_method": "rule_based",
            "advisory_type": "general",
            "warning_level": "none",
            "affected_areas": [],
            "key_points": []
        }

        text_lower = advisory_text.lower()

        # Detect advisory type
        if "heavy rainfall" in text_lower or "rainfall warning" in text_lower:
            result["advisory_type"] = "rainfall"
        elif "flood" in text_lower:
            result["advisory_type"] = "flood"
        elif "dam" in text_lower or "spillway" in text_lower:
            result["advisory_type"] = "dam"
        elif "typhoon" in text_lower or "bagyo" in text_lower:
            result["advisory_type"] = "typhoon"

        # Detect warning level (PAGASA color codes)
        if "red warning" in text_lower or "red rainfall" in text_lower:
            result["warning_level"] = "red"
        elif "orange warning" in text_lower or "orange rainfall" in text_lower:
            result["warning_level"] = "orange"
        elif "yellow warning" in text_lower or "yellow rainfall" in text_lower:
            result["warning_level"] = "yellow"
        elif "blue warning" in text_lower or "blue rainfall" in text_lower:
            result["warning_level"] = "blue"

        # Extract Marikina-related content
        marikina_keywords = ["marikina", "marikina city", "marikina river"]
        for keyword in marikina_keywords:
            if keyword in text_lower:
                result["affected_areas"].append("Marikina")
                break

        # Extract key sentences (simple extraction)
        sentences = advisory_text.split('.')
        for sentence in sentences[:5]:  # First 5 sentences
            sentence = sentence.strip()
            if len(sentence) > 20:  # Skip very short fragments
                result["key_points"].append(sentence)

        logger.info(
            f"[Rule-based] Advisory parsed: type={result['advisory_type']}, "
            f"level={result['warning_level']}"
        )

        return result

    def collect_and_parse_advisories(self, advisory_urls: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Collect and parse PAGASA advisories from multiple sources using AdvisoryScraperService.

        Args:
            advisory_urls: List of URLs to fetch advisories from.
                          If None, dynamically discovers from PAGASA website.

        Returns:
            List of parsed advisory dictionaries
        """
        if not self.advisory_scraper:
            logger.warning("AdvisoryScraperService not initialized")
            return []

        # Default PAGASA advisory URLs (examples)
        if advisory_urls is None:
            # First, try dynamic discovery from PAGASA
            advisory_urls = self.advisory_scraper.discover_pagasa_advisories()

        parsed_advisories = []

        # 1. Process PAGASA URLs
        for url in advisory_urls:
            try:
                # Fetch the advisory page
                soup = self._scrape_webpage(url)
                if not soup:
                    continue

                # Extract text content (adjust selector based on PAGASA page structure)
                content_div = soup.find('div', class_='advisory-content')
                if content_div:
                    advisory_text = content_div.get_text(strip=True)
                else:
                    advisory_text = soup.get_text(strip=True)[:5000]  # Limit length

                # Dedup: skip if already processed
                if self._is_duplicate_advisory(advisory_text):
                    continue

                # Parse the advisory
                parsed = self.parse_text_advisory(advisory_text)
                parsed['source_url'] = url
                parsed['fetched_at'] = datetime.now().isoformat()
                parsed['source_type'] = 'pagasa_website'

                parsed_advisories.append(parsed)

            except Exception as e:
                logger.error(f"Failed to fetch/parse advisory from {url}: {e}")
                continue

        # 2. Process Google News RSS (Fallback/Supplementary)
        try:
            rss_queries = ["Marikina River Flood", "Marikina Red Warning"]
            for query in rss_queries:
                news_items = self.advisory_scraper.scrape_google_news_rss(query)

                for item in news_items:
                    news_text = item.get("text", "")
                    pub_date = item.get("pub_date", "")
                    link = item.get("link", "")

                    if len(news_text) < 50:
                        continue

                    # Dedup: skip if already processed
                    if self._is_duplicate_advisory(news_text):
                        continue

                    parsed = self.parse_text_advisory(news_text)
                    if parsed.get('affected_areas') or parsed.get('warning_level'):
                        parsed['source_url'] = link or f"google_news_rss:{query}"
                        parsed['fetched_at'] = datetime.now().isoformat()
                        parsed['published_at'] = pub_date
                        parsed['source_type'] = 'google_news_rss'
                        parsed_advisories.append(parsed)

        except Exception as e:
            logger.error(f"Google News RSS processing failed: {e}")

        logger.info(f"Collected and parsed {len(parsed_advisories)} advisories from all sources")
        return parsed_advisories

    def _is_duplicate_advisory(self, text: str) -> bool:
        """
        Check if an advisory text has already been processed (hash-based dedup).

        Records the hash if new, returns True if already seen.
        """
        text_hash = hashlib.md5(text.strip().encode()).hexdigest()
        if text_hash in self._processed_advisory_hashes:
            logger.debug(f"Skipping duplicate advisory (hash={text_hash[:8]})")
            return True
        if len(self._processed_advisory_hashes) > 5000:
            self._processed_advisory_hashes.clear()
        self._processed_advisory_hashes.add(text_hash)
        return False

    def is_llm_enabled(self) -> bool:
        """Check if LLM processing is enabled and available."""
        return self.use_llm and self.llm_service is not None

    def get_agent_stats(self) -> Dict[str, Any]:
        """
        Get agent statistics and status.

        Returns:
            Dict with agent status information
        """
        return {
            "agent_id": self.agent_id,
            "llm_enabled": self.use_llm,
            "llm_available": self.llm_service.is_available() if self.llm_service else False,
            "real_apis_enabled": self.use_real_apis,
            "river_scraper_available": self.river_scraper is not None,
            "weather_service_available": self.weather_service is not None,
            "dam_scraper_available": self.dam_scraper is not None,
            "advisory_scraper_available": self.advisory_scraper is not None,
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "update_interval_seconds": self.data_update_interval,
            "cached_river_stations": len(self.river_levels),
            "cached_dam_levels": len(self.dam_levels),
            "processed_advisories": len(self._processed_advisory_hashes),
        }
