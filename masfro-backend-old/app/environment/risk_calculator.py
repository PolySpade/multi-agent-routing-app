# filename: app/environment/risk_calculator.py

"""
Risk Calculation Module for MAS-FRO

This module implements risk scoring functions for road segments based on
multiple factors including flood depth, hydrological energy, infrastructure
vulnerability, and traffic congestion.

The risk calculation is based on research by Kreibich et al. (2009) which
identifies energy head (h + v²/2g) and flow velocity as strong predictors
of infrastructure damage during floods.

Key Components:
- Hydrological risk (flood depth, flow velocity)
- Infrastructure risk (road type, surface quality)
- Congestion risk (traffic density)
- Historical risk (past flood frequency)

Author: MAS-FRO Development Team
Date: November 2025
"""

from typing import Dict, Any, Tuple
import math
import logging

logger = logging.getLogger(__name__)


class RiskCalculator:
    """
    Calculator for road segment flood risk scores.

    This class provides methods to calculate comprehensive risk scores
    for road segments based on multiple factors. Risk scores are normalized
    to a 0-1 scale where:
    - 0.0: No risk (completely safe)
    - 0.3: Low risk (minor flooding)
    - 0.6: Moderate risk (significant flooding)
    - 0.9+: High risk (dangerous/impassable)

    Attributes:
        gravity: Gravitational acceleration constant (m/s²)
        weights: Weights for different risk components

    Example:
        >>> calc = RiskCalculator()
        >>> risk = calc.calculate_composite_risk(
        ...     flood_depth=0.5,
        ...     flow_velocity=1.2,
        ...     road_type="residential"
        ... )
        >>> print(f"Risk score: {risk:.2f}")
    """

    def __init__(self):
        """Initialize the RiskCalculator with default parameters."""
        # Physical constants
        self.gravity = 9.81  # m/s²

        # Component weights for composite risk
        self.weights = {
            "hydrological": 0.50,  # Flood depth and flow
            "infrastructure": 0.25,  # Road characteristics
            "congestion": 0.15,  # Traffic conditions
            "historical": 0.10  # Past flood data
        }

        logger.info("RiskCalculator initialized with weights: %s", self.weights)

    def calculate_composite_risk(
        self,
        flood_depth: float = 0.0,
        flow_velocity: float = 0.0,
        road_type: str = "primary",
        congestion_level: float = 0.0,
        historical_frequency: float = 0.0
    ) -> float:
        """
        Calculate composite risk score for a road segment.

        Combines multiple risk factors into a single normalized score.

        Args:
            flood_depth: Current flood depth in meters
            flow_velocity: Water flow velocity in m/s
            road_type: Type of road ("highway", "primary", "residential", "tertiary")
            congestion_level: Traffic congestion level (0-1 scale)
            historical_frequency: Historical flood frequency (0-1 scale)

        Returns:
            Composite risk score (0-1 scale)

        Example:
            >>> risk = calc.calculate_composite_risk(
            ...     flood_depth=0.8,
            ...     flow_velocity=1.5,
            ...     road_type="residential",
            ...     congestion_level=0.4
            ... )
        """
        # Calculate component risks
        hydro_risk = self.calculate_hydrological_risk(flood_depth, flow_velocity)
        infra_risk = self.calculate_infrastructure_risk(road_type, flood_depth)
        congest_risk = congestion_level  # Already normalized
        hist_risk = historical_frequency  # Already normalized

        # Weighted combination
        composite = (
            hydro_risk * self.weights["hydrological"] +
            infra_risk * self.weights["infrastructure"] +
            congest_risk * self.weights["congestion"] +
            hist_risk * self.weights["historical"]
        )

        # Ensure result is in [0, 1]
        return min(max(composite, 0.0), 1.0)

    def calculate_hydrological_risk(
        self,
        flood_depth: float,
        flow_velocity: float = 0.0
    ) -> float:
        """
        Calculate hydrological risk based on energy head.

        Implements the energy head formula from Kreibich et al. (2009):
            E = h + v²/(2g)
        where h is flood depth and v is flow velocity.

        Higher energy indicates greater damage potential.

        Args:
            flood_depth: Flood depth in meters
            flow_velocity: Flow velocity in m/s (default: 0 for static water)

        Returns:
            Normalized risk score (0-1 scale)

        Reference:
            Kreibich et al. (2009): "Flood loss reduction of private households
            due to building precautionary measures"
        """
        if flood_depth <= 0:
            return 0.0

        # Calculate energy head
        velocity_head = (flow_velocity ** 2) / (2 * self.gravity)
        total_energy = flood_depth + velocity_head

        # Normalize to 0-1 scale
        # Based on research thresholds:
        # - E < 0.3m: Low risk (vehicles can pass)
        # - 0.3m < E < 0.6m: Moderate risk
        # - E > 0.6m: High risk (dangerous for vehicles)

        if total_energy < 0.3:
            risk = total_energy / 0.3 * 0.4  # Scale to 0-0.4
        elif total_energy < 0.6:
            risk = 0.4 + ((total_energy - 0.3) / 0.3) * 0.3  # Scale to 0.4-0.7
        else:
            risk = 0.7 + min((total_energy - 0.6) / 0.4, 0.3)  # Scale to 0.7-1.0

        return min(risk, 1.0)

    def calculate_infrastructure_risk(
        self,
        road_type: str,
        flood_depth: float
    ) -> float:
        """
        Calculate infrastructure vulnerability risk.

        Different road types have different vulnerabilities to flooding:
        - Highways: Better drainage, higher elevation
        - Primary roads: Moderate infrastructure
        - Residential: Variable quality
        - Tertiary: Often poor drainage

        Args:
            road_type: Type of road
            flood_depth: Current flood depth in meters

        Returns:
            Infrastructure risk score (0-1 scale)
        """
        # Base vulnerability by road type
        base_vulnerability = {
            "motorway": 0.1,
            "trunk": 0.1,
            "primary": 0.2,
            "secondary": 0.3,
            "tertiary": 0.4,
            "residential": 0.5,
            "unclassified": 0.6
        }

        base_risk = base_vulnerability.get(road_type.lower(), 0.5)

        # Increase risk with flood depth
        # Infrastructure fails more readily under deeper floods
        depth_multiplier = 1.0 + min(flood_depth * 0.5, 1.0)

        risk = base_risk * depth_multiplier

        return min(risk, 1.0)

    def calculate_passability_threshold(
        self,
        flood_depth: float,
        flow_velocity: float,
        vehicle_type: str = "car"
    ) -> Dict[str, Any]:
        """
        Determine if a road segment is passable for a vehicle.

        Based on established flood safety thresholds:
        - Cars: depth < 0.3m or (depth < 0.4m and velocity < 0.5m/s)
        - SUVs/Trucks: depth < 0.5m or (depth < 0.6m and velocity < 0.5m/s)

        Args:
            flood_depth: Flood depth in meters
            flow_velocity: Flow velocity in m/s
            vehicle_type: Type of vehicle ("car", "suv", "truck")

        Returns:
            Dict with passability information:
                {
                    "passable": bool,
                    "confidence": float,  # 0-1 scale
                    "reason": str
                }
        """
        thresholds = {
            "car": {"static_depth": 0.3, "flowing_depth": 0.4, "max_velocity": 0.5},
            "suv": {"static_depth": 0.5, "flowing_depth": 0.6, "max_velocity": 0.5},
            "truck": {"static_depth": 0.6, "flowing_depth": 0.7, "max_velocity": 0.6}
        }

        thresh = thresholds.get(vehicle_type.lower(), thresholds["car"])

        # Check passability
        if flood_depth <= 0:
            return {
                "passable": True,
                "confidence": 1.0,
                "reason": "No flooding detected"
            }

        # Static water check
        if flow_velocity < 0.1:
            if flood_depth < thresh["static_depth"]:
                return {
                    "passable": True,
                    "confidence": 0.8,
                    "reason": f"Shallow static water ({flood_depth:.2f}m)"
                }
            else:
                return {
                    "passable": False,
                    "confidence": 0.9,
                    "reason": f"Water too deep ({flood_depth:.2f}m)"
                }

        # Flowing water check
        if flood_depth < thresh["flowing_depth"] and flow_velocity < thresh["max_velocity"]:
            return {
                "passable": True,
                "confidence": 0.6,
                "reason": f"Manageable flowing water ({flood_depth:.2f}m at {flow_velocity:.2f}m/s)"
            }
        else:
            return {
                "passable": False,
                "confidence": 0.95,
                "reason": f"Dangerous flowing water ({flood_depth:.2f}m at {flow_velocity:.2f}m/s)"
            }

    def estimate_travel_time_adjustment(
        self,
        base_time: float,
        risk_score: float
    ) -> float:
        """
        Adjust travel time estimate based on risk/flood conditions.

        Higher risk conditions slow down travel significantly.

        Args:
            base_time: Base travel time in minutes (no flooding)
            risk_score: Risk score (0-1 scale)

        Returns:
            Adjusted travel time in minutes
        """
        if risk_score < 0.3:
            # Low risk: minimal slowdown (5-10%)
            factor = 1.0 + (risk_score * 0.3)
        elif risk_score < 0.6:
            # Moderate risk: moderate slowdown (10-30%)
            factor = 1.1 + ((risk_score - 0.3) * 0.6)
        else:
            # High risk: severe slowdown (30-50%)
            factor = 1.3 + ((risk_score - 0.6) * 0.5)

        adjusted_time = base_time * factor
        return adjusted_time

    def get_risk_category(self, risk_score: float) -> str:
        """
        Get descriptive category for risk score.

        Args:
            risk_score: Risk score (0-1 scale)

        Returns:
            Category string: "safe", "low", "moderate", "high", "critical"
        """
        if risk_score < 0.2:
            return "safe"
        elif risk_score < 0.4:
            return "low"
        elif risk_score < 0.6:
            return "moderate"
        elif risk_score < 0.8:
            return "high"
        else:
            return "critical"

    def get_risk_color(self, risk_score: float) -> str:
        """
        Get color code for risk visualization.

        Args:
            risk_score: Risk score (0-1 scale)

        Returns:
            Hex color code string
        """
        if risk_score < 0.2:
            return "#00FF00"  # Green
        elif risk_score < 0.4:
            return "#90EE90"  # Light green
        elif risk_score < 0.6:
            return "#FFFF00"  # Yellow
        elif risk_score < 0.8:
            return "#FFA500"  # Orange
        else:
            return "#FF0000"  # Red
