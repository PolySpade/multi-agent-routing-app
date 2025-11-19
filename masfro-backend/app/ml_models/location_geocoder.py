# filename: app/ml_models/location_geocoder.py

"""
Location Geocoder for Marikina City
------------------------------------
Provides coordinate mapping for locations extracted by NLP Processor.
Maps location names to lat/lon coordinates for spatial risk analysis.

Author: MAS-FRO Development Team
Date: November 2025
Version: 2.0 - CSV-based location database
"""

from typing import Dict, Tuple, Optional
import logging
import csv
from pathlib import Path

logger = logging.getLogger(__name__)


class LocationGeocoder:
    """
    Geocoder for Marikina City locations.

    Loads location database from CSV file containing 3000+ Marikina locations.
    Provides coordinate lookup for barangays, landmarks, roads, schools,
    subdivisions, and other points of interest.

    Attributes:
        location_coordinates: Dict mapping location names to (lat, lon) tuples
        csv_path: Path to location.csv file

    Example:
        >>> geocoder = LocationGeocoder()
        >>> coords = geocoder.get_coordinates("Nangka")
        >>> print(coords)
        (14.6728917, 121.109213)
    """

    def __init__(self, csv_path: Optional[Path] = None):
        """
        Initialize geocoder by loading locations from CSV file.

        Args:
            csv_path: Optional path to location.csv. If None, uses default path.
        """

        # Determine CSV path
        if csv_path is None:
            # Default: locations/location.csv in same directory as this file
            csv_path = Path(__file__).parent / "locations" / "location.csv"

        self.csv_path = csv_path
        self.location_coordinates = {}

        # Load locations from CSV
        self._load_from_csv()

        logger.info(
            f"LocationGeocoder v2.0 initialized with {len(self.location_coordinates)} "
            f"locations from {csv_path.name}"
        )

    def _load_from_csv(self):
        """Load location coordinates from CSV file."""
        if not self.csv_path.exists():
            logger.error(f"Location CSV not found: {self.csv_path}")
            logger.warning("Falling back to empty location database")
            return

        try:
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    name = row.get('name', '').strip()
                    lat_str = row.get('@lat', '').strip()
                    lon_str = row.get('@lon', '').strip()

                    # Skip rows with missing data
                    if not name or not lat_str or not lon_str:
                        continue

                    try:
                        lat = float(lat_str)
                        lon = float(lon_str)

                        # Store as (lat, lon) tuple
                        self.location_coordinates[name] = (lat, lon)

                    except ValueError as e:
                        logger.debug(f"Skipping invalid coordinates for '{name}': {e}")
                        continue

            logger.info(f"Loaded {len(self.location_coordinates)} locations from CSV")

        except Exception as e:
            logger.error(f"Error loading location CSV: {e}")
            logger.warning("Falling back to empty location database")

        # ===== LEGACY HARDCODED COORDINATES (FALLBACK) =====
        # Keep these as fallback for critical locations not in CSV
        # Source: OpenStreetMap, Google Maps
        # Coordinates represent approximate barangay centers
        fallback_barangays = {
            # District I
            "Barangka": (14.6386, 121.0978),
            "Tañong": (14.6425, 121.0892),
            "Tanong": (14.6425, 121.0892),
            "Jesus dela Peña": (14.6394, 121.0856),
            "Jesus de la Peña": (14.6394, 121.0856),
            "Jesus Dela Pena": (14.6394, 121.0856),
            "Industrial Valley Complex": (14.6520, 121.0870),
            "IVC": (14.6520, 121.0870),
            "Industrial Valley": (14.6520, 121.0870),
            "Kalumpang": (14.6394, 121.1067),
            "Calumpang": (14.6394, 121.1067),
            "San Roque": (14.6319, 121.1156),
            "Sta. Elena": (14.6489, 121.0956),
            "Santa Elena": (14.6489, 121.0956),
            "Sto. Niño": (14.6553, 121.0967),
            "Santo Niño": (14.6553, 121.0967),
            "Santo Nino": (14.6553, 121.0967),
            "Sto Nino": (14.6553, 121.0967),
            "Malanday": (14.6561, 121.0889),

            # District II
            "Concepcion Uno": (14.6664, 121.1067),
            "Concepcion I": (14.6664, 121.1067),
            "Concepcion 1": (14.6664, 121.1067),
            "Concepcion Dos": (14.6708, 121.1156),
            "Concepcion II": (14.6708, 121.1156),
            "Concepcion 2": (14.6708, 121.1156),
            "Nangka": (14.6507, 121.1009),
            "Parang": (14.6700, 121.0911),
            "Marikina Heights": (14.6631, 121.0822),
            "Fortune": (14.6689, 121.0956),
            "Tumana": (14.6789, 121.1100),
        }

        # Add fallback landmarks (if not in CSV)
        fallback_landmarks = {
            # Shopping Centers
            "SM Marikina": (14.6394, 121.1067),
            "SM City Marikina": (14.6394, 121.1067),
            "Robinsons Metro East": (14.6319, 121.1156),
            "Robinsons Marikina": (14.6319, 121.1156),
            "Sta. Lucia East Grand Mall": (14.6319, 121.1156),
            "Sta Lucia Mall": (14.6319, 121.1156),
            "Riverbanks Center": (14.6394, 121.1067),
            "Riverbanks Mall": (14.6394, 121.1067),

            # Government & Institutions
            "Marikina City Hall": (14.6489, 121.0956),
            "City Hall": (14.6489, 121.0956),
            "Marikina Sports Center": (14.6420, 121.0928),
            "Sports Center": (14.6420, 121.0928),
            "Marikina Health Center": (14.6489, 121.0956),

            # Religious Sites
            "Our Lady of the Abandoned": (14.6489, 121.0956),
            "Diocesan Shrine": (14.6489, 121.0956),
            "Marikina Cathedral": (14.6489, 121.0956),

            # Historical & Cultural
            "Shoe Museum": (14.6489, 121.0956),
            "Marikina Shoe Museum": (14.6489, 121.0956),

            # Natural Features
            "Marikina River": (14.6500, 121.1000),
            "Marikina Riverbanks": (14.6394, 121.1067),
            "Riverbanks": (14.6394, 121.1067),

            # Bridges
            "Marikina Bridge": (14.6386, 121.0978),
            "Tumana Bridge": (14.6789, 121.1100),
            "Rosario Bridge": (14.6553, 121.0967),

            # Residential Villages
            "SSS Village": (14.6631, 121.0822),
            "Provident Village": (14.6631, 121.0822),
            "Provident": (14.6631, 121.0822),
        }

        # Add fallback LRT stations (if not in CSV)
        fallback_lrt = {
            "Santolan Station": (14.6394, 121.1067),
            "Santolan LRT": (14.6394, 121.1067),
            "Marikina-Pasig Station": (14.6319, 121.1156),
            "Marikina Station": (14.6319, 121.1156),
            "Antipolo Station": (14.6244, 121.1242),
            "Antipolo LRT": (14.6244, 121.1242),
        }

        # Add fallback roads/highways (if not in CSV)
        fallback_roads = {
            "Marcos Highway": (14.6400, 121.1100),
            "Marikina-Infanta Highway": (14.6400, 121.1100),
            "Sumulong Highway": (14.6489, 121.0956),
            "Sumulong": (14.6489, 121.0956),
            "Gil Fernando Avenue": (14.6450, 121.0920),
            "Gil Fernando": (14.6450, 121.0920),
            "Mayor Gil Fernando": (14.6450, 121.0920),
            "Felix Avenue": (14.6420, 121.0950),
            "Felix": (14.6420, 121.0950),
            "A. Bonifacio": (14.6386, 121.0978),
            "Andres Bonifacio Avenue": (14.6386, 121.0978),
            "Aurora Boulevard": (14.6350, 121.1050),
            "Aurora Blvd": (14.6350, 121.1050),
            "Ramon Magsaysay Boulevard": (14.6300, 121.1100),
            "J.P. Rizal": (14.6489, 121.0956),
            "JP Rizal": (14.6489, 121.0956),
            "Rizal Avenue": (14.6489, 121.0956),
            "Shoe Avenue": (14.6489, 121.0956),
            "Riverbanks Road": (14.6394, 121.1067),
            "Liamzon Street": (14.6319, 121.1156),
            "Ditchoy Street": (14.6319, 121.1156),
            "Dasdasan Street": (14.6319, 121.1156),
        }

        # Merge fallback data (only add if not already in CSV)
        fallback_data = {
            **fallback_barangays,
            **fallback_landmarks,
            **fallback_lrt,
            **fallback_roads
        }

        added_fallbacks = 0
        for name, coords in fallback_data.items():
            if name not in self.location_coordinates:
                self.location_coordinates[name] = coords
                added_fallbacks += 1

        if added_fallbacks > 0:
            logger.info(f"Added {added_fallbacks} fallback locations not in CSV")

    def get_coordinates(self, location_name: str) -> Optional[Tuple[float, float]]:
        """
        Get coordinates for a location name.

        Args:
            location_name: Name of location (from NLP processor)

        Returns:
            (latitude, longitude) tuple, or None if not found

        Example:
            >>> coords = geocoder.get_coordinates("Nangka")
            >>> print(coords)
            (14.6507, 121.1009)
        """
        if not location_name:
            return None

        # Direct lookup (case-insensitive)
        coords = self.location_coordinates.get(location_name)
        if coords:
            return coords

        # Try case-insensitive match
        location_lower = location_name.lower()
        for loc_name, loc_coords in self.location_coordinates.items():
            if loc_name.lower() == location_lower:
                return loc_coords

        logger.warning(f"No coordinates found for location: {location_name}")
        return None

    def geocode_nlp_result(self, nlp_result: Dict) -> Dict:
        """
        Enhance NLP result with coordinates.

        Args:
            nlp_result: Result from NLPProcessor.extract_flood_info()

        Returns:
            Enhanced result with coordinates added

        Example:
            >>> nlp_result = {"location": "Nangka", "severity": 0.9, ...}
            >>> enhanced = geocoder.geocode_nlp_result(nlp_result)
            >>> print(enhanced["coordinates"])
            {"lat": 14.6507, "lon": 121.1009}
        """
        enhanced_result = nlp_result.copy()

        location = nlp_result.get("location")
        if location:
            coords = self.get_coordinates(location)
            if coords:
                enhanced_result["coordinates"] = {
                    "lat": coords[0],
                    "lon": coords[1]
                }
                enhanced_result["has_coordinates"] = True
            else:
                enhanced_result["coordinates"] = None
                enhanced_result["has_coordinates"] = False
        else:
            enhanced_result["coordinates"] = None
            enhanced_result["has_coordinates"] = False

        return enhanced_result

    def get_nearby_locations(
        self,
        lat: float,
        lon: float,
        radius_km: float = 1.0
    ) -> Dict[str, Tuple[float, float]]:
        """
        Find locations within radius of a point.

        Simple distance calculation (not accounting for Earth curvature).
        Good enough for small distances in Marikina.

        Args:
            lat: Latitude of center point
            lon: Longitude of center point
            radius_km: Radius in kilometers

        Returns:
            Dict of location names to coordinates within radius

        Example:
            >>> nearby = geocoder.get_nearby_locations(14.6507, 121.1009, 2.0)
            >>> print(nearby.keys())
            ['Nangka', 'Concepcion Uno', 'Tumana', ...]
        """
        nearby = {}

        # Simple distance calculation (Pythagoras)
        # 1 degree ≈ 111 km at equator
        # For Marikina (latitude ~14°), use 110 km for simplicity
        km_per_degree = 110.0

        for loc_name, (loc_lat, loc_lon) in self.location_coordinates.items():
            # Calculate distance
            lat_diff = abs(lat - loc_lat) * km_per_degree
            lon_diff = abs(lon - loc_lon) * km_per_degree * 0.97  # Adjust for latitude
            distance = (lat_diff**2 + lon_diff**2) ** 0.5

            if distance <= radius_km:
                nearby[loc_name] = (loc_lat, loc_lon)

        return nearby

    def get_barangay_for_point(
        self,
        lat: float,
        lon: float
    ) -> Optional[str]:
        """
        Find nearest barangay for a point.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            Name of nearest barangay, or None

        Example:
            >>> barangay = geocoder.get_barangay_for_point(14.6507, 121.1009)
            >>> print(barangay)
            'Nangka'
        """
        # List of official Marikina barangays
        official_barangays = [
            "Barangka", "Tañong", "Jesus dela Peña", "Jesus de la Peña",
            "Industrial Valley Complex", "IVC", "Kalumpang", "Calumpang",
            "San Roque", "Sta. Elena", "Santa Elena", "Sto. Niño", "Santo Niño",
            "Malanday", "Concepcion Uno", "Concepcion Dos", "Nangka",
            "Parang", "Marikina Heights", "Fortune", "Tumana"
        ]

        min_distance = float('inf')
        nearest_barangay = None

        km_per_degree = 110.0

        # Search through all locations for barangay matches
        for loc_name, (loc_lat, loc_lon) in self.location_coordinates.items():
            # Check if this location is a barangay
            if loc_name in official_barangays:
                lat_diff = abs(lat - loc_lat) * km_per_degree
                lon_diff = abs(lon - loc_lon) * km_per_degree * 0.97
                distance = (lat_diff**2 + lon_diff**2) ** 0.5

                if distance < min_distance:
                    min_distance = distance
                    nearest_barangay = loc_name

        return nearest_barangay


