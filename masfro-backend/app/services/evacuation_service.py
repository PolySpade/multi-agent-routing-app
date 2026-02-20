# filename: app/services/evacuation_service.py

"""
Evacuation Center Service for MAS-FRO

Manages evacuation center capacity tracking, occupancy updates, and
availability status. Backed by PostgreSQL for persistent occupancy.

Author: MAS-FRO Development Team
Date: February 2026
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.database.repository import EvacuationRepository

logger = logging.getLogger(__name__)


class EvacuationCenterService:
    """
    Service for managing evacuation center data and capacity.

    Uses PostgreSQL via EvacuationRepository for persistent storage.
    Each public method opens its own DB session so the service is
    safe to use as a long-lived singleton.
    """

    def __init__(self, db_session_factory: Optional[Callable[[], Session]] = None):
        """
        Initialize the evacuation center service.

        Args:
            db_session_factory: Callable returning a new SQLAlchemy Session.
                                Defaults to SessionLocal.
        """
        self._session_factory = db_session_factory or SessionLocal
        logger.info("EvacuationCenterService initialized (DB-backed)")

    def _get_repo(self, db: Session) -> EvacuationRepository:
        return EvacuationRepository(db)

    def seed_from_csv(self, csv_path: Path) -> int:
        """Seed the DB from CSV if table is empty. Returns count inserted."""
        db = self._session_factory()
        try:
            return self._get_repo(db).seed_from_csv(csv_path)
        finally:
            db.close()

    def get_all_centers(self) -> List[Dict[str, Any]]:
        """
        Get all evacuation centers with current status.

        Returns:
            List of center dictionaries with capacity status.
        """
        db = self._session_factory()
        try:
            repo = self._get_repo(db)
            centers = repo.get_all_centers()

            centers_list = []
            for c in centers:
                capacity = c.capacity or 0
                current_occupancy = c.current_occupancy or 0
                occupancy_ratio = current_occupancy / capacity if capacity > 0 else 0

                if occupancy_ratio >= 0.95:
                    status = "full"
                elif occupancy_ratio >= 0.70:
                    status = "limited"
                else:
                    status = "available"

                centers_list.append({
                    "name": c.name,
                    "coordinates": {
                        "lat": c.latitude,
                        "lon": c.longitude,
                    },
                    "location": "",
                    "barangay": c.barangay or "",
                    "capacity": capacity,
                    "current_occupancy": current_occupancy,
                    "available_slots": max(0, capacity - current_occupancy),
                    "occupancy_percentage": round(occupancy_ratio * 100, 1),
                    "status": status,
                    "type": c.type or "unknown",
                    "contact": c.contact or "",
                    "facilities": c.facilities.split(", ") if c.facilities else [],
                })

            status_order = {"available": 0, "limited": 1, "full": 2}
            centers_list.sort(key=lambda x: (status_order[x["status"]], -x["available_slots"]))
            return centers_list
        finally:
            db.close()

    def get_available_centers(self) -> List[Dict[str, Any]]:
        """Get only available evacuation centers (not full)."""
        all_centers = self.get_all_centers()
        return [c for c in all_centers if c["status"] != "full"]

    def get_center_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get specific evacuation center by name."""
        all_centers = self.get_all_centers()
        for center in all_centers:
            if center["name"] == name:
                return center
        return None

    def update_occupancy(self, center_name: str, occupancy: int) -> bool:
        """
        Update occupancy for a specific center.

        Returns:
            True if successful, False otherwise.
        """
        db = self._session_factory()
        try:
            repo = self._get_repo(db)
            return repo.update_occupancy(center_name, occupancy, event_type="manual_update")
        finally:
            db.close()

    def add_evacuees(self, center_name: str, count: int) -> Dict[str, Any]:
        """Add evacuees to a center."""
        db = self._session_factory()
        try:
            repo = self._get_repo(db)
            result = repo.add_evacuees(center_name, count)
            if result["success"]:
                # Re-fetch formatted center dict for response
                result["center"] = self.get_center_by_name(center_name)
            return result
        finally:
            db.close()

    def reset_all_occupancy(self) -> None:
        """Reset occupancy to 0 for all centers."""
        db = self._session_factory()
        try:
            self._get_repo(db).reset_all_occupancy()
        finally:
            db.close()

    def get_statistics(self) -> Dict[str, Any]:
        """Get overall statistics about evacuation centers."""
        db = self._session_factory()
        try:
            return self._get_repo(db).get_statistics()
        finally:
            db.close()

    def get_centers_as_dataframe(self) -> pd.DataFrame:
        """
        Get all centers as a DataFrame (for routing_agent compatibility).
        """
        db = self._session_factory()
        try:
            return self._get_repo(db).get_centers_as_dataframe()
        finally:
            db.close()


# Global instance (singleton pattern)
_evacuation_service_instance: Optional[EvacuationCenterService] = None


def get_evacuation_service() -> EvacuationCenterService:
    """
    Get the global evacuation service instance.

    Returns:
        EvacuationCenterService instance
    """
    global _evacuation_service_instance
    if _evacuation_service_instance is None:
        _evacuation_service_instance = EvacuationCenterService()
    return _evacuation_service_instance
