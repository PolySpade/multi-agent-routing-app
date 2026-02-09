"""
SQLAlchemy models for flood data persistence.

Tables:
- flood_data_collections: Main collection runs
- river_levels: Individual river station readings
- weather_data: Weather conditions from OpenWeatherMap
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from uuid import uuid4

from app.database.connection import Base


class FloodDataCollection(Base):
    """
    Main table tracking each flood data collection run.

    Represents a single execution of the FloodDataScheduler,
    containing metadata about the collection process.
    """

    __tablename__ = "flood_data_collections"

    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )

    # Collection metadata
    collected_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True
    )
    data_source = Column(
        String(20),
        nullable=False,
        default="real",
        comment="Source: 'real' or 'simulated'"
    )
    success = Column(Boolean, nullable=False, default=True)
    duration_seconds = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)

    # Statistics
    river_stations_count = Column(Integer, nullable=True, default=0)
    weather_data_available = Column(Boolean, nullable=False, default=False)

    # Relationships
    river_levels = relationship(
        "RiverLevel",
        back_populates="collection",
        cascade="all, delete-orphan"
    )
    weather_data = relationship(
        "WeatherData",
        back_populates="collection",
        cascade="all, delete-orphan",
        uselist=False  # One-to-one relationship
    )

    # Indexes for common queries
    __table_args__ = (
        Index("idx_collected_at_desc", collected_at.desc()),
        Index("idx_success_collected_at", success, collected_at),
    )

    def __repr__(self):
        return (
            f"<FloodDataCollection(id={self.id}, "
            f"collected_at={self.collected_at}, "
            f"success={self.success})>"
        )


class RiverLevel(Base):
    """
    Individual river station water level readings.

    Stores real-time water levels from PAGASA river monitoring stations.
    """

    __tablename__ = "river_levels"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to collection
    collection_id = Column(
        UUID(as_uuid=True),
        ForeignKey("flood_data_collections.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Station information
    station_name = Column(String(100), nullable=False, index=True)
    station_id = Column(String(50), nullable=True)

    # Water level data
    water_level = Column(
        Float,
        nullable=False,
        comment="Water level in meters"
    )
    risk_level = Column(
        String(20),
        nullable=False,
        comment="NORMAL, ALERT, ALARM, or CRITICAL"
    )

    # Threshold levels (from PAGASA)
    alert_level = Column(Float, nullable=True, comment="Alert threshold in meters")
    alarm_level = Column(Float, nullable=True, comment="Alarm threshold in meters")
    critical_level = Column(
        Float,
        nullable=True,
        comment="Critical threshold in meters"
    )

    # Timestamp
    recorded_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Additional metadata
    data_source = Column(
        String(50),
        nullable=True,
        comment="PAGASA station or simulated"
    )

    # Relationships
    collection = relationship("FloodDataCollection", back_populates="river_levels")

    # Indexes for efficient queries
    __table_args__ = (
        Index("idx_station_recorded_at", station_name, recorded_at.desc()),
        Index("idx_risk_level", risk_level),
        Index("idx_collection_station", collection_id, station_name),
    )

    def __repr__(self):
        return (
            f"<RiverLevel(station={self.station_name}, "
            f"level={self.water_level}m, "
            f"risk={self.risk_level})>"
        )


class WeatherData(Base):
    """
    Weather conditions from OpenWeatherMap API.

    Stores rainfall, temperature, and humidity data for flood prediction.
    """

    __tablename__ = "weather_data"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to collection (one-to-one)
    collection_id = Column(
        UUID(as_uuid=True),
        ForeignKey("flood_data_collections.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    # Rainfall data
    rainfall_1h = Column(
        Float,
        nullable=True,
        comment="Rainfall in last hour (mm)"
    )
    rainfall_3h = Column(
        Float,
        nullable=True,
        comment="Rainfall in last 3 hours (mm)"
    )
    rainfall_24h_forecast = Column(
        Float,
        nullable=True,
        comment="24-hour rainfall forecast (mm)"
    )

    # Rainfall intensity classification
    intensity = Column(
        String(20),
        nullable=True,
        comment="Light, Moderate, Heavy, or Intense"
    )
    intensity_category = Column(
        String(50),
        nullable=True,
        comment="PAGASA classification"
    )

    # Temperature and humidity
    temperature = Column(Float, nullable=True, comment="Temperature in Celsius")
    humidity = Column(Float, nullable=True, comment="Humidity percentage")
    pressure = Column(Float, nullable=True, comment="Atmospheric pressure (hPa)")

    # Weather conditions
    weather_main = Column(String(50), nullable=True, comment="Main weather condition")
    weather_description = Column(
        String(100),
        nullable=True,
        comment="Detailed description"
    )

    # Wind data
    wind_speed = Column(Float, nullable=True, comment="Wind speed (m/s)")
    wind_direction = Column(Float, nullable=True, comment="Wind direction (degrees)")

    # Location
    location_name = Column(
        String(100),
        nullable=True,
        default="Marikina City",
        comment="Location name"
    )
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Timestamp
    recorded_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Data source
    data_source = Column(
        String(50),
        nullable=True,
        default="OpenWeatherMap",
        comment="API source"
    )

    # Relationships
    collection = relationship("FloodDataCollection", back_populates="weather_data")

    # Indexes
    __table_args__ = (
        Index("idx_recorded_at", recorded_at.desc()),
        Index("idx_intensity", intensity),
    )

    def __repr__(self):
        return (
            f"<WeatherData(rainfall_1h={self.rainfall_1h}mm, "
            f"intensity={self.intensity}, "
            f"temp={self.temperature}°C)>"
        )
