# filename: app/services/simulated_image_analyzer.py

"""
Simulated Image Analyzer for MAS-FRO ScoutAgent

This module provides a fallback image analyzer when Qwen 3-VL or other vision
models are unavailable. It uses filename patterns and metadata to simulate
image analysis results for testing purposes.

This enables the full ScoutAgent pipeline to be tested without:
- Running Ollama locally
- Having GPU resources
- Actual flood images

Author: MAS-FRO Development Team
Date: February 2026
"""

import re
import random
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class SimulatedImageAnalyzer:
    """
    Simulates vision model analysis for flood images.

    Uses filename patterns to determine flood severity and returns
    pre-defined analysis results for testing the ScoutAgent pipeline.

    Supported filename patterns:
    - ankle_deep_*.jpg  -> Minor flooding (0.1-0.15m)
    - knee_deep_*.jpg   -> Moderate flooding (0.3-0.45m)
    - waist_deep_*.jpg  -> Severe flooding (0.6-0.9m)
    - chest_deep_*.jpg  -> Critical flooding (1.0-1.5m)
    - flood_*.jpg       -> Random severity (for variety)

    Example:
        >>> analyzer = SimulatedImageAnalyzer()
        >>> result = analyzer.analyze("flood_levels/knee_deep_01.jpg")
        >>> print(result['estimated_depth_m'])
        0.35
    """

    # Flood level configurations
    FLOOD_LEVELS = {
        "ankle": {
            "depth_range": (0.10, 0.15),
            "risk_range": (0.15, 0.25),
            "vehicles_passable": ["car", "suv", "truck", "motorcycle", "bicycle"],
            "flow_options": ["still", "slow"],
            "indicators": [
                "Water barely covering feet",
                "Shallow puddles on road surface",
                "Curb partially submerged"
            ]
        },
        "knee": {
            "depth_range": (0.30, 0.45),
            "risk_range": (0.40, 0.55),
            "vehicles_passable": ["suv", "truck"],
            "flow_options": ["slow", "moderate"],
            "indicators": [
                "Water reaching knee level on pedestrians",
                "Car tires partially submerged",
                "Sidewalk fully underwater"
            ]
        },
        "waist": {
            "depth_range": (0.60, 0.90),
            "risk_range": (0.70, 0.85),
            "vehicles_passable": ["truck"],
            "flow_options": ["moderate", "fast"],
            "indicators": [
                "Water at waist level",
                "Vehicles stalled and abandoned",
                "Strong current visible",
                "Debris floating in water"
            ]
        },
        "chest": {
            "depth_range": (1.00, 1.50),
            "risk_range": (0.90, 1.00),
            "vehicles_passable": [],
            "flow_options": ["fast", "dangerous"],
            "indicators": [
                "Water at chest level or higher",
                "Vehicles fully submerged",
                "Rescue boats visible",
                "Residents on rooftops",
                "Life-threatening conditions"
            ]
        }
    }

    def __init__(self, add_variance: bool = True):
        """
        Initialize the simulated analyzer.

        Args:
            add_variance: If True, add random variance to results for realism
        """
        self.add_variance = add_variance
        logger.info("SimulatedImageAnalyzer initialized (fallback mode)")

    def analyze(self, image_path: str) -> Dict[str, Any]:
        """
        Analyze an image and return simulated flood analysis.

        Determines flood level from filename pattern and returns
        appropriate analysis results.

        Args:
            image_path: Path to the image file

        Returns:
            Dict with simulated analysis:
            {
                "estimated_depth_m": float,
                "risk_score": float,
                "vehicles_passable": List[str],
                "visual_indicators": str,
                "flow_assessment": str,
                "visibility": str,
                "confidence": float,
                "source": str,
                "simulated": bool
            }
        """
        if not image_path:
            logger.warning("No image path provided")
            return {}

        # Determine flood level from filename
        flood_level = self._detect_flood_level(image_path)

        if flood_level is None:
            logger.debug(f"No flood level pattern found in: {image_path}")
            # Return random moderate result for unknown patterns
            flood_level = random.choice(["ankle", "knee", "waist"])

        config = self.FLOOD_LEVELS[flood_level]

        # Generate values with optional variance
        depth_min, depth_max = config["depth_range"]
        risk_min, risk_max = config["risk_range"]

        if self.add_variance:
            depth = round(random.uniform(depth_min, depth_max), 2)
            risk = round(random.uniform(risk_min, risk_max), 2)
        else:
            depth = round((depth_min + depth_max) / 2, 2)
            risk = round((risk_min + risk_max) / 2, 2)

        # Build result
        result = {
            "estimated_depth_m": depth,
            "risk_score": risk,
            "vehicles_passable": config["vehicles_passable"].copy(),
            "visual_indicators": random.choice(config["indicators"]),
            "flow_assessment": random.choice(config["flow_options"]),
            "visibility": random.choice(["clear", "murky", "debris-filled"]),
            "confidence": 0.75 if self.add_variance else 0.90,
            "source": "simulated_analyzer",
            "simulated": True,
            "detected_level": flood_level,
            "image_analyzed": str(image_path)
        }

        logger.info(
            f"[SimulatedAnalyzer] Image: {Path(image_path).name}, "
            f"level={flood_level}, depth={depth}m, risk={risk}"
        )

        return result

    def _detect_flood_level(self, image_path: str) -> Optional[str]:
        """
        Detect flood level from filename pattern.

        Args:
            image_path: Path to image file

        Returns:
            Flood level string or None if not detected
        """
        filename = Path(image_path).name.lower()

        patterns = {
            "ankle": r"ankle[_-]?deep",
            "knee": r"knee[_-]?deep",
            "waist": r"waist[_-]?deep",
            "chest": r"chest[_-]?deep|critical|severe"
        }

        for level, pattern in patterns.items():
            if re.search(pattern, filename):
                return level

        # Check for generic flood indicators with severity hints
        if re.search(r"minor|light|shallow", filename):
            return "ankle"
        elif re.search(r"moderate|medium", filename):
            return "knee"
        elif re.search(r"heavy|high", filename):
            return "waist"
        elif re.search(r"extreme|critical|severe|emergency", filename):
            return "chest"

        return None

    def is_available(self) -> bool:
        """Check if analyzer is available (always True for simulated)."""
        return True

    def get_health(self) -> Dict[str, Any]:
        """Get health status for API endpoint."""
        return {
            "available": True,
            "mode": "simulated",
            "supported_levels": list(self.FLOOD_LEVELS.keys()),
            "add_variance": self.add_variance
        }


# Singleton instance
_simulated_analyzer: Optional[SimulatedImageAnalyzer] = None


def get_simulated_analyzer() -> SimulatedImageAnalyzer:
    """Get or create the global simulated analyzer instance."""
    global _simulated_analyzer
    if _simulated_analyzer is None:
        _simulated_analyzer = SimulatedImageAnalyzer()
    return _simulated_analyzer