# Test the geocoder when run directly
if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO)

    print("=== Testing Location Geocoder ===\n")

    geocoder = LocationGeocoder()

    # Test coordinate lookup
    test_locations = [
        "Nangka",
        "SM Marikina",
        "Marikina Bridge",
        "LRT Santolan",
        "Gil Fernando Avenue",
        "Unknown Location"
    ]

    print("Testing coordinate lookup:\n")
    for location in test_locations:
        coords = geocoder.get_coordinates(location)
        if coords:
            print(f"  {location}: {coords[0]:.4f}, {coords[1]:.4f}")
        else:
            print(f"  {location}: NOT FOUND")

    # Test NLP integration
    print("\n\nTesting NLP integration:\n")

    from nlp_processor import NLPProcessor

    nlp = NLPProcessor()

    test_texts = [
        "Baha sa Nangka! Tuhod level!",
        "Flooded sa SM Marikina, waist deep",
        "Clear na sa Tumana Bridge"
    ]

    for text in test_texts:
        nlp_result = nlp.extract_flood_info(text)
        enhanced = geocoder.geocode_nlp_result(nlp_result)

        print(f"Text: {text}")
        print(f"  Location: {enhanced.get('location')}")
        print(f"  Coordinates: {enhanced.get('coordinates')}")
        print(f"  Severity: {enhanced.get('severity'):.2f}")
        print()

    # Test nearby locations
    print("\nTesting nearby locations (Nangka, 1km radius):\n")
    nangka_coords = geocoder.get_coordinates("Nangka")
    if nangka_coords:
        nearby = geocoder.get_nearby_locations(nangka_coords[0], nangka_coords[1], 1.0)
        print(f"  Found {len(nearby)} locations within 1km of Nangka:")
        for loc_name in list(nearby.keys())[:5]:
            print(f"    - {loc_name}")

    # Test barangay identification
    print("\n\nTesting barangay identification:\n")
    test_points = [
        (14.6507, 121.1009, "Near Nangka"),
        (14.6394, 121.1067, "Near SM Marikina"),
        (14.6789, 121.1100, "Near Tumana")
    ]

    for lat, lon, description in test_points:
        barangay = geocoder.get_barangay_for_point(lat, lon)
        print(f"  {description}: Barangay {barangay}")
