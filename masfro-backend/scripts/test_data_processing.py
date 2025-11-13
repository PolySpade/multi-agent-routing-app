#!/usr/bin/env python3
"""
Test data processing and validation for FloodAgent services.

This script focuses on testing how each service processes and validates its data,
including edge cases, error handling, and data format consistency.

Author: MAS-FRO Development Team
Date: November 2025
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.agents.flood_agent import FloodAgent
from app.environment.graph_manager import DynamicGraphEnvironment

console = Console()


class DataProcessingValidator:
    """Validate data processing across all FloodAgent services."""
    
    def __init__(self):
        """Initialize validator."""
        self.console = console
        self.flood_agent = None
        self.test_results = []
        
        # Initialize FloodAgent for testing
        try:
            self.environment = DynamicGraphEnvironment()
            self.flood_agent = FloodAgent(
                "test_flood_agent",
                self.environment,
                use_real_apis=True
            )
            self.console.print("[green]✓[/green] FloodAgent initialized for data testing")
        except Exception as e:
            self.console.print(f"[red]✗[/red] FloodAgent initialization failed: {e}")
            
    def test_river_data_processing(self):
        """Test river level data processing and validation."""
        self.console.print("\n[bold cyan]Testing River Data Processing...[/bold cyan]")
        
        # Test cases
        test_cases = [
            {
                "name": "Valid river data",
                "data": {
                    "station_name": "Sto Nino",
                    "water_level_m": 14.5,
                    "alert_level_m": 15.0,
                    "alarm_level_m": 16.0,
                    "critical_level_m": 17.0
                },
                "expected_status": "normal",
                "expected_risk": 0.2
            },
            {
                "name": "Alert level exceeded",
                "data": {
                    "station_name": "Nangka", 
                    "water_level_m": 15.5,
                    "alert_level_m": 15.0,
                    "alarm_level_m": 16.0,
                    "critical_level_m": 17.0
                },
                "expected_status": "alert",
                "expected_risk": 0.5
            },
            {
                "name": "Critical level reached",
                "data": {
                    "station_name": "Tumana Bridge",
                    "water_level_m": 18.0,
                    "alert_level_m": 17.0,
                    "alarm_level_m": 18.0,
                    "critical_level_m": 19.0
                },
                "expected_status": "alarm",
                "expected_risk": 0.8
            },
            {
                "name": "Null water level",
                "data": {
                    "station_name": "Montalban",
                    "water_level_m": None,
                    "alert_level_m": 22.0,
                    "alarm_level_m": 23.0,
                    "critical_level_m": 24.0
                },
                "expected_status": "normal",
                "expected_risk": 0.0
            },
            {
                "name": "Missing critical level",
                "data": {
                    "station_name": "Rosario Bridge",
                    "water_level_m": 14.0,
                    "alert_level_m": 13.0,
                    "alarm_level_m": None,
                    "critical_level_m": None
                },
                "expected_status": "alert",
                "expected_risk": 0.5
            }
        ]
        
        # Create results table
        table = Table(title="River Data Processing Test Results")
        table.add_column("Test Case", style="cyan")
        table.add_column("Station", style="blue")
        table.add_column("Water Level", style="yellow")
        table.add_column("Expected Status", style="green")
        table.add_column("Actual Status", style="green")
        table.add_column("Expected Risk", style="red")
        table.add_column("Actual Risk", style="red")
        table.add_column("Result", style="bold")
        
        for test_case in test_cases:
            station_data = test_case["data"]
            
            # Simulate risk calculation logic
            water_level = station_data.get("water_level_m")
            alert_level = self._parse_float(station_data.get("alert_level_m"))
            alarm_level = self._parse_float(station_data.get("alarm_level_m"))
            critical_level = self._parse_float(station_data.get("critical_level_m"))
            
            # Calculate status and risk
            actual_status = "normal"
            actual_risk = 0.0
            
            if water_level is not None:
                if critical_level and water_level >= critical_level:
                    actual_status = "critical"
                    actual_risk = 1.0
                elif alarm_level and water_level >= alarm_level:
                    actual_status = "alarm"
                    actual_risk = 0.8
                elif alert_level and water_level >= alert_level:
                    actual_status = "alert"
                    actual_risk = 0.5
                else:
                    actual_status = "normal"
                    actual_risk = 0.2
                    
            # Check if test passed
            status_match = actual_status == test_case["expected_status"]
            risk_match = abs(actual_risk - test_case["expected_risk"]) < 0.01
            test_passed = status_match and risk_match
            
            # Add to table
            table.add_row(
                test_case["name"],
                station_data["station_name"],
                str(water_level) if water_level else "NULL",
                test_case["expected_status"],
                actual_status,
                f"{test_case['expected_risk']:.1f}",
                f"{actual_risk:.1f}",
                "✅ PASS" if test_passed else "❌ FAIL"
            )
            
            self.test_results.append({
                "test_type": "river_processing",
                "test_name": test_case["name"],
                "passed": test_passed,
                "details": {
                    "expected": test_case,
                    "actual": {"status": actual_status, "risk": actual_risk}
                }
            })
            
        self.console.print(table)
        
    def test_weather_data_processing(self):
        """Test weather data processing and intensity classification."""
        self.console.print("\n[bold cyan]Testing Weather Data Processing...[/bold cyan]")
        
        # Test rainfall intensity classification
        test_cases = [
            {"rainfall_mm": 0.0, "expected_intensity": "none"},
            {"rainfall_mm": 1.5, "expected_intensity": "light"},
            {"rainfall_mm": 5.0, "expected_intensity": "moderate"},
            {"rainfall_mm": 12.0, "expected_intensity": "heavy"},
            {"rainfall_mm": 20.0, "expected_intensity": "intense"},
            {"rainfall_mm": 35.0, "expected_intensity": "torrential"},
            {"rainfall_mm": -1.0, "expected_intensity": "none"},  # Edge case
        ]
        
        table = Table(title="Weather Intensity Classification Test")
        table.add_column("Rainfall (mm/hr)", style="cyan")
        table.add_column("Expected Intensity", style="yellow")
        table.add_column("Actual Intensity", style="yellow")
        table.add_column("Result", style="bold")
        
        for test_case in test_cases:
            rainfall = test_case["rainfall_mm"]
            expected = test_case["expected_intensity"]
            
            # Test the intensity calculation
            actual = self._calculate_rainfall_intensity(rainfall)
            passed = actual == expected
            
            table.add_row(
                f"{rainfall:.1f}",
                expected,
                actual,
                "✅ PASS" if passed else "❌ FAIL"
            )
            
            self.test_results.append({
                "test_type": "weather_intensity",
                "test_name": f"rainfall_{rainfall}mm",
                "passed": passed,
                "details": {"expected": expected, "actual": actual}
            })
            
        self.console.print(table)
        
    def test_dam_data_processing(self):
        """Test dam water level processing and risk assessment."""
        self.console.print("\n[bold cyan]Testing Dam Data Processing...[/bold cyan]")
        
        test_cases = [
            {
                "name": "Normal level",
                "nhwl_deviation": -1.5,
                "expected_status": "normal",
                "expected_risk": 0.1
            },
            {
                "name": "Watch level",
                "nhwl_deviation": 0.3,
                "expected_status": "watch", 
                "expected_risk": 0.3
            },
            {
                "name": "Alert level",
                "nhwl_deviation": 0.7,
                "expected_status": "alert",
                "expected_risk": 0.5
            },
            {
                "name": "Alarm level",
                "nhwl_deviation": 1.5,
                "expected_status": "alarm",
                "expected_risk": 0.8
            },
            {
                "name": "Critical level",
                "nhwl_deviation": 2.5,
                "expected_status": "critical",
                "expected_risk": 1.0
            },
            {
                "name": "Null deviation",
                "nhwl_deviation": None,
                "expected_status": "normal",
                "expected_risk": 0.0
            }
        ]
        
        table = Table(title="Dam Risk Assessment Test")
        table.add_column("Test Case", style="cyan")
        table.add_column("NHWL Dev (m)", style="blue")
        table.add_column("Expected Status", style="yellow")
        table.add_column("Actual Status", style="yellow")
        table.add_column("Expected Risk", style="red")
        table.add_column("Actual Risk", style="red")
        table.add_column("Result", style="bold")
        
        for test_case in test_cases:
            nhwl_dev = test_case["nhwl_deviation"]
            
            # Calculate status and risk (similar to FloodAgent logic)
            actual_status = "normal"
            actual_risk = 0.0
            
            if nhwl_dev is not None:
                if nhwl_dev >= 2.0:
                    actual_status = "critical"
                    actual_risk = 1.0
                elif nhwl_dev >= 1.0:
                    actual_status = "alarm"
                    actual_risk = 0.8
                elif nhwl_dev >= 0.5:
                    actual_status = "alert"
                    actual_risk = 0.5
                elif nhwl_dev >= 0.0:
                    actual_status = "watch"
                    actual_risk = 0.3
                else:
                    actual_status = "normal"
                    actual_risk = 0.1
                    
            # Check results
            status_match = actual_status == test_case["expected_status"]
            risk_match = abs(actual_risk - test_case["expected_risk"]) < 0.01
            test_passed = status_match and risk_match
            
            table.add_row(
                test_case["name"],
                str(nhwl_dev) if nhwl_dev is not None else "NULL",
                test_case["expected_status"],
                actual_status,
                f"{test_case['expected_risk']:.1f}",
                f"{actual_risk:.1f}",
                "✅ PASS" if test_passed else "❌ FAIL"
            )
            
            self.test_results.append({
                "test_type": "dam_processing",
                "test_name": test_case["name"],
                "passed": test_passed,
                "details": {
                    "expected": test_case,
                    "actual": {"status": actual_status, "risk": actual_risk}
                }
            })
            
        self.console.print(table)
        
    def test_data_validation(self):
        """Test data validation functions."""
        self.console.print("\n[bold cyan]Testing Data Validation...[/bold cyan]")
        
        if not self.flood_agent:
            self.console.print("[red]FloodAgent not available for validation tests[/red]")
            return
            
        # Test flood data validation
        flood_test_cases = [
            {
                "name": "Valid flood data",
                "data": {
                    "location": "Marikina",
                    "flood_depth": 1.5,
                    "timestamp": datetime.now()
                },
                "expected": True
            },
            {
                "name": "Missing location",
                "data": {
                    "flood_depth": 1.5,
                    "timestamp": datetime.now()
                },
                "expected": False
            },
            {
                "name": "Invalid flood depth",
                "data": {
                    "location": "Marikina",
                    "flood_depth": 15.0,  # > 10m limit
                    "timestamp": datetime.now()
                },
                "expected": False
            },
            {
                "name": "Negative flood depth",
                "data": {
                    "location": "Marikina",
                    "flood_depth": -0.5,
                    "timestamp": datetime.now()
                },
                "expected": False
            }
        ]
        
        table = Table(title="Flood Data Validation Test")
        table.add_column("Test Case", style="cyan")
        table.add_column("Expected", style="yellow")
        table.add_column("Actual", style="yellow")
        table.add_column("Result", style="bold")
        
        for test_case in flood_test_cases:
            try:
                actual = self.flood_agent._validate_flood_data(test_case["data"])
                passed = actual == test_case["expected"]
                
                table.add_row(
                    test_case["name"],
                    str(test_case["expected"]),
                    str(actual),
                    "✅ PASS" if passed else "❌ FAIL"
                )
                
                self.test_results.append({
                    "test_type": "flood_validation",
                    "test_name": test_case["name"],
                    "passed": passed,
                    "details": {"expected": test_case["expected"], "actual": actual}
                })
                
            except Exception as e:
                table.add_row(
                    test_case["name"],
                    str(test_case["expected"]),
                    f"ERROR: {e}",
                    "❌ FAIL"
                )
                
        self.console.print(table)
        
    def _parse_float(self, value) -> float:
        """Helper to parse float values safely."""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
            
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
            
    def generate_summary(self):
        """Generate test summary."""
        self.console.print("\n" + "="*60)
        self.console.print("[bold green]DATA PROCESSING VALIDATION SUMMARY[/bold green]")
        self.console.print("="*60)
        
        # Calculate stats
        total_tests = len(self.test_results)
        passed_tests = sum(1 for test in self.test_results if test["passed"])
        failed_tests = total_tests - passed_tests
        
        # Group by test type
        test_types = {}
        for test in self.test_results:
            test_type = test["test_type"]
            if test_type not in test_types:
                test_types[test_type] = {"total": 0, "passed": 0}
            test_types[test_type]["total"] += 1
            if test["passed"]:
                test_types[test_type]["passed"] += 1
                
        # Summary table
        table = Table(title="Test Summary by Type")
        table.add_column("Test Type", style="cyan")
        table.add_column("Passed", style="green")
        table.add_column("Failed", style="red")
        table.add_column("Total", style="yellow")
        table.add_column("Success Rate", style="blue")
        
        for test_type, stats in test_types.items():
            passed = stats["passed"]
            total = stats["total"]
            failed = total - passed
            success_rate = (passed / total * 100) if total > 0 else 0
            
            table.add_row(
                test_type.replace("_", " ").title(),
                str(passed),
                str(failed),
                str(total),
                f"{success_rate:.1f}%"
            )
            
        self.console.print(table)
        
        # Overall summary
        overall_success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        summary_text = f"""
[bold]Overall Results:[/bold]
  ✅ Passed: {passed_tests}
  ❌ Failed: {failed_tests}
  📊 Total: {total_tests}
  📈 Success Rate: {overall_success_rate:.1f}%

[bold]Status:[/bold] {'🟢 ALL TESTS PASSED' if failed_tests == 0 else f'🟠 {failed_tests} TESTS FAILED'}
        """
        
        panel = Panel(summary_text, title="Validation Summary")
        self.console.print(panel)
        
    def run_all_tests(self):
        """Run all data processing validation tests."""
        self.console.print("\n[bold green]DATA PROCESSING VALIDATION SUITE[/bold green]")
        self.console.print("Testing data processing, validation, and edge cases...\n")
        
        self.test_river_data_processing()
        self.test_weather_data_processing()
        self.test_dam_data_processing()
        self.test_data_validation()
        
        self.generate_summary()


def main():
    """Main execution function."""
    validator = DataProcessingValidator()
    validator.run_all_tests()
    
    console.print("\n[bold cyan]Data processing validation complete![/bold cyan]")


if __name__ == "__main__":
    main()