# filename: app/core/validation.py

"""
Input Validation Utilities for MAS-FRO Agents

This module provides comprehensive input validation functions for all agents.
Ensures coordinate bounds, type checking, range validation, and required fields.

Issue #17: Missing Input Validation Across Agents

Author: MAS-FRO Development Team
Date: January 2026
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation check."""
    is_valid: bool
    error_message: Optional[str] = None
    sanitized_value: Any = None


class CoordinateValidator:
    """Validates geographic coordinates."""

    # Philippines region bounds (with buffer)
    DEFAULT_BOUNDS = {
        "min_lat": 4.0,
        "max_lat": 21.0,
        "min_lon": 116.0,
        "max_lon": 127.0,
    }

    # Marikina City specific bounds (tighter validation)
    MARIKINA_BOUNDS = {
        "min_lat": 14.60,
        "max_lat": 14.70,
        "min_lon": 121.05,
        "max_lon": 121.15,
    }

    @classmethod
    def validate_coordinates(
        cls,
        lat: Any,
        lon: Any,
        bounds: Optional[Dict[str, float]] = None,
        allow_none: bool = False
    ) -> ValidationResult:
        """
        Validate latitude and longitude coordinates.

        Args:
            lat: Latitude value
            lon: Longitude value
            bounds: Optional custom bounds dict with min_lat, max_lat, min_lon, max_lon
            allow_none: If True, None values are considered valid

        Returns:
            ValidationResult with is_valid, error_message, and sanitized coordinates
        """
        if lat is None or lon is None:
            if allow_none:
                return ValidationResult(is_valid=True, sanitized_value=(None, None))
            return ValidationResult(
                is_valid=False,
                error_message="Coordinates cannot be None"
            )

        # Type conversion
        try:
            lat = float(lat)
            lon = float(lon)
        except (TypeError, ValueError) as e:
            return ValidationResult(
                is_valid=False,
                error_message=f"Invalid coordinate types: {e}"
            )

        # Global bounds check
        if not (-90 <= lat <= 90):
            return ValidationResult(
                is_valid=False,
                error_message=f"Latitude {lat} out of valid range [-90, 90]"
            )

        if not (-180 <= lon <= 180):
            return ValidationResult(
                is_valid=False,
                error_message=f"Longitude {lon} out of valid range [-180, 180]"
            )

        # Regional bounds check
        if bounds is None:
            bounds = cls.DEFAULT_BOUNDS

        if not (bounds["min_lat"] <= lat <= bounds["max_lat"]):
            logger.warning(
                f"Latitude {lat} outside expected region "
                f"[{bounds['min_lat']}, {bounds['max_lat']}]"
            )

        if not (bounds["min_lon"] <= lon <= bounds["max_lon"]):
            logger.warning(
                f"Longitude {lon} outside expected region "
                f"[{bounds['min_lon']}, {bounds['max_lon']}]"
            )

        return ValidationResult(
            is_valid=True,
            sanitized_value=(lat, lon)
        )

    @classmethod
    def validate_coordinate_tuple(
        cls,
        coords: Any,
        bounds: Optional[Dict[str, float]] = None
    ) -> ValidationResult:
        """
        Validate a coordinate tuple (lat, lon).

        Args:
            coords: Tuple or list of (latitude, longitude)
            bounds: Optional custom bounds

        Returns:
            ValidationResult
        """
        if not coords:
            return ValidationResult(
                is_valid=False,
                error_message="Coordinates cannot be empty"
            )

        if not isinstance(coords, (tuple, list)) or len(coords) != 2:
            return ValidationResult(
                is_valid=False,
                error_message=f"Coordinates must be (lat, lon) tuple, got {type(coords)}"
            )

        return cls.validate_coordinates(coords[0], coords[1], bounds)


class RiskValidator:
    """Validates risk-related values."""

    @classmethod
    def validate_risk_score(
        cls,
        value: Any,
        field_name: str = "risk_score"
    ) -> ValidationResult:
        """
        Validate a risk score is in [0, 1] range.

        Args:
            value: Risk score value
            field_name: Name of field for error message

        Returns:
            ValidationResult with clamped value if needed
        """
        if value is None:
            return ValidationResult(
                is_valid=False,
                error_message=f"{field_name} cannot be None"
            )

        try:
            value = float(value)
        except (TypeError, ValueError):
            return ValidationResult(
                is_valid=False,
                error_message=f"{field_name} must be numeric, got {type(value)}"
            )

        # Clamp to valid range
        sanitized = max(0.0, min(1.0, value))

        if value != sanitized:
            logger.warning(
                f"{field_name} {value} clamped to valid range [0, 1] -> {sanitized}"
            )

        return ValidationResult(
            is_valid=True,
            sanitized_value=sanitized
        )

    @classmethod
    def validate_flood_depth(
        cls,
        depth: Any,
        max_reasonable_depth: float = 10.0
    ) -> ValidationResult:
        """
        Validate flood depth value.

        Args:
            depth: Flood depth in meters
            max_reasonable_depth: Maximum reasonable depth (default 10m)

        Returns:
            ValidationResult
        """
        if depth is None:
            return ValidationResult(
                is_valid=False,
                error_message="Flood depth cannot be None"
            )

        try:
            depth = float(depth)
        except (TypeError, ValueError):
            return ValidationResult(
                is_valid=False,
                error_message=f"Flood depth must be numeric, got {type(depth)}"
            )

        if depth < 0:
            return ValidationResult(
                is_valid=False,
                error_message=f"Flood depth cannot be negative: {depth}"
            )

        if depth > max_reasonable_depth:
            logger.warning(
                f"Flood depth {depth}m exceeds reasonable maximum {max_reasonable_depth}m"
            )

        return ValidationResult(
            is_valid=True,
            sanitized_value=depth
        )


