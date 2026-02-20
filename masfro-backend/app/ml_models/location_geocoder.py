# filename: app/ml_models/location_geocoder.py

"""
Location Geocoder for Marikina City
------------------------------------
Provides coordinate mapping for locations extracted by NLP Processor.
Maps location names to lat/lon coordinates for spatial risk analysis.

Author: MAS-FRO Development Team
Date: November 2025
Version: 2.1 - Enhanced Fuzzy Search & Optimization (Complete Dataset)
"""

from typing import Dict, Tuple, Optional, List
import logging
import csv
from pathlib import Path
import difflib
import math

logger = logging.getLogger(__name__)


class LocationGeocoder:
    """
    Geocoder for Marikina City locations.

    Loads location database from CSV file containing 3000+ Marikina locations.
    Provides coordinate lookup for barangays, landmarks, roads, schools,
    subdivisions, and other points of interest.

    Features:
    - CSV-based database loading
    - Complete fallback database for critical locations
    - Exact and case-insensitive lookup
    - Fuzzy string matching for robust location finding
    - Optimized spatial queries (bounding box + equirectangular distance)

    Attributes:
        location_coordinates: Dict mapping location names to (lat, lon) tuples
        location_names: List of all registered location names (for fuzzy search)
        csv_path: Path to location.csv file
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
        self.location_coordinates: Dict[str, Tuple[float, float]] = {}
        self.location_names: List[str] = []

        # Load locations from CSV
        self._load_from_csv()



        # Index names for search
        self.location_names = list(self.location_coordinates.keys())

        logger.info(
            f"LocationGeocoder v2.1 initialized with {len(self.location_coordinates)} "
            f"locations from {csv_path.name}"
        )

    def _load_from_csv(self):
        """Load location coordinates from CSV file."""
        if not self.csv_path.exists():
            logger.error(f"Location CSV not found: {self.csv_path}")
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



    def get_coordinates(
        self, 
        location_name: str, 
        fuzzy: bool = True, 
        threshold: float = 0.85
    ) -> Optional[Tuple[float, float]]:
        """
        Get coordinates for a location name.
        
        Implements a 3-step lookup strategy:
        1. Exact match (Fastest)
        2. Case-insensitive match
        3. Fuzzy string matching (difflib)

        Args:
            location_name: Name of location (from NLP processor)
            fuzzy: Enable fuzzy matching if exact match fails (default: True)
            threshold: Similarity threshold for fuzzy matching (0.0-1.0)

        Returns:
            (latitude, longitude) tuple, or None if not found
        """
        if not location_name:
            return None

        # 1. Direct lookup (O(1))
        coords = self.location_coordinates.get(location_name)
        if coords:
            return coords

        # 2. Case-insensitive match
        location_lower = location_name.lower()
        for loc_name, loc_coords in self.location_coordinates.items():
            if loc_name.lower() == location_lower:
                return loc_coords

        # 3. Fuzzy matching
        if fuzzy and self.location_names:
            matches = difflib.get_close_matches(
                location_name, 
                self.location_names, 
                n=1, 
                cutoff=threshold
            )
            
            if matches:
                best_match = matches[0]
                ratio = difflib.SequenceMatcher(None, location_name, best_match).ratio()
                logger.info(f"Fuzzy match: '{location_name}' -> '{best_match}' (confidence: {ratio:.2f})")
                return self.location_coordinates[best_match]

        # 4. Google Maps Fallback
        logger.info(f"Trying Google Maps geocoding for: {location_name}")
        google_result = self._geocode_with_google(location_name)
        if google_result:
            return google_result

        logger.warning(f"No coordinates found for location: {location_name}")
        return None

    def _geocode_with_google(self, location_name: str) -> Optional[Tuple[float, float]]:
        """
        Use Google Maps Geocoding API to resolve a location name to coordinates.
        Results are biased toward Marikina City and validated against the city bounding box.
        """
        import requests
        from app.core.config import settings

        api_key = settings.GOOGLE_API_KEY
        if not api_key:
            logger.warning("[MISS] Google Maps API key not configured")
            return None

        try:
            # Reject queries that explicitly mention other cities
            excluded_keywords = [
                "manila", "quezon city", "qc", "pasig", "antipolo",
                "cainta", "san mateo", "makati", "taguig"
            ]
            query_lower = location_name.lower()
            if any(city in query_lower for city in excluded_keywords):
                logger.warning(f"[MISS] Rejected out-of-bounds location query: '{location_name}'")
                return None

            # Marikina City bounding box (with small buffer)
            MARIKINA_BOUNDS = {
                "lat_min": 14.61, "lat_max": 14.68,
                "lon_min": 121.08, "lon_max": 121.13,
            }

            params = {
                "address": f"{location_name}, Marikina City, Philippines",
                "key": api_key,
                # Bias results toward Marikina City center
                "bounds": "14.61,121.08|14.68,121.13",
            }

            resp = requests.get(
                "https://maps.googleapis.com/maps/api/geocode/json",
                params=params,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") != "OK" or not data.get("results"):
                logger.info(f"[MISS] Google geocode returned no results for '{location_name}' (status: {data.get('status')})")
                return None

            result = data["results"][0]
            loc = result["geometry"]["location"]
            lat, lon = loc["lat"], loc["lng"]

            # Validate the result is within Marikina bounds
            if not (MARIKINA_BOUNDS["lat_min"] <= lat <= MARIKINA_BOUNDS["lat_max"]
                    and MARIKINA_BOUNDS["lon_min"] <= lon <= MARIKINA_BOUNDS["lon_max"]):
                logger.info(
                    f"[MISS] Google result for '{location_name}' is outside Marikina: "
                    f"({lat:.5f}, {lon:.5f})"
                )
                return None

            formatted_address = result.get("formatted_address", "")
            logger.info(
                f"[OK] Google geocoded '{location_name}' -> ({lat:.5f}, {lon:.5f}) "
                f"[{formatted_address}]"
            )
            return (lat, lon)

        except requests.RequestException as e:
            logger.error(f"Google geocoding request error: {e}")
        except (KeyError, ValueError) as e:
            logger.error(f"Google geocoding parse error: {e}")

        return None
    
    def geocode_nlp_result(self, nlp_result: Dict) -> Dict:
        """
        Enhance NLP result with coordinates.

        Args:
            nlp_result: Result from NLPProcessor.extract_flood_info()

        Returns:
            Enhanced result with coordinates added
        """
        enhanced_result = nlp_result.copy()

        location = nlp_result.get("location")
        if location:
            # Use fuzzy matching for NLP extracted text as it's often messy
            coords = self.get_coordinates(location, fuzzy=True, threshold=0.6)
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
        
        Optimized using a bounding box filter before distance calculation.

        Args:
            lat: Latitude of center point
            lon: Longitude of center point
            radius_km: Radius in kilometers

        Returns:
            Dict of location names to coordinates within radius
        """
        nearby = {}

        # Conversion factors for Marikina (approx Lat 14.65)
        # 1 deg Lat ~= 110.574 km
        # 1 deg Lon ~= 111.320 * cos(lat) ~= 107.7 km
        LAT_PER_KM = 1 / 110.574
        LON_PER_KM = 1 / 107.7

        # Bounding box limits
        lat_min = lat - (radius_km * LAT_PER_KM)
        lat_max = lat + (radius_km * LAT_PER_KM)
        lon_min = lon - (radius_km * LON_PER_KM)
        lon_max = lon + (radius_km * LON_PER_KM)

        for loc_name, (loc_lat, loc_lon) in self.location_coordinates.items():
            # Fast bounding box check
            if not (lat_min <= loc_lat <= lat_max and lon_min <= loc_lon <= lon_max):
                continue

            # Detailed distance calculation (Equirectangular approximation)
            x = (lon - loc_lon) * 107.7
            y = (lat - loc_lat) * 110.6
            distance = math.sqrt(x*x + y*y)

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
        """
        # List of official Marikina barangays (Complete list)
        official_barangays = {
            "Barangka", "Tañong", "Jesus dela Peña", "Jesus de la Peña",
            "Industrial Valley Complex", "IVC", "Kalumpang", "Calumpang",
            "San Roque", "Sta. Elena", "Santa Elena", "Sto. Niño", "Santo Niño",
            "Malanday", "Concepcion Uno", "Concepcion Dos", "Nangka", 
            "Parang", "Marikina Heights", "Fortune", "Tumana"
        }

        min_distance = float('inf')
        nearest_barangay = None

        # Optimization: Only check known barangays/aliases if they exist in our DB
        target_locations = [
            (name, coords) for name, coords in self.location_coordinates.items() 
            if name in official_barangays or 
            any(b in name for b in official_barangays) 
        ]
        
        # If filter too strict, fallback to checking all locations
        if not target_locations:
            target_locations = self.location_coordinates.items()

        for loc_name, (loc_lat, loc_lon) in target_locations:
            # Equirectangular approximation
            x = (lon - loc_lon) * 107.7
            y = (lat - loc_lat) * 110.6
            distance = math.sqrt(x*x + y*y)

            if distance < min_distance:
                min_distance = distance
                nearest_barangay = loc_name

        return nearest_barangay


# Test the geocoder when run directly
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("=== Testing Location Geocoder (v2.1 - Complete Fallback) ===\n")

    geocoder = LocationGeocoder()

    # Test coordinate lookup with fuzzy matching
    test_locations = [
        "A. Bonifacio Avenue"
    ]

    print("Testing coordinate lookup:\n")
    for location in test_locations:
        coords = geocoder.get_coordinates(location)
        if coords:
            print(f"  {location}: {coords[0]:.4f}, {coords[1]:.4f}")
        else:
            print(f"  {location}: NOT FOUND")