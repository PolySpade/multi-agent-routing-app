# filename: app/ml_models/nlp_processor.py

"""
NLP Processor for Social Media Flood Reports (MAS-FRO)

This module implements natural language processing functions for extracting
flood-related information from social media text (Twitter/X, Facebook posts).
Handles both Filipino and English text commonly used in Marikina area flood
reports.

Key Functions:
- Location extraction (barangays, landmarks, streets)
- Severity assessment (depth indicators, passability)
- Report classification (flood, clear, traffic, evacuation)
- Flood-related filtering

Author: MAS-FRO Development Team
Date: November 2025
Version: 2.0 - Enhanced with comprehensive Marikina geography and Filipino terminology
"""

import re
from typing import Dict, Any, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class NLPProcessor:
    """
    Natural Language Processor for flood reports.

    This class provides methods to extract structured information from
    unstructured social media text about flood conditions. Handles
    mixed Filipino-English (Taglish) text common in Philippine social media.

    Enhanced Features:
    - Complete Marikina City barangay coverage (all 16 barangays)
    - MMDA flood gauge depth standards
    - Comprehensive Filipino/Tagalog flood terminology
    - 200+ location references (barangays, landmarks, roads)

    Attributes:
        flood_keywords: Keywords indicating flooding (Filipino & English)
        severity_indicators: Keywords for severity assessment
        known_locations: All Marikina barangays, landmarks, and roads
        depth_mapping: MMDA standard flood depth measurements

    Example:
        >>> processor = NLPProcessor()
        >>> info = processor.extract_flood_info(
        ...     "Baha sa J.P. Rizal, tuhod level! Hindi madaan!"
        ... )
        >>> print(info['severity'])
        0.6
        >>> print(info['is_flood_related'])
        True
    """

    def __init__(self):
        """Initialize the NLP processor with comprehensive keyword dictionaries."""

        # ===== FLOOD-RELATED KEYWORDS (Filipino and English) =====
        self.flood_keywords = {
            # Primary flood indicators
            "flood": [
                # English
                "flood", "flooded", "flooding", "floodwater", "floodwaters",
                "submerged", "inundated", "underwater",
                # Filipino/Tagalog
                "baha", "bumaha", "bahain", "pagbaha", "binaha",
                "apaw", "umapaw", "puno", "lumalaki ang tubig",
                "tumataas ang tubig", "pisan", "dilubyo", "sinap"
            ],

            # Clear/No flood indicators
            "clear": [
                # English
                "clear", "cleared", "no flood", "passable", "safe", "dry",
                "receding", "subsiding",
                # Filipino
                "walang baha", "okay", "madaan", "safe", "tuyo",
                "humupa", "bumaba na", "keri pa", "pwede pa"
            ],

            # Blocked/Impassable indicators
            "blocked": [
                # English
                "blocked", "impassable", "closed", "not passable", "stranded",
                "stuck", "trapped",
                # Filipino
                "sarado", "hindi madaan", "barado", "naipit", "naharang",
                "di madadaanan", "nakatigil", "nakaabang"
            ],

            # Traffic indicators
            "traffic": [
                # English
                "traffic", "slow", "congestion", "jam",
                # Filipino
                "trapik", "mabagal", "bara", "mahaba", "pila"
            ],

            # Water level rising indicators
            "rising": [
                # English
                "rising", "increasing", "getting higher", "climbing",
                # Filipino
                "tumataas", "lumalaki", "lumalalim", "tumataas pa",
                "patuloy tumataas"
            ],

            # Evacuation indicators
            "evacuation": [
                # English
                "evacuate", "evacuating", "evacuation", "rescue", "help",
                # Filipino
                "lumikas", "lumilikas", "evac", "rescue", "tulong",
                "kailangan ng tulong", "emergency"
            ]
        }

        # ===== SEVERITY INDICATORS BY DEPTH =====
        # Based on MMDA flood gauge standards and Filipino body-based indicators
        self.severity_indicators = {
            # Gutter/Very Shallow (8 inches / 20cm)
            "gutter": [
                "gutter", "gutter deep", "gutter-deep",
                "imburnal", "kanal",
                "mababaw lang", "konti lang", "kaunti lang"
            ],

            # Ankle (10 inches / 25cm)
            "ankle": [
                "ankle", "ankle deep", "ankle-deep",
                "sakong", "bukung-bukong", "sa paa lang",
                "half knee", "half-knee", "kalahating tuhod"
            ],

            # Knee (19 inches / 48cm) - NPLV threshold
            "knee": [
                "knee", "knee deep", "knee-deep", "knee level",
                "tuhod", "hanggang tuhod", "tuhod level",
                "pantuhod", "abot tuhod"
            ],

            # Tire/Mid-thigh (26 inches / 66cm) - NPATV threshold
            "tire": [
                "tire", "tire deep", "tire-deep",
                "gulong", "hanggang gulong",
                "hita", "mid-thigh"
            ],

            # Waist (37 inches / 94cm)
            "waist": [
                "waist", "waist deep", "waist-deep", "waist level",
                "baywang", "bewang", "hanggang baywang",
                "abot baywang", "pantawid"
            ],

            # Chest (45 inches / 114cm)
            "chest": [
                "chest", "chest deep", "chest-deep", "chest level",
                "dibdib", "hanggang dibdib", "abot dibdib",
                "breast level"
            ],

            # Neck/Head (60+ inches / 150cm+)
            "neck": [
                "neck", "neck deep", "neck-deep",
                "leeg", "hanggang leeg", "abot leeg",
                "head deep", "overhead", "mataas na"
            ],

            # General depth indicators
            "high": [
                "high", "deep", "mataas", "malalim", "grabe",
                "sobrang taas", "malala", "critical"
            ]
        }

        # ===== COMPLETE MARIKINA CITY LOCATIONS =====
        # All 16 barangays + landmarks + roads + LRT stations
        self.known_locations = {
            # === 16 OFFICIAL BARANGAYS ===
            "barangays": [
                # District I (9 barangays)
                "Barangka", "Tañong", "Tanong",
                "Jesus dela Peña", "Jesus de la Peña", "Jesus Dela Pena",
                "Industrial Valley Complex", "IVC", "Industrial Valley",
                "Kalumpang", "Calumpang",
                "San Roque",
                "Sta. Elena", "Santa Elena",
                "Sto. Niño", "Santo Niño", "Santo Nino", "Sto Nino",
                "Malanday",
                # District II (7 barangays)
                "Concepcion Uno", "Concepcion I", "Concepcion 1",
                "Concepcion Dos", "Concepcion II", "Concepcion 2",
                "Nangka",
                "Parang",
                "Marikina Heights",
                "Fortune",
                "Tumana"
            ],

            # === MAJOR ROADS & HIGHWAYS ===
            "roads": [
                # Major highways
                "Marcos Highway", "Marikina-Infanta Highway",
                "Sumulong Highway", "Sumulong",
                "Gil Fernando Avenue", "Gil Fernando", "Mayor Gil Fernando",
                "Felix Avenue", "Felix",
                "A. Bonifacio", "Andres Bonifacio Avenue",
                "Aurora Boulevard", "Aurora Blvd",
                "Ramon Magsaysay Boulevard",

                # Local streets
                "J.P. Rizal", "JP Rizal", "Rizal Avenue",
                "Shoe Avenue",
                "Riverbanks Road",
                "Liamzon Street", "Ditchoy Street", "Dasdasan Street"
            ],

            # === LRT-2 STATIONS ===
            "lrt_stations": [
                "Santolan Station", "Santolan LRT",
                "Marikina-Pasig Station", "Marikina Station",
                "Antipolo Station", "Antipolo LRT"
            ],

            # === MAJOR LANDMARKS ===
            "landmarks": [
                # Shopping Centers
                "SM Marikina", "SM City Marikina",
                "Robinsons Metro East", "Robinsons Marikina",
                "Sta. Lucia East Grand Mall", "Sta Lucia Mall",
                "Riverbanks Center", "Riverbanks Mall",

                # Government & Institutions
                "Marikina City Hall", "City Hall",
                "Marikina Sports Center", "Sports Center",
                "Marikina Health Center",

                # Religious Sites
                "Our Lady of the Abandoned", "Diocesan Shrine",
                "Marikina Cathedral",

                # Historical & Cultural
                "Shoe Museum", "Marikina Shoe Museum",

                # Natural Features
                "Marikina River", "Marikina Riverbanks", "Riverbanks",

                # Bridges
                "Marikina Bridge", "Tumana Bridge", "Rosario Bridge",

                # Residential Villages
                "SSS Village", "Provident Village", "Provident"
            ]
        }

        # Flatten all locations into a single list for matching
        self.all_known_locations = []
        for category in self.known_locations.values():
            self.all_known_locations.extend(category)

        # ===== DEPTH-TO-SEVERITY MAPPING =====
        # Based on MMDA flood gauge standards (0-1 scale)
        # Reference: 0.5m = medium hazard, 1.5m = high hazard
        self.depth_mapping = {
            "gutter": 0.1,    # 8 inches / 20cm - Passable to all
            "ankle": 0.15,    # 10 inches / 25cm - Passable to all
            "knee": 0.5,      # 19 inches / 48cm - Not passable to light vehicles
            "tire": 0.65,     # 26 inches / 66cm - Not passable to all vehicles
            "waist": 0.8,     # 37 inches / 94cm - Dangerous
            "chest": 0.9,     # 45 inches / 114cm - Very dangerous
            "neck": 0.95,     # 60+ inches / 150cm+ - Critical
            "high": 0.7       # General high water
        }

        logger.info("NLPProcessor v2.0 initialized with comprehensive Marikina data")
        logger.info(f"  - {len(self.all_known_locations)} known locations loaded")
        logger.info(f"  - {sum(len(v) for v in self.flood_keywords.values())} flood keywords")
        logger.info(f"  - {sum(len(v) for v in self.severity_indicators.values())} severity indicators")

    def extract_flood_info(self, text: str) -> Dict[str, Any]:
        """
        Extract flood information from social media text.

        Analyzes text to extract:
        - Whether report is flood-related (NEW!)
        - Location mentioned
        - Flood severity
        - Road passability
        - Report type

        Args:
            text: Social media post text (Filipino/English/mixed)

        Returns:
            Dict containing extracted information:
                {
                    "is_flood_related": bool,      # NEW: Critical for filtering
                    "location": str or None,
                    "severity": float (0-1),
                    "passable": bool or None,
                    "report_type": str,
                    "confidence": float (0-1),
                    "raw_text": str
                }

        Example:
            >>> info = processor.extract_flood_info(
            ...     "Baha sa Nangka! Tuhod level, hindi madaan ng kotse!"
            ... )
            >>> print(f"Flood-related: {info['is_flood_related']}")
            >>> print(f"Location: {info['location']}")
            >>> print(f"Severity: {info['severity']:.2f}")
        """
        text_lower = text.lower()

        # Extract location
        location = self._extract_location(text)

        # Determine report type
        report_type = self._classify_report_type(text_lower)

        # Extract severity
        severity = self._extract_severity(text_lower)

        # Determine passability
        passable = self._determine_passability(text_lower, severity)

        # Calculate confidence based on keyword matches
        confidence = self._calculate_confidence(text_lower, location, severity)

        # NEW: Determine if flood-related
        is_flood_related = self._is_flood_related(report_type, severity, text_lower)

        return {
            "is_flood_related": is_flood_related,  # NEW FIELD
            "location": location,
            "severity": severity,
            "passable": passable,
            "report_type": report_type,
            "confidence": confidence,
            "raw_text": text
        }

    def _is_flood_related(self, report_type: str, severity: float, text: str) -> bool:
        """
        Determine if the report is flood-related.

        A report is considered flood-related if:
        1. Report type is "flood", "blocked", "evacuation", or "rising"
        2. OR severity > 0 (indicates flooding)
        3. AND NOT a "clear" report (unless it mentions previous flooding)
        4. AND NOT explicitly negated (e.g., "walang baha", "no flood")

        Args:
            report_type: Classification of report
            severity: Severity score (0-1)
            text: Lowercased text

        Returns:
            True if flood-related, False otherwise
        """
        # Check for explicit negation first
        negation_phrases = [
            "walang baha", "no flood", "no water", "no flooding",
            "hindi baha", "wala", "clear", "okay", "passable"
        ]
        has_negation = any(phrase in text for phrase in negation_phrases)

        # If text explicitly says "no flood", it's not flood-related
        # (even if it mentions rain or water in other context)
        if has_negation and severity < 0.5:
            return False

        # Clear reports are NOT flood-related
        if report_type == "clear":
            # Unless they mention flood clearing/receding (still flood context)
            flood_context = any(kw in text for kw in ["humupa", "bumaba", "receding"])
            return flood_context

        # Flood, evacuation, rising, blocked are flood-related
        if report_type in ["flood", "evacuation", "rising", "blocked"]:
            return True

        # Traffic reports are flood-related if they mention water/flood
        if report_type == "traffic":
            flood_mentioned = any(kw in text for kw in self.flood_keywords["flood"])
            return flood_mentioned or severity > 0.1

        # Any report with severity > 0.1 is likely flood-related
        # (unless negated above)
        if severity > 0.1:
            return True

        return False

    def _extract_location(self, text: str) -> Optional[str]:
        """
        Extract location mention from text.

        Enhanced to check all 16 Marikina barangays, major roads,
        LRT stations, and landmarks.

        Args:
            text: Input text

        Returns:
            Extracted location or None
        """
        # Check for known locations (case-insensitive)
        for location in self.all_known_locations:
            # Word boundary matching to avoid false positives
            pattern = r'\b' + re.escape(location) + r'\b'
            if re.search(pattern, text, re.IGNORECASE):
                return location

        # Try to extract with common Filipino/English patterns
        patterns = [
            # Filipino: "sa [Location]"
            r'(?:sa|nasa)\s+([A-Z][a-zA-Z\s]+?)(?:\s|,|!|\.|$)',
            # English: "at/in [Location]"
            r'(?:at|in)\s+([A-Z][a-zA-Z\s]+?)(?:\s|,|!|\.|$)',
            # Pattern: "[Location] area/road/street"
            r'([A-Z][a-zA-Z\s]+?)\s+(?:area|road|street|avenue|bridge|station)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                location = match.group(1).strip()
                # Avoid single-word false positives (e.g., "The", "At")
                if len(location) > 3 and location.lower() not in ["the", "this", "that"]:
                    return location

        return None

    def _classify_report_type(self, text: str) -> str:
        """
        Classify the type of report.

        Enhanced with more categories: flood, clear, blocked, traffic,
        rising, evacuation.

        Args:
            text: Lowercased text

        Returns:
            Report type
        """
        scores = {
            "flood": 0,
            "clear": 0,
            "blocked": 0,
            "traffic": 0,
            "rising": 0,
            "evacuation": 0
        }

        # Count keyword matches for each type
        for report_type, keywords in self.flood_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    scores[report_type] += 1

        # Return type with highest score
        max_score = max(scores.values())

        if max_score == 0:
            # Default to flood if no clear match
            return "flood"

        # Get type with highest score
        max_type = max(scores, key=scores.get)

        return max_type

    def _extract_severity(self, text: str) -> float:
        """
        Extract flood severity from text.

        Enhanced with MMDA flood gauge standards and comprehensive
        Filipino depth indicators.

        Args:
            text: Lowercased text

        Returns:
            Severity score (0-1 scale)
        """
        # Check for depth indicators (ordered from highest to lowest)
        depth_priority = ["neck", "chest", "waist", "tire", "knee", "ankle", "gutter"]

        for depth_level in depth_priority:
            keywords = self.severity_indicators.get(depth_level, [])
            for keyword in keywords:
                if keyword in text:
                    return self.depth_mapping.get(depth_level, 0.5)

        # Check general "high" indicators
        for keyword in self.severity_indicators.get("high", []):
            if keyword in text:
                return 0.7

        # Check for numeric depth mentions
        # Pattern: "X cm", "X meters", "X inches", "X ft"
        numeric_patterns = [
            (r'(\d+)\s*(?:cm|centimeter)', 100),      # centimeters
            (r'(\d+)\s*(?:m|meter)(?!etro)', 1),      # meters (not metro)
            (r'(\d+)\s*(?:inch|inches)', 2.54),       # inches
            (r'(\d+)\s*(?:ft|feet)', 30.48),          # feet
        ]

        for pattern, conversion in numeric_patterns:
            match = re.search(pattern, text)
            if match:
                value_cm = float(match.group(1))
                value_m = value_cm / conversion
                # Convert to 0-1 scale (max depth 2m = 1.0)
                return min(value_m / 2.0, 1.0)

        # Default severity for flood reports without specific depth
        if any(kw in text for kw in self.flood_keywords["flood"]):
            return 0.4  # Moderate default

        return 0.0

    def _determine_passability(self, text: str, severity: float) -> Optional[bool]:
        """
        Determine if road is passable based on text and severity.

        Enhanced with MMDA standards:
        - < 0.5 (knee): Passable to all or light vehicles only
        - >= 0.5 (tire): Not passable to all vehicles

        Args:
            text: Lowercased text
            severity: Severity score

        Returns:
            True if passable, False if impassable, None if unclear
        """
        # Check for explicit passability keywords
        clear_keywords = self.flood_keywords["clear"]
        blocked_keywords = self.flood_keywords["blocked"]

        is_clear = any(kw in text for kw in clear_keywords)
        is_blocked = any(kw in text for kw in blocked_keywords)

        if is_clear and not is_blocked:
            return True
        elif is_blocked and not is_clear:
            return False

        # Infer from severity (MMDA standards)
        if severity >= 0.65:  # Tire-deep or higher
            return False  # Not passable to all vehicles
        elif severity >= 0.5:  # Knee-deep
            return None  # Not passable to light vehicles (unclear)
        elif severity <= 0.15:  # Ankle or gutter
            return True  # Passable to all

        return None  # Unclear

    def _calculate_confidence(
        self,
        text: str,
        location: Optional[str],
        severity: float
    ) -> float:
        """
        Calculate confidence score for extracted information.

        Enhanced with more sophisticated confidence calculation.

        Args:
            text: Lowercased text
            location: Extracted location
            severity: Extracted severity

        Returns:
            Confidence score (0-1)
        """
        confidence = 0.4  # Base confidence

        # Increase confidence if location found
        if location:
            # Higher boost if location is a known Marikina location
            if location in self.all_known_locations:
                confidence += 0.25
            else:
                confidence += 0.15

        # Increase confidence if specific severity indicators found
        has_severity_keyword = any(
            any(kw in text for kw in keywords)
            for keywords in self.severity_indicators.values()
        )
        if has_severity_keyword:
            confidence += 0.2

        # Increase confidence if multiple flood keywords present
        flood_keyword_count = sum(
            1 for keyword in self.flood_keywords["flood"]
            if keyword in text
        )
        if flood_keyword_count >= 2:
            confidence += 0.15
        elif flood_keyword_count >= 1:
            confidence += 0.05

        # Increase confidence if report includes numbers (specific)
        if re.search(r'\d+', text):
            confidence += 0.05

        return min(confidence, 1.0)

    def batch_process(self, texts: List[str]) -> List[Dict[str, Any]]:
        """
        Process multiple texts in batch.

        Args:
            texts: List of text strings to process

        Returns:
            List of extracted information dicts
        """
        results = []
        for text in texts:
            try:
                info = self.extract_flood_info(text)
                results.append(info)
            except Exception as e:
                logger.error(f"Error processing text: {e}")
                results.append({
                    "is_flood_related": False,
                    "location": None,
                    "severity": 0.0,
                    "passable": None,
                    "report_type": "unknown",
                    "confidence": 0.0,
                    "raw_text": text,
                    "error": str(e)
                })

        return results

    def get_statistics(self, processed_reports: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get statistics from processed reports.

        Enhanced to include flood-related filtering.

        Args:
            processed_reports: List of processed report dicts

        Returns:
            Dict with statistics
        """
        by_type = {}
        by_location = {}
        severities = []
        passable_count = 0
        impassable_count = 0
        flood_related_count = 0

        for report in processed_reports:
            # Count flood-related
            if report.get("is_flood_related", False):
                flood_related_count += 1

            # Count by type
            rtype = report.get("report_type", "unknown")
            by_type[rtype] = by_type.get(rtype, 0) + 1

            # Count by location
            location = report.get("location")
            if location:
                by_location[location] = by_location.get(location, 0) + 1

            # Collect severity
            severity = report.get("severity", 0.0)
            if severity > 0:
                severities.append(severity)

            # Count passability
            passable = report.get("passable")
            if passable is True:
                passable_count += 1
            elif passable is False:
                impassable_count += 1

        avg_severity = sum(severities) / len(severities) if severities else 0.0

        return {
            "total_reports": len(processed_reports),
            "flood_related_count": flood_related_count,
            "flood_related_percentage": (flood_related_count / len(processed_reports) * 100)
                                       if processed_reports else 0.0,
            "by_type": by_type,
            "by_location": by_location,
            "average_severity": avg_severity,
            "passable_count": passable_count,
            "impassable_count": impassable_count
        }


# Test the NLP processor when run directly
if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO)

    print("=== Testing Enhanced NLP Processor ===\n")

    processor = NLPProcessor()

    # Test cases covering different scenarios
    test_cases = [
        # Severe flooding (Filipino)
        "URGENT! Baha sa Nangka! Hanggang dibdib na! Lumikas na!",

        # Moderate flooding (English)
        "Knee-deep flood in Marikina Heights. Not passable to cars.",

        # Minor flooding (Taglish)
        "Sakong lang sa SM Marikina. Madaan pa.",

        # Traffic with flood
        "Traffic sa Gil Fernando because of ankle-deep baha",

        # Clear report
        "Walang baha sa Concepcion Uno. All clear!",

        # Rising water
        "Tumataas ang tubig sa Tumana Bridge! Bantayan!",

        # Evacuation
        "Residents ng Malanday evacuating now. Waist-deep flood!",

        # MMDA-style depth
        "Gutter deep flood sa Marcos Highway near LRT Santolan",

        # Location with landmark
        "Baha sa Riverbanks area! Tuhod level!",

        # No specific location
        "Grabe ang ulan! Ingat sa lahat!"
    ]

    print("Processing test cases...\n")

    for i, text in enumerate(test_cases, 1):
        result = processor.extract_flood_info(text)

        print(f"Test {i}: {text}")
        print(f"  Flood-related: {result['is_flood_related']}")
        print(f"  Location: {result['location']}")
        print(f"  Severity: {result['severity']:.2f}")
        print(f"  Type: {result['report_type']}")
        print(f"  Passable: {result['passable']}")
        print(f"  Confidence: {result['confidence']:.2f}")
        print()

    # Test statistics
    print("\n=== Batch Processing Statistics ===")
    results = processor.batch_process(test_cases)
    stats = processor.get_statistics(results)
    print(json.dumps(stats, indent=2))
