"""
SQLAlchemy models for MAS-FRO data persistence.

Tables:
- flood_data_collections: Main collection runs
- river_levels: Individual river station readings
- weather_data: Weather conditions from OpenWeatherMap
- evacuation_centers: Evacuation center reference data
- evacuation_occupancy_log: Occupancy change history
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


class EvacuationCenter(Base):
    """
    Evacuation center reference data.

    Stores static information about evacuation centers in Marikina City,
    seeded from CSV on first startup. Current occupancy is stored directly
    on this table for fast reads.
    """

    __tablename__ = "evacuation_centers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), unique=True, nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    capacity = Column(Integer, nullable=False, default=0)
    current_occupancy = Column(Integer, nullable=False, default=0)
    type = Column(String(50), nullable=True)
    status = Column(String(20), nullable=True)
    suitability = Column(String(200), nullable=True)
    barangay = Column(String(100), nullable=True, index=True)
    operator = Column(String(200), nullable=True)
    contact = Column(String(200), nullable=True)
    facilities = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    occupancy_logs = relationship(
        "EvacuationOccupancyLog",
        back_populates="center",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_center_status", status),
    )

    def __repr__(self):
        return (
            f"<EvacuationCenter(name={self.name}, "
            f"occupancy={self.current_occupancy}/{self.capacity}, "
            f"status={self.status})>"
        )


class EvacuationOccupancyLog(Base):
    """
    Append-only log of occupancy changes for evacuation centers.

    Tracks every occupancy update for audit and historical analysis.
    """

    __tablename__ = "evacuation_occupancy_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    center_id = Column(
        Integer,
        ForeignKey("evacuation_centers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    occupancy = Column(Integer, nullable=False)
    event_type = Column(
        String(30),
        nullable=False,
        comment="evacuees_added, manual_update, reset"
    )
    recorded_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    center = relationship("EvacuationCenter", back_populates="occupancy_logs")

    __table_args__ = (
        Index("idx_occupancy_center_recorded", center_id, recorded_at.desc()),
    )

    def __repr__(self):
        return (
            f"<EvacuationOccupancyLog(center_id={self.center_id}, "
            f"occupancy={self.occupancy}, "
            f"event_type={self.event_type})>"
        )
