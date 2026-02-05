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

    def __init__(self, csv_path: Optional[Path] = None, llm_service=None):
        """
        Initialize geocoder by loading locations from CSV file.

        Args:
            csv_path: Optional path to location.csv. If None, uses default path.
            llm_service: Optional LLMService instance for enhanced lookup.
        """

        # Determine CSV path
        if csv_path is None:
            # Default: locations/location.csv in same directory as this file
            csv_path = Path(__file__).parent / "locations" / "location.csv"

        self.csv_path = csv_path
        self.llm_service = llm_service
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

        # 4. LLM Fallback (New in v2.2)
        if self.llm_service and self.llm_service.is_available():
            logger.info(f"Trying LLM geocoding for: {location_name}")
            return self._geocode_with_llm(location_name)

        logger.warning(f"No coordinates found for location: {location_name}")
        return None

    def _geocode_with_llm(self, location_name: str) -> Optional[Tuple[float, float]]:
        """
        Use LLM to semantically match location_name against the location database.
        Instead of generating coordinates, the LLM searches the CSV for the best match.
        """
        import json
        import ollama
        
        try:
            # 1. OPTIMIZATION: Strict keyword filtering
            # If the query explicitly mentions another city, reject immediately without LLM.
            excluded_keywords = [
                "manila", "quezon city", "qc", "pasig", "antipolo", 
                "cainta", "san mateo", "makati", "taguig"
            ]
            query_lower = location_name.lower()
            if any(city in query_lower for city in excluded_keywords):
                logger.warning(f"❌ Rejected out-of-bounds location query: '{location_name}'")
                return None

            # Sample a subset of locations for the prompt (to avoid token limits)
            # Prioritize locations that might be relevant
            sample_locations = self._get_relevant_location_sample(location_name, sample_size=50)
            
            if not sample_locations:
                logger.warning("No location samples available for LLM matching")
                return None
            
            prompt = f"""You are a Geospatial Validator for Marikina City.

QUERY: "{location_name}"

REFERENCE LIST (Authorized Locations):
{chr(10).join(f"- {loc}" for loc in sample_locations)}

INSTRUCTIONS:
1. Search the Reference List for the location that best matches the Query.
2. STRICTLY follow these rules:
   - If the Query is for a non-Marikina city (Manila, Quezon City, etc.), return {{"match": null, "conf": 0.0}}.
   - If the Query is generic (e.g. "Church") and ambiguous, return null.
   - Do NOT map "Memorial Circle" (QC) to anything in Marikina.
   
OUTPUT:
Return ONLY a valid JSON object in this format:
{{"match": "Exact Name From List", "conf": 0.95}}

If no match:
{{"match": null, "conf": 0.0}}

Do not add any explanation or markdown."""
            
            model = self.llm_service.text_model if self.llm_service else "llama3.2:latest"
            
            logger.info(f"Querying {model} to match '{location_name}' against {len(sample_locations)} locations...")
            
            response = ollama.chat(
                model=model,
                messages=[{'role': 'user', 'content': prompt}]
            )
            
            content = response['message']['content']
            logger.debug(f"LLM Raw Response: {content}")
            
            # Parse JSON response
            content = content.replace("```json", "").replace("```", "").strip()
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_candidate = content[start_idx:end_idx]
                
                try:
                    data = json.loads(json_candidate)
                except json.JSONDecodeError:
                    # Try fixing common mistakes
                    try:
                        fixed = json_candidate.replace("'", '"')
                        data = json.loads(fixed)
                    except Exception:
                        logger.warning(f"❌ Failed to parse LLM response: {json_candidate[:100]}")
                        return None
                
                matched_loc = data.get('match') or data.get('matched_location')  # Support both formats
                confidence = float(data.get('conf') or data.get('confidence', 0.0))
                
                if matched_loc and confidence >= 0.75:
                    # Look up the matched location in our database
                    coords = self.location_coordinates.get(matched_loc)
                    if coords:
                        logger.info(
                            f"✅ LLM matched '{location_name}' -> '{matched_loc}' "
                            f"(confidence: {confidence:.2f}) -> {coords}"
                        )
                        return coords
                    else:
                        logger.warning(f"❌ LLM returned location not in database: {matched_loc}")
                else:
                    logger.info(f"❌ No confident match found for '{location_name}' (confidence: {confidence:.2f})")
            else:
                logger.warning("❌ Could not find JSON in LLM response")
            
        except Exception as e:
            logger.error(f"LLM semantic matching error: {e}")
            
        return None
    
    def _get_relevant_location_sample(self, query: str, sample_size: int = 50) -> List[str]:
        """
        Get a sample of locations most likely to be relevant to the query.
        Uses basic string similarity to prioritize likely candidates.
        """
        query_lower = query.lower()
        
        # Score each location by simple relevance heuristics
        scored_locations = []
        for loc_name in self.location_names:
            score = 0
            loc_lower = loc_name.lower()
            
            # Exact match = highest priority
            if loc_lower == query_lower:
                score = 1000
            # Starts with query
            elif loc_lower.startswith(query_lower):
                score = 100
            # Contains query
            elif query_lower in loc_lower:
                score = 50
            # Query contains location name
            elif loc_lower in query_lower:
                score = 30
            # Word overlap
            else:
                query_words = set(query_lower.split())
                loc_words = set(loc_lower.split())
                overlap = len(query_words & loc_words)
                score = overlap * 10
            
            scored_locations.append((score, loc_name))
        
        # Sort by score and take top N
        scored_locations.sort(reverse=True, key=lambda x: x[0])
        
        # Take top sample_size, or all if we have fewer
        top_locations = [name for score, name in scored_locations[:sample_size]]
        
        # If no locations scored above 0, return a random sample
        if not top_locations or scored_locations[0][0] == 0:
            import random
            top_locations = random.sample(self.location_names, min(sample_size, len(self.location_names)))
        
        return top_locations

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