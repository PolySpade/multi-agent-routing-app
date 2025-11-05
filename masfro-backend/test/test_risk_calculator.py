# filename: test/test_risk_calculator.py

"""
Tests for Risk Calculator
"""

import pytest
from app.environment.risk_calculator import RiskCalculator


class TestRiskCalculator:
    """Test risk calculation functions."""

    @pytest.fixture
    def calculator(self):
        """Create a RiskCalculator instance."""
        return RiskCalculator()

    def test_initialization(self, calculator):
        """Test calculator initialization."""
        assert calculator.gravity == 9.81
        assert "hydrological" in calculator.weights
        assert sum(calculator.weights.values()) == 1.0

    def test_hydrological_risk_no_flood(self, calculator):
        """Test hydrological risk with no flooding."""
        risk = calculator.calculate_hydrological_risk(
            flood_depth=0.0,
            flow_velocity=0.0
        )
        assert risk == 0.0

    def test_hydrological_risk_low_flood(self, calculator):
        """Test hydrological risk with low flooding."""
        risk = calculator.calculate_hydrological_risk(
            flood_depth=0.2,
            flow_velocity=0.0
        )
        assert 0.0 < risk < 0.4

    def test_hydrological_risk_moderate_flood(self, calculator):
        """Test hydrological risk with moderate flooding."""
        risk = calculator.calculate_hydrological_risk(
            flood_depth=0.5,
            flow_velocity=0.5
        )
        assert 0.4 <= risk <= 0.7

    def test_hydrological_risk_high_flood(self, calculator):
        """Test hydrological risk with high flooding."""
        risk = calculator.calculate_hydrological_risk(
            flood_depth=1.0,
            flow_velocity=1.5
        )
        assert risk > 0.7

    def test_infrastructure_risk_highway(self, calculator):
        """Test infrastructure risk for highway."""
        risk = calculator.calculate_infrastructure_risk(
            road_type="motorway",
            flood_depth=0.3
        )
        # Highways have better infrastructure
        assert risk < 0.5

    def test_infrastructure_risk_residential(self, calculator):
        """Test infrastructure risk for residential road."""
        risk = calculator.calculate_infrastructure_risk(
            road_type="residential",
            flood_depth=0.3
        )
        # Residential roads more vulnerable
        assert risk > 0.3

    def test_composite_risk_no_flood(self, calculator):
        """Test composite risk with no flooding."""
        risk = calculator.calculate_composite_risk(
            flood_depth=0.0,
            flow_velocity=0.0,
            road_type="primary",
            congestion_level=0.0,
            historical_frequency=0.0
        )
        assert risk == 0.0

    def test_composite_risk_moderate_flood(self, calculator):
        """Test composite risk with moderate flooding."""
        risk = calculator.calculate_composite_risk(
            flood_depth=0.5,
            flow_velocity=0.8,
            road_type="residential",
            congestion_level=0.3,
            historical_frequency=0.2
        )
        assert 0.0 < risk < 1.0

    def test_composite_risk_high_flood(self, calculator):
        """Test composite risk with severe flooding."""
        risk = calculator.calculate_composite_risk(
            flood_depth=1.5,
            flow_velocity=2.0,
            road_type="tertiary",
            congestion_level=0.5,
            historical_frequency=0.7
        )
        assert risk > 0.6

    def test_passability_no_flood(self, calculator):
        """Test passability with no flood."""
        result = calculator.calculate_passability_threshold(
            flood_depth=0.0,
            flow_velocity=0.0,
            vehicle_type="car"
        )
        assert result["passable"] is True
        assert result["confidence"] == 1.0

    def test_passability_shallow_static(self, calculator):
        """Test passability with shallow static water."""
        result = calculator.calculate_passability_threshold(
            flood_depth=0.2,
            flow_velocity=0.0,
            vehicle_type="car"
        )
        assert result["passable"] is True
        assert result["confidence"] > 0.5

    def test_passability_deep_water(self, calculator):
        """Test passability with deep water."""
        result = calculator.calculate_passability_threshold(
            flood_depth=0.8,
            flow_velocity=0.0,
            vehicle_type="car"
        )
        assert result["passable"] is False

    def test_passability_flowing_water(self, calculator):
        """Test passability with dangerous flowing water."""
        result = calculator.calculate_passability_threshold(
            flood_depth=0.5,
            flow_velocity=1.5,
            vehicle_type="car"
        )
        assert result["passable"] is False
        assert "flowing water" in result["reason"].lower()

    def test_passability_suv_higher_threshold(self, calculator):
        """Test that SUVs have higher passability threshold."""
        car_result = calculator.calculate_passability_threshold(
            flood_depth=0.4,
            flow_velocity=0.0,
            vehicle_type="car"
        )
        suv_result = calculator.calculate_passability_threshold(
            flood_depth=0.4,
            flow_velocity=0.0,
            vehicle_type="suv"
        )
        # SUV should be passable where car is not
        assert suv_result["passable"] is True or car_result["passable"] is False

    def test_travel_time_adjustment_low_risk(self, calculator):
        """Test travel time adjustment with low risk."""
        adjusted = calculator.estimate_travel_time_adjustment(
            base_time=10.0,
            risk_score=0.2
        )
        # Should be slightly longer than base time
        assert adjusted > 10.0
        assert adjusted < 12.0

    def test_travel_time_adjustment_high_risk(self, calculator):
        """Test travel time adjustment with high risk."""
        adjusted = calculator.estimate_travel_time_adjustment(
            base_time=10.0,
            risk_score=0.8
        )
        # Should be significantly longer
        assert adjusted > 13.0

    def test_risk_category_safe(self, calculator):
        """Test risk category for safe conditions."""
        category = calculator.get_risk_category(0.1)
        assert category == "safe"

    def test_risk_category_low(self, calculator):
        """Test risk category for low risk."""
        category = calculator.get_risk_category(0.3)
        assert category == "low"

    def test_risk_category_moderate(self, calculator):
        """Test risk category for moderate risk."""
        category = calculator.get_risk_category(0.5)
        assert category == "moderate"

    def test_risk_category_high(self, calculator):
        """Test risk category for high risk."""
        category = calculator.get_risk_category(0.7)
        assert category == "high"

    def test_risk_category_critical(self, calculator):
        """Test risk category for critical risk."""
        category = calculator.get_risk_category(0.9)
        assert category == "critical"

    def test_risk_color_codes(self, calculator):
        """Test color codes for different risk levels."""
        safe_color = calculator.get_risk_color(0.1)
        moderate_color = calculator.get_risk_color(0.5)
        critical_color = calculator.get_risk_color(0.9)

        assert safe_color.startswith("#")
        assert moderate_color.startswith("#")
        assert critical_color.startswith("#")
        # Different risk levels should have different colors
        assert safe_color != critical_color
