"""
Database repository for flood data and evacuation center operations.

Provides CRUD operations for flood data collections, river levels, weather data,
and evacuation center management with persistent occupancy tracking.
"""

from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, func
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path

# pandas imported lazily to reduce startup memory

from app.database.models import (
    FloodDataCollection, RiverLevel, WeatherData,
    EvacuationCenter, EvacuationOccupancyLog,
)
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


class EvacuationRepository:
    """Repository for managing evacuation centers in the database."""

    def __init__(self, db: Session):
        self.db = db

    def seed_from_csv(self, csv_path: Path) -> int:
        """
        Bulk-insert evacuation centers from CSV if the table is empty.

        Returns:
            Number of centers inserted (0 if table was already populated).
        """
        import pandas as pd
        existing = self.db.query(func.count(EvacuationCenter.id)).scalar()
        if existing > 0:
            logger.info(f"Evacuation centers table already has {existing} rows, skipping seed")
            return 0

        try:
            df = pd.read_csv(csv_path)
            # Drop duplicate names (CSV has 5 pairs with same name, different coords)
            dupes_before = len(df)
            df = df.drop_duplicates(subset="name", keep="first")
            if len(df) < dupes_before:
                logger.info(f"Dropped {dupes_before - len(df)} duplicate center names from CSV")

            centers = []
            for _, row in df.iterrows():
                lat = row.get("latitude")
                lon = row.get("longitude")
                if pd.isna(lat) or pd.isna(lon):
                    continue

                raw_cap = row.get("capacity")
                try:
                    capacity = int(raw_cap) if pd.notna(raw_cap) else 0
                except (ValueError, TypeError, OverflowError):
                    capacity = 0

                centers.append(EvacuationCenter(
                    name=str(row["name"]).strip() if pd.notna(row.get("name")) else "Unknown",
                    latitude=float(lat),
                    longitude=float(lon),
                    capacity=capacity,
                    current_occupancy=0,
                    type=str(row["type"]).strip() if pd.notna(row.get("type")) else None,
                    status=str(row["status"]).strip() if pd.notna(row.get("status")) else None,
                    suitability=str(row["suitability"]).strip() if pd.notna(row.get("suitability")) else None,
                    barangay=str(row["barangay"]).strip() if pd.notna(row.get("barangay")) else None,
                    operator=str(row["operator"]).strip() if pd.notna(row.get("operator")) else None,
                ))

            self.db.add_all(centers)
            self.db.commit()
            logger.info(f"Seeded {len(centers)} evacuation centers from {csv_path}")
            return len(centers)

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error seeding evacuation centers: {e}")
            raise

    def get_all_centers(self, status_filter: Optional[str] = None) -> List[EvacuationCenter]:
        """Get all active evacuation centers, optionally filtered by status."""
        query = self.db.query(EvacuationCenter).filter(EvacuationCenter.is_active == True)
        if status_filter:
            query = query.filter(EvacuationCenter.status == status_filter)
        return query.order_by(EvacuationCenter.name).all()

    def get_available_centers(self) -> List[EvacuationCenter]:
        """Get centers where current_occupancy < capacity (and capacity > 0)."""
        return (
            self.db.query(EvacuationCenter)
            .filter(
                EvacuationCenter.is_active == True,
                EvacuationCenter.capacity > 0,
                EvacuationCenter.current_occupancy < EvacuationCenter.capacity,
            )
            .order_by(EvacuationCenter.name)
            .all()
        )

    def get_center_by_name(self, name: str) -> Optional[EvacuationCenter]:
        """Get a single center by exact name."""
        return (
            self.db.query(EvacuationCenter)
            .filter(EvacuationCenter.name == name)
            .first()
        )

    def get_centers_as_dataframe(self):
        """
        Return all active centers as a pandas DataFrame.

        Compatible with RoutingAgent's existing evacuation center logic.
        """
        import pandas as pd
        centers = self.get_all_centers()
        if not centers:
            return pd.DataFrame(columns=["name", "latitude", "longitude", "capacity", "type"])

        rows = [
            {
                "name": c.name,
                "latitude": c.latitude,
                "longitude": c.longitude,
                "capacity": c.capacity,
                "current_occupancy": c.current_occupancy,
                "type": c.type or "unknown",
                "status": c.status,
                "barangay": c.barangay,
            }
            for c in centers
        ]
        return pd.DataFrame(rows)

    def update_occupancy(
        self, center_name: str, occupancy: int, event_type: str = "manual_update"
    ) -> bool:
        """
        Set a center's occupancy to an absolute value and log the change.

        Returns True on success, False if center not found.
        """
        center = self.get_center_by_name(center_name)
        if not center:
            return False

        occupancy = max(0, min(occupancy, center.capacity) if center.capacity > 0 else occupancy)
        center.current_occupancy = occupancy
        center.updated_at = datetime.utcnow()

        self.db.add(EvacuationOccupancyLog(
            center_id=center.id,
            occupancy=occupancy,
            event_type=event_type,
        ))

        self.db.commit()
        return True

    def add_evacuees(self, center_name: str, count: int) -> Dict[str, Any]:
        """
        Add *count* evacuees to a center. Returns result dict.
        """
        center = self.get_center_by_name(center_name)
        if not center:
            return {"success": False, "message": f"Center '{center_name}' not found"}

        available = (center.capacity - center.current_occupancy) if center.capacity > 0 else 0
        if count > available and center.capacity > 0:
            return {
                "success": False,
                "message": f"Not enough space. Requested: {count}, Available: {available}",
            }

        new_occ = center.current_occupancy + count
        if center.capacity > 0:
            new_occ = min(new_occ, center.capacity)

        center.current_occupancy = new_occ
        center.updated_at = datetime.utcnow()

        self.db.add(EvacuationOccupancyLog(
            center_id=center.id,
            occupancy=new_occ,
            event_type="evacuees_added",
        ))
        self.db.commit()

        return {
            "success": True,
            "message": f"Added {count} evacuees to {center_name}",
            "current_occupancy": new_occ,
            "capacity": center.capacity,
        }

    def reset_all_occupancy(self) -> None:
        """Reset occupancy to 0 for all centers and log a reset event."""
        centers = self.db.query(EvacuationCenter).all()
        now = datetime.utcnow()
        for c in centers:
            if c.current_occupancy > 0:
                c.current_occupancy = 0
                c.updated_at = now
                self.db.add(EvacuationOccupancyLog(
                    center_id=c.id,
                    occupancy=0,
                    event_type="reset",
                ))
        self.db.commit()
        logger.info("Reset all evacuation center occupancy to 0")

    def get_statistics(self) -> Dict[str, Any]:
        """Get aggregate statistics for all active centers."""
        centers = self.get_all_centers()

        total_capacity = sum(c.capacity for c in centers)
        total_occupancy = sum(c.current_occupancy for c in centers)
        total_available = total_capacity - total_occupancy

        status_counts = {"available": 0, "limited": 0, "full": 0}
        for c in centers:
            ratio = c.current_occupancy / c.capacity if c.capacity > 0 else 0
            if ratio >= 0.95:
                status_counts["full"] += 1
            elif ratio >= 0.70:
                status_counts["limited"] += 1
            else:
                status_counts["available"] += 1

        return {
            "total_centers": len(centers),
            "total_capacity": total_capacity,
            "total_occupancy": total_occupancy,
            "total_available_slots": total_available,
            "overall_occupancy_percentage": round(
                (total_occupancy / total_capacity * 100) if total_capacity > 0 else 0, 1
            ),
            "status_counts": status_counts,
            "last_update": datetime.utcnow().isoformat(),
        }

