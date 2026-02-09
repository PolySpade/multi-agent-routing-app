# filename: app/services/llm_service.py

"""
LLM Service for Multi-Agent System for Flood Route Optimization (MAS-FRO)

This module provides a centralized service for LLM text and vision model
integration via the Ollama API. The service enables enhanced semantic
understanding for flood report analysis and multimodal flood detection.

Supported models (configurable via environment variables):
- Text models: moondream, qwen3, llama3, etc.
- Vision models: moondream, qwen3-vl, llava, etc.

Key Features:
- LLM text model for unstructured report parsing
- LLM vision model for flood image analysis
- Response caching for performance optimization
- Graceful degradation when LLM is unavailable
- Health check with caching

Author: MAS-FRO Development Team
Date: February 2026
"""

import json
import base64
import hashlib
import time
import logging
from typing import Dict, Optional, Any, List
from pathlib import Path
from functools import lru_cache
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Try to import ollama, gracefully handle if not installed
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    logger.warning("Ollama package not installed. LLM features will be disabled.")


class LLMService:
    """
    Centralized LLM service for text and vision models via Ollama.

    Wraps the Ollama API for structured flood data extraction.
    Provides graceful degradation when LLM is unavailable.

    Attributes:
        text_model: Name of the text model (from LLM_TEXT_MODEL env var)
        vision_model: Name of the vision model (from LLM_VISION_MODEL env var)
        base_url: Ollama API base URL
        timeout: Request timeout in seconds
        enabled: Whether LLM is enabled via configuration
        _available: Cached availability status
        _last_health_check: Timestamp of last health check
        _response_cache: Cache for LLM responses

    Example:
        >>> llm = LLMService()
        >>> result = llm.analyze_text_report("Baha sa J.P. Rizal, halos tuhod na ang tubig!")
        >>> print(result)
        {'location': 'J.P. Rizal', 'severity': 0.5, 'is_flood_related': True, ...}
    """

    # Cache configuration
    HEALTH_CHECK_CACHE_SECONDS = 60  # Cache health check for 1 minute
    RESPONSE_CACHE_SIZE = 100  # Max cached responses
    RESPONSE_CACHE_TTL_SECONDS = 300  # Cache responses for 5 minutes

    def __init__(
        self,
        text_model: Optional[str] = None,
        vision_model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 30,
        enabled: bool = True
    ):
        """
        Initialize the LLM Service.

        Args:
            text_model: Text model name (default from LLM_TEXT_MODEL env var)
            vision_model: Vision model name (default from LLM_VISION_MODEL env var)
            base_url: Ollama API URL (default from OLLAMA_BASE_URL env var)
            timeout: Request timeout in seconds (default: 30)
            enabled: Whether LLM is enabled (default: True)
        """
        # Load configuration from environment or use defaults
        self.text_model = text_model or self._get_env("LLM_TEXT_MODEL", "llama3.2:latest")
        self.vision_model = vision_model or self._get_env("LLM_VISION_MODEL", "moondream:latest")
        self.base_url = base_url or self._get_env("OLLAMA_BASE_URL", "http://localhost:11434")
        self.timeout = int(self._get_env("LLM_TIMEOUT_SECONDS", str(timeout)))
        self.enabled = enabled and self._get_env("LLM_ENABLED", "true").lower() == "true"

        # Availability tracking
        self._available: Optional[bool] = None
        self._last_health_check: float = 0

        # Response cache: {hash: (response, timestamp)}
        self._response_cache: Dict[str, tuple] = {}

        # Configure Ollama client
        if OLLAMA_AVAILABLE and self.enabled:
            try:
                # Set the host for ollama client
                ollama.Client(host=self.base_url)
                logger.info(
                    f"LLMService initialized: text={self.text_model}, "
                    f"vision={self.vision_model}, url={self.base_url}"
                )
            except Exception as e:
                logger.warning(f"Failed to configure Ollama client: {e}")
        elif not OLLAMA_AVAILABLE:
            logger.warning("LLMService disabled: ollama package not installed")
        else:
            logger.info("LLMService disabled by configuration")

    def _get_env(self, key: str, default: str) -> str:
        """Get environment variable with default fallback."""
        import os
        return os.environ.get(key, default)

    def _get_cache_key(self, prefix: str, content: str) -> str:
        """Generate cache key from content hash."""
        return f"{prefix}:{hashlib.md5(content.encode()).hexdigest()}"

    def _get_cached_response(self, cache_key: str) -> Optional[Dict]:
        """Get cached response if still valid."""
        if cache_key in self._response_cache:
            response, timestamp = self._response_cache[cache_key]
            if time.time() - timestamp < self.RESPONSE_CACHE_TTL_SECONDS:
                logger.debug(f"LLM cache hit for {cache_key[:20]}...")
                return response
            else:
                # Expired, remove from cache
                del self._response_cache[cache_key]
        return None

    def _set_cached_response(self, cache_key: str, response: Dict) -> None:
        """Cache a response with timestamp."""
        # Enforce cache size limit (LRU eviction)
        if len(self._response_cache) >= self.RESPONSE_CACHE_SIZE:
            # Remove oldest entry
            oldest_key = min(
                self._response_cache.keys(),
                key=lambda k: self._response_cache[k][1]
            )
            del self._response_cache[oldest_key]

        self._response_cache[cache_key] = (response, time.time())

    def is_available(self) -> bool:
        """
        Check if LLM service is available.

        Returns cached result if checked recently.

        Returns:
            True if Ollama is running and model is loaded, False otherwise
        """
        if not OLLAMA_AVAILABLE or not self.enabled:
            return False

        # Return cached result if recent
        if self._available is not None:
            if time.time() - self._last_health_check < self.HEALTH_CHECK_CACHE_SECONDS:
                return self._available

        # Perform health check
        try:
            # Try to list models - quick health check
            response = ollama.list()
            self._available = True
            self._last_health_check = time.time()
            logger.debug("LLM service health check: OK")
            return True
        except Exception as e:
            self._available = False
            self._last_health_check = time.time()
            logger.warning(f"LLM service health check failed: {e}")
            return False

    def get_health(self) -> Dict[str, Any]:
        """
        Get detailed health status for API endpoint.

        Returns:
            Dict with health information:
            {
                "available": bool,
                "text_model": str,
                "vision_model": str,
                "base_url": str,
                "models_loaded": List[str],
                "cache_size": int,
                "last_check": str
            }
        """
        health = {
            "available": False,
            "enabled": self.enabled,
            "ollama_installed": OLLAMA_AVAILABLE,
            "text_model": self.text_model,
            "vision_model": self.vision_model,
            "base_url": self.base_url,
            "models_loaded": [],
            "cache_size": len(self._response_cache),
            "last_check": datetime.fromtimestamp(self._last_health_check).isoformat()
                if self._last_health_check > 0 else None
        }

        if not OLLAMA_AVAILABLE or not self.enabled:
            return health

        try:
            response = ollama.list()

            # Helper function to extract model name from various formats
            def get_model_name(m) -> str:
                """Extract model name from dict or object."""
                if isinstance(m, dict):
                    return m.get("name", "") or m.get("model", "")
                # Object-style response (newer ollama package)
                if hasattr(m, 'name') and m.name:
                    return m.name
                if hasattr(m, 'model') and m.model:
                    return m.model
                return str(m)

            # Handle both dict-style and object-style responses
            if hasattr(response, 'models'):
                # New object-style: ListResponse with .models attribute
                models = response.models
            elif isinstance(response, dict):
                # Old dict-style response
                models = response.get("models", [])
            else:
                models = []

            # Extract model names
            health["models_loaded"] = [get_model_name(m) for m in models]
            health["available"] = True

            # Check if our models are loaded (compare base names without :tag)
            model_base_names = [name.split(":")[0] for name in health["models_loaded"]]
            health["text_model_loaded"] = self.text_model.split(":")[0] in model_base_names
            health["vision_model_loaded"] = self.vision_model.split(":")[0] in model_base_names

        except Exception as e:
            health["error"] = str(e)

        return health

    def analyze_text_report(self, text: str) -> Dict[str, Any]:
        """
        Uses Qwen 3 to extract structured data from unstructured flood reports.

        Parses text reports (tweets, advisories, citizen reports) and extracts
        location, severity, and flood-related information.

        Args:
            text: Raw flood report text (tweet, advisory, etc.)

        Returns:
            Dict with extracted fields:
            {
                "location": str,        # Landmark or street name
                "severity": float,      # 0.0 to 1.0
                "is_flood_related": bool,
                "description": str,     # Summary
                "confidence": float     # Model confidence
            }

            Returns empty dict if LLM unavailable or analysis fails.

        Example:
            >>> llm.analyze_text_report("Baha sa Sto. Nino, hanggang tuhod!")
            {'location': 'Sto. Nino', 'severity': 0.5, 'is_flood_related': True, ...}
        """
        if not text or not text.strip():
            logger.warning("Empty text provided to analyze_text_report")
            return {}

        # Check cache first
        cache_key = self._get_cache_key("text", text)
        cached = self._get_cached_response(cache_key)
        if cached is not None:
            return cached

        # Check availability
        if not self.is_available():
            logger.debug("LLM unavailable, returning empty result for text analysis")
            return {}

        prompt = f"""You are a flood report analyzer for Marikina City, Philippines.

Analyze this flood report and extract JSON:
{{
    "location": "string (landmark, street, or barangay in Marikina - be specific)",
    "severity": float (0.0 to 1.0, mapped from depth:
        0.0 = no flooding,
        0.1-0.2 = ankle-deep ~15cm,
        0.3-0.4 = knee-deep ~35cm,
        0.5-0.6 = thigh/waist ~50-70cm,
        0.7-0.8 = chest-deep ~100cm,
        0.9-1.0 = neck/head-deep or life-threatening >130cm),
    "is_flood_related": boolean (true if report is about flooding),
    "description": "brief summary of the flood situation",
    "flood_depth_description": "string describing water level (ankle, shin, knee, thigh, waist, chest, neck, head)",
    "report_type": "flood/observation/warning/rescue",
    "urgency": "low/medium/high/critical"
}}

Report: "{text}"

Important:
- If the text is in Filipino/Tagalog, translate key details
- Marikina barangays: Barangka, Calumpang, Concepcion Uno, Concepcion Dos, Fortune, IVC (Industrial Valley Complex), Jesus de la Pena, Malanday, Marikina Heights, Nangka, Parang, San Roque, Santa Elena, Santo Nino, Tanong, Tumana
- Key landmarks: SM Marikina, Marcos Highway, Sumulong Highway, Gil Fernando Ave, J.P. Rizal, Shoe Ave, Riverbanks, Marikina Sports Center, Marikina River Park
- Return ONLY valid JSON, no explanation or markdown."""

        try:
            response = ollama.chat(
                model=self.text_model,
                messages=[{'role': 'user', 'content': prompt}],
                options={'timeout': self.timeout}
            )

            result = self._clean_json(response['message']['content'])

            # Add confidence based on response quality
            if result:
                result['confidence'] = 0.8 if result.get('is_flood_related') else 0.5
                result['source'] = self.text_model # Update source to match actual model
                
                # Cache the result
                self._set_cached_response(cache_key, result)

                logger.info(
                    f"[{self.text_model}] Text analysis: location={result.get('location')}, "
                    f"severity={result.get('severity')}, flood={result.get('is_flood_related')}"
                )

            return result

        except Exception as e:
            logger.error(f"LLM text analysis failed: {e}")
            return {}

    def analyze_text_with_visual_context(
        self, text: str, visual_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze text with additional visual context for cross-modal understanding.

        Called when visual analysis found risk >= 0.3. The LLM reconciles text
        content with image evidence for more accurate extraction.

        Args:
            text: Raw flood report text
            visual_context: Dict with visual findings:
                - estimated_depth_m: float or None
                - risk_score: float
                - visual_indicators: str or None

        Returns:
            Same structure as analyze_text_report() plus:
                - cross_modal: True
                - text_visual_agreement: str ("agree"/"disagree"/"partial")

            Falls back to analyze_text_report() on failure.
        """
        if not text or not text.strip():
            return {}

        visual_risk = visual_context.get('risk_score', 0)
        if visual_risk < 0.3:
            # Guard: no meaningful visual context, use standard analysis
            return self.analyze_text_report(text)

        # Build cache key that includes visual context fingerprint
        context_fingerprint = (
            f"{visual_context.get('estimated_depth_m', '')}"
            f":{visual_context.get('risk_score', '')}"
        )
        cache_key = self._get_cache_key("text_ctx", f"{text}|{context_fingerprint}")
        cached = self._get_cached_response(cache_key)
        if cached is not None:
            return cached

        if not self.is_available():
            return self.analyze_text_report(text)

        depth_str = visual_context.get('estimated_depth_m')
        depth_info = f"{depth_str}m" if depth_str is not None else "unknown"
        indicators = visual_context.get('visual_indicators') or "none described"

        prompt = f"""You are a flood report analyzer for Marikina City, Philippines.

An accompanying image was analyzed and found:
- Estimated flood depth: {depth_info}
- Visual risk score: {visual_risk}
- Visual indicators: {indicators}

Now analyze the TEXT of the same report and reconcile with the visual evidence.

Extract JSON:
{{
    "location": "string (landmark, street, or barangay in Marikina)",
    "severity": float (0.0-1.0, consider both text and visual evidence),
    "is_flood_related": boolean,
    "description": "summary reconciling text and visual evidence",
    "flood_depth_description": "ankle/shin/knee/thigh/waist/chest/neck/head",
    "report_type": "flood/observation/warning/rescue",
    "urgency": "low/medium/high/critical",
    "text_visual_agreement": "agree/disagree/partial (do text and image tell the same story?)"
}}

Report text: "{text}"

Important:
- Marikina barangays: Barangka, Calumpang, Concepcion Uno, Concepcion Dos, Fortune, IVC, Jesus de la Pena, Malanday, Marikina Heights, Nangka, Parang, San Roque, Santa Elena, Santo Nino, Tanong, Tumana
- If text contradicts image, prefer the higher severity signal
- Return ONLY valid JSON."""

        try:
            response = ollama.chat(
                model=self.text_model,
                messages=[{'role': 'user', 'content': prompt}],
                options={'timeout': self.timeout}
            )

            result = self._clean_json(response['message']['content'])

            if result:
                result['confidence'] = 0.85 if result.get('is_flood_related') else 0.5
                result['source'] = self.text_model
                result['cross_modal'] = True
                self._set_cached_response(cache_key, result)

                logger.info(
                    f"[{self.text_model}] Cross-modal text analysis: "
                    f"location={result.get('location')}, "
                    f"severity={result.get('severity')}, "
                    f"agreement={result.get('text_visual_agreement')}"
                )

            return result

        except Exception as e:
            logger.warning(f"Cross-modal text analysis failed, falling back: {e}")
            return self.analyze_text_report(text)

    def analyze_flood_image(self, image_path: str, use_fallback: bool = True) -> Dict[str, Any]:
        """
        Uses configured Vision Model (default: moondream) to estimate flood depth from an image.

        Analyzes flood images to estimate water depth, assess risk level,
        and determine vehicle passability. Falls back to SimulatedImageAnalyzer
        when vision model is unavailable.

        Args:
            image_path: Path to flood image file (JPEG, PNG supported)
            use_fallback: If True, use simulated analyzer when LLM unavailable

        Returns:
            Dict with visual analysis:
            {
                "estimated_depth_m": float,     # Water depth estimate in meters
                "risk_score": float,            # 0.0 to 1.0
                "vehicles_passable": List[str], # Vehicles that can pass
                "visual_indicators": str,       # What indicates flood severity
                "confidence": float             # Model confidence
            }

            Returns empty dict if LLM unavailable and fallback disabled.
        """
        if not image_path:
            logger.warning("No image path provided to analyze_flood_image")
            return {}

        # Verify image exists
        image_file = Path(image_path)
        if not image_file.exists():
            # For simulation mode, image may not exist - use fallback
            if use_fallback:
                logger.debug(f"Image not found, using simulated analyzer: {image_path}")
                return self._fallback_image_analysis(image_path)
            logger.error(f"Image file not found: {image_path}")
            return {}

        # Check cache (use file path + modification time as key)
        cache_content = f"{image_path}:{image_file.stat().st_mtime}"
        cache_key = self._get_cache_key("image", cache_content)
        cached = self._get_cached_response(cache_key)
        if cached is not None:
            return cached

        # Check availability - use fallback if LLM not available
        if not self.is_available():
            if use_fallback:
                logger.debug("LLM unavailable, using simulated image analyzer")
                return self._fallback_image_analysis(image_path)
            logger.debug("LLM unavailable, returning empty result for image analysis")
            return {}

        prompt = """You are a flood depth estimator analyzing an image from Marikina City, Philippines.

Analyze this flood image and estimate the water depth. Return JSON:
{
    "estimated_depth_m": float (water depth estimate in meters, use visual references like:
        - Ankle-deep: ~0.1-0.15m
        - Knee-deep: ~0.3-0.45m
        - Waist-deep: ~0.6-0.9m
        - Chest-deep: ~1.0-1.2m
        - Above head: >1.5m),
    "risk_score": float (0.0 to 1.0, based on depth and flow),
    "vehicles_passable": ["car", "suv", "truck", "motorcycle", "bicycle"] (list which can safely pass),
    "visual_indicators": "describe what you see indicating flood severity (water line on objects, submerged items, water color/flow)",
    "flow_assessment": "still/slow/moderate/fast/dangerous",
    "visibility": "clear/murky/debris-filled"
}

Vehicle passability guidelines:
- Motorcycle/bicycle: max ~0.15m
- Car: max ~0.3m (danger at 0.2m+)
- SUV: max ~0.45m
- Truck: max ~0.6m

Return ONLY valid JSON, no explanation."""

        try:
            response = ollama.chat(
                model=self.vision_model,
                messages=[{
                    'role': 'user',
                    'content': prompt,
                    'images': [image_path]
                }],
                options={'timeout': self.timeout * 2}  # Vision takes longer
            )

            result = self._clean_json(response['message']['content'])

            if result:
                # Calculate confidence based on response completeness
                has_depth = result.get('estimated_depth_m') is not None
                has_risk = result.get('risk_score') is not None
                has_indicators = bool(result.get('visual_indicators'))

                confidence = 0.5
                if has_depth and has_risk and has_indicators:
                    confidence = 0.85
                elif has_depth and has_risk:
                    confidence = 0.7

                result['confidence'] = confidence
                result['source'] = self.vision_model
                result['image_analyzed'] = str(image_path)

                # Cache the result
                self._set_cached_response(cache_key, result)

                logger.info(
                    f"[{self.vision_model}] Image analysis: depth={result.get('estimated_depth_m')}m, "
                    f"risk={result.get('risk_score')}, confidence={confidence}"
                )

            return result

        except Exception as e:
            logger.error(f"LLM vision analysis failed: {e}")
            return {}

    def _fallback_image_analysis(self, image_path: str) -> Dict[str, Any]:
        """
        Fallback image analysis using SimulatedImageAnalyzer.

        Used when vision model is unavailable but image analysis is needed
        for testing/simulation purposes.

        Args:
            image_path: Path to image file

        Returns:
            Dict with simulated analysis results
        """
        try:
            from .simulated_image_analyzer import get_simulated_analyzer
            analyzer = get_simulated_analyzer()
            result = analyzer.analyze(image_path)
            logger.info(f"[Fallback] Simulated image analysis for: {image_path}")
            return result
        except Exception as e:
            logger.error(f"Fallback image analysis failed: {e}")
            return {}

    def parse_pagasa_advisory(self, advisory_text: str) -> Dict[str, Any]:
        """
        Uses configured LLM to parse PAGASA text advisories.

        Extracts structured information from official weather bulletins
        including rainfall warnings, river level alerts, and forecasts.

        Args:
            advisory_text: Raw PAGASA advisory text

        Returns:
            Dict with parsed advisory:
            {
                "advisory_type": str,       # "rainfall", "flood", "dam", etc.
                "warning_level": str,       # "blue", "yellow", "orange", "red"
                "affected_areas": List[str],
                "expected_rainfall_mm": float,
                "valid_until": str,
                "key_points": List[str]
            }
        """
        if not advisory_text or not advisory_text.strip():
            return {}

        cache_key = self._get_cache_key("advisory", advisory_text)
        cached = self._get_cached_response(cache_key)
        if cached is not None:
            return cached

        if not self.is_available():
            return {}

        prompt = f"""Parse this PAGASA weather advisory and extract structured information.

Advisory Text:
{advisory_text}

Return JSON:
{{
    "advisory_type": "rainfall/flood/dam/typhoon/general",
    "warning_level": "blue/yellow/orange/red/none (based on PAGASA color codes)",
    "affected_areas": ["list of affected areas/provinces"],
    "expected_rainfall_mm": float or null (if mentioned),
    "expected_duration_hours": float or null,
    "river_status": {{
        "river_name": "status" (normal/alert/alarm/critical)
    }},
    "dam_status": {{
        "dam_name": "status" (normal/spilling/critical)
    }},
    "valid_until": "datetime string if mentioned",
    "key_points": ["list of important points"],
    "recommended_actions": ["list of recommended actions"]
}}

Return ONLY valid JSON."""

        try:
            response = ollama.chat(
                model=self.text_model,
                messages=[{'role': 'user', 'content': prompt}],
                options={'timeout': self.timeout}
            )

            result = self._clean_json(response['message']['content'])

            if result:
                result['source'] = self.text_model
                result['parsed_at'] = datetime.now().isoformat()
                self._set_cached_response(cache_key, result)

                logger.info(
                    f"[{self.text_model}] Advisory parsed: type={result.get('advisory_type')}, "
                    f"level={result.get('warning_level')}"
                )

            return result

        except Exception as e:
            logger.error(f"LLM advisory parsing failed: {e}")
            return {}

    def text_chat(self, prompt: str) -> str:
        """
        General-purpose LLM text chat. Returns raw text (not JSON-parsed).

        Wraps ollama.chat() with caching, timeout, and error handling.

        Args:
            prompt: The prompt to send to the text model

        Returns:
            Raw text response from the LLM, or empty string on failure
        """
        if not prompt or not prompt.strip():
            logger.warning("Empty prompt provided to text_chat")
            return ""

        # Check cache first
        cache_key = self._get_cache_key("chat", prompt)
        cached = self._get_cached_response(cache_key)
        if cached is not None:
            return cached.get("text", "")

        # Check availability
        if not self.is_available():
            logger.debug("LLM unavailable, returning empty result for text_chat")
            return ""

        try:
            response = ollama.chat(
                model=self.text_model,
                messages=[{'role': 'user', 'content': prompt}],
                options={'timeout': self.timeout}
            )

            text = response['message']['content'].strip()

            if text:
                self._set_cached_response(cache_key, {"text": text})
                logger.debug(f"[{self.text_model}] text_chat response: {text[:80]}...")

            return text

        except Exception as e:
            logger.error(f"LLM text_chat failed: {e}")
            return ""

    def text_chat_multi(self, messages: list) -> str:
        """
        Multi-turn LLM text chat with conversation history.

        Args:
            messages: List of {'role': 'system'|'user'|'assistant', 'content': str}

        Returns:
            Raw text response from the LLM, or empty string on failure
        """
        if not messages:
            logger.warning("Empty messages list provided to text_chat_multi")
            return ""

        if not self.is_available():
            logger.debug("LLM unavailable, returning empty result for text_chat_multi")
            return ""

        try:
            response = ollama.chat(
                model=self.text_model,
                messages=messages,
                options={'timeout': self.timeout}
            )

            text = response['message']['content'].strip()
            if text:
                logger.debug(f"[{self.text_model}] text_chat_multi response: {text[:80]}...")
            return text

        except Exception as e:
            logger.error(f"LLM text_chat_multi failed: {e}")
            return ""

    def _clean_json(self, content: str) -> Dict[str, Any]:
        """
        Helper to extract and parse JSON from LLM response.
        Uses raw_decode to handle extra text after the JSON object.
        """
        if not content:
            return {}

        # Remove markdown code blocks
        content = content.replace("```json", "").replace("```", "").strip()

        # Find first '{'
        start_idx = content.find('{')
        if start_idx == -1:
            return {}

        try:
            # raw_decode parses the first valid JSON object and ignores the rest
            obj, _ = json.JSONDecoder().raw_decode(content, idx=start_idx)
            return obj
        except json.JSONDecodeError as e:
            logger.debug(f"JSON raw_decode failed: {e}")
            
            # Fallback for edge cases (e.g. malformed json) without strict strictness
            try:
                end_idx = content.rfind('}') + 1
                if end_idx > start_idx:
                    json_str = content[start_idx:end_idx]
                    return json.loads(json_str)
            except Exception:
                pass

            logger.warning(f"JSON parse failed: {e}, content: {content[:100]}...")
            return {}

    def clear_cache(self) -> int:
        """
        Clear the response cache.

        Returns:
            Number of cached entries cleared
        """
        count = len(self._response_cache)
        self._response_cache.clear()
        logger.info(f"LLM response cache cleared: {count} entries")
        return count


# Singleton instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """
    Get or create the global LLM service instance.

    Returns:
        LLMService singleton instance
    """
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service


def reset_llm_service() -> None:
    """Reset the global LLM service instance (useful for testing)."""
    global _llm_service
    _llm_service = None
