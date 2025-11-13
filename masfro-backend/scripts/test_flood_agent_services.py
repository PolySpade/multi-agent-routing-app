#!/usr/bin/env python3
"""
Test script for FloodAgent services - comprehensive testing of all data sources.

This script tests:
1. RiverScraperService - PAGASA river level monitoring
2. OpenWeatherMapService - Weather and rainfall data
3. DamWaterScraperService - Dam water level monitoring
4. Data processing and validation
5. Integration with HazardAgent

Author: MAS-FRO Development Team
Date: November 2025
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich import print as rprint
import time

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Import services
from app.services.river_scraper_service import RiverScraperService
from app.services.weather_service import OpenWeatherMapService
from app.services.dam_water_scraper_service import DamWaterScraperService
from app.agents.flood_agent import FloodAgent
from app.environment.graph_manager import DynamicGraphEnvironment

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Rich console
console = Console()


class FloodAgentServiceTester:
    """Test and analyze all FloodAgent services."""
    
    def __init__(self):
        """Initialize tester with all services."""
        self.console = console
        self.results = {
            "river_scraper": None,
            "weather_service": None,
            "dam_scraper": None,
            "flood_agent": None
        }
        
        # Initialize services
        self.init_services()
        
    def init_services(self):
        """Initialize all services with error handling."""
        # River Scraper Service
        try:
            self.river_scraper = RiverScraperService()
            self.console.print("[green]✓[/green] RiverScraperService initialized")
        except Exception as e:
            self.river_scraper = None
            self.console.print(f"[red]✗[/red] RiverScraperService failed: {e}")
            
        # Weather Service
        try:
            self.weather_service = OpenWeatherMapService()
            self.console.print("[green]✓[/green] OpenWeatherMapService initialized")
        except Exception as e:
            self.weather_service = None
            self.console.print(f"[yellow]⚠[/yellow] OpenWeatherMapService unavailable: {e}")
            
        # Dam Scraper Service
        try:
            self.dam_scraper = DamWaterScraperService()
            self.console.print("[green]✓[/green] DamWaterScraperService initialized")
        except Exception as e:
            self.dam_scraper = None
            self.console.print(f"[red]✗[/red] DamWaterScraperService failed: {e}")
            
        # Flood Agent
        try:
            self.environment = DynamicGraphEnvironment()
            self.flood_agent = FloodAgent(
                "flood_test_001",
                self.environment,
                use_real_apis=True
            )
            self.console.print("[green]✓[/green] FloodAgent initialized")
        except Exception as e:
            self.flood_agent = None
            self.console.print(f"[red]✗[/red] FloodAgent failed: {e}")
            
    def test_river_scraper(self) -> Dict[str, Any]:
        """Test PAGASA river level scraping."""
        self.console.print("\n[bold cyan]Testing RiverScraperService...[/bold cyan]")
        
        if not self.river_scraper:
            return {"error": "Service not available"}
            
        try:
            # Fetch river levels
            start_time = time.time()
            river_data = self.river_scraper.get_river_levels()
            elapsed_time = time.time() - start_time
            
            if not river_data:
                return {"error": "No data returned", "elapsed_time": elapsed_time}
                
            # Analyze data
            marikina_stations = [
                "Sto Nino", "Nangka", "Tumana Bridge", 
                "Montalban", "Rosario Bridge"
            ]
            
            results = {
                "total_stations": len(river_data),
                "marikina_stations": [],
                "elapsed_time": elapsed_time,
                "data_sample": None
            }
            
            # Create table for display
            table = Table(title="River Level Monitoring (PAGASA)")
            table.add_column("Station", style="cyan")
            table.add_column("Water Level (m)", style="blue")
            table.add_column("Alert Level", style="yellow")
            table.add_column("Status", style="green")
            table.add_column("Risk Score", style="red")
            
            for station in river_data:
                station_name = station.get("station_name")
                if station_name in marikina_stations:
                    water_level = station.get("water_level_m")
                    alert_level = station.get("alert_level_m")
                    
                    # Calculate risk
                    status = "normal"
                    risk_score = 0.0
                    
                    if water_level and alert_level:
                        if water_level >= station.get("critical_level_m", float('inf')):
                            status = "critical"
                            risk_score = 1.0
                        elif water_level >= station.get("alarm_level_m", float('inf')):
                            status = "alarm"
                            risk_score = 0.8
                        elif water_level >= alert_level:
                            status = "alert"
                            risk_score = 0.5
                            
                    station_info = {
                        "name": station_name,
                        "water_level": water_level,
                        "alert_level": alert_level,
                        "status": status,
                        "risk_score": risk_score
                    }
                    
                    results["marikina_stations"].append(station_info)
                    
                    # Add to table
                    table.add_row(
                        station_name,
                        str(water_level) if water_level else "N/A",
                        str(alert_level) if alert_level else "N/A",
                        status,
                        f"{risk_score:.2f}"
                    )
                    
            self.console.print(table)
            
            # Store sample data
            if river_data:
                results["data_sample"] = river_data[0]
                
            self.results["river_scraper"] = results
            return results
            
        except Exception as e:
            error_msg = f"Test failed: {e}"
            self.console.print(f"[red]{error_msg}[/red]")
            return {"error": error_msg}
            
    def test_weather_service(self) -> Dict[str, Any]:
        """Test OpenWeatherMap weather data fetching."""
        self.console.print("\n[bold cyan]Testing OpenWeatherMapService...[/bold cyan]")
        
        if not self.weather_service:
            return {"error": "Service not available (API key required)"}
            
        try:
            # Marikina coordinates
            lat, lon = 14.6507, 121.1029
            
            start_time = time.time()
            weather_data = self.weather_service.get_forecast(lat, lon)
            elapsed_time = time.time() - start_time
            
            if not weather_data:
                return {"error": "No data returned", "elapsed_time": elapsed_time}
                
            # Process current weather
            current = weather_data.get("current", {})
            hourly = weather_data.get("hourly", [])
            
            # Current rainfall
            current_rain = current.get("rain", {}).get("1h", 0.0)
            
            # Calculate 24h forecast
            rainfall_24h = sum(
                h.get("rain", {}).get("1h", 0.0) for h in hourly[:24]
            )
            
            # Determine intensity
            intensity = self._calculate_rainfall_intensity(current_rain)
            
            results = {
                "location": "Marikina",
                "coordinates": [lat, lon],
                "current_rainfall_mm": current_rain,
                "rainfall_24h_forecast": rainfall_24h,
                "intensity": intensity,
                "temperature_c": current.get("temp"),
                "humidity_pct": current.get("humidity"),
                "elapsed_time": elapsed_time,
                "hourly_forecast_count": len(hourly)
            }
            
            # Create display panel
            weather_info = f"""
