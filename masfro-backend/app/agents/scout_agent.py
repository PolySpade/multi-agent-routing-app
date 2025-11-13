# filename: app/agents/scout_agent.py

import time
import os
import json
import pickle
import hashlib
import csv
from datetime import datetime
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from .base_agent import BaseAgent
import logging

if TYPE_CHECKING:
    from ..environment.graph_manager import DynamicGraphEnvironment
    from ..core.credentials import TwitterCredentials
    from .hazard_agent import HazardAgent

logger = logging.getLogger(__name__)

class ScoutAgent(BaseAgent):
    """
    The ScoutAgent is responsible for scraping real-time data from social media
    (X.com/Twitter) to identify flood-related events in Marikina City.

    This agent collects crowdsourced Volunteered Geographic Information (VGI)
    from social media, processes it using NLP, and forwards validated reports
    to the HazardAgent for data fusion.

    WARNING: This agent currently uses deprecated Selenium-based scraping.
    Migrate to Twitter API v2 for better reliability and security.

    Attributes:
        agent_id: Unique identifier for this agent
        environment: Reference to DynamicGraphEnvironment
        hazard_agent: Reference to HazardAgent for data forwarding
        nlp_processor: NLP processor for tweet analysis
        _credentials: Optional TwitterCredentials for authentication (DEPRECATED)
    """
    def __init__(
        self,
        agent_id: str,
        environment: "DynamicGraphEnvironment",
        credentials: Optional["TwitterCredentials"] = None,
        hazard_agent: Optional["HazardAgent"] = None,
        simulation_mode: bool = False,
        simulation_scenario: int = 1
    ) -> None:
        """
        Initialize ScoutAgent for crowdsourced flood data collection.

        WARNING: This agent currently uses Selenium-based web scraping which is:
        - Fragile and prone to breaking when Twitter/X updates their UI
        - Slow and resource-intensive
        - Security risk if credentials are used

        RECOMMENDED: Migrate to Twitter API v2 instead.

        Args:
            agent_id: Unique identifier for this agent
            environment: Reference to the DynamicGraphEnvironment instance
            credentials: Optional TwitterCredentials for authentication (NOT RECOMMENDED)
            hazard_agent: Optional reference to HazardAgent for data forwarding
            simulation_mode: If True, uses synthetic data instead of scraping (default: False)
            simulation_scenario: Which scenario to load (1-3) when in simulation mode
        """
        super().__init__(agent_id, environment)

        # Store credentials object (not individual fields) - only if provided
        self._credentials = credentials
        if credentials and (credentials.twitter_email or credentials.twitter_password):
            self.logger.warning(
                "ScoutAgent initialized with plain-text credentials. "
                "This is a SECURITY RISK. Consider using Twitter API v2 instead."
            )

        self.driver = None
        self.hazard_agent = hazard_agent

        # Simulation mode settings
        self.simulation_mode = simulation_mode
        self.simulation_scenario = simulation_scenario
        self.simulation_tweets = []
        self.simulation_index = 0
        self.simulation_batch_size = 10  # Default batch size

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
        
        # --- CENTRALIZED FILE PATHS ---
        # Define the path to the data directory relative to the project root.
        data_directory = os.path.join("app", "data")
        
        # Set the full path for the master tweet file.
        self.master_file = os.path.join(data_directory, "marikina_tweets_master.json")
        
        # NEW: Set the full path for the Twitter session file.
        self.session_file = os.path.join(data_directory, "twitter_session.pkl")
        
        self.master_tweets = {}

        # Log initialization
        mode_str = "SIMULATION MODE" if self.simulation_mode else "SCRAPING MODE"
        self.logger.info(f"ScoutAgent '{self.agent_id}' initialized in {mode_str}")
        if self.simulation_mode:
            self.logger.info(f"  Using synthetic data scenario {self.simulation_scenario}")
        else:
            self.logger.debug(f"  Master tweet file path: {self.master_file}")
            self.logger.debug(f"  Session file path: {self.session_file}")

    def set_hazard_agent(self, hazard_agent) -> None:
        """
        Set reference to HazardAgent for data forwarding.

        Args:
            hazard_agent: HazardAgent instance
        """
        self.hazard_agent = hazard_agent
        logger.info(f"{self.agent_id} linked to {hazard_agent.agent_id}")

    def setup(self) -> bool:
        """
        Initializes the agent for operation.
        - In scraping mode: Sets up Selenium WebDriver and logs into X.com
        - In simulation mode: Loads synthetic data from file

        Returns:
            bool: True if setup was successful, False otherwise.
        """
        if self.simulation_mode:
            # Simulation mode: Load synthetic data
            self.logger.info(f"{self.agent_id} loading synthetic data")
            return self._load_simulation_data()
        else:
            # Scraping mode: Login to Twitter
            self.logger.info(f"{self.agent_id} setting up WebDriver and logging in")
            self.driver = self._login_to_twitter()
            if self.driver:
                self.master_tweets = self._load_master_tweets()
                self.logger.info(f"{self.agent_id} setup completed successfully")
                return True
            self.logger.error(f"{self.agent_id} setup failed - could not login")
            return False


    def step(self) -> list:
        """
        Performs one cycle of the agent's primary task.
        - In scraping mode: Searches for, extracts, and processes new tweets
        - In simulation mode: Returns the next batch of synthetic tweets

        This method is designed to be called repeatedly by the main simulation loop.

        Returns:
            list: A list of newly found tweet dictionaries.
        """
        self.logger.info(
            f"{self.agent_id} performing step at {datetime.now().strftime('%H:%M:%S')}"
        )

        if self.simulation_mode:
            # Simulation mode: Get next batch of tweets
            raw_tweets = self._get_simulation_tweets(batch_size=self.simulation_batch_size)
        else:
            # Scraping mode: Search Twitter
            raw_tweets = self._search_tweets()

        if not self.simulation_mode:
            # In scraping mode, track which tweets are new
            newly_added_tweets = self._add_new_tweets_to_master(raw_tweets)
        else:
            # In simulation mode, all tweets are "new"
            newly_added_tweets = raw_tweets

        if newly_added_tweets:
            self.logger.info(f"{self.agent_id} found {len(newly_added_tweets)} new tweets")

            # Process tweets with NLP and forward to HazardAgent
            self._process_and_forward_tweets(newly_added_tweets)
        else:
            self.logger.debug(f"{self.agent_id} no new tweets found in this step")

        return newly_added_tweets

    def _process_and_forward_tweets(self, tweets: list) -> None:
        """
        Process tweets using NLP and forward to HazardAgent.

        Args:
            tweets: List of tweet dictionaries to process
        """
        if not self.nlp_processor:
            logger.warning(f"{self.agent_id} has no NLP processor, skipping tweet processing")
            return

        if not self.hazard_agent:
            logger.warning(f"{self.agent_id} has no HazardAgent reference, data not forwarded")
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

        # Forward all processed reports to HazardAgent using coordinate-based method
        if processed_reports:
            logger.info(
                f"{self.agent_id} forwarding {len(processed_reports)} "
                f"flood reports with coordinates to HazardAgent "
                f"(skipped {skipped_no_coordinates} without coordinates)"
            )
            self.hazard_agent.process_scout_data_with_coordinates(processed_reports)
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
                    logger.debug(
                        f"{self.agent_id} processed tweet from @{tweet.get('username')}: "
                        f"{flood_info['location']} - severity {flood_info['severity']:.2f}"
                    )

            except Exception as e:
                logger.error(f"{self.agent_id} error processing tweet: {e}")
                continue

        # Forward using legacy method without coordinates
        if processed_reports:
            logger.info(
                f"{self.agent_id} forwarding {len(processed_reports)} "
                f"flood reports to HazardAgent (legacy mode without coordinates)"
            )
            self.hazard_agent.process_scout_data(processed_reports)

    def shutdown(self) -> None:
        """
        Gracefully closes the Selenium WebDriver and performs any final cleanup.
        """
        self.logger.info(f"{self.agent_id} shutting down")
        if self.driver:
            self.driver.quit()
            self.logger.info(f"{self.agent_id} WebDriver closed")

        if not self.simulation_mode:
            self._export_master_tweets_to_csv()

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

    # --- PRIVATE HELPER METHODS (from your original script) ---
    # The following methods are encapsulated within the agent class.

    def _login_to_twitter(self, use_saved_session: bool = True) -> Optional[webdriver.Chrome]:
        """
        Logs into Twitter/X.com using Selenium. Attempts to restore a saved session
        first, then performs a fresh login if needed.
        
        WARNING: This method is deprecated and should be replaced with Twitter API v2.
        
        Args:
            use_saved_session: Whether to attempt session restoration
        
        Returns:
            WebDriver instance if successful, None otherwise.
        
        Raises:
            MissingCredentialError: If credentials are not provided
        """
        from ..exceptions import MissingCredentialError
        
        # Check if credentials are available
        if not self._credentials or not self._credentials.twitter_email:
            raise MissingCredentialError("TWITTER_EMAIL")
        if not self._credentials or not self._credentials.twitter_password:
            raise MissingCredentialError("TWITTER_PASSWORD")
        
        chrome_options = Options()
        # Standard options
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Anti-bot detection options
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument('--disable-infobars')
        chrome_options.add_argument('--start-maximized')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-gpu")
        custom_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36"
        chrome_options.add_argument(f'user-agent={custom_user_agent}')

        # Experimental options to make it look less like a bot
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.maximize_window()

        try:
            # Try to restore saved session first
            if use_saved_session and self._load_cookies():
                if self._verify_login_status():
                    self.logger.info(f"{self.agent_id} successfully restored session")
                    return self.driver
            
            # Perform fresh login
            self.logger.info(f"{self.agent_id} performing fresh login")
            self.driver.get("https://x.com/i/flow/login")
            
            # Wait for and enter email/username
            self.logger.debug(f"{self.agent_id} entering email")
            email_input = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[autocomplete='username']"))
            )
            email_input.send_keys(self._credentials.twitter_email)
            email_input.send_keys(Keys.RETURN)
            time.sleep(2)
            
            # Sometimes Twitter asks for username verification (unusual activity)
            try:
                self.logger.debug(f"{self.agent_id} checking for username verification prompt")
                username_input = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[data-testid='ocfEnterTextTextInput']"))
                )
                # Extract username from email (assumes email format: username@domain.com)
                username = self._credentials.twitter_email.split('@')[0]
                username_input.send_keys(username)
                username_input.send_keys(Keys.RETURN)
                time.sleep(2)
                self.logger.info(f"{self.agent_id} username verification completed")
            except TimeoutException:
                self.logger.debug(f"{self.agent_id} no username verification required")
            
            # Wait for and enter password
            self.logger.debug(f"{self.agent_id} entering password")
            password_input = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='password']"))
            )
            password_input.send_keys(self._credentials.twitter_password)
            password_input.send_keys(Keys.RETURN)
            
            # Wait for successful login (home timeline appears)
            self.logger.info(f"{self.agent_id} waiting for login to complete")
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[aria-label='Home timeline']"))
            )
            
            self.logger.info(f"{self.agent_id} fresh login successful")
            self._save_cookies()
            return self.driver
            
        except Exception as e:
            self.logger.error(
                f"{self.agent_id} error during login: {e}",
                exc_info=True
            )
            if self.driver:
                self.driver.quit()
            self.driver = None
            return None


    def _search_tweets(self, search_url: Optional[str] = None) -> list:
        """
        Searches for tweets, scrolls to load more, and triggers extraction.
        
        Args:
            search_url: Optional custom search URL. If None, uses default Marikina flood query.
        
        Returns:
            List of extracted tweet dictionaries
        """
        if search_url is None:
            date = datetime.now().strftime("%Y-%m-%d")
            search_url = f'https://x.com/search?q=%22Marikina%22%20(Baha%20OR%20Flood%20OR%20Ulan%20OR%20Rain%20OR%20pagbaha%20OR%20%22heavy%20rain%22%20OR%20%22water%20level%22)%20since:2025-10-01&f=live'

        try:
            self.logger.debug(f"{self.agent_id} navigating to search URL")
            self.driver.get(search_url)
            
            # Wait for at least one tweet to appear
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='tweet']"))
            )
            self.logger.debug(f"{self.agent_id} search results loaded")
            
            # Scroll down to load more tweets from the dynamic feed
            self.logger.debug(f"{self.agent_id} scrolling to load more tweets")
            for i in range(3): # Scroll 3 times
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)

            tweet_elements = self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='tweet']")
            self.logger.info(f"{self.agent_id} found {len(tweet_elements)} tweet elements on page")
            
            extracted_tweets = [self._extract_tweet_data(t) for t in tweet_elements]
            return [t for t in extracted_tweets if t]  # Filter out None values

        except TimeoutException:
            self.logger.warning(
                f"{self.agent_id} no tweets found on page or page took too long to load"
            )
            return []
        except Exception as e:
            self.logger.error(
                f"{self.agent_id} error during tweet search: {e}",
                exc_info=True
            )
            return []

    def _extract_tweet_data(self, tweet_element):
        """
        Extracts detailed information from a single Selenium WebElement for a tweet.
        """
        try:
            data = {}
            # Extract username, text, timestamp, URL, and engagement metrics
            data['username'] = tweet_element.find_element(By.CSS_SELECTOR, "[data-testid='User-Name'] a").get_attribute('href').split('/')[-1]
            data['text'] = tweet_element.find_element(By.CSS_SELECTOR, "[data-testid='tweetText']").text
            time_element = tweet_element.find_element(By.CSS_SELECTOR, "time")
            data['timestamp'] = time_element.get_attribute('datetime')
            data['url'] = time_element.find_element(By.XPATH, "..").get_attribute('href')
            
            # Engagement metrics can sometimes be absent
            try:
                data['replies'] = tweet_element.find_element(By.CSS_SELECTOR, "[data-testid='reply']").text or "0"
            except NoSuchElementException:
                data['replies'] = "0"
            try:
                data['retweets'] = tweet_element.find_element(By.CSS_SELECTOR, "[data-testid='retweet']").text or "0"
            except NoSuchElementException:
                data['retweets'] = "0"
            try:
                data['likes'] = tweet_element.find_element(By.CSS_SELECTOR, "[data-testid='like']").text or "0"
            except NoSuchElementException:
                data['likes'] = "0"
            
            return data
        except Exception:
            # This can happen with ads or other non-standard tweet elements
            return None

    def _add_new_tweets_to_master(self, new_tweets):
        """
        Adds new tweets to the master list, checking for duplicates.
        """
        newly_added = []
        for tweet in new_tweets:
            tweet_id = self._create_tweet_id(tweet)
            if tweet_id not in self.master_tweets:
                tweet['scraped_at'] = datetime.now().isoformat()
                tweet['tweet_id'] = tweet_id
                self.master_tweets[tweet_id] = tweet
                newly_added.append(tweet)
        
        if newly_added:
            self._save_master_tweets()
        return newly_added

    def _create_tweet_id(self, tweet_data):
        """
        Creates a unique ID for a tweet, prioritizing the ID from the URL.
        """
        # The most reliable ID is the numerical string at the end of the URL
        if tweet_data.get('url') and 'status' in tweet_data['url']:
            return tweet_data['url'].split('/status/')[-1]
        
        # Fallback to creating a hash if the URL is not available
        unique_string = f"{tweet_data.get('username', '')}_{tweet_data.get('text', '')}_{tweet_data.get('timestamp', '')}"
        return hashlib.md5(unique_string.encode('utf-8')).hexdigest()

    def _load_master_tweets(self) -> dict:
        """
        Loads the master tweet dictionary from the JSON file.
        
        Returns:
            Dictionary of tweets keyed by tweet ID
        """
        try:
            if os.path.exists(self.master_file):
                with open(self.master_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.logger.info(
                        f"{self.agent_id} loaded {len(data)} tweets from master file"
                    )
                    return data
            else:
                self.logger.info(
                    f"{self.agent_id} master file not found, will create new one"
                )
                return {}
        except (json.JSONDecodeError, IOError) as e:
            self.logger.error(
                f"{self.agent_id} error loading master file: {e}, starting fresh",
                exc_info=True
            )
            return {}

    def _save_master_tweets(self) -> None:
        """
        Saves the master tweet dictionary to a JSON file with a backup system.
        """
        backup_file = f"{self.master_file}.backup"
        try:
            # Create a backup of the existing file
            if os.path.exists(self.master_file):
                os.rename(self.master_file, backup_file)

            # Ensure the directory exists
            os.makedirs(os.path.dirname(self.master_file), exist_ok=True)

            # Write the new master file
            with open(self.master_file, 'w', encoding='utf-8') as f:
                json.dump(self.master_tweets, f, indent=2, ensure_ascii=False)
            
            # Remove the backup if the save was successful
            if os.path.exists(backup_file):
                os.remove(backup_file)
            
            self.logger.debug(
                f"{self.agent_id} saved {len(self.master_tweets)} tweets to master file"
            )
        except Exception as e:
            self.logger.error(
                f"{self.agent_id} error saving master file: {e}, restoring from backup",
                exc_info=True
            )
            # Restore the backup if something went wrong
            if os.path.exists(backup_file):
                os.rename(backup_file, self.master_file)

    def _save_cookies(self) -> None:
        """Saves the current session cookies to the defined session file path."""
        try:
            # MODIFIED: Uses the self.session_file path
            with open(self.session_file, 'wb') as f:
                pickle.dump(self.driver.get_cookies(), f)
            self.logger.info(f"{self.agent_id} session cookies saved to {self.session_file}")
        except Exception as e:
            self.logger.error(f"{self.agent_id} error saving cookies: {e}", exc_info=True)

    def _load_cookies(self) -> bool:
        """
        Loads session cookies from the defined session file path.
        
        Returns:
            True if cookies loaded successfully, False otherwise
        """
        # MODIFIED: Uses the self.session_file path
        if not os.path.exists(self.session_file):
            return False
        try:
            # MODIFIED: Uses the self.session_file path
            with open(self.session_file, 'rb') as f:
                cookies = pickle.load(f)
            self.driver.get("https://x.com")
            for cookie in cookies:
                self.driver.add_cookie(cookie)
            self.logger.info(f"{self.agent_id} session cookies loaded from {self.session_file}")
            return True
        except Exception as e:
            self.logger.error(f"{self.agent_id} error loading cookies: {e}", exc_info=True)
            return False

    def _verify_login_status(self) -> bool:
        """
        Verifies if the driver's session is currently logged in.
        
        Returns:
            True if session is valid, False otherwise
        """
        try:
            # FIX: Uses self.driver
            self.driver.get("https://x.com/home")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[aria-label='Home timeline']"))
            )
            self.logger.info(f"{self.agent_id} session is valid")
            return True
        except TimeoutException:
            self.logger.warning(f"{self.agent_id} session is invalid or expired")
            return False


    def _export_master_tweets_to_csv(self) -> None:
        """Exports the entire master tweet list to a timestamped CSV file."""
        if not self.master_tweets:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Ensure the directory exists
        output_dir = os.path.join("app", "data", "exports")
        os.makedirs(output_dir, exist_ok=True)
        csv_filename = os.path.join(output_dir, f"marikina_tweets_export_{timestamp}.csv")
        
        try:
            tweets_list = list(self.master_tweets.values())
            with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=tweets_list[0].keys())
                writer.writeheader()
                writer.writerows(tweets_list)
            self.logger.info(
                f"{self.agent_id} exported {len(tweets_list)} tweets to {csv_filename}"
            )
        except Exception as e:
            self.logger.error(f"{self.agent_id} error exporting to CSV: {e}", exc_info=True)