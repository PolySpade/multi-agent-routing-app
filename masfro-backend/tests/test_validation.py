# filename: tests/test_validation.py
"""
Test suite for validation utilities.

Tests cover Issue #17: Input validation across agents.

Author: MAS-FRO Development Team
Date: January 2026
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.validation import (
    CoordinateValidator,
    RiskValidator,
    ReportValidator,
    TypeValidator,
    ValidationResult,
    validate_coordinates,
    validate_risk_score,
    validate_scout_report
)


class TestCoordinateValidator:
    """Tests for coordinate validation."""

    def test_valid_coordinates(self):
        """Valid coordinates should pass validation."""
        result = CoordinateValidator.validate_coordinates(14.65, 121.10)
        assert result.is_valid is True
        assert result.sanitized_value == (14.65, 121.10)

    def test_invalid_latitude_range(self):
        """Latitude outside [-90, 90] should fail."""
        result = CoordinateValidator.validate_coordinates(100.0, 121.10)
        assert result.is_valid is False
        assert "out of valid range" in result.error_message

    def test_invalid_longitude_range(self):
        """Longitude outside [-180, 180] should fail."""
        result = CoordinateValidator.validate_coordinates(14.65, 200.0)
        assert result.is_valid is False
        assert "out of valid range" in result.error_message

    def test_none_coordinates(self):
        """None coordinates should fail by default."""
        result = CoordinateValidator.validate_coordinates(None, 121.10)
        assert result.is_valid is False
        assert "cannot be None" in result.error_message

    def test_none_coordinates_allowed(self):
        """None coordinates should pass when allow_none=True."""
        result = CoordinateValidator.validate_coordinates(
            None, None, allow_none=True
        )
        assert result.is_valid is True
        assert result.sanitized_value == (None, None)

    def test_string_coordinates_converted(self):
        """String coordinates should be converted to float."""
        result = CoordinateValidator.validate_coordinates("14.65", "121.10")
        assert result.is_valid is True
        assert result.sanitized_value == (14.65, 121.10)

    def test_invalid_type_coordinates(self):
        """Non-numeric coordinates should fail."""
        result = CoordinateValidator.validate_coordinates("invalid", 121.10)
        assert result.is_valid is False
        assert "Invalid coordinate types" in result.error_message

    def test_marikina_bounds_warning(self):
        """Coordinates outside Marikina should still pass but trigger warning."""
        # Manila coordinates (outside Marikina bounds)
        result = CoordinateValidator.validate_coordinates(
            14.60, 120.98,
            bounds=CoordinateValidator.MARIKINA_BOUNDS
        )
        # Should still be valid (just logged warning)
        assert result.is_valid is True

    def test_coordinate_tuple_validation(self):
        """Tuple format should be validated."""
        result = CoordinateValidator.validate_coordinate_tuple((14.65, 121.10))
        assert result.is_valid is True
        assert result.sanitized_value == (14.65, 121.10)

    def test_invalid_tuple_length(self):
        """Tuple with wrong length should fail."""
        result = CoordinateValidator.validate_coordinate_tuple((14.65,))
        assert result.is_valid is False
        assert "must be (lat, lon) tuple" in result.error_message


class TestRiskValidator:
    """Tests for risk score validation."""

    def test_valid_risk_score(self):
        """Valid risk score should pass."""
        result = RiskValidator.validate_risk_score(0.5)
        assert result.is_valid is True
        assert result.sanitized_value == 0.5

    def test_risk_score_clamped_high(self):
        """Risk score > 1.0 should be clamped."""
        result = RiskValidator.validate_risk_score(1.5)
        assert result.is_valid is True
        assert result.sanitized_value == 1.0

    def test_risk_score_clamped_low(self):
        """Risk score < 0.0 should be clamped."""
        result = RiskValidator.validate_risk_score(-0.5)
        assert result.is_valid is True
        assert result.sanitized_value == 0.0

    def test_none_risk_score(self):
        """None risk score should fail."""
        result = RiskValidator.validate_risk_score(None)
        assert result.is_valid is False
        assert "cannot be None" in result.error_message

    def test_string_risk_score_converted(self):
        """String risk score should be converted."""
        result = RiskValidator.validate_risk_score("0.75")
        assert result.is_valid is True
        assert result.sanitized_value == 0.75

    def test_valid_flood_depth(self):
        """Valid flood depth should pass."""
        result = RiskValidator.validate_flood_depth(0.5)
        assert result.is_valid is True
        assert result.sanitized_value == 0.5

    def test_negative_flood_depth(self):
        """Negative flood depth should fail."""
        result = RiskValidator.validate_flood_depth(-0.5)
        assert result.is_valid is False
        assert "cannot be negative" in result.error_message

    def test_excessive_flood_depth_warning(self):
        """Excessive flood depth should still pass but trigger warning."""
        result = RiskValidator.validate_flood_depth(15.0)
        # Should still be valid (just logged warning)
        assert result.is_valid is True


class TestReportValidator:
    """Tests for report validation."""

    def test_valid_scout_report(self):
        """Valid scout report should pass."""
        report = {
            'location': 'Nangka',
            'severity': 0.8
        }
        result = ReportValidator.validate_scout_report(report)
        assert result.is_valid is True

    def test_scout_report_missing_fields(self):
        """Report missing required fields should fail."""
        report = {
            'location': 'Nangka'
            # Missing 'severity'
        }
        result = ReportValidator.validate_scout_report(report)
        assert result.is_valid is False
        assert "Missing required fields" in result.error_message

    def test_scout_report_extreme_severity_clamped(self):
        """Report with extreme severity should be clamped, not rejected."""
        report = {
            'location': 'Nangka',
            'severity': 1.5  # Gets clamped to 1.0
        }
        result = ReportValidator.validate_scout_report(report)
        # Validation clamps values to valid range rather than rejecting
        assert result.is_valid is True

    def test_scout_report_with_coordinates(self):
        """Report with coordinates should validate them."""
        report = {
            'location': 'Nangka',
            'severity': 0.8,
            'coordinates': {'lat': 14.65, 'lon': 121.10}
        }
        result = ReportValidator.validate_scout_report(report)
        assert result.is_valid is True

    def test_scout_report_with_invalid_coordinates(self):
        """Report with invalid coordinates should fail."""
        report = {
            'location': 'Nangka',
            'severity': 0.8,
            'coordinates': {'lat': 100.0, 'lon': 121.10}  # Invalid lat
        }
        result = ReportValidator.validate_scout_report(report)
        assert result.is_valid is False

    def test_non_dict_report(self):
        """Non-dict report should fail."""
        result = ReportValidator.validate_scout_report("not a dict")
        assert result.is_valid is False
        assert "must be dict" in result.error_message


class TestTypeValidator:
    """Tests for general type validation."""

    def test_valid_string(self):
        """Valid string should pass."""
        result = TypeValidator.validate_string("test", "field")
        assert result.is_valid is True
        assert result.sanitized_value == "test"

    def test_string_too_short(self):
        """String too short should fail."""
        result = TypeValidator.validate_string("", "field", min_length=1)
        assert result.is_valid is False
        assert "too short" in result.error_message

    def test_string_truncated(self):
        """Long string should be truncated."""
        long_string = "a" * 100
        result = TypeValidator.validate_string(long_string, "field", max_length=10)
        assert result.is_valid is True
        assert len(result.sanitized_value) == 10

    def test_none_string(self):
        """None string should fail by default."""
        result = TypeValidator.validate_string(None, "field")
        assert result.is_valid is False
        assert "cannot be None" in result.error_message

    def test_none_string_allowed(self):
        """None string should pass when allowed."""
        result = TypeValidator.validate_string(None, "field", allow_none=True)
        assert result.is_valid is True
        assert result.sanitized_value is None

    def test_valid_positive_number(self):
        """Valid positive number should pass."""
        result = TypeValidator.validate_positive_number(5.0, "field")
        assert result.is_valid is True
        assert result.sanitized_value == 5.0

    def test_negative_number(self):
        """Negative number should fail."""
        result = TypeValidator.validate_positive_number(-5.0, "field")
        assert result.is_valid is False
        assert "non-negative" in result.error_message

    def test_zero_when_not_allowed(self):
        """Zero should fail when allow_zero=False."""
        result = TypeValidator.validate_positive_number(
            0.0, "field", allow_zero=False
        )
        assert result.is_valid is False
        assert "must be positive" in result.error_message


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_validate_coordinates_convenience(self):
        """Convenience function should work correctly."""
        is_valid, error, coords = validate_coordinates(14.65, 121.10)
        assert is_valid is True
        assert error is None
        assert coords == (14.65, 121.10)

    def test_validate_risk_score_convenience(self):
        """Convenience function should work correctly."""
        is_valid, value = validate_risk_score(0.5)
        assert is_valid is True
        assert value == 0.5

    def test_validate_scout_report_convenience(self):
        """Convenience function should work correctly."""
        report = {'location': 'Test', 'severity': 0.5}
        is_valid, error = validate_scout_report(report)
        assert is_valid is True
        assert error is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
