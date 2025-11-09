"""
Database repository for flood data operations.

Provides CRUD operations for flood data collections, river levels, and weather data.
"""

from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, func
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID

from app.database.models import FloodDataCollection, RiverLevel, WeatherData
import logging

logger = logging.getLogger(__name__)


class FloodDataRepository:
    """Repository for managing flood data in the database."""

    def __init__(self, db: Session):
        """
        Initialize repository with database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create_collection(
        self,
        river_levels_data: List[Dict[str, Any]],
        weather_data_dict: Optional[Dict[str, Any]] = None,
        data_source: str = "real",
        duration_seconds: Optional[float] = None,
    ) -> FloodDataCollection:
        """
        Create a new flood data collection with river levels and weather data.

        Args:
            river_levels_data: List of river level dictionaries
            weather_data_dict: Weather data dictionary (optional)
            data_source: Data source ('real' or 'simulated')
            duration_seconds: Collection duration in seconds

        Returns:
            Created FloodDataCollection instance
        """
        try:
            # Create main collection record
            collection = FloodDataCollection(
                data_source=data_source,
                success=True,
                duration_seconds=duration_seconds,
                river_stations_count=len(river_levels_data),
                weather_data_available=weather_data_dict is not None,
            )

            self.db.add(collection)
            self.db.flush()  # Get the collection ID

            # Create river level records
            for river_data in river_levels_data:
                river_level = RiverLevel(
                    collection_id=collection.id,
                    station_name=river_data.get("station_name"),
                    station_id=river_data.get("station_id"),
                    water_level=river_data.get("water_level", 0.0),
                    risk_level=river_data.get("risk_level", "NORMAL"),
                    alert_level=river_data.get("alert_level"),
                    alarm_level=river_data.get("alarm_level"),
                    critical_level=river_data.get("critical_level"),
                    data_source=river_data.get("data_source", "PAGASA"),
                )
                self.db.add(river_level)

            # Create weather data record if provided
            if weather_data_dict:
                weather = WeatherData(
                    collection_id=collection.id,
                    rainfall_1h=weather_data_dict.get("rainfall_1h"),
                    rainfall_3h=weather_data_dict.get("rainfall_3h"),
                    rainfall_24h_forecast=weather_data_dict.get("rainfall_24h_forecast"),
                    intensity=weather_data_dict.get("intensity"),
                    intensity_category=weather_data_dict.get("intensity_category"),
                    temperature=weather_data_dict.get("temperature"),
                    humidity=weather_data_dict.get("humidity"),
                    pressure=weather_data_dict.get("pressure"),
                    weather_main=weather_data_dict.get("weather_main"),
                    weather_description=weather_data_dict.get("weather_description"),
                    wind_speed=weather_data_dict.get("wind_speed"),
                    wind_direction=weather_data_dict.get("wind_direction"),
                    location_name=weather_data_dict.get("location_name", "Marikina City"),
                    latitude=weather_data_dict.get("latitude"),
                    longitude=weather_data_dict.get("longitude"),
                    data_source=weather_data_dict.get("data_source", "OpenWeatherMap"),
                )
                self.db.add(weather)

            self.db.commit()
            self.db.refresh(collection)

            logger.info(
                f"Saved flood data collection {collection.id} with "
                f"{len(river_levels_data)} river stations"
            )

            return collection

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating flood data collection: {e}")
            raise

    def create_failed_collection(
        self,
        error_message: str,
        data_source: str = "real",
    ) -> FloodDataCollection:
        """
        Create a failed collection record for tracking errors.

        Args:
            error_message: Error description
            data_source: Data source that failed

        Returns:
            Created FloodDataCollection instance
        """
        try:
            collection = FloodDataCollection(
                data_source=data_source,
                success=False,
                error_message=error_message,
                river_stations_count=0,
                weather_data_available=False,
            )

            self.db.add(collection)
            self.db.commit()
            self.db.refresh(collection)

            logger.warning(f"Saved failed collection {collection.id}: {error_message}")

            return collection

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating failed collection: {e}")
            raise

    def get_latest_collection(self) -> Optional[FloodDataCollection]:
        """
        Get the most recent flood data collection.

        Returns:
            Latest FloodDataCollection or None
        """
        return (
            self.db.query(FloodDataCollection)
            .order_by(desc(FloodDataCollection.collected_at))
            .first()
        )

    def get_collection_by_id(self, collection_id: UUID) -> Optional[FloodDataCollection]:
        """
        Get a specific flood data collection by ID.

        Args:
            collection_id: Collection UUID

        Returns:
            FloodDataCollection or None
        """
        return (
            self.db.query(FloodDataCollection)
            .filter(FloodDataCollection.id == collection_id)
            .first()
        )

    def get_collections_in_range(
        self,
        start_time: datetime,
        end_time: datetime,
        success_only: bool = True,
    ) -> List[FloodDataCollection]:
        """
        Get all collections within a time range.

        Args:
            start_time: Range start datetime
            end_time: Range end datetime
            success_only: Only return successful collections

        Returns:
            List of FloodDataCollection instances
        """
        query = self.db.query(FloodDataCollection).filter(
            and_(
                FloodDataCollection.collected_at >= start_time,
                FloodDataCollection.collected_at <= end_time,
            )
        )

        if success_only:
            query = query.filter(FloodDataCollection.success == True)

        return query.order_by(desc(FloodDataCollection.collected_at)).all()

    def get_river_level_history(
        self,
        station_name: str,
        hours: int = 24,
    ) -> List[RiverLevel]:
        """
        Get historical river levels for a specific station.

        Args:
            station_name: Name of the river station
            hours: Number of hours of history (default 24)

        Returns:
            List of RiverLevel instances
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        return (
            self.db.query(RiverLevel)
            .filter(
                and_(
                    RiverLevel.station_name == station_name,
                    RiverLevel.recorded_at >= cutoff_time,
                )
            )
            .order_by(desc(RiverLevel.recorded_at))
            .all()
        )

    def get_weather_history(self, hours: int = 24) -> List[WeatherData]:
        """
        Get historical weather data.

        Args:
            hours: Number of hours of history (default 24)

        Returns:
            List of WeatherData instances
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        return (
            self.db.query(WeatherData)
            .filter(WeatherData.recorded_at >= cutoff_time)
            .order_by(desc(WeatherData.recorded_at))
            .all()
        )

    def get_critical_alerts_history(self, hours: int = 24) -> List[RiverLevel]:
        """
        Get history of critical water level alerts.

        Args:
            hours: Number of hours of history (default 24)

        Returns:
            List of RiverLevel instances with ALARM or CRITICAL status
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        return (
            self.db.query(RiverLevel)
            .filter(
                and_(
                    RiverLevel.recorded_at >= cutoff_time,
                    RiverLevel.risk_level.in_(["ALARM", "CRITICAL"]),
                )
            )
            .order_by(desc(RiverLevel.recorded_at))
            .all()
        )

    def get_statistics(self, days: int = 7) -> Dict[str, Any]:
        """
        Get summary statistics for the specified time period.

        Args:
            days: Number of days for statistics (default 7)

        Returns:
            Dictionary with statistics
        """
        cutoff_time = datetime.utcnow() - timedelta(days=days)

        # Count total collections
        total_collections = (
            self.db.query(func.count(FloodDataCollection.id))
            .filter(FloodDataCollection.collected_at >= cutoff_time)
            .scalar()
        )

        # Count successful collections
        successful_collections = (
            self.db.query(func.count(FloodDataCollection.id))
            .filter(
                and_(
                    FloodDataCollection.collected_at >= cutoff_time,
                    FloodDataCollection.success == True,
                )
            )
            .scalar()
        )

        # Count total data points
        total_river_readings = (
            self.db.query(func.count(RiverLevel.id))
            .join(FloodDataCollection)
            .filter(FloodDataCollection.collected_at >= cutoff_time)
            .scalar()
        )

        # Count critical alerts
        critical_alerts = (
            self.db.query(func.count(RiverLevel.id))
            .join(FloodDataCollection)
            .filter(
                and_(
                    FloodDataCollection.collected_at >= cutoff_time,
                    RiverLevel.risk_level.in_(["ALARM", "CRITICAL"]),
                )
            )
            .scalar()
        )

        # Calculate success rate
        success_rate = (
            (successful_collections / total_collections * 100)
            if total_collections > 0
            else 0.0
        )

        return {
            "period_days": days,
            "total_collections": total_collections or 0,
            "successful_collections": successful_collections or 0,
            "failed_collections": (total_collections or 0) - (successful_collections or 0),
            "success_rate_percent": round(success_rate, 2),
            "total_river_readings": total_river_readings or 0,
            "critical_alerts": critical_alerts or 0,
        }

    def cleanup_old_data(self, retention_days: int = 90) -> int:
        """
        Delete data older than retention period.

        Args:
            retention_days: Number of days to retain (default 90)

        Returns:
            Number of collections deleted
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

            deleted_count = (
                self.db.query(FloodDataCollection)
                .filter(FloodDataCollection.collected_at < cutoff_date)
                .delete()
            )

            self.db.commit()

            logger.info(
                f"Cleaned up {deleted_count} collections older than {retention_days} days"
            )

            return deleted_count

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error cleaning up old data: {e}")
            raise