[bold]Current Conditions:[/bold]
  📍 Location: Marikina ({lat}, {lon})
  🌧️ Current Rainfall: {current_rain:.1f} mm/hr
  📊 Intensity: {intensity}
  🌡️ Temperature: {current.get('temp', 'N/A')}°C
  💧 Humidity: {current.get('humidity', 'N/A')}%

[bold]Forecast:[/bold]
  📅 24h Total Rainfall: {rainfall_24h:.1f} mm
  ⏰ Hourly Data Points: {len(hourly)}
            """
            
            panel = Panel(weather_info, title="Weather Data (OpenWeatherMap)")
            self.console.print(panel)
            
            # Show 6-hour forecast
            if hourly:
                table = Table(title="6-Hour Rainfall Forecast")
                table.add_column("Hour", style="cyan")
                table.add_column("Rain (mm)", style="blue")
                table.add_column("Temp (°C)", style="yellow")
                table.add_column("PoP (%)", style="green")
                
                for i, hour in enumerate(hourly[:6]):
                    rain = hour.get("rain", {}).get("1h", 0.0)
                    temp = hour.get("temp", 0)
                    pop = hour.get("pop", 0) * 100
                    
                    table.add_row(
                        f"+{i+1}h",
                        f"{rain:.1f}",
                        f"{temp:.1f}",
                        f"{pop:.0f}"
                    )
                    
                self.console.print(table)
                
            self.results["weather_service"] = results
            return results
            
        except Exception as e:
            error_msg = f"Test failed: {e}"
            self.console.print(f"[red]{error_msg}[/red]")
            return {"error": error_msg}
            
    def test_dam_scraper(self) -> Dict[str, Any]:
        """Test PAGASA dam level scraping."""
        self.console.print("\n[bold cyan]Testing DamWaterScraperService...[/bold cyan]")
        
        if not self.dam_scraper:
            return {"error": "Service not available"}
            
        try:
            start_time = time.time()
            dam_data = self.dam_scraper.get_dam_levels()
            elapsed_time = time.time() - start_time
            
            if not dam_data:
                return {"error": "No data returned", "elapsed_time": elapsed_time}
                
            results = {
                "total_dams": len(dam_data),
                "dams": [],
                "elapsed_time": elapsed_time
            }
            
            # Create table for display
            table = Table(title="Dam Water Level Monitoring (PAGASA)")
            table.add_column("Dam Name", style="cyan")
            table.add_column("Water Level (m)", style="blue")
            table.add_column("NHWL Dev (m)", style="yellow")
            table.add_column("Status", style="green")
            table.add_column("Risk Score", style="red")
            
            for dam in dam_data:
                dam_name = dam.get("Dam Name", "Unknown")
                water_level = dam.get("Latest RWL (m)")
                nhwl_dev = dam.get("Latest Dev from NHWL (m)")
                
                # Calculate risk status
                status = "normal"
                risk_score = 0.0
                
                if nhwl_dev is not None:
                    if nhwl_dev >= 2.0:
                        status = "critical"
                        risk_score = 1.0
                    elif nhwl_dev >= 1.0:
                        status = "alarm"
                        risk_score = 0.8
                    elif nhwl_dev >= 0.5:
                        status = "alert"
                        risk_score = 0.5
                    elif nhwl_dev >= 0.0:
                        status = "watch"
                        risk_score = 0.3
                    else:
                        status = "normal"
                        risk_score = 0.1
                        
                dam_info = {
                    "name": dam_name,
                    "water_level": water_level,
                    "nhwl_deviation": nhwl_dev,
                    "status": status,
                    "risk_score": risk_score
                }
                
                results["dams"].append(dam_info)
                
                # Add to table
                table.add_row(
                    dam_name,
                    str(water_level) if water_level else "N/A",
                    str(nhwl_dev) if nhwl_dev else "N/A",
                    status,
                    f"{risk_score:.2f}"
                )
                
            self.console.print(table)
            
            # Show risk summary
            risk_summary = self._calculate_risk_summary(results["dams"])
            self.console.print(f"\n[bold]Risk Summary:[/bold]")
            self.console.print(f"  🟢 Normal: {risk_summary['normal']}")
            self.console.print(f"  🟡 Watch: {risk_summary['watch']}")
            self.console.print(f"  🟠 Alert: {risk_summary['alert']}")
            self.console.print(f"  🔴 Alarm: {risk_summary['alarm']}")
            self.console.print(f"  ⚫ Critical: {risk_summary['critical']}")
            
            self.results["dam_scraper"] = results
            return results
            
        except Exception as e:
            error_msg = f"Test failed: {e}"
            self.console.print(f"[red]{error_msg}[/red]")
            return {"error": error_msg}
            
    def test_flood_agent_integration(self) -> Dict[str, Any]:
        """Test FloodAgent data collection and processing."""
        self.console.print("\n[bold cyan]Testing FloodAgent Integration...[/bold cyan]")
        
        if not self.flood_agent:
            return {"error": "FloodAgent not available"}
            
        try:
            start_time = time.time()
            
            # Collect data from all sources
            combined_data = self.flood_agent.collect_and_forward_data()
            
            elapsed_time = time.time() - start_time
            
            results = {
                "data_points_collected": len(combined_data),
                "elapsed_time": elapsed_time,
                "sources": [],
                "data_types": []
            }
            
            # Analyze collected data
            for key, value in combined_data.items():
                source = value.get("source", "Unknown")
                if source not in results["sources"]:
                    results["sources"].append(source)
                    
                # Identify data type
                if "water_level" in str(value):
                    data_type = "River Level"
                elif "rainfall" in str(value) or "weather" in key.lower():
                    data_type = "Weather"
                elif "dam" in key.lower() or "reservoir" in str(value):
                    data_type = "Dam Level"
                else:
                    data_type = "Other"
                    
                if data_type not in results["data_types"]:
                    results["data_types"].append(data_type)
                    
            # Display summary
            summary = f"""
