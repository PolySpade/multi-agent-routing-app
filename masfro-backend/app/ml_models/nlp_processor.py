# filename: app/ml_models/nlp_processor.py

"""
NLP Processor for Social Media Flood Reports (MAS-FRO)

This module implements ML-based natural language processing for extracting
flood-related information from social media text (Twitter/X, Facebook posts).
Handles both Filipino and English text commonly used in Marikina area flood reports.

Key Features:
- ML-based flood classification (flood vs none)
- spaCy NER for location extraction
- ML-based severity classification (critical, dangerous, minor, none)
- Backward compatible with existing ScoutAgent interface

Author: MAS-FRO Development Team
Date: November 2025
Version: 3.0 - ML-based models with spaCy NER
"""

import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class NLPProcessor:
    """
    ML-based Natural Language Processor for flood reports.

    This class uses trained machine learning models to extract structured
    information from unstructured social media text about flood conditions.

    Models Used:
    - flood_classifier.pkl: Binary classification (flood/none)
    - location_extract (spaCy): Named Entity Recognition for locations
    - severity_classifier.pkl: Multi-class classification (critical/dangerous/minor/none)

    Attributes:
        flood_classifier: Sklearn model for flood detection
        location_model: spaCy NER model for location extraction
        severity_classifier: Sklearn model for severity assessment
        severity_mapping: Maps model output to 0-1 scale

    Example:
        >>> processor = NLPProcessor()
        >>> info = processor.extract_flood_info(
        ...     "Baha sa J.P. Rizal, tuhod level! Hindi madaan!"
        ... )
        >>> print(info['severity'])
        0.8
        >>> print(info['is_flood_related'])
        True
    """

    def __init__(self):
        """Initialize the NLP processor with ML models."""

        # Define model paths
        models_dir = Path(__file__).parent / "new_models"

        self.flood_classifier = None
        self.location_model = None
        self.severity_classifier = None

        # Load flood classifier
        try:
            import joblib
            flood_model_path = models_dir / "flood_classifier.pkl"
            self.flood_classifier = joblib.load(flood_model_path)
            logger.info(f"Flood classifier loaded from {flood_model_path}")
        except ImportError:
            logger.error("joblib not installed. Install with: uv add joblib")
            logger.warning("Flood detection will fall back to rule-based method")
        except Exception as e:
            logger.error(f"Failed to load flood classifier: {e}")
            logger.warning("Flood detection will fall back to rule-based method")

        # Load spaCy location extraction model
        try:
            import spacy
            location_model_path = models_dir / "location_extract"
            self.location_model = spacy.load(str(location_model_path))
            logger.info(f"Location extraction model loaded from {location_model_path}")
        except ImportError:
            logger.error("spaCy not installed. Install with: pip install spacy")
            logger.warning("Location extraction will fall back to rule-based method")
        except Exception as e:
            logger.error(f"Failed to load location extraction model: {e}")
            logger.warning("Location extraction will fall back to rule-based method")

        # Load severity classifier
        try:
            import joblib
            severity_model_path = models_dir / "severity_classifier.pkl"
            self.severity_classifier = joblib.load(severity_model_path)
            logger.info(f"Severity classifier loaded from {severity_model_path}")
        except ImportError:
            logger.error("joblib not installed. Install with: uv add joblib")
            logger.warning("Severity assessment will fall back to rule-based method")
        except Exception as e:
            logger.error(f"Failed to load severity classifier: {e}")
            logger.warning("Severity assessment will fall back to rule-based method")

        # Severity mapping: Model output -> 0-1 scale
        # Based on MMDA flood depth standards
        self.severity_mapping = {
            "none": 0.0,        # No flooding
            "minor": 0.3,       # Gutter to ankle (passable)
            "dangerous": 0.65,  # Knee to waist (not passable)
            "critical": 0.95    # Chest to neck (life-threatening)
        }

        # Report type mapping based on severity
        self.report_type_mapping = {
            "none": "clear",
            "minor": "flood",
            "dangerous": "blocked",
            "critical": "evacuation"
        }

        # Passability rules based on severity
        self.passability_rules = {
            "none": True,       # Clear, passable
            "minor": True,      # Minor flooding, still passable
            "dangerous": False, # Not passable
            "critical": False   # Definitely not passable
        }

        # Fallback keywords for rule-based methods
        self._init_fallback_keywords()

        logger.info("NLPProcessor v3.0 initialized with ML models")
        logger.info(f"  - Flood classifier: {'OK' if self.flood_classifier else 'FALLBACK'}")
        logger.info(f"  - Location model: {'OK' if self.location_model else 'FALLBACK'}")
        logger.info(f"  - Severity classifier: {'OK' if self.severity_classifier else 'FALLBACK'}")

    def _init_fallback_keywords(self):
        """Initialize fallback keywords for rule-based processing."""

        # Minimal keyword set for fallback
        self.flood_keywords = [
            "baha", "flood", "flooded", "flooding", "bumaha", "pagbaha",
            "water", "tubig", "ulan", "rain"
        ]

        self.clear_keywords = [
            "clear", "cleared", "walang baha", "no flood", "okay",
            "passable", "madaan", "safe"
        ]

        self.severity_keywords = {
            "minor": ["gutter", "ankle", "sakong", "mababaw"],
            "dangerous": ["knee", "waist", "tuhod", "baywang", "tire"],
            "critical": ["chest", "neck", "dibdib", "leeg", "grabe", "malala"]
        }

        # Simple Marikina location patterns
        self.location_patterns = [
            r'\b(Barangka|Nangka|Malanday|Tumana|Parang|Concepcion|Fortune)\b',
            r'\b(Marikina Heights|Industrial Valley|IVC|San Roque|Sta\.? Elena)\b',
            r'\b(SM Marikina|Riverbanks|Marcos Highway|Sumulong)\b',
            r'\bsa\s+([A-Z][a-zA-Z\s]+?)(?:\s|,|!|\.)',
            r'\bat\s+([A-Z][a-zA-Z\s]+?)(?:\s|,|!|\.)'
        ]

    def extract_flood_info(self, text: str) -> Dict[str, Any]:
        """
        Extract flood information from social media text using ML models.

        Analyzes text to extract:
        - Whether report is flood-related (ML classifier)
        - Location mentioned (spaCy NER)
        - Flood severity (ML classifier)
        - Road passability (rule-based from severity)
        - Report type (derived from severity)

        Args:
            text: Social media post text (Filipino/English/mixed)

        Returns:
            Dict containing extracted information:
                {
                    "is_flood_related": bool,
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

        # 1. Flood classification (ML or fallback)
        is_flood_related, flood_confidence = self._classify_flood(text)

        # 2. Location extraction (spaCy NER or fallback)
        location, location_confidence = self._extract_location(text)

        # 3. Severity classification (ML or fallback)
        severity_label, severity_score = self._classify_severity(text)

        # 4. Map severity to 0-1 scale
        # If model outputs unknown label, default to 0.0
        severity = self.severity_mapping.get(severity_label, 0.0)

        # If unknown severity label, log warning and use fallback
        if severity_label not in self.severity_mapping:
            logger.warning(
                f"Unknown severity label '{severity_label}'. "
                f"Expected: {list(self.severity_mapping.keys())}. Defaulting to 'none'."
            )
            severity_label = "none"
            severity = 0.0

        # 5. Determine report type from severity
        report_type = self.report_type_mapping.get(severity_label, "flood")

        # 6. Determine passability from severity
        passable = self.passability_rules.get(severity_label, None)

        # 7. Calculate overall confidence
        confidence = self._calculate_overall_confidence(
            flood_confidence,
            location_confidence,
            severity_score
        )

        return {
            "is_flood_related": is_flood_related,
            "location": location,
            "severity": severity,
            "passable": passable,
            "report_type": report_type,
            "confidence": confidence,
            "raw_text": text,
            # Additional metadata
            "severity_label": severity_label,  # Raw model output
            "model_confidence": {
                "flood": flood_confidence,
                "location": location_confidence,
                "severity": severity_score
            }
        }

    def _classify_flood(self, text: str) -> tuple[bool, float]:
        """
        Classify if text is flood-related using ML model.

        Args:
            text: Input text

        Returns:
            (is_flood: bool, confidence: float)
        """
        if self.flood_classifier is None:
            # Fallback: Rule-based classification
            return self._classify_flood_fallback(text)

        try:
            # Use ML model
            # Assuming classifier has predict_proba method
            prediction = self.flood_classifier.predict([text])[0]

            # Get probability scores if available
            if hasattr(self.flood_classifier, 'predict_proba'):
                proba = self.flood_classifier.predict_proba([text])[0]
                confidence = float(max(proba))
            else:
                confidence = 0.5  # Default confidence if no proba

            is_flood = (prediction == "flood")

            logger.debug(f"Flood classification: {prediction} (confidence: {confidence:.2f})")
            return is_flood, confidence

        except Exception as e:
            logger.error(f"Error in flood classification: {e}")
            return self._classify_flood_fallback(text)

    def _classify_flood_fallback(self, text: str) -> tuple[bool, float]:
        """Fallback rule-based flood classification."""
        text_lower = text.lower()

        # Check for clear/no flood indicators first
        if any(kw in text_lower for kw in self.clear_keywords):
            return False, 0.6

        # Check for flood keywords
        flood_count = sum(1 for kw in self.flood_keywords if kw in text_lower)

        if flood_count >= 1:
            confidence = min(0.5 + (flood_count * 0.15), 0.9)
            return True, confidence

        return False, 0.3

    def _extract_location(self, text: str) -> tuple[Optional[str], float]:
        """
        Extract location using spaCy NER model.

        Args:
            text: Input text

        Returns:
            (location: str or None, confidence: float)
        """
        if self.location_model is None:
            # Fallback: Rule-based extraction
            return self._extract_location_fallback(text)

        try:
            # Use spaCy NER model
            doc = self.location_model(text)

            # Extract location entities
            locations = [ent.text for ent in doc.ents if ent.label_ == "LOC"]

            if locations:
                # Clean and filter locations
                cleaned_locations = []
                for loc in locations:
                    # Split on punctuation and take first part (in case entity spans multiple phrases)
                    import re
                    parts = re.split(r'[.!?;]+', loc)
                    cleaned = parts[0].strip() if parts else loc

                    # Remove trailing and leading punctuation from cleaned part
                    cleaned = cleaned.strip('.,!?;:')

                    # Remove common suffixes/prefixes that aren't part of location
                    stop_words = ['area', 'near', 'at', 'sa', 'ng', 'pa', 'na', 'ko', 'ka']
                    words = cleaned.split()

                    # Remove stop words from the end
                    while words and words[-1].lower() in stop_words:
                        words.pop()

                    # Remove stop words from the beginning
                    while words and words[0].lower() in stop_words:
                        words.pop(0)

                    cleaned = ' '.join(words) if words else cleaned

                    # Filter out common false positives
                    false_positives = [
                        'urgent', 'update', 'alert', 'warning', 'help',
                        'all', 'now', 'today', 'yesterday', 'ulan', 'rain',
                        'baha', 'flood', 'tubig', 'water', 'bantayan',
                        'madaan', 'lahat'
                    ]

                    if cleaned.lower() not in false_positives and len(cleaned) > 2:
                        cleaned_locations.append(cleaned)

                if cleaned_locations:
                    # Return first valid location with high confidence
                    location = cleaned_locations[0]
                    confidence = 0.85  # Default high confidence for NER

                    logger.debug(f"Location extracted: {location} (confidence: {confidence:.2f})")
                    return location, confidence

            logger.debug("No valid location entities found")
            return None, 0.0

        except Exception as e:
            logger.error(f"Error in location extraction: {e}")
            return self._extract_location_fallback(text)

    def _extract_location_fallback(self, text: str) -> tuple[Optional[str], float]:
        """Fallback rule-based location extraction."""

        for pattern in self.location_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                location = match.group(1) if match.lastindex else match.group(0)
                location = location.strip()

                # Filter out false positives
                if len(location) > 3 and location.lower() not in ["the", "this", "that"]:
                    return location, 0.5

        return None, 0.0

    def _classify_severity(self, text: str) -> tuple[str, float]:
        """
        Classify severity using ML model.

        Args:
            text: Input text

        Returns:
            (severity_label: str, confidence: float)
            Severity labels: "critical", "dangerous", "minor", "none"
        """
        if self.severity_classifier is None:
            # Fallback: Rule-based classification
            return self._classify_severity_fallback(text)

        try:
            # Use ML model
            prediction = self.severity_classifier.predict([text])[0]

            # Get probability scores if available
            if hasattr(self.severity_classifier, 'predict_proba'):
                proba = self.severity_classifier.predict_proba([text])[0]
                confidence = float(max(proba))
            else:
                confidence = 0.8  # Default confidence

            logger.debug(f"Severity classification: {prediction} (confidence: {confidence:.2f})")
            return prediction, confidence

        except Exception as e:
            logger.error(f"Error in severity classification: {e}")
            return self._classify_severity_fallback(text)

    def _classify_severity_fallback(self, text: str) -> tuple[str, float]:
        """Fallback rule-based severity classification."""
        text_lower = text.lower()

        # Check from highest to lowest severity
        for severity_level in ["critical", "dangerous", "minor"]:
            keywords = self.severity_keywords.get(severity_level, [])
            if any(kw in text_lower for kw in keywords):
                return severity_level, 0.6

        # Default to none if no severity keywords found
        return "none", 0.4

    def _calculate_overall_confidence(
        self,
        flood_conf: float,
        location_conf: float,
        severity_conf: float
    ) -> float:
        """
        Calculate overall confidence from component confidences.

        Args:
            flood_conf: Flood classification confidence
            location_conf: Location extraction confidence
            severity_conf: Severity classification confidence

        Returns:
            Overall confidence (0-1)
        """
        # Weighted average (flood classification is most important)
        weights = {
            'flood': 0.4,
            'location': 0.3,
            'severity': 0.3
        }

        overall = (
            flood_conf * weights['flood'] +
            location_conf * weights['location'] +
            severity_conf * weights['severity']
        )

        return min(overall, 1.0)

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

        Args:
            processed_reports: List of processed report dicts

        Returns:
            Dict with statistics
        """
        by_type = {}
        by_location = {}
        by_severity_label = {}
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

            # Count by severity label
            severity_label = report.get("severity_label", "none")
            by_severity_label[severity_label] = by_severity_label.get(severity_label, 0) + 1

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
            "by_severity_label": by_severity_label,
            "by_location": by_location,
            "average_severity": avg_severity,
            "passable_count": passable_count,
            "impassable_count": impassable_count
        }


# Test the NLP processor when run directly
if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO)

    print("=== Testing ML-based NLP Processor v3.0 ===\n")

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
        print(f"  Severity: {result['severity']:.2f} ({result['severity_label']})")
        print(f"  Type: {result['report_type']}")
        print(f"  Passable: {result['passable']}")
        print(f"  Confidence: {result['confidence']:.2f}")
        print()

    # Test statistics
    print("\n=== Batch Processing Statistics ===")
    results = processor.batch_process(test_cases)
    stats = processor.get_statistics(results)
    print(json.dumps(stats, indent=2))
