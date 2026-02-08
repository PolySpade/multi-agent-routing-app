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

Author: MAS-FRO Development Team
Date: November 2025
"""

from .base_agent import BaseAgent
from typing import Dict, Any, Optional, List, Tuple, TYPE_CHECKING
import logging
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import sys
from pathlib import Path

if TYPE_CHECKING:
    from ..environment.graph_manager import DynamicGraphEnvironment
    from ..communication.message_queue import MessageQueue

# ACL Protocol imports
try:
    from communication.acl_protocol import ACLMessage, Performative, create_inform_message
except ImportError:
    from app.communication.acl_protocol import ACLMessage, Performative, create_inform_message

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

try:
    from services.data_sources import DataCollector
    from services.river_scraper_service import RiverScraperService
    from services.weather_service import OpenWeatherMapService
    from services.dam_water_scraper_service import DamWaterScraperService
except ImportError:
    from app.services.data_sources import DataCollector
    from app.services.river_scraper_service import RiverScraperService
    from app.services.weather_service import OpenWeatherMapService
    from app.services.dam_water_scraper_service import DamWaterScraperService

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
        hazard_agent_id: str = "hazard_agent_001"
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
        """
        super().__init__(agent_id, environment)
        self.message_queue = message_queue
        self.hazard_agent_id = hazard_agent_id
        self.use_real_apis = use_real_apis

        # Register with message queue
        if self.message_queue:
            try:
                self.message_queue.register_agent(self.agent_id)
                logger.info(f"{self.agent_id} registered with MessageQueue")
            except ValueError as e:
                logger.warning(f"{self.agent_id} already registered: {e}")

        # Initialize real API services
        if use_real_apis:
            # PAGASA River Scraper Service
            try:
                self.river_scraper = RiverScraperService()
                logger.info(f"{self.agent_id} initialized RiverScraperService")
            except Exception as e:
                logger.error(f"Failed to initialize RiverScraperService: {e}")
                self.river_scraper = None

            # OpenWeatherMap Service
            try:
                self.weather_service = OpenWeatherMapService()
                logger.info(f"{self.agent_id} initialized OpenWeatherMapService")
            except ValueError as e:
                logger.warning(f"OpenWeatherMap not available: {e}")
                self.weather_service = None
            except Exception as e:
                logger.error(f"Failed to initialize OpenWeatherMapService: {e}")
                self.weather_service = None

            # Dam Water Scraper Service
            try:
                self.dam_scraper = DamWaterScraperService()
                logger.info(f"{self.agent_id} initialized DamWaterScraperService")
            except Exception as e:
                logger.error(f"Failed to initialize DamWaterScraperService: {e}")
                self.dam_scraper = None
        else:
            self.river_scraper = None
            self.weather_service = None
            self.dam_scraper = None
            logger.info(f"{self.agent_id} real APIs disabled")

        # Initialize data collector (fallback for simulated data)
        self.data_collector = DataCollector(
            use_simulated=use_simulated,
            enable_pagasa=False,
            enable_noah=False,
            enable_mmda=False
        )

        # Configuration
        self.data_update_interval = 300  # 5 minutes
        self.last_update: Optional[datetime] = None

        # Data caches
        self.rainfall_data: Dict[str, Any] = {}
        self.river_levels: Dict[str, Any] = {}
        self.flood_depth_data: Dict[str, Any] = {}
        self.dam_levels: Dict[str, Any] = {}

        logger.info(
            f"{self.agent_id} initialized with update interval "
            f"{self.data_update_interval}s, real_apis={use_real_apis}, "
            f"simulated={use_simulated}"
        )

    def step(self):
        """
        Perform one step of the agent's operation.

        Fetches latest official flood data from all configured sources,
        validates the data, and sends it to the HazardAgent via MessageQueue
        using ACL protocol.
        """
        logger.debug(f"{self.agent_id} performing step at {datetime.now()}")

        # Check if update is needed
        if self._should_update():
            collected_data = self.collect_flood_data()
            if collected_data:
                self.send_flood_data_via_message(collected_data)

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

        # ========== FALLBACK: SIMULATED DATA ==========
        # Only use if no real data was collected
        if not combined_data and self.data_collector:
            logger.warning(
                "⚠️ No real data available, falling back to simulated data"
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

    def fetch_rainfall_data(self) -> Dict[str, Any]:
        """
        Fetch rainfall data from PAGASA rain gauges.

        Uses DataCollector to query PAGASA or simulated sources for current
        rainfall measurements in the Marikina area.

        Returns:
            Dict containing rainfall measurements by location
                Format:
                {
                    "location_name": {
                        "rainfall_1h": float,  # mm in last hour
                        "rainfall_24h": float,  # mm in last 24 hours
                        "intensity": str,  # "light", "moderate", "heavy"
                        "timestamp": datetime
                    },
                    ...
                }
        """
        logger.info(f"{self.agent_id} fetching rainfall data from PAGASA")

        try:
            # Use DataCollector to get rainfall data
            data = self.data_collector.collect_flood_data(
                location="Marikina",
                coordinates=(14.6507, 121.1029)
            )

            # Extract rainfall data from collected sources
            rainfall_data = {}
            if "sources" in data:
                if "simulated" in data["sources"]:
                    sim_data = data["sources"]["simulated"]
                    if "rainfall" in sim_data:
                        rainfall_info = sim_data["rainfall"]
                        rainfall_data["Marikina"] = {
                            "rainfall_1h": rainfall_info.get("rainfall_mm", 0.0),
                            "rainfall_24h": rainfall_info.get("rainfall_mm", 0.0) * 24,
                            "intensity": rainfall_info.get("intensity", "unknown"),
                            "timestamp": datetime.fromisoformat(rainfall_info.get("timestamp"))
                        }

                if "pagasa" in data["sources"]:
                    pagasa_data = data["sources"]["pagasa"]
                    if pagasa_data.get("available"):
                        rainfall_data["PAGASA"] = {
                            "rainfall_1h": pagasa_data.get("rainfall_mm", 0.0),
                            "timestamp": datetime.fromisoformat(pagasa_data.get("timestamp"))
                        }

            logger.info(f"Fetched rainfall data for {len(rainfall_data)} locations")
            self.rainfall_data = rainfall_data
            return rainfall_data

        except Exception as e:
            logger.error(f"Failed to fetch rainfall data: {e}")
            return {}

    def fetch_river_levels(self) -> Dict[str, Any]:
        """
        Fetch river water level data from monitoring sensors.

        Uses DataCollector to query DOST-NOAH or other official sources for
        current river water levels in the Marikina River and tributaries.

        Returns:
            Dict containing river level measurements
                Format:
                {
                    "river_name": {
                        "water_level": float,  # meters above normal
                        "flow_rate": float,  # cubic meters per second
                        "status": str,  # "normal", "alert", "critical"
                        "timestamp": datetime
                    },
                    ...
                }
        """
        logger.info(f"{self.agent_id} fetching river level data")

        try:
            # Use DataCollector to get hazard data (includes river levels)
            data = self.data_collector.collect_flood_data(
                location="Marikina River",
                coordinates=(14.6507, 121.1029)
            )

            # Extract river level data from NOAH source
            river_data = {}
            if "sources" in data and "noah" in data["sources"]:
                noah_data = data["sources"]["noah"]
                if noah_data.get("hazard_level"):
                    river_data["Marikina River"] = {
                        "water_level": 0.0,  # Placeholder
                        "flow_rate": 0.0,
                        "status": noah_data.get("hazard_level", "unknown"),
                        "timestamp": datetime.fromisoformat(noah_data.get("timestamp"))
                    }

            # For simulated mode, create placeholder data
            if not river_data and self.data_collector.use_simulated:
                river_data["Marikina River"] = {
                    "water_level": 1.2,
                    "flow_rate": 45.3,
                    "status": "alert",
                    "timestamp": datetime.now()
                }

            logger.info(f"Fetched river level data for {len(river_data)} rivers")
            self.river_levels = river_data
            return river_data

        except Exception as e:
            logger.error(f"Failed to fetch river level data: {e}")
            return {}

    def fetch_flood_depths(self) -> Dict[str, Any]:
        """
        Fetch current flood depth measurements from monitoring stations.

        Uses DataCollector to query flood monitoring systems (MMDA, LGU sensors)
        for actual measured flood depths at key locations.

        Returns:
            Dict containing flood depth measurements
                Format:
                {
                    "location_name": {
                        "flood_depth": float,  # meters
                        "affected_area": str,
                        "passability": str,  # "passable", "impassable"
                        "timestamp": datetime
                    },
                    ...
                }
        """
        logger.info(f"{self.agent_id} fetching flood depth measurements")

        try:
            # Use DataCollector to get flood depth data
            data = self.data_collector.collect_flood_data(
                location="Marikina",
                coordinates=(14.6507, 121.1029)
            )

            # Extract flood depth data from collected sources
            flood_data = {}
            
            # Process simulated data
            if "sources" in data and "simulated" in data["sources"]:
                sim_data = data["sources"]["simulated"]
                if "flood_depth" in sim_data:
                    depth_info = sim_data["flood_depth"]
                    flood_depth_m = depth_info.get("flood_depth_cm", 0.0) / 100.0
                    
                    # Determine passability based on depth (FEMA standards)
                    # FEMA recommends 0.3m (12 inches) max for safe vehicle passage
                    # 0.3-0.45m is dangerous, >0.45m is impassable
                    if flood_depth_m < 0.15:
                        passability = "safe"
                    elif flood_depth_m < 0.3:
                        passability = "passable"  # Caution required
                    elif flood_depth_m < 0.45:
                        passability = "dangerous"  # High risk
                    else:
                        passability = "impassable"
                    
                    flood_data["Marikina"] = {
                        "flood_depth": flood_depth_m,
                        "affected_area": "City center",
                        "passability": passability,
                        "timestamp": datetime.fromisoformat(depth_info.get("timestamp"))
                    }

            # Process MMDA data if available
            if "sources" in data and "mmda" in data["sources"]:
                mmda_reports = data["sources"]["mmda"]
                if isinstance(mmda_reports, list):
                    for report in mmda_reports:
                        location = report.get("area", "Unknown")
                        flood_data[location] = {
                            "flood_depth": report.get("flood_level", 0.0),
                            "affected_area": location,
                            "passability": report.get("status", "unknown"),
                            "timestamp": datetime.fromisoformat(report.get("timestamp"))
                        }

            logger.info(f"Fetched flood depth data for {len(flood_data)} locations")
            self.flood_depth_data = flood_data
            return flood_data

        except Exception as e:
            logger.error(f"Failed to fetch flood depth data: {e}")
            return {}

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

            # Key Marikina River stations to monitor
            marikina_stations = [
                "Sto Nino",
                "Nangka",
                "Tumana Bridge",
                "Montalban",
                "Rosario Bridge"
            ]

            for station in stations:
                station_name = station.get("station_name")

                # Focus on Marikina-relevant stations
                if station_name not in marikina_stations:
                    continue

                water_level = station.get("water_level_m")
                alert_level = self._parse_float(station.get("alert_level_m"))
                alarm_level = self._parse_float(station.get("alarm_level_m"))
                critical_level = self._parse_float(station.get("critical_level_m"))

                # Calculate risk status
                status = "normal"
                risk_score = 0.0

                if water_level is not None:
                    if critical_level and water_level >= critical_level:
                        status = "critical"
                        risk_score = 1.0
                    elif alarm_level and water_level >= alarm_level:
                        status = "alarm"
                        risk_score = 0.8
                    elif alert_level and water_level >= alert_level:
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
                forecast_6h.append({
                    "timestamp": datetime.fromtimestamp(hour.get("dt")),
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

                # Calculate risk status based on deviation from NHWL
                status = "normal"
                risk_score = 0.0

                if latest_dev_nhwl is not None:
                    if latest_dev_nhwl >= 2.0:
                        # >2m above NHWL = critical
                        status = "critical"
                        risk_score = 1.0
                    elif latest_dev_nhwl >= 1.0:
                        # 1-2m above NHWL = alarm
                        status = "alarm"
                        risk_score = 0.8
                    elif latest_dev_nhwl >= 0.5:
                        # 0.5-1m above NHWL = alert
                        status = "alert"
                        risk_score = 0.5
                    elif latest_dev_nhwl >= 0.0:
                        # At or slightly above NHWL = watch
                        status = "watch"
                        risk_score = 0.3
                    else:
                        # Below NHWL = normal
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

        Based on PAGASA rainfall intensity classification:
        - Light: 0.1 - 2.5 mm/hr
        - Moderate: 2.6 - 7.5 mm/hr
        - Heavy: 7.6 - 15.0 mm/hr
        - Intense: 15.1 - 30.0 mm/hr
        - Torrential: > 30.0 mm/hr

        Args:
            rainfall_mm: Rainfall in mm/hr

        Returns:
            Intensity category string
        """
        if rainfall_mm <= 0:
            return "none"
        elif rainfall_mm <= 2.5:
            return "light"
        elif rainfall_mm <= 7.5:
            return "moderate"
        elif rainfall_mm <= 15.0:
            return "heavy"
        elif rainfall_mm <= 30.0:
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

    def _combine_data(
        self,
        rainfall: Dict[str, Any],
        river_levels: Dict[str, Any],
        flood_depths: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Combine data from multiple sources into unified format.

        Args:
            rainfall: Rainfall measurements
            river_levels: River level measurements
            flood_depths: Flood depth measurements

        Returns:
            Combined data dict with standardized format for HazardAgent
        """
        combined = {}

        # Combine rainfall data
        for location, data in rainfall.items():
            if location not in combined:
                combined[location] = {}
            combined[location].update({
                "rainfall_1h": data.get("rainfall_1h"),
                "rainfall_24h": data.get("rainfall_24h"),
                "timestamp": data.get("timestamp")
            })

        # Add flood depth data
        for location, data in flood_depths.items():
            if location not in combined:
                combined[location] = {}
            combined[location].update({
                "flood_depth": data.get("flood_depth"),
                "passability": data.get("passability"),
                "timestamp": data.get("timestamp")
            })

        # Add river level context
        for river, data in river_levels.items():
            # River data affects nearby locations
            combined[f"{river}_monitoring"] = {
                "water_level": data.get("water_level"),
                "status": data.get("status"),
                "timestamp": data.get("timestamp")
            }

        return combined

    def _should_update(self) -> bool:
        """
        Check if it's time to fetch new data.

        Returns:
            True if update interval has elapsed, False otherwise
        """
        if self.last_update is None:
            return True

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
