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

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, TYPE_CHECKING

from .base_agent import BaseAgent
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

    Attributes:
        agent_id: Unique identifier for this agent
        environment: Reference to DynamicGraphEnvironment
        message_queue: MessageQueue for asynchronous MAS communication
        hazard_agent_id: Target HazardAgent ID for message routing
        nlp_processor: Traditional NLP processor (fallback)
        llm_service: LLM service for enhanced analysis
        use_llm: Whether LLM processing is enabled
    """

    def __init__(
        self,
        agent_id: str,
        environment: "DynamicGraphEnvironment",
        message_queue: Optional["MessageQueue"] = None,
        hazard_agent_id: str = "hazard_agent_001",
        simulation_scenario: int = 1,
        use_ml_in_simulation: bool = True,
        enable_llm: bool = True
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
        """
        super().__init__(agent_id, environment)

        # Message queue for MAS communication
        self.message_queue = message_queue
        self.hazard_agent_id = hazard_agent_id

        # Register with message queue
        if self.message_queue:
            try:
                self.message_queue.register_agent(self.agent_id)
                logger.info(f"{self.agent_id} registered with MessageQueue")
            except ValueError as e:
                logger.warning(f"{self.agent_id} already registered: {e}")

        # Simulation mode settings
        self.simulation_mode = True
        self.simulation_scenario = simulation_scenario
        self.simulation_tweets = []
        self.simulation_index = 0
        self.simulation_batch_size = 10
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
                    self.logger.info(
                        f"{self.agent_id} LLM Service initialized (text + vision models)"
                    )
                else:
                    self.logger.warning(
                        f"{self.agent_id} LLM Service not available, will use fallback NLP"
                    )
            except Exception as e:
                self.logger.warning(
                    f"{self.agent_id} failed to initialize LLM Service: {e}. "
                    "Falling back to traditional NLP."
                )
                self.llm_service = None

        # ========== TRADITIONAL NLP PROCESSOR (FALLBACK) ==========
        try:
            from ..ml_models.nlp_processor import NLPProcessor
            self.nlp_processor = NLPProcessor()
            self.logger.info(f"{self.agent_id} initialized with NLP processor (fallback)")
        except Exception as e:
            self.logger.warning(
                f"{self.agent_id} failed to initialize NLP processor: {e}"
            )
            self.nlp_processor = None

        # ========== LOCATION GEOCODER ==========
        try:
            from ..ml_models.location_geocoder import LocationGeocoder
            self.geocoder = LocationGeocoder(llm_service=self.llm_service)
            self.logger.info(f"{self.agent_id} initialized with LocationGeocoder")
        except Exception as e:
            self.logger.warning(
                f"{self.agent_id} failed to initialize LocationGeocoder: {e}"
            )
            self.geocoder = None

        # Log initialization summary
        processing_mode = "LLM" if self.use_llm else "Traditional NLP"
        self.logger.info(f"ScoutAgent '{self.agent_id}' initialized in SIMULATION MODE")
        self.logger.info(f"  Using synthetic data scenario {self.simulation_scenario}")
        self.logger.info(f"  Text processing mode: {processing_mode}")
        self.logger.info(f"  Vision processing: {'ENABLED' if self.use_llm else 'DISABLED'}")

    def setup(self) -> bool:
        """
        Initializes the agent for operation by loading synthetic data.

        Returns:
            bool: True if setup was successful, False otherwise.
        """
        self.logger.info(f"{self.agent_id} loading synthetic data")
        return self._load_simulation_data()

    def step(self) -> list:
        """
        Collects and processes synthetic flood data from simulation.

        This method is designed to be called repeatedly by the main simulation loop.

        Returns:
            list: A list of processed tweet dictionaries.
        """
        self.logger.info(
            f"{self.agent_id} collecting simulated data at {datetime.now().strftime('%H:%M:%S')}"
        )

        # Get next batch of simulation tweets
        raw_tweets = self._get_simulation_tweets(batch_size=self.simulation_batch_size)

        # Prepare simulation tweets for ML processing
        prepared_tweets = self._prepare_simulation_tweets_for_ml(raw_tweets)

        if prepared_tweets:
            self.logger.info(f"{self.agent_id} found {len(prepared_tweets)} simulated tweets")

            # Process tweets with LLM/NLP and forward to HazardAgent
            self._process_and_forward_tweets(prepared_tweets)
        else:
            self.logger.debug(f"{self.agent_id} no more simulation data available")

        return prepared_tweets

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

        Args:
            tweet: Tweet dictionary with 'text', 'timestamp', etc.

        Returns:
            Processed report dictionary or None if processing fails
        """
        report_data = {
            'visual_evidence': False,
            'confidence': 0.5,
            'is_flood_related': False,
            'source': 'scout_agent'
        }

        # ========== 1. VISUAL ANALYSIS (Vision Model) ==========
        if tweet.get('image_path') and self.llm_service and self.use_llm:
            visual_result = self._analyze_image(tweet['image_path'])
            if visual_result:
                report_data.update(visual_result)

        # ========== 2. TEXT ANALYSIS (LLM or fallback NLP) ==========
        text_result = self._analyze_text(tweet.get('text', ''))
        if text_result:
            # Merge text analysis into report
            report_data['location'] = text_result.get('location') or tweet.get('location')
            report_data['is_flood_related'] = text_result.get('is_flood_related', False)
            report_data['description'] = text_result.get('description')
            report_data['report_type'] = text_result.get('report_type', 'flood')

            # Update source if LLM was used
            if text_result.get('source') and 'nlp' not in text_result.get('source', '').lower():
                report_data['source'] = 'scout_agent_llm_enhanced'

        # ========== 3. FUSION LOGIC ==========
        # Take maximum risk from visual and text analysis
        visual_risk = report_data.get('risk_score', 0) or 0
        text_severity = text_result.get('severity', 0) if text_result else 0
        final_risk = max(visual_risk, text_severity)

        report_data['severity'] = final_risk
        report_data['risk_score'] = final_risk

        # Visual evidence with high risk = high confidence
        if report_data.get('visual_evidence') and final_risk > 0.5:
            report_data['confidence'] = 0.9
        elif text_result:
            report_data['confidence'] = text_result.get('confidence', 0.5)

        # Skip non-flood reports
        if not report_data.get('is_flood_related') and not report_data.get('visual_evidence'):
            return None

        # ========== 4. GEOCODING ==========
        if report_data.get('location') and self.geocoder:
            coords = self._geocode_location(report_data['location'])
            if coords:
                report_data['coordinates'] = coords
                report_data['has_coordinates'] = True
            else:
                report_data['has_coordinates'] = False
        else:
            report_data['has_coordinates'] = False

        # ========== 5. BUILD FINAL PAYLOAD ==========
        timestamp = tweet.get('timestamp')
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except:
                timestamp = datetime.now()

        payload = {
            "location": report_data.get('location') or "Marikina",
            "coordinates": report_data.get('coordinates'),
            "severity": report_data.get('severity', 0),
            "risk_score": report_data.get('risk_score', 0),
            "report_type": report_data.get('report_type', 'flood') if final_risk > 0.3 else 'observation',
            "confidence": report_data.get('confidence', 0.5),
            "visual_evidence": report_data.get('visual_evidence', False),
            "estimated_depth_m": report_data.get('estimated_depth_m'),
            "vehicles_passable": report_data.get('vehicles_passable'),
            "timestamp": timestamp,
            "source": report_data.get('source', 'scout_agent'),
            "source_url": tweet.get('url', ''),
            "username": tweet.get('username', ''),
            "text": tweet.get('text', ''),
            "is_flood_related": report_data.get('is_flood_related', False),
            "has_coordinates": report_data.get('has_coordinates', False)
        }

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
                if visual_analysis.get('risk_score', 0) > 0.5:
                    self.logger.info(
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

    def _geocode_location(self, location: str) -> Optional[Dict[str, float]]:
        """
        Geocode a location string to coordinates.

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

        except Exception as e:
            logger.debug(f"Geocoding failed for '{location}': {e}")

        return None

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

    def _process_and_forward_tweets_without_coordinates(self, tweets: list) -> None:
        """
        Fallback method for processing tweets without geocoder (legacy).

        Args:
            tweets: List of tweet dictionaries to process
        """
        # Guard: Check processing capability
        if not self.nlp_processor and not self.use_llm:
            logger.error(
                f"{self.agent_id} cannot process tweets: no processor available."
            )
            return

        processed_reports = []

        for tweet in tweets:
            try:
                # Use LLM or NLP
                flood_info = self._analyze_text(tweet.get('text', ''))

                if not flood_info or not isinstance(flood_info, dict):
                    continue

                if flood_info.get('is_flood_related'):
                    report = {
                        "location": flood_info.get('location') or "Marikina",
                        "severity": flood_info.get('severity', 0),
                        "report_type": flood_info.get('report_type', 'flood'),
                        "confidence": flood_info.get('confidence', 0.5),
                        "timestamp": datetime.fromisoformat(
                            tweet['timestamp'].replace('Z', '+00:00')
                        ) if tweet.get('timestamp') else datetime.now(),
                        "source": "twitter",
                        "source_url": tweet.get('url', ''),
                        "username": tweet.get('username', ''),
                        "text": tweet.get('text', ''),
                        "visual_evidence": False
                    }

                    processed_reports.append(report)
                    logger.info(f"Message sent: {tweet.get('text', '')[:100]}...")

            except Exception as e:
                logger.error(f"{self.agent_id} error processing tweet: {e}")
                continue

        # Forward via MessageQueue (legacy mode without coordinates)
        if processed_reports:
            logger.info(
                f"{self.agent_id} forwarding {len(processed_reports)} "
                f"flood reports to {self.hazard_agent_id} (legacy mode)"
            )

            try:
                message = create_inform_message(
                    sender=self.agent_id,
                    receiver=self.hazard_agent_id,
                    info_type="scout_report_batch",
                    data={
                        "reports": processed_reports,
                        "has_coordinates": False,
                        "report_count": len(processed_reports)
                    }
                )

                self.message_queue.send_message(message)

            except Exception as e:
                logger.error(
                    f"{self.agent_id} failed to send message to {self.hazard_agent_id}: {e}"
                )

    def shutdown(self) -> None:
        """Performs cleanup on agent shutdown."""
        self.logger.info(f"{self.agent_id} shutting down")

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
                self.logger.error(
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
            self.logger.info(
                f"{self.agent_id} loaded {len(self.simulation_tweets)} synthetic tweets "
                f"from scenario {self.simulation_scenario}"
            )
            return True

        except Exception as e:
            self.logger.error(f"{self.agent_id} error loading simulation data: {e}")
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
            self.logger.warning(f"{self.agent_id} no simulation data loaded")
            return []

        if self.simulation_index >= len(self.simulation_tweets):
            self.logger.info(
                f"{self.agent_id} reached end of simulation data "
                f"({self.simulation_index}/{len(self.simulation_tweets)} tweets processed)"
            )
            return []

        start_idx = self.simulation_index
        end_idx = min(start_idx + batch_size, len(self.simulation_tweets))
        batch = self.simulation_tweets[start_idx:end_idx]

        self.simulation_index = end_idx

        self.logger.debug(
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

        prepared_tweets = []
        for tweet in tweets:
            clean_tweet = {
                "tweet_id": tweet.get("tweet_id"),
                "username": tweet.get("username"),
                "text": tweet.get("text"),
                "timestamp": tweet.get("timestamp"),
                "url": tweet.get("url"),
                "image_path": tweet.get("image_path"),  # Include image path for VL
                "replies": tweet.get("replies"),
                "retweets": tweet.get("retweets"),
                "likes": tweet.get("likes"),
                "scraped_at": tweet.get("scraped_at")
            }
            prepared_tweets.append(clean_tweet)

        self.logger.debug(
            f"{self.agent_id} prepared {len(prepared_tweets)} simulation tweets "
            f"for ML processing (ground truth stripped)"
        )

        return prepared_tweets

    def reset_simulation(self) -> None:
        """Reset simulation to the beginning."""
        self.simulation_index = 0
        self.logger.info(f"{self.agent_id} simulation reset to beginning")

    def set_batch_size(self, batch_size: int) -> None:
        """
        Set the batch size for simulation mode.

        Args:
            batch_size: Number of tweets to return per step
        """
        if batch_size < 1:
            raise ValueError("Batch size must be at least 1")

        self.simulation_batch_size = batch_size
        self.logger.info(f"{self.agent_id} batch size set to {batch_size}")

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