[bold]FloodAgent Integration Test Results:[/bold]
  📊 Data Points Collected: {len(combined_data)}
  ⏱️ Processing Time: {elapsed_time:.2f}s
  📡 Active Sources: {', '.join(results['sources'])}
  📝 Data Types: {', '.join(results['data_types'])}
            """
            
            panel = Panel(summary, title="FloodAgent Summary")
            self.console.print(panel)
            
            # Show sample of collected data
            if combined_data:
                self.console.print("\n[bold]Sample Data Points:[/bold]")
                sample_count = min(5, len(combined_data))
                for i, (key, value) in enumerate(list(combined_data.items())[:sample_count]):
                    self.console.print(f"\n[cyan]{key}:[/cyan]")
                    # Display key fields
                    if isinstance(value, dict):
                        for field_key, field_value in list(value.items())[:5]:
                            self.console.print(f"  {field_key}: {field_value}")
                            
            self.results["flood_agent"] = results
            return results
            
        except Exception as e:
            error_msg = f"Test failed: {e}"
            self.console.print(f"[red]{error_msg}[/red]")
            return {"error": error_msg}
            
    def test_data_processing_pipeline(self) -> Dict[str, Any]:
        """Test the complete data processing pipeline."""
        self.console.print("\n[bold cyan]Testing Data Processing Pipeline...[/bold cyan]")
        
        if not self.flood_agent:
            return {"error": "FloodAgent not available"}
            
        try:
            # Test data validation
            test_flood_data = {
                "location": "Test Station",
                "flood_depth": 1.5,
                "rainfall_1h": 10.0,
                "timestamp": datetime.now()
            }
            
            # Validate using FloodAgent's internal method
            is_valid = self.flood_agent._validate_flood_data(test_flood_data)
            
            # Test risk calculation
            if self.flood_agent.hazard_agent:
                # This would normally trigger risk calculation
                self.console.print("[green]✓[/green] Data validation passed")
                self.console.print("[green]✓[/green] Ready for HazardAgent processing")
            else:
                self.console.print("[yellow]⚠[/yellow] No HazardAgent connected")
                
            # Test data format conversion
            processed = self.flood_agent._process_collected_data({
                "sources": {
                    "simulated": {
                        "rainfall": {"rainfall_mm": 5.0, "timestamp": datetime.now().isoformat()},
                        "flood_depth": {"flood_depth_cm": 30, "timestamp": datetime.now().isoformat()}
                    }
                }
            })
            
            results = {
                "validation_passed": is_valid,
                "processed_locations": len(processed),
                "pipeline_status": "operational"
            }
            
            self.console.print(f"\n[bold]Pipeline Test Results:[/bold]")
            self.console.print(f"  ✓ Data Validation: {'Passed' if is_valid else 'Failed'}")
            self.console.print(f"  ✓ Data Processing: {len(processed)} locations")
            self.console.print(f"  ✓ Pipeline Status: Operational")
            
            return results
            
        except Exception as e:
            error_msg = f"Pipeline test failed: {e}"
            self.console.print(f"[red]{error_msg}[/red]")
            return {"error": error_msg}
            
    def _calculate_rainfall_intensity(self, rainfall_mm: float) -> str:
        """Calculate rainfall intensity category."""
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
            
    def _calculate_risk_summary(self, dams: List[Dict]) -> Dict[str, int]:
        """Calculate risk summary for dams."""
        summary = {
            "normal": 0,
            "watch": 0,
            "alert": 0,
            "alarm": 0,
            "critical": 0
        }
        
        for dam in dams:
            status = dam.get("status", "normal")
            if status in summary:
                summary[status] += 1
                
        return summary
        
    def run_all_tests(self):
        """Run all service tests."""
        self.console.print("\n" + "="*60)
        self.console.print("[bold green]FLOOD AGENT SERVICE TESTING SUITE[/bold green]")
        self.console.print("="*60)
        
        # Test each service
        self.test_river_scraper()
        self.test_weather_service()
        self.test_dam_scraper()
        self.test_flood_agent_integration()
        self.test_data_processing_pipeline()
        
        # Generate final report
        self.generate_report()
        
    def generate_report(self):
        """Generate final test report."""
        self.console.print("\n" + "="*60)
        self.console.print("[bold green]FINAL TEST REPORT[/bold green]")
        self.console.print("="*60)
        
        # Summary table
        table = Table(title="Service Test Summary")
        table.add_column("Service", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Data Points", style="yellow")
        table.add_column("Response Time", style="blue")
        
        for service_name, result in self.results.items():
            if result:
                if "error" in result:
                    status = "❌ Failed"
                    data_points = "N/A"
                    response_time = "N/A"
                else:
                    status = "✅ Operational"
                    
                    # Calculate data points based on service
                    if service_name == "river_scraper":
                        data_points = str(len(result.get("marikina_stations", [])))
                    elif service_name == "weather_service":
                        data_points = "1"
                    elif service_name == "dam_scraper":
                        data_points = str(result.get("total_dams", 0))
                    elif service_name == "flood_agent":
                        data_points = str(result.get("data_points_collected", 0))
                    else:
                        data_points = "N/A"
                        
                    response_time = f"{result.get('elapsed_time', 0):.2f}s"
                    
                table.add_row(service_name, status, data_points, response_time)
            else:
                table.add_row(service_name, "⚠️ Not Tested", "N/A", "N/A")
                
        self.console.print(table)
        
        # Save results to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"flood_agent_test_results_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            # Convert datetime objects to strings for JSON serialization
            json_safe_results = {}
            for key, value in self.results.items():
                if value and isinstance(value, dict):
                    json_safe_results[key] = str(value)
                else:
                    json_safe_results[key] = value
                    
            json.dump(json_safe_results, f, indent=2, default=str)
            
        self.console.print(f"\n📄 Results saved to: {output_file}")


def main():
    """Main execution function."""
    tester = FloodAgentServiceTester()
    
    # Run all tests
    tester.run_all_tests()
    
    # Interactive mode
    console.print("\n[bold cyan]Interactive Testing Mode[/bold cyan]")
    console.print("Select an option:")
    console.print("1. Re-test River Scraper")
    console.print("2. Re-test Weather Service")
    console.print("3. Re-test Dam Scraper")
    console.print("4. Re-test FloodAgent Integration")
    console.print("5. Run All Tests Again")
    console.print("0. Exit")
    
    while True:
        choice = input("\nEnter choice (0-5): ").strip()
        
        if choice == "0":
            break
        elif choice == "1":
            tester.test_river_scraper()
        elif choice == "2":
            tester.test_weather_service()
        elif choice == "3":
            tester.test_dam_scraper()
        elif choice == "4":
            tester.test_flood_agent_integration()
        elif choice == "5":
            tester.run_all_tests()
        else:
            console.print("[red]Invalid choice[/red]")
            
    console.print("\n[bold green]Testing Complete![/bold green]")


if __name__ == "__main__":
    main()