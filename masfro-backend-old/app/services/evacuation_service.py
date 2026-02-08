# filename: app/services/evacuation_service.py

"""
Evacuation Center Service for MAS-FRO

Manages evacuation center capacity tracking, occupancy updates, and
availability status. Integrates with simulation to show centers filling up.

Author: MAS-FRO Development Team
Date: November 2025
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class EvacuationCenterService:
    """
    Service for managing evacuation center data and capacity.

    Tracks current occupancy, calculates availability status, and provides
    methods for updating occupancy during simulations.

    Attributes:
        centers: DataFrame containing evacuation center information
        occupancy: Dict mapping center names to current occupancy counts
    """

    def __init__(self, csv_path: Optional[Path] = None):
        """
        Initialize the evacuation center service.

        Args:
            csv_path: Optional path to evacuation centers CSV file
        """
        self.centers: pd.DataFrame = pd.DataFrame()
        self.occupancy: Dict[str, int] = {}
        self.last_update: datetime = datetime.now()

        # Load centers from CSV
        if csv_path and csv_path.exists():
            self.load_from_csv(csv_path)
        else:
            # Try default paths
            self._load_default_centers()

        logger.info(
            f"EvacuationCenterService initialized with {len(self.centers)} centers"
        )

    def _load_default_centers(self) -> None:
        """Load evacuation centers from default paths."""
        possible_paths = [
            Path(__file__).parent.parent / "data" / "evacuation_centers.csv",
            Path(__file__).parent.parent.parent / "data" / "evacuation_centers.csv",
        ]

        for csv_path in possible_paths:
            if csv_path.exists():
                self.load_from_csv(csv_path)
                return

        logger.warning("No evacuation centers CSV found, using empty dataset")

    def load_from_csv(self, csv_path: Path) -> None:
        """
        Load evacuation centers from CSV file.

        Args:
            csv_path: Path to CSV file
        """
        try:
            self.centers = pd.read_csv(csv_path)
            logger.info(f"Loaded {len(self.centers)} evacuation centers from {csv_path}")

            # Initialize occupancy to 0 for all centers
            self.occupancy = {row['name']: 0 for _, row in self.centers.iterrows()}

        except Exception as e:
            logger.error(f"Failed to load evacuation centers: {e}")
            self.centers = pd.DataFrame()
            self.occupancy = {}

    def get_all_centers(self) -> List[Dict[str, Any]]:
        """
        Get all evacuation centers with current status.

        Returns:
            List of center dictionaries with capacity status
        """
        if self.centers.empty:
            return []

        centers_list = []
        for _, row in self.centers.iterrows():
            center_name = row['name']
            capacity = int(row['capacity'])
            current_occupancy = self.occupancy.get(center_name, 0)

            # Calculate availability status
            occupancy_ratio = current_occupancy / capacity if capacity > 0 else 0
            if occupancy_ratio >= 0.95:
                status = 'full'
            elif occupancy_ratio >= 0.70:
                status = 'limited'
            else:
                status = 'available'

            centers_list.append({
                'name': center_name,
                'coordinates': {
                    'lat': float(row['latitude']),
                    'lon': float(row['longitude'])
                },
                'location': row.get('address', ''),
                'barangay': row.get('barangay', ''),
                'capacity': capacity,
                'current_occupancy': current_occupancy,
                'available_slots': max(0, capacity - current_occupancy),
                'occupancy_percentage': round(occupancy_ratio * 100, 1),
                'status': status,
                'type': row.get('type', 'unknown'),
                'contact': row.get('contact', ''),
                'facilities': row.get('facilities', '').split(', ') if pd.notna(row.get('facilities')) else []
            })

        # Sort by availability (available first, then limited, then full)
        status_order = {'available': 0, 'limited': 1, 'full': 2}
        centers_list.sort(key=lambda x: (status_order[x['status']], -x['available_slots']))

        return centers_list

    def get_available_centers(self) -> List[Dict[str, Any]]:
        """
        Get only available evacuation centers (not full).

        Returns:
            List of centers with status 'available' or 'limited'
        """
        all_centers = self.get_all_centers()
        return [c for c in all_centers if c['status'] != 'full']

    def get_center_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get specific evacuation center by name.

        Args:
            name: Name of the evacuation center

        Returns:
            Center dictionary or None if not found
        """
        all_centers = self.get_all_centers()
        for center in all_centers:
            if center['name'] == name:
                return center
        return None

    def update_occupancy(self, center_name: str, occupancy: int) -> bool:
        """
        Update occupancy for a specific center.

        Args:
            center_name: Name of the evacuation center
            occupancy: New occupancy count

        Returns:
            True if successful, False otherwise
        """
        if center_name not in self.occupancy:
            logger.warning(f"Center '{center_name}' not found")
            return False

        # Get capacity to validate
        center_row = self.centers[self.centers['name'] == center_name]
        if center_row.empty:
            return False

        capacity = int(center_row.iloc[0]['capacity'])

        # Clamp occupancy to valid range
        occupancy = max(0, min(occupancy, capacity))

        old_occupancy = self.occupancy[center_name]
        self.occupancy[center_name] = occupancy
        self.last_update = datetime.now()

        logger.info(
            f"Updated {center_name}: {old_occupancy} -> {occupancy} "
            f"({occupancy}/{capacity} = {(occupancy/capacity*100):.1f}%)"
        )

        return True

    def add_evacuees(self, center_name: str, count: int) -> Dict[str, Any]:
        """
        Add evacuees to a center (for simulation).

        Args:
            center_name: Name of the evacuation center
            count: Number of evacuees to add

        Returns:
            Dict with result status and updated center info
        """
        center = self.get_center_by_name(center_name)
        if not center:
            return {
                'success': False,
                'message': f"Center '{center_name}' not found"
            }

        new_occupancy = center['current_occupancy'] + count
        available_slots = center['available_slots']

        if count > available_slots:
            return {
                'success': False,
                'message': f"Not enough space. Requested: {count}, Available: {available_slots}",
                'center': center
            }

        self.update_occupancy(center_name, new_occupancy)

        return {
            'success': True,
            'message': f"Added {count} evacuees to {center_name}",
            'center': self.get_center_by_name(center_name)
        }

    def reset_all_occupancy(self) -> None:
        """Reset occupancy to 0 for all centers (for simulation reset)."""
        for center_name in self.occupancy:
            self.occupancy[center_name] = 0
        self.last_update = datetime.now()
        logger.info("Reset all evacuation center occupancy to 0")

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get overall statistics about evacuation centers.

        Returns:
            Dict with statistics
        """
        all_centers = self.get_all_centers()

        total_capacity = sum(c['capacity'] for c in all_centers)
        total_occupancy = sum(c['current_occupancy'] for c in all_centers)
        total_available = sum(c['available_slots'] for c in all_centers)

        status_counts = {
            'available': len([c for c in all_centers if c['status'] == 'available']),
            'limited': len([c for c in all_centers if c['status'] == 'limited']),
            'full': len([c for c in all_centers if c['status'] == 'full'])
        }

        return {
            'total_centers': len(all_centers),
            'total_capacity': total_capacity,
            'total_occupancy': total_occupancy,
            'total_available_slots': total_available,
            'overall_occupancy_percentage': round((total_occupancy / total_capacity * 100) if total_capacity > 0 else 0, 1),
            'status_counts': status_counts,
            'last_update': self.last_update.isoformat()
        }


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
