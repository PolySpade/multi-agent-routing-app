# filename: app/ml_models/nlp_processor.py

"""
NLP Processor for Social Media Flood Reports (MAS-FRO)

This module implements natural language processing functions for extracting
flood-related information from social media text (Twitter/X, Facebook posts).
Handles both Filipino and English text commonly used in Marikina area flood
reports.

Key Functions:
- Location extraction (street names, landmarks)
- Severity assessment (depth indicators, passability)
- Report classification (flood, clear, traffic)

Author: MAS-FRO Development Team
Date: November 2025
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

    Attributes:
        flood_keywords: Keywords indicating flooding
        severity_indicators: Keywords for severity assessment
        location_patterns: Regex patterns for location extraction

    Example:
        >>> processor = NLPProcessor()
        >>> info = processor.extract_flood_info(
        ...     "Baha sa J.P. Rizal, tuhod level! Hindi madaan!"
        ... )
        >>> print(info['severity'])
        0.6
    """

    def __init__(self):
        """Initialize the NLP processor with keyword dictionaries."""

        # Flood-related keywords (Filipino and English)
        self.flood_keywords = {
            "flood": ["baha", "flood", "flooded", "binaha", "apaw", "tubig"],
            "clear": ["clear", "walang baha", "okay", "passable", "madaan", "safe"],
            "blocked": ["blocked", "sarado", "hindi madaan", "impassable", "barado"],
            "traffic": ["traffic", "trapik", "bara", "slow", "mabagal"]
        }

        # Severity indicators by depth
        self.severity_indicators = {
            "ankle": ["ankle", "sakong", "binti", "ankle-deep"],
            "knee": ["knee", "tuhod", "knee-deep", "tuhod level"],
            "waist": ["waist", "baywang", "bewang", "waist-deep"],
            "chest": ["chest", "dibdib", "chest-deep"],
            "neck": ["neck", "leeg"],
            "high": ["mataas", "high", "deep", "malalim"]
        }

        # Common Marikina locations
        self.known_locations = [
            "J.P. Rizal", "JP Rizal", "Rizal",
            "Nangka", "Concepcion", "Marikina Heights",
            "SSS Village", "Provident", "IPI",
            "Malanday", "Kalumpang", "Tumana",
            "Parang", "Marikina River", "LRT",
            "Shoe Avenue", "Sumulong Highway"
        ]

        # Depth-to-severity mapping (meters to 0-1 scale)
        self.depth_mapping = {
            "ankle": 0.15,  # ~15cm
            "knee": 0.5,  # ~50cm
            "waist": 0.8,  # ~80cm
            "chest": 0.9,  # ~1.2m
            "neck": 0.95  # ~1.5m
        }

        logger.info("NLPProcessor initialized")

    def extract_flood_info(self, text: str) -> Dict[str, Any]:
        """
        Extract flood information from social media text.

        Analyzes text to extract:
        - Location mentioned
        - Flood severity
        - Road passability
        - Report type

        Args:
            text: Social media post text (Filipino/English/mixed)

        Returns:
            Dict containing extracted information:
                {
                    "location": str or None,
                    "severity": float (0-1),
                    "passable": bool or None,
                    "report_type": str ("flood", "clear", "blocked", "traffic"),
                    "confidence": float (0-1),
                    "raw_text": str
                }

        Example:
            >>> info = processor.extract_flood_info(
            ...     "Baha sa Nangka! Tuhod level, hindi madaan ng kotse!"
            ... )
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

        return {
            "location": location,
            "severity": severity,
            "passable": passable,
            "report_type": report_type,
            "confidence": confidence,
            "raw_text": text
        }

    def _extract_location(self, text: str) -> Optional[str]:
        """
        Extract location mention from text.

        Args:
            text: Input text

        Returns:
            Extracted location or None
        """
        # Check for known locations
        for location in self.known_locations:
            # Case-insensitive search
            if re.search(r'\b' + re.escape(location) + r'\b', text, re.IGNORECASE):
                return location

        # Try to extract with common patterns
        # Pattern: "sa/at/in [Location]"
        patterns = [
            r'(?:sa|at|in)\s+([A-Z][a-zA-Z\s]+?)(?:\s|,|!|\.|$)',
            r'([A-Z][a-zA-Z\s]+?)\s+(?:area|road|street|avenue)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                location = match.group(1).strip()
                if len(location) > 3:  # Avoid single-word false positives
                    return location

        return None

    def _classify_report_type(self, text: str) -> str:
        """
        Classify the type of report.

        Args:
            text: Lowercased text

        Returns:
            Report type: "flood", "clear", "blocked", or "traffic"
        """
        scores = {
            "flood": 0,
            "clear": 0,
            "blocked": 0,
            "traffic": 0
        }

        # Count keyword matches for each type
        for report_type, keywords in self.flood_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    scores[report_type] += 1

        # Return type with highest score
        max_type = max(scores, key=scores.get)

        # Default to flood if no clear match
        if scores[max_type] == 0:
            return "flood"

        return max_type

    def _extract_severity(self, text: str) -> float:
        """
        Extract flood severity from text.

        Args:
            text: Lowercased text

        Returns:
            Severity score (0-1 scale)
        """
        # Check for depth indicators
        for depth_level, keywords in self.severity_indicators.items():
            for keyword in keywords:
                if keyword in text:
                    return self.depth_mapping.get(depth_level, 0.5)

        # Check for numeric depth mentions
        # Pattern: "X cm", "X meters", "X ft"
        numeric_patterns = [
            (r'(\d+)\s*cm', 100),  # centimeters
            (r'(\d+)\s*m(?:eter)?', 1),  # meters
            (r'(\d+)\s*ft', 0.3048),  # feet
        ]

        for pattern, conversion in numeric_patterns:
            match = re.search(pattern, text)
            if match:
                value = float(match.group(1)) / conversion
                # Convert to 0-1 scale (max depth 2m = 1.0)
                return min(value / 2.0, 1.0)

        # Default severity for flood reports without specific depth
        if any(kw in text for kw in self.flood_keywords["flood"]):
            return 0.4  # Moderate default

        return 0.0

    def _determine_passability(self, text: str, severity: float) -> Optional[bool]:
        """
        Determine if road is passable based on text and severity.

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

        # Infer from severity
        if severity >= 0.6:
            return False  # High severity = impassable
        elif severity <= 0.3:
            return True  # Low severity = passable

        return None  # Unclear

    def _calculate_confidence(
        self,
        text: str,
        location: Optional[str],
        severity: float
    ) -> float:
        """
        Calculate confidence score for extracted information.

        Args:
            text: Lowercased text
            location: Extracted location
            severity: Extracted severity

        Returns:
            Confidence score (0-1)
        """
        confidence = 0.5  # Base confidence

        # Increase confidence if location found
        if location:
            confidence += 0.2

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
            confidence += 0.1

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

        Args:
            processed_reports: List of processed report dicts

        Returns:
            Dict with statistics:
                {
                    "total_reports": int,
                    "by_type": Dict[str, int],
                    "by_location": Dict[str, int],
                    "average_severity": float,
                    "passable_count": int,
                    "impassable_count": int
                }
        """
        by_type = {}
        by_location = {}
        severities = []
        passable_count = 0
        impassable_count = 0

        for report in processed_reports:
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
            "by_type": by_type,
            "by_location": by_location,
            "average_severity": avg_severity,
            "passable_count": passable_count,
            "impassable_count": impassable_count
        }
