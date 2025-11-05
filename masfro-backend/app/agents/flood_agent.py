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
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

try:
    from services.data_sources import DataCollector
except ImportError:
    from app.services.data_sources import DataCollector

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
        environment,
        hazard_agent=None,
        use_simulated: bool = True
    ):
        """
        Initialize the FloodAgent.

        Args:
            agent_id: Unique identifier for this agent
            environment: DynamicGraphEnvironment instance
            hazard_agent: Optional reference to HazardAgent for direct communication
            use_simulated: Use simulated data for testing (default: True)
        """
        super().__init__(agent_id, environment)
        self.hazard_agent = hazard_agent

        # Initialize data collector (Phase 3 integration)
        self.data_collector = DataCollector(
            use_simulated=use_simulated,
            enable_pagasa=False,  # Enable when API access is granted
            enable_noah=False,    # Enable when real-time data available
            enable_mmda=False     # Enable when API access available
        )

        # API/Data source URLs (placeholders - update with actual endpoints)
        self.pagasa_api_url = "https://www.pagasa.dost.gov.ph/api/rainfall"
        self.river_sensor_url = "https://api.noah.dost.gov.ph/river-levels"
        self.flood_monitoring_url = "https://mmda.gov.ph/flood-monitoring"

        # Configuration
        self.data_update_interval = 300  # 5 minutes
        self.last_update: Optional[datetime] = None

        # Data caches
        self.rainfall_data: Dict[str, Any] = {}
        self.river_levels: Dict[str, Any] = {}
        self.flood_depth_data: Dict[str, Any] = {}

        logger.info(
            f"{self.agent_id} initialized with update interval "
            f"{self.data_update_interval}s, simulated={use_simulated}"
        )

    def set_hazard_agent(self, hazard_agent) -> None:
        """
        Set reference to HazardAgent for data forwarding.

        Args:
            hazard_agent: HazardAgent instance
        """
        self.hazard_agent = hazard_agent
        logger.info(f"{self.agent_id} linked to {hazard_agent.agent_id}")

    def step(self):
        """
        Perform one step of the agent's operation.

        Fetches latest official flood data from all configured sources,
        validates the data, and forwards it to the HazardAgent for
        risk assessment.
        """
        logger.debug(f"{self.agent_id} performing step at {datetime.now()}")

        # Check if update is needed
        if self._should_update():
            self.collect_and_forward_data()

    def collect_and_forward_data(self) -> Dict[str, Any]:
        """
        Manually trigger data collection and forwarding.

        This method can be called to force data collection regardless
        of the update interval. Useful for testing and on-demand updates.

        Returns:
            Combined data that was collected
        """
        logger.info(f"{self.agent_id} collecting flood data...")

        # Use DataCollector to gather data from all enabled sources
        # Default location is Marikina City Hall
        collected_data = self.data_collector.collect_flood_data(
            location="Marikina",
            coordinates=(14.6507, 121.1029)
        )

        # Extract and format data for internal use
        combined_data = self._process_collected_data(collected_data)

        # Forward to Hazard Agent if available
        if combined_data:
            self.send_to_hazard_agent(combined_data)

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
                    
                    # Determine passability based on depth
                    passability = "passable" if flood_depth_m < 0.5 else "impassable"
                    
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

    def send_to_hazard_agent(self, data: Dict[str, Any]) -> None:
        """
        Forward collected data to HazardAgent for processing.

        Args:
            data: Combined flood data from all sources
        """
        logger.info(
            f"{self.agent_id} sending {len(data)} data points to HazardAgent"
        )

        if not self.hazard_agent:
            logger.warning(f"{self.agent_id} has no HazardAgent reference, data not forwarded")
            return

        # Send data to HazardAgent
        try:
            # Convert combined data to format HazardAgent expects
            for location, location_data in data.items():
                flood_data = {
                    "location": location,
                    "flood_depth": location_data.get("flood_depth", 0.0),
                    "rainfall_1h": location_data.get("rainfall_1h", 0.0),
                    "rainfall_24h": location_data.get("rainfall_24h", 0.0),
                    "timestamp": location_data.get("timestamp")
                }
                self.hazard_agent.process_flood_data(flood_data)

            logger.info(f"{self.agent_id} successfully forwarded data to {self.hazard_agent.agent_id}")

        except Exception as e:
            logger.error(f"{self.agent_id} failed to forward data to HazardAgent: {e}")

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
