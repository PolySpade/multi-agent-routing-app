# filename: app/agents/scout_agent.py

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, TYPE_CHECKING

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
    ScoutAgent - Crowdsourced Data Collection

    CURRENT MODE: Simulation only
    FUTURE: Integrate Twitter API v2 when available

    Generates synthetic flood reports for testing and development.
    Processes simulated tweets through NLP models and forwards validated
    reports to the HazardAgent via MessageQueue using FIPA-ACL protocol.

    Attributes:
        agent_id: Unique identifier for this agent
        environment: Reference to DynamicGraphEnvironment
        message_queue: MessageQueue for asynchronous MAS communication
        hazard_agent_id: Target HazardAgent ID for message routing
        nlp_processor: NLP processor for tweet analysis
    """
    def __init__(
        self,
        agent_id: str,
        environment: "DynamicGraphEnvironment",
        message_queue: Optional["MessageQueue"] = None,
        hazard_agent_id: str = "hazard_agent_001",
        simulation_scenario: int = 1,
        use_ml_in_simulation: bool = True
    ) -> None:
        """
        Initialize ScoutAgent for crowdsourced flood data collection.

        CURRENT MODE: Simulation only - generates synthetic flood reports
        FUTURE: Integrate Twitter API v2 for real-time data

        Args:
            agent_id: Unique identifier for this agent
            environment: Reference to the DynamicGraphEnvironment instance
            message_queue: MessageQueue instance for MAS communication
            hazard_agent_id: Target HazardAgent ID for message routing (default: "hazard_agent_001")
            simulation_scenario: Which scenario to load (1-3) for simulation
            use_ml_in_simulation: If True, process simulation tweets through ML models instead
                                 of using pre-computed ground truth (default: True)
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

        # Simulation mode settings (ALWAYS simulation-only now)
        self.simulation_mode = True
        self.simulation_scenario = simulation_scenario
        self.simulation_tweets = []
        self.simulation_index = 0
        self.simulation_batch_size = 10  # Default batch size
        self.use_ml_in_simulation = use_ml_in_simulation

        # Initialize NLP processor
        try:
            from ..ml_models.nlp_processor import NLPProcessor
            self.nlp_processor = NLPProcessor()
            self.logger.info(f"{self.agent_id} initialized with NLP processor")
        except Exception as e:
            self.logger.warning(
                f"{self.agent_id} failed to initialize NLP processor: {e}"
            )
            self.nlp_processor = None

        # Initialize LocationGeocoder for coordinate extraction
        try:
            from ..ml_models.location_geocoder import LocationGeocoder
            self.geocoder = LocationGeocoder()
            self.logger.info(f"{self.agent_id} initialized with LocationGeocoder")
        except Exception as e:
            self.logger.warning(
                f"{self.agent_id} failed to initialize LocationGeocoder: {e}"
            )
            self.geocoder = None
        
        # Log initialization
        self.logger.info(f"ScoutAgent '{self.agent_id}' initialized in SIMULATION MODE")
        self.logger.info(f"  Using synthetic data scenario {self.simulation_scenario}")
        ml_mode = "ML PREDICTION" if self.use_ml_in_simulation else "PRE-COMPUTED GROUND TRUTH"
        self.logger.info(f"  Simulation processing mode: {ml_mode}")

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
        # This strips ground truth if use_ml_in_simulation is True
        prepared_tweets = self._prepare_simulation_tweets_for_ml(raw_tweets)

        if prepared_tweets:
            self.logger.info(f"{self.agent_id} found {len(prepared_tweets)} simulated tweets")

            # Process tweets with NLP and forward to HazardAgent
            self._process_and_forward_tweets(prepared_tweets)
        else:
            self.logger.debug(f"{self.agent_id} no more simulation data available")

        return prepared_tweets

    def _process_and_forward_tweets(self, tweets: list) -> None:
        """
        Process tweets using NLP and forward to HazardAgent.

        Args:
            tweets: List of tweet dictionaries to process
        """
        if not self.nlp_processor:
            logger.warning(f"{self.agent_id} has no NLP processor, skipping tweet processing")
            return

        if not self.message_queue:
            logger.warning(f"{self.agent_id} has no MessageQueue, data not forwarded")
            return

        if not self.geocoder:
            logger.warning(f"{self.agent_id} has no LocationGeocoder, using old method")
            self._process_and_forward_tweets_without_coordinates(tweets)
            return

        processed_reports = []
        skipped_no_coordinates = 0

        for tweet in tweets:
            try:
                # Extract flood info using NLP
                flood_info = self.nlp_processor.extract_flood_info(tweet['text'])

                # Enhance with coordinates using geocoder
                enhanced_info = self.geocoder.geocode_nlp_result(flood_info)

                # Only process flood-related reports with coordinates
                if enhanced_info['is_flood_related'] and enhanced_info.get('has_coordinates'):
                    # Create scout report for HazardAgent with coordinates
                    report = {
                        "location": enhanced_info['location'] or "Marikina",
                        "coordinates": enhanced_info['coordinates'],  # NEW: Critical field
                        "severity": enhanced_info['severity'],
                        "report_type": enhanced_info['report_type'],
                        "confidence": enhanced_info['confidence'],
                        "timestamp": datetime.fromisoformat(tweet['timestamp'].replace('Z', '+00:00')),
                        "source": "twitter",
                        "source_url": tweet.get('url', ''),
                        "username": tweet.get('username', ''),
                        "text": tweet['text']
                    }

                    processed_reports.append(report)

                    # Log the actual message content being sent
                    logger.info(
                        f"Message sent: {tweet['text']}"
                    )

                    logger.debug(
                        f"{self.agent_id} processed tweet from @{tweet.get('username')}: "
                        f"{enhanced_info['location']} ({enhanced_info['coordinates']['lat']:.4f}, "
                        f"{enhanced_info['coordinates']['lon']:.4f}) - severity {enhanced_info['severity']:.2f}"
                    )
                elif enhanced_info['is_flood_related'] and not enhanced_info.get('has_coordinates'):
                    skipped_no_coordinates += 1
                    logger.debug(
                        f"{self.agent_id} skipped flood-related tweet without coordinates: "
                        f"location '{enhanced_info.get('location')}'"
                    )

            except Exception as e:
                logger.error(f"{self.agent_id} error processing tweet: {e}")
                continue

        # Forward all processed reports to HazardAgent via MessageQueue (MAS architecture)
        if processed_reports:
            logger.info(
                f"{self.agent_id} forwarding {len(processed_reports)} "
                f"flood reports with coordinates to {self.hazard_agent_id} via MessageQueue "
                f"(skipped {skipped_no_coordinates} without coordinates)"
            )

            try:
                # Create ACL INFORM message with scout reports (with coordinates)
                message = create_inform_message(
                    sender=self.agent_id,
                    receiver=self.hazard_agent_id,
                    info_type="scout_report_batch",  # Standard message type
                    data={
                        "reports": processed_reports,
                        "has_coordinates": True,  # Flag for HazardAgent to use coordinate-based processing
                        "report_count": len(processed_reports),
                        "skipped_count": skipped_no_coordinates
                    }
                )

                # Send via message queue
                self.message_queue.send_message(message)

                logger.info(
                    f"{self.agent_id} successfully sent INFORM message to "
                    f"{self.hazard_agent_id} ({len(processed_reports)} reports with coordinates)"
                )

            except Exception as e:
                logger.error(
                    f"{self.agent_id} failed to send message to {self.hazard_agent_id}: {e}"
                )

        elif skipped_no_coordinates > 0:
            logger.warning(
                f"{self.agent_id} all {skipped_no_coordinates} flood-related tweets "
                f"lacked coordinates and were skipped"
            )

    def _process_and_forward_tweets_without_coordinates(self, tweets: list) -> None:
        """
        Fallback method for processing tweets without geocoder (legacy).

        Args:
            tweets: List of tweet dictionaries to process
        """
        processed_reports = []

        for tweet in tweets:
            try:
                # Extract flood info using NLP
                flood_info = self.nlp_processor.extract_flood_info(tweet['text'])

                if flood_info['is_flood_related']:
                    # Create scout report for HazardAgent (without coordinates)
                    report = {
                        "location": flood_info['location'] or "Marikina",
                        "severity": flood_info['severity'],
                        "report_type": flood_info['report_type'],
                        "confidence": flood_info['confidence'],
                        "timestamp": datetime.fromisoformat(tweet['timestamp'].replace('Z', '+00:00')),
                        "source": "twitter",
                        "source_url": tweet.get('url', ''),
                        "username": tweet.get('username', ''),
                        "text": tweet['text']
                    }

                    processed_reports.append(report)

                    # Log the actual message content being sent
                    logger.info(
                        f"Message sent: {tweet['text']}"
                    )

                    logger.debug(
                        f"{self.agent_id} processed tweet from @{tweet.get('username')}: "
                        f"{flood_info['location']} - severity {flood_info['severity']:.2f}"
                    )

            except Exception as e:
                logger.error(f"{self.agent_id} error processing tweet: {e}")
                continue

        # Forward via MessageQueue (MAS architecture) - legacy mode without coordinates
        if processed_reports:
            logger.info(
                f"{self.agent_id} forwarding {len(processed_reports)} "
                f"flood reports to {self.hazard_agent_id} via MessageQueue (legacy mode without coordinates)"
            )

            try:
                # Create ACL INFORM message with scout reports (without coordinates)
                message = create_inform_message(
                    sender=self.agent_id,
                    receiver=self.hazard_agent_id,
                    info_type="scout_report_batch",  # Standard message type
                    data={
                        "reports": processed_reports,
                        "has_coordinates": False,  # Flag for HazardAgent to use legacy processing
                        "report_count": len(processed_reports)
                    }
                )

                # Send via message queue
                self.message_queue.send_message(message)

                logger.info(
                    f"{self.agent_id} successfully sent INFORM message to "
                    f"{self.hazard_agent_id} ({len(processed_reports)} reports without coordinates)"
                )

            except Exception as e:
                logger.error(
                    f"{self.agent_id} failed to send message to {self.hazard_agent_id}: {e}"
                )

    def shutdown(self) -> None:
        """
        Performs cleanup on agent shutdown.
        """
        self.logger.info(f"{self.agent_id} shutting down")

    # --- SIMULATION MODE METHODS ---

    def _load_simulation_data(self) -> bool:
        """
        Load synthetic tweet data for simulation mode.

        Returns:
            bool: True if data loaded successfully, False otherwise
        """
        try:
            # Build path to synthetic data file
            data_dir = Path(__file__).parent.parent / "data" / "synthetic"
            tweet_file = data_dir / f"scout_tweets_{self.simulation_scenario}.json"

            if not tweet_file.exists():
                self.logger.error(
                    f"Simulation data file not found: {tweet_file}\n"
                    f"Run 'scripts/generate_scout_synthetic_data.py' to create synthetic data"
                )
                return False

            # Load tweets from file
            with open(tweet_file, 'r', encoding='utf-8') as f:
                tweets_data = json.load(f)

            # Convert dict to list if necessary
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
            batch_size: Number of tweets to return per step (default: 10)

        Returns:
            list: Next batch of tweet dictionaries
        """
        if not self.simulation_tweets:
            self.logger.warning(f"{self.agent_id} no simulation data loaded")
            return []

        # Check if we've reached the end
        if self.simulation_index >= len(self.simulation_tweets):
            self.logger.info(
                f"{self.agent_id} reached end of simulation data "
                f"({self.simulation_index}/{len(self.simulation_tweets)} tweets processed)"
            )
            return []

        # Get next batch
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

        When use_ml_in_simulation is True, this method removes pre-computed
        values from simulation tweets so they are processed through NLP models
        instead of using ground truth.

        Args:
            tweets: List of raw simulation tweet dictionaries

        Returns:
            list: Tweets with ground truth removed, ready for ML processing
        """
        if not self.use_ml_in_simulation:
            # Return tweets as-is if not using ML (use ground truth)
            return tweets

        prepared_tweets = []
        for tweet in tweets:
            # Create a copy without ground truth
            clean_tweet = {
                "tweet_id": tweet.get("tweet_id"),
                "username": tweet.get("username"),
                "text": tweet.get("text"),  # Raw text for ML processing
                "timestamp": tweet.get("timestamp"),
                "url": tweet.get("url"),
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
        """
        Reset simulation to the beginning.
        Useful for running multiple simulation cycles.
        """
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

