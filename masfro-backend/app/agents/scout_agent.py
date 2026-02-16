# filename: app/agents/scout_agent.py

"""
Scout Agent for Multi-Agent System for Flood Route Optimization (MAS-FRO)

This module implements the ScoutAgent class for crowdsourced flood data collection.
The agent processes synthetic/real flood reports through NLP models and LLM analysis,
then forwards validated reports to the HazardAgent.

v2 Enhancements:
- LLM integration for semantic text understanding (configurable via env)
- Vision model integration for flood image analysis
- Graceful fallback to traditional NLP when LLM unavailable
- Visual evidence flag for HazardAgent Visual Override

Author: MAS-FRO Development Team
Date: February 2026
"""

import re
import json
import time
import threading
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, TYPE_CHECKING

from .base_agent import BaseAgent
from app.core.agent_config import get_config, ScoutConfig
import logging

# ACL Protocol imports for MAS communication
try:
    from communication.acl_protocol import ACLMessage, Performative, create_inform_message
except ImportError:
    from app.communication.acl_protocol import ACLMessage, Performative, create_inform_message

if TYPE_CHECKING:
    from ..environment.graph_manager import DynamicGraphEnvironment
    from ..communication.message_queue import MessageQueue

logger = logging.getLogger(__name__)


class ScoutAgent(BaseAgent):
    """
    ScoutAgent - Crowdsourced Data Collection with LLM Enhancement

    Collects and processes flood reports from crowdsourced data (simulated tweets).
    Uses LLM for semantic text understanding and vision model for image analysis.
    Falls back to traditional NLP processing when LLM is unavailable.

    v2 Features:
    - LLM-enhanced text analysis (configurable model)
    - Vision-based flood detection (configurable model)
    - Visual evidence flagging for HazardAgent override logic
    - Improved severity estimation from visual cues
    - Depth extraction from text descriptions
    - Confidence-weighted fusion of visual and text signals
    - Temporal deduplication of location reports
    - Cross-modal context for text analysis

    Attributes:
        agent_id: Unique identifier for this agent
        environment: Reference to DynamicGraphEnvironment
        message_queue: MessageQueue for asynchronous MAS communication
        hazard_agent_id: Target HazardAgent ID for message routing
        nlp_processor: Traditional NLP processor (fallback)
        llm_service: LLM service for enhanced analysis
        use_llm: Whether LLM processing is enabled
    """

    # Mapping of text flood depth descriptions to meters
    DEPTH_MAP: Dict[str, float] = {
        "ankle": 0.15,
        "shin": 0.25,
        "knee": 0.35,
        "thigh": 0.50,
        "waist": 0.70,
        "chest": 1.0,
        "neck": 1.3,
        "head": 1.5,
    }

    # Known Marikina barangays for quick location extraction (temporal dedup)
    _KNOWN_LOCATIONS: List[str] = [
        "Barangka", "Calumpang", "Concepcion Uno", "Concepcion Dos",
        "Fortune", "IVC", "Industrial Valley Complex",
        "Jesus de la Pena", "Malanday", "Marikina Heights",
        "Nangka", "Parang", "San Roque", "Santa Elena",
        "Santo Nino", "Sto. Nino", "Tanong", "Tumana",
        # Key landmarks
        "SM Marikina", "Marcos Highway", "Sumulong Highway",
        "Gil Fernando", "J.P. Rizal", "Shoe Ave", "Riverbanks",
        "Marikina Sports Center", "Marikina River",
    ]

    def __init__(
        self,
        agent_id: str,
        environment: "DynamicGraphEnvironment",
        message_queue: Optional["MessageQueue"] = None,
        hazard_agent_id: str = "hazard_agent_001",
        simulation_scenario: int = 1,
        use_ml_in_simulation: bool = True,
        enable_llm: bool = True,
        use_scraper: bool = False,
        scraper_base_url: str = "http://localhost:8081"
    ) -> None:
        """
        Initialize ScoutAgent for crowdsourced flood data collection.

        Args:
            agent_id: Unique identifier for this agent
            environment: Reference to the DynamicGraphEnvironment instance
            message_queue: MessageQueue instance for MAS communication
            hazard_agent_id: Target HazardAgent ID for message routing
            simulation_scenario: Which scenario to load (1-3) for simulation
            use_ml_in_simulation: If True, process simulation tweets through ML models
            enable_llm: If True, attempt to use LLM for enhanced processing
            use_scraper: If True, use SocialScraperService instead of JSON files
            scraper_base_url: Base URL for the social scraper service
        """
        super().__init__(agent_id, environment, message_queue=message_queue)

        # Target agent for forwarding reports
        self.hazard_agent_id = hazard_agent_id

        # Load configuration from YAML
        try:
            self._config = get_config().get_scout_config()
        except Exception as e:
            logger.warning(f"Failed to load scout config, using defaults: {e}")
            self._config = ScoutConfig()

        # Scraper mode (for mock server / real social scraping)
        self.use_scraper = use_scraper
        self.social_scraper = None
        if use_scraper:
            try:
                from ..services.social_scraper_service import SocialScraperService
                self.social_scraper = SocialScraperService(base_url=scraper_base_url)
                logger.info(f"{self.agent_id} initialized SocialScraperService (url={scraper_base_url})")
            except Exception as e:
                logger.warning(f"{self.agent_id} failed to init SocialScraperService: {e}")
                self.use_scraper = False

        # Scraper throttle: only scrape every N seconds (thread-safe)
        self._scrape_interval = self._config.scraper_throttle_interval_seconds
        self._last_scrape_time = 0.0
        self._scrape_lock = threading.Lock()

        # Simulation mode settings
        self.simulation_mode = not use_scraper  # Disable simulation mode when scraper active
        self.simulation_scenario = simulation_scenario
        self.simulation_tweets = []
        self.simulation_index = 0
        self.simulation_batch_size = self._config.batch_size
        self.use_ml_in_simulation = use_ml_in_simulation

        # ========== LLM SERVICE INITIALIZATION (v2) ==========
        self.llm_service = None
        self.use_llm = False

        if enable_llm:
            try:
                from ..services.llm_service import get_llm_service
                self.llm_service = get_llm_service()
                if self.llm_service.is_available():
                    self.use_llm = True
                    logger.info(
                        f"{self.agent_id} LLM Service initialized (text + vision models)"
                    )
                else:
                    logger.warning(
                        f"{self.agent_id} LLM Service not available, will use fallback NLP"
                    )
            except Exception as e:
                logger.warning(
                    f"{self.agent_id} failed to initialize LLM Service: {e}. "
                    "Falling back to traditional NLP."
                )
                self.llm_service = None

        # ========== TRADITIONAL NLP PROCESSOR (FALLBACK) ==========
        try:
            from ..ml_models.nlp_processor import NLPProcessor
            self.nlp_processor = NLPProcessor()
            logger.info(f"{self.agent_id} initialized with NLP processor (fallback)")
        except Exception as e:
            logger.warning(
                f"{self.agent_id} failed to initialize NLP processor: {e}"
            )
            self.nlp_processor = None

        # ========== LOCATION GEOCODER ==========
        try:
            from ..ml_models.location_geocoder import LocationGeocoder
            self.geocoder = LocationGeocoder(llm_service=self.llm_service)
            logger.info(f"{self.agent_id} initialized with LocationGeocoder")
        except Exception as e:
            logger.warning(
                f"{self.agent_id} failed to initialize LocationGeocoder: {e}"
            )
            self.geocoder = None

        # ========== TWEET ID DEDUPLICATION ==========
        self._processed_tweet_ids: OrderedDict = OrderedDict()

        # ========== TEMPORAL DEDUPLICATION ==========
        self._recent_locations: Dict[str, datetime] = {}
        self._temporal_dedup_window_minutes = self._config.temporal_dedup_window_minutes

        # Log initialization summary
        processing_mode = "LLM" if self.use_llm else "Traditional NLP"
        data_mode = "SIMULATION MODE" if self.simulation_mode else "SCRAPER MODE"
        logger.info(f"ScoutAgent '{self.agent_id}' initialized in {data_mode}")
        logger.info(f"  Using synthetic data scenario {self.simulation_scenario}")
        logger.info(f"  Text processing mode: {processing_mode}")
        logger.info(f"  Vision processing: {'ENABLED' if self.use_llm else 'DISABLED'}")
        logger.info(f"  Temporal dedup window: {self._temporal_dedup_window_minutes} min")

    def setup(self) -> bool:
        """
        Initializes the agent for operation by loading synthetic data.

        Returns:
            bool: True if setup was successful, False otherwise.
        """
        logger.info(f"{self.agent_id} loading synthetic data")
        return self._load_simulation_data()

    def step(self) -> list:
        """
        Collects and processes flood data from simulation or live scraper.

        This method is designed to be called repeatedly by the main simulation loop.
        Also processes any pending MQ requests from the orchestrator.

        Returns:
            list: A list of processed tweet dictionaries.
        """
        # Process any orchestrator REQUEST messages first
        self._process_mq_requests()

        logger.debug(
            f"{self.agent_id} collecting data at {datetime.now().strftime('%H:%M:%S')}"
        )

        # Scraper mode: fetch from live social scraper service (throttled, thread-safe)
        if self.use_scraper and self.social_scraper:
            with self._scrape_lock:
                now = time.time()
                if now - self._last_scrape_time < self._scrape_interval:
                    return []
                self._last_scrape_time = now
            return self._step_scraper()

        # Simulation mode: load from JSON files
        raw_tweets = self._get_simulation_tweets(batch_size=self.simulation_batch_size)
        prepared_tweets = self._prepare_simulation_tweets_for_ml(raw_tweets)

        if prepared_tweets:
            logger.info(f"{self.agent_id} found {len(prepared_tweets)} simulated tweets")
            self._process_and_forward_tweets(prepared_tweets)
        else:
            logger.debug(f"{self.agent_id} no more simulation data available")

        return prepared_tweets

    def _step_scraper(self) -> list:
        """
        Fetch tweets from SocialScraperService and process them.

        Uses the same _process_and_forward_tweets() pipeline as simulation mode.

        Returns:
            list: Processed tweet dictionaries from scraper.
        """
        try:
            raw_tweets = self.social_scraper.scrape_feed()
            if not raw_tweets:
                logger.debug(f"{self.agent_id} scraper returned no tweets")
                return []

            logger.info(f"{self.agent_id} scraped {len(raw_tweets)} tweets from live feed")
            self._process_and_forward_tweets(raw_tweets)
            return raw_tweets

        except Exception as e:
            logger.error(f"{self.agent_id} scraper step failed: {e}")
            return []

    def _process_mq_requests(self) -> None:
        """Process incoming REQUEST messages from orchestrator via MQ."""
        if not self.message_queue:
            return

        while True:
            msg = self.message_queue.receive_message(
                agent_id=self.agent_id, timeout=0.0, block=False
            )
            if msg is None:
                break

            if msg.performative == Performative.REQUEST:
                action = msg.content.get("action")
                data = msg.content.get("data", {})

                if action == "scan_location":
                    self._handle_scan_location(msg, data)
                else:
                    logger.warning(
                        f"{self.agent_id}: unknown REQUEST action '{action}' "
                        f"from {msg.sender}"
                    )
            else:
                logger.debug(
                    f"{self.agent_id}: ignoring {msg.performative} from {msg.sender}"
                )

    def _handle_scan_location(self, msg: ACLMessage, data: dict) -> None:
        """Handle scan_location REQUEST: geocode location and reply."""
        location = data.get("location", "")
        result = {"location": location, "status": "unknown"}

        try:
            if self.geocoder:
                coords = self.geocoder.get_coordinates(location)
                if coords:
                    result["coordinates"] = coords
                    result["status"] = "scanned"
                else:
                    result["status"] = "location_not_found"
            else:
                result["status"] = "geocoder_unavailable"
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

        logger.info(
            f"{self.agent_id}: scan_location '{location}' -> {result['status']}"
        )

        # Send INFORM reply to requester
        reply = create_inform_message(
            sender=self.agent_id,
            receiver=msg.sender,
            info_type="scan_location_result",
            data=result,
            conversation_id=msg.conversation_id,
            in_reply_to=msg.reply_with,
        )
        try:
            self.message_queue.send_message(reply)
        except Exception as e:
            logger.error(f"{self.agent_id}: failed to reply to {msg.sender}: {e}")

    def inject_manual_tweet(self, tweet_content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Manually inject a tweet into the agent for immediate processing.
        
        Args:
            tweet_content: Dictionary containing tweet data (text, image_path, etc.)
            
        Returns:
            Processed report data
        """
        logger.info(f"{self.agent_id} received manual tweet injection")
        
        # Normalize input
        if "timestamp" not in tweet_content:
            tweet_content["timestamp"] = datetime.now()
            
        # Process immediately
        try:
            # Re-use the single tweet processing logic
            report_data = self._process_single_tweet(tweet_content)
            
            if report_data:
                # Add injection flag
                report_data['source'] = 'manual_injection'
                
                # Forward to Hazard Agent
                self._send_reports_to_hazard_agent(
                    [report_data], 
                    skipped_count=0, 
                    llm_count=1 if self.use_llm else 0, 
                    nlp_count=0 if self.use_llm else 1
                )
                return report_data
            else:
                logger.warning(f"{self.agent_id} manual injection failed processing")
                return {"status": "error", "message": "Processing returned no valid report"}
                
        except Exception as e:
            logger.error(f"{self.agent_id} manual injection error: {e}")
            return {"status": "error", "message": str(e)}


    def _process_and_forward_tweets(self, tweets: list) -> None:
        """
        Process tweets using LLM (primary) or NLP (fallback) and forward to HazardAgent.

        v2 Processing Pipeline:
        1. Visual Analysis (if image present) - Vision Model
        2. Text Analysis - LLM (or fallback NLP)
        3. Fusion - Combine visual and text signals
        4. Geocode - Add coordinates if available
        5. Forward to HazardAgent via MessageQueue

        Args:
            tweets: List of tweet dictionaries to process
        """
        if not self.message_queue:
            logger.warning(f"{self.agent_id} has no MessageQueue, data not forwarded")
            return

        # Check if we have any processing capability
        if not self.use_llm and not self.nlp_processor:
            logger.error(
                f"{self.agent_id} has no LLM or NLP processor available, "
                "cannot process tweets"
            )
            return

        processed_reports = []
        skipped_no_coordinates = 0
        llm_processed = 0
        nlp_processed = 0

        for tweet in tweets:
            try:
                # Tweet ID deduplication: skip already-processed tweets
                tweet_id = tweet.get('tweet_id') or tweet.get('id')
                if tweet_id and tweet_id in self._processed_tweet_ids:
                    continue
                if tweet_id:
                    self._processed_tweet_ids[tweet_id] = None
                    # Bound the dict to prevent unbounded growth
                    if len(self._processed_tweet_ids) > 10000:
                        for _ in range(2000):
                            self._processed_tweet_ids.popitem(last=False)

                # Temporal deduplication: skip if same location reported recently
                quick_loc = self._extract_quick_location(tweet.get('text', ''))
                if quick_loc and self._is_recently_reported(quick_loc):
                    logger.debug(
                        f"{self.agent_id} skipping temporally duplicate report "
                        f"for '{quick_loc}'"
                    )
                    continue

                report_data = self._process_single_tweet(tweet)

                if report_data is None:
                    continue

                # Track processing method
                if report_data.get('source') == 'scout_agent_llm_enhanced':
                    llm_processed += 1
                else:
                    nlp_processed += 1

                # Skip non-flood reports
                if not report_data.get('is_flood_related', False):
                    continue

                # Skip reports without coordinates
                if not report_data.get('coordinates'):
                    skipped_no_coordinates += 1
                    logger.debug(
                        f"{self.agent_id} skipped flood report without coordinates: "
                        f"location '{report_data.get('location')}'"
                    )
                    continue

                processed_reports.append(report_data)

                # Log the message
                logger.info(f"Message sent: {tweet.get('text', '')[:100]}...")

            except Exception as e:
                logger.error(f"{self.agent_id} error processing tweet: {e}")
                continue

        # Forward all processed reports to HazardAgent
        if processed_reports:
            self._send_reports_to_hazard_agent(
                processed_reports,
                skipped_no_coordinates,
                llm_processed,
                nlp_processed
            )
        elif skipped_no_coordinates > 0:
            logger.warning(
                f"{self.agent_id} all {skipped_no_coordinates} flood-related tweets "
                f"lacked coordinates and were skipped"
            )

    def _process_single_tweet(self, tweet: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process a single tweet using LLM or NLP.

        Pipeline:
        1. Visual analysis (vision model, if image present)
        2. Text analysis (LLM with optional cross-modal context, or fallback NLP)
        3. Depth extraction from text descriptions
        4. Confidence-weighted fusion of visual and text signals
        5. Geocoding with retry/simplification
        6. Multi-factor confidence calculation
        7. Build final payload

        Args:
            tweet: Tweet dictionary with 'text', 'timestamp', etc.

        Returns:
            Processed report dictionary or None if processing fails
        """
        report_data = {
            'visual_evidence': False,
            'confidence': self._config.default_confidence,
            'is_flood_related': False,
            'source': 'scout_agent'
        }

        # ========== 1. VISUAL ANALYSIS (Vision Model) ==========
        visual_confidence = 0.0
        if tweet.get('image_path') and self.llm_service and self.use_llm:
            visual_result = self._analyze_image(tweet['image_path'])
            if visual_result:
                report_data.update(visual_result)
                visual_confidence = visual_result.get('confidence', 0.0)

        # ========== 2. TEXT ANALYSIS (LLM or fallback NLP) ==========
        # Use cross-modal context if visual analysis found significant risk
        visual_risk = report_data.get('risk_score', 0) or 0
        if visual_risk > 0.3 and report_data.get('visual_evidence'):
            text_result = self._analyze_text_with_context(
                tweet.get('text', ''), report_data
            )
        else:
            text_result = self._analyze_text(tweet.get('text', ''))

        text_confidence = 0.0
        if text_result:
            # Merge text analysis into report
            report_data['location'] = text_result.get('location') or tweet.get('location')
            report_data['is_flood_related'] = text_result.get('is_flood_related', False)
            report_data['description'] = text_result.get('description')
            report_data['report_type'] = text_result.get('report_type', 'flood')
            text_confidence = text_result.get('confidence', self._config.default_confidence)

            # Update source if LLM was used
            if text_result.get('source') and 'nlp' not in text_result.get('source', '').lower():
                report_data['source'] = 'scout_agent_llm_enhanced'

        # ========== 3. DEPTH EXTRACTION FROM TEXT ==========
        # If vision didn't provide depth, derive from text description
        if not report_data.get('estimated_depth_m') and text_result:
            depth_desc = text_result.get('flood_depth_description', '')
            if depth_desc:
                derived_depth = self._depth_description_to_meters(depth_desc)
                if derived_depth is not None:
                    report_data['estimated_depth_m'] = derived_depth
                    logger.debug(
                        f"Derived depth from text: '{depth_desc}' -> {derived_depth}m"
                    )

        # ========== 4. CONFIDENCE-WEIGHTED FUSION ==========
        text_severity = text_result.get('severity', 0) if text_result else 0

        if visual_risk > 0 and text_severity > 0:
            # Both signals present: weighted average by confidence
            vc = visual_confidence or self._config.default_confidence
            tc = text_confidence or self._config.default_confidence
            final_risk = (visual_risk * vc + text_severity * tc) / (vc + tc)
        elif visual_risk > 0:
            final_risk = visual_risk
        else:
            final_risk = text_severity

        report_data['severity'] = final_risk
        report_data['risk_score'] = final_risk

        # Skip non-flood reports
        if not report_data.get('is_flood_related') and not report_data.get('visual_evidence'):
            return None

        # ========== 5. GEOCODING ==========
        if report_data.get('location') and self.geocoder:
            coords = self._geocode_location(report_data['location'])
            if coords:
                report_data['coordinates'] = coords
                report_data['has_coordinates'] = True
            else:
                report_data['has_coordinates'] = False
        else:
            report_data['has_coordinates'] = False

        # ========== 6. MULTI-FACTOR CONFIDENCE ==========
        report_data['confidence'] = self._calculate_fused_confidence(
            visual_confidence=visual_confidence,
            text_confidence=text_confidence,
            visual_risk=visual_risk,
            text_severity=text_severity,
            has_visual=report_data.get('visual_evidence', False),
            has_coordinates=report_data.get('has_coordinates', False),
        )

        # ========== 7. BUILD FINAL PAYLOAD ==========
        timestamp = tweet.get('timestamp')
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                timestamp = datetime.now()

        depth = report_data.get('estimated_depth_m')

        payload = {
            "location": report_data.get('location') or "Marikina",
            "coordinates": report_data.get('coordinates'),
            "severity": round(report_data.get('severity', 0), 2),
            "risk_score": round(report_data.get('risk_score', 0), 2),
            "report_type": report_data.get('report_type', 'flood') if final_risk > 0.3 else 'observation',
            "confidence": round(report_data.get('confidence', self._config.default_confidence), 2),
            "visual_evidence": report_data.get('visual_evidence', False),
            "estimated_depth_m": round(depth, 2) if depth else None,
            "vehicles_passable": report_data.get('vehicles_passable'),
            "timestamp": timestamp,
            "source": report_data.get('source', 'scout_agent'),
            "source_url": tweet.get('url', ''),
            "username": tweet.get('username', ''),
            "text": tweet.get('text', ''),
            "is_flood_related": report_data.get('is_flood_related', False),
            "has_coordinates": report_data.get('has_coordinates', False)
        }

        # Record location for temporal dedup
        if payload.get('location'):
            self._record_location_report(payload['location'])

        return payload

    def _analyze_image(self, image_path: str) -> Optional[Dict[str, Any]]:
        """
        Analyze flood image using vision model.

        Args:
            image_path: Path to the image file

        Returns:
            Dict with visual analysis results or None
        """
        if not self.llm_service:
            return None

        try:
            visual_analysis = self.llm_service.analyze_flood_image(image_path)

            if visual_analysis:
                result = {
                    'estimated_depth_m': visual_analysis.get('estimated_depth_m'),
                    'risk_score': visual_analysis.get('risk_score', 0),
                    'vehicles_passable': visual_analysis.get('vehicles_passable', []),
                    'visual_evidence': True,
                    'visual_indicators': visual_analysis.get('visual_indicators')
                }

                # Visual evidence with high risk = high confidence
                if visual_analysis.get('risk_score', 0) > self._config.min_confidence:
                    logger.info(
                        f"[Vision] High-risk visual detected: "
                        f"depth={visual_analysis.get('estimated_depth_m')}m, "
                        f"risk={visual_analysis.get('risk_score')}"
                    )

                return result

        except Exception as e:
            logger.warning(f"Image analysis failed: {e}")

        return None

    def _analyze_text(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Analyze text using LLM (primary) or NLP (fallback).

        Args:
            text: Tweet text to analyze

        Returns:
            Dict with text analysis results or None
        """
        if not text or not text.strip():
            return None

        # Try LLM first
        if self.use_llm and self.llm_service:
            try:
                llm_result = self.llm_service.analyze_text_report(text)
                if llm_result:
                    return llm_result
            except Exception as e:
                logger.warning(f"LLM text analysis failed, falling back to NLP: {e}")

        # Fallback to traditional NLP
        if self.nlp_processor:
            try:
                nlp_result = self.nlp_processor.extract_flood_info(text)
                if nlp_result and isinstance(nlp_result, dict):
                    nlp_result['source'] = 'nlp_processor'
                    return nlp_result
            except Exception as e:
                logger.error(f"NLP processing failed: {e}")

        return None

    def _analyze_text_with_context(
        self, text: str, visual_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze text with cross-modal visual context for better LLM understanding.

        Falls back to standard _analyze_text() on failure.

        Args:
            text: Tweet text to analyze
            visual_data: Visual analysis results to provide as context

        Returns:
            Dict with text analysis results or None
        """
        if not text or not text.strip():
            return None

        if self.use_llm and self.llm_service:
            try:
                visual_context = {
                    "estimated_depth_m": visual_data.get('estimated_depth_m'),
                    "risk_score": visual_data.get('risk_score', 0),
                    "visual_indicators": visual_data.get('visual_indicators'),
                }
                result = self.llm_service.analyze_text_with_visual_context(
                    text, visual_context
                )
                if result:
                    return result
            except Exception as e:
                logger.warning(
                    f"Cross-modal text analysis failed, falling back to standard: {e}"
                )

        # Fallback to standard text analysis
        return self._analyze_text(text)

    def _depth_description_to_meters(self, description: str) -> Optional[float]:
        """
        Convert a textual flood depth description to an estimated depth in meters.

        Supports direct matches (e.g. "knee") and partial matches
        (e.g. "knee-deep", "hanggang tuhod").

        Args:
            description: Text description of flood depth

        Returns:
            Estimated depth in meters, or None if no match
        """
        if not description:
            return None

        desc_lower = description.lower().strip()

        # Direct match first
        if desc_lower in self.DEPTH_MAP:
            return self.DEPTH_MAP[desc_lower]

        # Partial match: check if any key appears in the description
        for keyword, depth in self.DEPTH_MAP.items():
            if keyword in desc_lower:
                return depth

        return None

    def _calculate_fused_confidence(
        self,
        visual_confidence: float,
        text_confidence: float,
        visual_risk: float,
        text_severity: float,
        has_visual: bool,
        has_coordinates: bool,
    ) -> float:
        """
        Calculate multi-factor fused confidence score.

        Factors:
        - Base: max of visual/text confidence (minimum 0.3)
        - +0.1 if visual evidence present
        - +0.05 if coordinates resolved
        - +0.1 if visual and text signals agree (within 0.2)
        - Capped at 0.95

        Returns:
            Confidence score between 0.3 and 0.95
        """
        base = max(visual_confidence, text_confidence, 0.3)

        if has_visual:
            base += 0.1

        if has_coordinates:
            base += 0.05

        # Cross-modal agreement bonus
        if has_visual and text_severity > 0 and visual_risk > 0:
            if abs(visual_risk - text_severity) <= 0.2:
                base += 0.1

        return min(base, 0.95)

    # --- TEMPORAL DEDUPLICATION METHODS ---

    def _extract_quick_location(self, text: str) -> Optional[str]:
        """
        Extract a known Marikina location from text using regex (no LLM call).

        Used for fast temporal deduplication before full processing.

        Args:
            text: Raw tweet text

        Returns:
            Matched location name or None
        """
        if not text:
            return None

        for loc in self._KNOWN_LOCATIONS:
            if re.search(re.escape(loc), text, re.IGNORECASE):
                return loc
        return None

    def _is_recently_reported(self, location: str) -> bool:
        """
        Check if a location was reported within the temporal dedup window.

        Args:
            location: Location name to check

        Returns:
            True if this location was recently reported
        """
        loc_key = location.lower().strip()
        last_report = self._recent_locations.get(loc_key)
        if last_report is None:
            return False

        elapsed = (datetime.now() - last_report).total_seconds() / 60.0
        return elapsed < self._temporal_dedup_window_minutes

    def _record_location_report(self, location: str) -> None:
        """
        Record that a location was reported at the current time.

        Also cleans up entries older than the dedup window.

        Args:
            location: Location name to record
        """
        now = datetime.now()
        loc_key = location.lower().strip()
        self._recent_locations[loc_key] = now

        # Cleanup old entries
        cutoff = self._temporal_dedup_window_minutes
        expired = [
            k for k, ts in self._recent_locations.items()
            if (now - ts).total_seconds() / 60.0 > cutoff
        ]
        for k in expired:
            del self._recent_locations[k]

    # --- GEOCODING ---

    def _geocode_location(self, location: str) -> Optional[Dict[str, float]]:
        """
        Geocode a location string to coordinates.

        Tries direct geocoding, then NLP format, then simplified string retry.

        Args:
            location: Location name/description

        Returns:
            Dict with 'lat' and 'lon' keys or None
        """
        if not self.geocoder or not location:
            return None

        try:
            # Try direct geocoding first
            coords = self.geocoder.get_coordinates(location)
            if coords:
                return coords

            # Try geocoding with NLP result format
            nlp_format = {'location': location}
            enhanced = self.geocoder.geocode_nlp_result(nlp_format)
            if enhanced and enhanced.get('has_coordinates'):
                return enhanced.get('coordinates')

            # Retry with simplified location string
            simplified = self._simplify_location(location)
            if simplified and simplified != location and len(simplified) > 2:
                coords = self.geocoder.get_coordinates(simplified)
                if coords:
                    logger.debug(
                        f"Geocoding succeeded after simplification: "
                        f"'{location}' -> '{simplified}'"
                    )
                    return coords

        except Exception as e:
            logger.debug(f"Geocoding failed for '{location}': {e}")

        return None

    @staticmethod
    def _simplify_location(location: str) -> Optional[str]:
        """
        Simplify a noisy location string for geocoding retry.

        Strips common Filipino/English prefixes and suffixes that
        confuse geocoders (e.g. "near Sto. Nino Church area" -> "Sto. Nino").

        Args:
            location: Raw location string

        Returns:
            Simplified string or None
        """
        if not location:
            return None

        result = location.strip()

        # Strip common prefixes
        prefix_pattern = r'^(?:near|along|sa|malapit\s+sa|dito\s+sa|around|beside|in\s+front\s+of)\s+'
        result = re.sub(prefix_pattern, '', result, flags=re.IGNORECASE).strip()

        # Strip common suffixes
        suffix_pattern = r'\s+(?:area|vicinity|church|school|market|plaza|park|bridge)\s*$'
        result = re.sub(suffix_pattern, '', result, flags=re.IGNORECASE).strip()

        return result if result else None

    def _send_reports_to_hazard_agent(
        self,
        reports: List[Dict[str, Any]],
        skipped_count: int,
        llm_count: int,
        nlp_count: int
    ) -> None:
        """
        Send processed reports to HazardAgent via MessageQueue.

        Args:
            reports: List of processed report dictionaries
            skipped_count: Number of reports skipped (no coordinates)
            llm_count: Number of reports processed with LLM
            nlp_count: Number of reports processed with NLP
        """
        logger.info(
            f"{self.agent_id} forwarding {len(reports)} flood reports to "
            f"{self.hazard_agent_id} via MessageQueue "
            f"(LLM: {llm_count}, NLP: {nlp_count}, skipped: {skipped_count})"
        )

        # Log details of each report being sent
        for i, report in enumerate(reports, 1):
            coords = report.get('coordinates')
            if coords and isinstance(coords, dict):
                coord_str = f"[{coords.get('lat', 0):.4f}, {coords.get('lon', 0):.4f}]"
            elif coords and isinstance(coords, (list, tuple)):
                coord_str = f"[{coords[0]:.4f}, {coords[1]:.4f}]"
            else:
                coord_str = "None"
            logger.info(
                f"  Report {i}: location='{report.get('location', 'N/A')}', "
                f"coords={coord_str}, severity={report.get('severity', 0):.1f}, "
                f"risk={report.get('risk_score', 0):.1f}, type={report.get('report_type', 'N/A')}, "
                f"visual={report.get('visual_evidence', False)}"
            )

        # Check if any reports have visual evidence (for HazardAgent Visual Override)
        visual_reports = sum(1 for r in reports if r.get('visual_evidence'))
        if visual_reports > 0:
            logger.info(
                f"  {visual_reports} reports have visual evidence "
                f"(eligible for Visual Override)"
            )

        try:
            # Create ACL INFORM message with scout reports
            message = create_inform_message(
                sender=self.agent_id,
                receiver=self.hazard_agent_id,
                info_type="scout_report_batch",
                data={
                    "reports": reports,
                    "has_coordinates": True,
                    "report_count": len(reports),
                    "skipped_count": skipped_count,
                    "llm_processed": llm_count,
                    "nlp_processed": nlp_count,
                    "visual_evidence_count": visual_reports,
                    "processing_version": "v2_llm_enhanced"
                }
            )

            # Send via message queue
            self.message_queue.send_message(message)

            logger.info(
                f"{self.agent_id} successfully sent INFORM message to "
                f"{self.hazard_agent_id} ({len(reports)} reports)"
            )

        except Exception as e:
            logger.error(
                f"{self.agent_id} failed to send message to {self.hazard_agent_id}: {e}"
            )

    def shutdown(self) -> None:
        """Performs cleanup on agent shutdown."""
        logger.info(f"{self.agent_id} shutting down")

    # --- SIMULATION MODE METHODS ---

    def _load_simulation_data(self) -> bool:
        """
        Load synthetic tweet data for simulation mode.

        Returns:
            bool: True if data loaded successfully, False otherwise
        """
        try:
            data_dir = Path(__file__).parent.parent / "data" / "synthetic"
            tweet_file = data_dir / f"scout_tweets_{self.simulation_scenario}.json"

            if not tweet_file.exists():
                logger.error(
                    f"Simulation data file not found: {tweet_file}\n"
                    f"Run 'scripts/generate_scout_synthetic_data.py' to create synthetic data"
                )
                return False

            with open(tweet_file, 'r', encoding='utf-8') as f:
                tweets_data = json.load(f)

            if isinstance(tweets_data, dict):
                self.simulation_tweets = list(tweets_data.values())
            else:
                self.simulation_tweets = tweets_data

            self.simulation_index = 0
            logger.info(
                f"{self.agent_id} loaded {len(self.simulation_tweets)} synthetic tweets "
                f"from scenario {self.simulation_scenario}"
            )
            return True

        except Exception as e:
            logger.error(f"{self.agent_id} error loading simulation data: {e}")
            return False

    def _get_simulation_tweets(self, batch_size: int = 10) -> list:
        """
        Get the next batch of simulation tweets.

        Args:
            batch_size: Number of tweets to return per step

        Returns:
            list: Next batch of tweet dictionaries
        """
        if not self.simulation_tweets:
            logger.debug(f"{self.agent_id} no simulation data loaded")
            return []

        if self.simulation_index >= len(self.simulation_tweets):
            logger.info(
                f"{self.agent_id} reached end of simulation data "
                f"({self.simulation_index}/{len(self.simulation_tweets)} tweets processed)"
            )
            return []

        start_idx = self.simulation_index
        end_idx = min(start_idx + batch_size, len(self.simulation_tweets))
        batch = self.simulation_tweets[start_idx:end_idx]

        self.simulation_index = end_idx

        logger.debug(
            f"{self.agent_id} returning simulation batch: "
            f"tweets {start_idx+1}-{end_idx} of {len(self.simulation_tweets)}"
        )

        return batch

    def _prepare_simulation_tweets_for_ml(self, tweets: list) -> list:
        """
        Prepare simulation tweets for ML processing by stripping ground truth.

        Args:
            tweets: List of raw simulation tweet dictionaries

        Returns:
            list: Tweets with ground truth removed, ready for ML processing
        """
        if not self.use_ml_in_simulation:
            return tweets

        KEEP_KEYS = {"tweet_id", "username", "text", "timestamp", "url", "image_path", "replies", "retweets", "likes", "scraped_at"}
        prepared_tweets = []
        for tweet in tweets:
            clean_tweet = {k: tweet.get(k) for k in KEEP_KEYS}
            prepared_tweets.append(clean_tweet)

        logger.debug(
            f"{self.agent_id} prepared {len(prepared_tweets)} simulation tweets "
            f"for ML processing (ground truth stripped)"
        )

        return prepared_tweets

    def reset_simulation(self) -> None:
        """Reset simulation to the beginning."""
        self.simulation_index = 0
        logger.info(f"{self.agent_id} simulation reset to beginning")

    def set_batch_size(self, batch_size: int) -> None:
        """
        Set the batch size for simulation mode.

        Args:
            batch_size: Number of tweets to return per step
        """
        if batch_size < 1:
            raise ValueError("Batch size must be at least 1")

        self.simulation_batch_size = batch_size
        logger.info(f"{self.agent_id} batch size set to {batch_size}")

    def is_llm_enabled(self) -> bool:
        """Check if LLM processing is enabled and available."""
        return self.use_llm and self.llm_service is not None

    def get_processing_stats(self) -> Dict[str, Any]:
        """
        Get processing statistics.

        Returns:
            Dict with processing mode and availability info
        """
        return {
            "llm_enabled": self.use_llm,
            "llm_available": self.llm_service.is_available() if self.llm_service else False,
            "nlp_available": self.nlp_processor is not None,
            "geocoder_available": self.geocoder is not None,
            "simulation_scenario": self.simulation_scenario,
            "tweets_processed": self.simulation_index,
            "tweets_total": len(self.simulation_tweets)
        }