class ReportValidator:
    """Validates scout/flood reports."""

    REQUIRED_SCOUT_FIELDS = ["location", "severity"]
    REQUIRED_FLOOD_FIELDS = ["location", "flood_depth"]

    @classmethod
    def validate_scout_report(cls, report: Any) -> ValidationResult:
        """
        Validate a scout report dictionary.

        Args:
            report: Scout report dictionary

        Returns:
            ValidationResult
        """
        if not isinstance(report, dict):
            return ValidationResult(
                is_valid=False,
                error_message=f"Report must be dict, got {type(report)}"
            )

        # Check required fields
        missing = [f for f in cls.REQUIRED_SCOUT_FIELDS if f not in report]
        if missing:
            return ValidationResult(
                is_valid=False,
                error_message=f"Missing required fields: {missing}"
            )

        # Validate severity
        severity_result = RiskValidator.validate_risk_score(
            report.get("severity"), "severity"
        )
        if not severity_result.is_valid:
            return severity_result

        # Validate confidence if present
        if "confidence" in report:
            conf_result = RiskValidator.validate_risk_score(
                report.get("confidence"), "confidence"
            )
            if not conf_result.is_valid:
                return conf_result

        # Validate coordinates if present
        if "coordinates" in report:
            coords = report["coordinates"]
            if isinstance(coords, dict):
                coord_result = CoordinateValidator.validate_coordinates(
                    coords.get("lat"), coords.get("lon")
                )
            else:
                coord_result = CoordinateValidator.validate_coordinate_tuple(coords)

            if not coord_result.is_valid:
                return coord_result

        return ValidationResult(is_valid=True, sanitized_value=report)

    @classmethod
    def validate_flood_data(cls, data: Any) -> ValidationResult:
        """
        Validate flood data dictionary.

        Args:
            data: Flood data dictionary

        Returns:
            ValidationResult
        """
        if not isinstance(data, dict):
            return ValidationResult(
                is_valid=False,
                error_message=f"Flood data must be dict, got {type(data)}"
            )

        # Check required fields
        missing = [f for f in cls.REQUIRED_FLOOD_FIELDS if f not in data]
        if missing:
            return ValidationResult(
                is_valid=False,
                error_message=f"Missing required fields: {missing}"
            )

        # Validate flood depth
        depth_result = RiskValidator.validate_flood_depth(data.get("flood_depth"))
        if not depth_result.is_valid:
            return depth_result

        return ValidationResult(is_valid=True, sanitized_value=data)


class TypeValidator:
    """General type validation utilities."""

    @classmethod
    def validate_string(
        cls,
        value: Any,
        field_name: str,
        min_length: int = 0,
        max_length: int = 10000,
        allow_none: bool = False
    ) -> ValidationResult:
        """Validate a string value."""
        if value is None:
            if allow_none:
                return ValidationResult(is_valid=True, sanitized_value=None)
            return ValidationResult(
                is_valid=False,
                error_message=f"{field_name} cannot be None"
            )

        if not isinstance(value, str):
            try:
                value = str(value)
            except Exception:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"{field_name} must be string, got {type(value)}"
                )

        if len(value) < min_length:
            return ValidationResult(
                is_valid=False,
                error_message=f"{field_name} too short: {len(value)} < {min_length}"
            )

        if len(value) > max_length:
            logger.warning(f"{field_name} truncated from {len(value)} to {max_length}")
            value = value[:max_length]

        return ValidationResult(is_valid=True, sanitized_value=value)

    @classmethod
    def validate_positive_number(
        cls,
        value: Any,
        field_name: str,
        allow_zero: bool = True
    ) -> ValidationResult:
        """Validate a positive number."""
        if value is None:
            return ValidationResult(
                is_valid=False,
                error_message=f"{field_name} cannot be None"
            )

        try:
            value = float(value)
        except (TypeError, ValueError):
            return ValidationResult(
                is_valid=False,
                error_message=f"{field_name} must be numeric, got {type(value)}"
            )

        if allow_zero and value < 0:
            return ValidationResult(
                is_valid=False,
                error_message=f"{field_name} must be non-negative, got {value}"
            )

        if not allow_zero and value <= 0:
            return ValidationResult(
                is_valid=False,
                error_message=f"{field_name} must be positive, got {value}"
            )

        return ValidationResult(is_valid=True, sanitized_value=value)


# Convenience functions
def validate_coordinates(lat: Any, lon: Any) -> Tuple[bool, Optional[str], Optional[Tuple[float, float]]]:
    """
    Validate coordinates (convenience function).

    Returns:
        Tuple of (is_valid, error_message, (lat, lon) or None)
    """
    result = CoordinateValidator.validate_coordinates(lat, lon)
    return result.is_valid, result.error_message, result.sanitized_value


def validate_risk_score(value: Any) -> Tuple[bool, float]:
    """
    Validate and clamp risk score (convenience function).

    Returns:
        Tuple of (is_valid, clamped_value)
    """
    result = RiskValidator.validate_risk_score(value)
    return result.is_valid, result.sanitized_value if result.is_valid else 0.0


def validate_scout_report(report: Dict) -> Tuple[bool, Optional[str]]:
    """
    Validate scout report (convenience function).

    Returns:
        Tuple of (is_valid, error_message)
    """
    result = ReportValidator.validate_scout_report(report)
    return result.is_valid, result.error_message
