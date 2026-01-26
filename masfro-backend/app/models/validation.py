"""
Data validation models using Pydantic.

Provides comprehensive validation for external data inputs to ensure
data quality and prevent invalid values from entering the system.
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Tuple
from datetime import datetime


class CoordinateInput(BaseModel):
    """
    Validated coordinate input (latitude, longitude).

    Ensures coordinates are within valid WGS84 bounds.
    """
    lat: float = Field(ge=-90, le=90, description="Latitude in decimal degrees (-90 to 90)")
    lon: float = Field(ge=-180, le=180, description="Longitude in decimal degrees (-180 to 180)")

    @model_validator(mode='after')
    def validate_coordinates(self) -> 'CoordinateInput':
        """Ensure coordinates are not exactly at poles or antimeridian."""
        if abs(self.lat) == 90:
            raise ValueError("Latitude cannot be exactly at poles (+90 or -90)")
        if abs(self.lon) == 180:
            raise ValueError("Longitude cannot be exactly at antimeridian (+180 or -180)")
        return self

    def to_tuple(self) -> Tuple[float, float]:
        """Convert to (lat, lon) tuple."""
        return (self.lat, self.lon)


class FloodDataPoint(BaseModel):
    """
    Validated flood data point from external sources.

    Ensures flood data meets quality standards before processing.
    """
    location: str = Field(min_length=1, max_length=200, description="Location name or identifier")
    flood_depth: float = Field(ge=0.0, le=10.0, description="Flood depth in meters (0-10m)")
    timestamp: datetime = Field(description="Timestamp of observation")
    source: str = Field(min_length=1, max_length=100, description="Data source identifier")
    confidence: Optional[float] = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score (0-1)")

    @field_validator('timestamp')
    @classmethod
    def not_future(cls, v: datetime) -> datetime:
        """Ensure timestamp is not in the future."""
        if v > datetime.now():
            raise ValueError("Timestamp cannot be in the future")
        return v

    @field_validator('flood_depth')
    @classmethod
    def validate_depth(cls, v: float) -> float:
        """Validate flood depth is reasonable."""
        if v < 0:
            raise ValueError("Flood depth cannot be negative")
        if v > 10:
            raise ValueError("Flood depth exceeds maximum reasonable value (10m)")
        return v


class ScoutReportInput(BaseModel):
    """
    Validated crowdsourced report from scout agents.

    Ensures scout reports meet minimum quality standards.
    """
    location: CoordinateInput = Field(description="Report location coordinates")
    severity: float = Field(ge=0.0, le=1.0, description="Severity score (0-1)")
    report_type: str = Field(min_length=1, max_length=50, description="Type of report")
    description: Optional[str] = Field(default=None, max_length=500, description="Report description")
    timestamp: datetime = Field(description="Report timestamp")
    source: str = Field(min_length=1, max_length=100, description="Report source")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score (0-1)")

    @field_validator('timestamp')
    @classmethod
    def not_future(cls, v: datetime) -> datetime:
        """Ensure timestamp is not in the future."""
        if v > datetime.now():
            raise ValueError("Report timestamp cannot be in the future")

        # Ensure timestamp is not too old (more than 7 days)
        age_days = (datetime.now() - v).days
        if age_days > 7:
            raise ValueError(f"Report timestamp is too old ({age_days} days)")

        return v

    @field_validator('report_type')
    @classmethod
    def validate_report_type(cls, v: str) -> str:
        """Validate report type against known types."""
        valid_types = ["flooding", "clear", "blocked", "traffic", "hazard", "evacuation"]
        if v.lower() not in valid_types:
            raise ValueError(f"Invalid report type. Must be one of: {', '.join(valid_types)}")
        return v.lower()


class RiskScoreInput(BaseModel):
    """
    Validated risk score input.

    Ensures risk scores are within valid bounds.
    """
    risk_score: float = Field(ge=0.0, le=1.0, description="Risk score (0-1, where 1 is highest risk)")
    confidence: Optional[float] = Field(default=1.0, ge=0.0, le=1.0, description="Confidence in risk score")
    timestamp: datetime = Field(description="Risk assessment timestamp")

    @field_validator('timestamp')
    @classmethod
    def not_future(cls, v: datetime) -> datetime:
        """Ensure timestamp is not in the future."""
        if v > datetime.now():
            raise ValueError("Risk assessment timestamp cannot be in the future")
        return v


class WeatherDataInput(BaseModel):
    """
    Validated weather data input from external APIs.

    Ensures weather data meets quality standards.
    """
    location: str = Field(min_length=1, max_length=200, description="Location identifier")
    temperature: Optional[float] = Field(default=None, ge=-50, le=60, description="Temperature in Celsius")
    humidity: Optional[float] = Field(default=None, ge=0, le=100, description="Humidity percentage")
    rainfall_1h: Optional[float] = Field(default=None, ge=0, le=500, description="Rainfall in last hour (mm)")
    rainfall_24h_forecast: Optional[float] = Field(default=None, ge=0, le=1000, description="24h rainfall forecast (mm)")
    wind_speed: Optional[float] = Field(default=None, ge=0, le=200, description="Wind speed (km/h)")
    timestamp: datetime = Field(description="Weather observation timestamp")

    @field_validator('timestamp')
    @classmethod
    def not_future(cls, v: datetime) -> datetime:
        """Ensure timestamp is not in the future."""
        if v > datetime.now():
            raise ValueError("Weather timestamp cannot be in the future")
        return v

    @field_validator('rainfall_1h')
    @classmethod
    def validate_rainfall_1h(cls, v: Optional[float]) -> Optional[float]:
        """Validate 1-hour rainfall is reasonable."""
        if v is not None and v > 500:
            raise ValueError("1-hour rainfall exceeds reasonable maximum (500mm)")
        return v

    @field_validator('temperature')
    @classmethod
    def validate_temperature(cls, v: Optional[float]) -> Optional[float]:
        """Validate temperature is within reasonable range."""
        if v is not None:
            if v < -50 or v > 60:
                raise ValueError("Temperature outside reasonable range (-50°C to 60°C)")
        return v


class RoutePreferencesInput(BaseModel):
    """
    Validated route preferences from users.

    Ensures user preferences are valid.
    """
    preference_type: str = Field(description="Routing preference")
    risk_tolerance: Optional[float] = Field(default=0.5, ge=0.0, le=1.0, description="Risk tolerance (0-1)")
    max_detour_meters: Optional[int] = Field(default=5000, ge=0, le=50000, description="Maximum detour distance")
    avoid_highways: Optional[bool] = Field(default=False, description="Avoid highways")
    avoid_tolls: Optional[bool] = Field(default=False, description="Avoid toll roads")

    @field_validator('preference_type')
    @classmethod
    def validate_preference(cls, v: str) -> str:
        """Validate preference type against known types."""
        valid_prefs = ["safest", "balanced", "fastest"]
        if v.lower() not in valid_prefs:
            raise ValueError(f"Invalid preference type. Must be one of: {', '.join(valid_prefs)}")
        return v.lower()
